"""FastMCP 3.2 startup connectivity probes (fleet standard)."""

from __future__ import annotations

import importlib.util
import logging

import httpx

from arxiv_mcp.config import Settings, load_settings

log = logging.getLogger("arxiv_mcp.startup_probe")


async def run_startup_probes(settings: Settings | None = None) -> None:
    """Cheap dependency checks before MCP lifespan yields. Warn-only for network/RAG."""
    settings = settings or load_settings()
    await _probe_arxiv_reachability(settings)
    _probe_rag_dependencies(settings)
    _probe_data_dir(settings)


async def _probe_arxiv_reachability(settings: Settings) -> None:
    url = "https://arxiv.org/"
    timeout = min(5.0, settings.arxiv_http_timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.head(url)
        if resp.status_code < 500:
            log.info("STARTUP PROBE: arxiv.org OK (HTTP %s)", resp.status_code)
            return
        log.warning(
            "STARTUP PROBE: arxiv.org returned HTTP %s - discovery tools may fail until connectivity returns",
            resp.status_code,
        )
    except httpx.TimeoutException:
        log.warning(
            "STARTUP PROBE: arxiv.org timed out after %.0fs - discovery tools may fail (local depot still works)",
            timeout,
        )
    except Exception as exc:
        log.warning(
            "STARTUP PROBE: arxiv.org unreachable (%s: %s) - discovery tools may fail",
            type(exc).__name__,
            exc,
        )


def _probe_rag_dependencies(settings: Settings) -> None:
    if not settings.rag_enabled:
        log.info("STARTUP PROBE: RAG disabled (ARXIV_MCP_RAG_ENABLED=0)")
        return
    missing: list[str] = []
    for module in ("lancedb", "fastembed", "pyarrow"):
        if importlib.util.find_spec(module) is None:
            missing.append(module)
    if missing:
        log.warning(
            "STARTUP PROBE: RAG enabled but missing packages: %s"
            " - install with `uv sync --extra rag`; semantic/hybrid search will fall back to FTS",
            ", ".join(missing),
        )
        return
    log.info(
        "STARTUP PROBE: RAG deps OK (embedding model=%s)",
        settings.embedding_model,
    )


def _probe_data_dir(settings: Settings) -> None:
    root = settings.resolved_data_dir()
    log.info("STARTUP PROBE: depot data dir OK - %s", root)
