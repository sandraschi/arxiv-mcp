"""CLI: stdio (Cursor) / daemon-proxy (opencode) / HTTP server (FastAPI + MCP)."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

import httpx
import uvicorn

from arxiv_mcp.config import load_settings
from arxiv_mcp.server import mcp

_DEFAULT_API_URL = "http://127.0.0.1:10770/mcp"


def _configure_logging(*, debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stderr,
    )


def _probe_daemon(api_url: str) -> bool:
    """Probe the HTTP daemon. If alive, we become a lightweight proxy."""
    try:
        r = httpx.post(
            api_url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "probe", "version": "1"},
                },
            },
            headers={"Accept": "application/json, text/event-stream"},
            timeout=3,
        )
        return r.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="arxiv-mcp (FastMCP 3.1)")
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Run FastAPI on ARXIV_MCP_HOST:ARXIV_MCP_PORT with MCP mounted at /mcp",
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Run MCP over stdio (default when --serve is not passed)",
    )
    parser.add_argument("--debug", action="store_true", help="Verbose logs (stderr only)")
    args = parser.parse_args()
    _configure_logging(debug=args.debug)

    transport = os.getenv("MCP_TRANSPORT", "").lower()
    use_http = args.serve or transport in {"http", "streamable"}

    if use_http and args.stdio:
        parser.error("Choose either --serve or --stdio, not both.")

    settings = load_settings()

    if use_http:
        uvicorn.run(
            "arxiv_mcp.app:app",
            host=settings.host,
            port=settings.port,
            log_level="debug" if args.debug else "info",
        )
        return

    # Daemon-proxy: if HTTP daemon is already running, become a lightweight proxy
    api_url = os.getenv("ARXIV_MCP_API_URL", _DEFAULT_API_URL)
    if _probe_daemon(api_url):
        from fastmcp.server import create_proxy

        proxy = create_proxy(api_url, name="arxiv-mcp")
        asyncio.run(proxy.run_stdio_async(show_banner=False))
        return

    asyncio.run(mcp.run_stdio_async(show_banner=False))


if __name__ == "__main__":
    main()
