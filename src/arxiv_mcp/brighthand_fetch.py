"""Bright Hand - Bright Data Web Unlocker for justified gate bypass (opt-in, billed)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from arxiv_mcp.config import Settings, load_settings

log = logging.getLogger(__name__)

_UNLOCKER_URL = "https://api.brightdata.com/request"


def _api_token(settings: Settings) -> str | None:
    return (
        settings.brightdata_api_token
        or os.environ.get("ARXIV_MCP_BRIGHTDATA_API_TOKEN")
        or os.environ.get("BRIGHTDATA_API_TOKEN")
    )


def brighthand_configured(settings: Settings | None = None) -> bool:
    settings = settings or load_settings()
    return bool(_api_token(settings) and settings.brightdata_zone)


async def brighthand_fetch_markdown(
    url: str,
    *,
    settings: Settings | None = None,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Fetch public page as markdown via Bright Data Web Unlocker."""
    settings = settings or load_settings()
    token = _api_token(settings)
    zone = (settings.brightdata_zone or "").strip()
    if not token:
        return {"success": False, "error": "brightdata_api_token_missing"}
    if not zone:
        return {"success": False, "error": "brightdata_zone_missing"}
    if not url.strip().startswith("http"):
        return {"success": False, "error": "invalid_url"}

    payload: dict[str, Any] = {
        "zone": zone,
        "url": url.strip(),
        "format": "json",
        "method": "GET",
        "data_format": "markdown",
    }
    if extra_headers:
        payload["headers"] = extra_headers
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    timeout = float(settings.brightdata_timeout_seconds)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(_UNLOCKER_URL, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        return {"success": False, "error": f"brightdata_http_error: {exc}"}

    if resp.status_code == 401:
        return {"success": False, "error": "brightdata_unauthorized"}
    if resp.status_code >= 400:
        return {
            "success": False,
            "error": f"brightdata_http_{resp.status_code}",
            "detail": resp.text[:240],
        }

    text = resp.text
    content = text
    status_code: int | None = None
    try:
        data = resp.json()
        if isinstance(data, dict):
            status_code = data.get("status_code")
            if isinstance(data.get("body"), str):
                content = data["body"]
            elif isinstance(data.get("content"), str):
                content = data["content"]
    except ValueError:
        pass

    if status_code is not None and int(status_code) >= 400:
        return {
            "success": False,
            "error": f"brightdata_upstream_{status_code}",
        }

    content = (content or "").strip()
    if not content:
        return {"success": False, "error": "brightdata_empty_body"}

    return {
        "success": True,
        "content": content,
        "via": "brighthand",
        "provider": "brightdata_web_unlocker",
        "zone": zone,
        "unlocker_url": _UNLOCKER_URL,
    }
