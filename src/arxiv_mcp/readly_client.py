"""HTTP client for readly-mcp REST API (magazine full-text via subscriber session)."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx

from arxiv_mcp.config import Settings, load_settings

log = logging.getLogger(__name__)


def readly_base_url(settings: Settings | None = None) -> str | None:
    settings = settings or load_settings()
    url = (
        settings.readly_mcp_url
        or os.environ.get("ARXIV_MCP_READLY_MCP_URL")
        or os.environ.get("READLY_MCP_URL")
    )
    if not url:
        return None
    return url.rstrip("/")


def readly_enabled(settings: Settings | None = None) -> bool:
    settings = settings or load_settings()
    if not settings.readly_enabled:
        return False
    return bool(readly_base_url(settings))


def _parse_valid_till(settings: Settings) -> date | None:
    raw = settings.readly_valid_till or os.environ.get("ARXIV_MCP_READLY_VALID_TILL")
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw).strip()[:10])
    except ValueError:
        return None


def readly_subscription_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or load_settings()
    valid_till = _parse_valid_till(settings)
    today = datetime.now(UTC).date()
    base = readly_base_url(settings)
    if not settings.readly_enabled:
        status = "disabled"
    elif not base:
        status = "not_configured"
    elif valid_till is None:
        status = "credentials_incomplete"
    elif valid_till < today:
        status = "expired"
    elif (valid_till - today).days <= settings.publication_expiring_warn_days:
        status = "expiring_soon"
    else:
        status = "valid"
    return {
        "enabled": settings.readly_enabled,
        "status": status,
        "valid_till": valid_till.isoformat() if valid_till else None,
        "readly_mcp_url": base,
        "silent_failure": False,
    }


def assert_readly_usable(settings: Settings | None = None) -> dict[str, Any] | None:
    row = readly_subscription_status(settings)
    if row["status"] == "disabled":
        return None
    if row["status"] == "not_configured":
        return {
            "subscription_error": "readly_not_configured",
            "message": "Set ARXIV_MCP_READLY_MCP_URL and ARXIV_MCP_READLY_ENABLED=1",
            "silent_failure": False,
        }
    if row["status"] == "credentials_incomplete":
        return {
            "subscription_error": "readly_valid_till_missing",
            "message": "Set ARXIV_MCP_READLY_VALID_TILL (YYYY-MM-DD) — required for loud expiry",
            "silent_failure": False,
            "severity": "error",
        }
    if row["status"] == "expired":
        return {
            "subscription_error": "readly_subscription_expired",
            "publication": "readly",
            "publication_name": "Readly",
            "valid_till": row["valid_till"],
            "message": (
                f"Readly subscription expired on {row['valid_till']} — "
                "renew and update ARXIV_MCP_READLY_VALID_TILL"
            ),
            "silent_failure": False,
            "severity": "critical",
        }
    return None


def _manifest_path(settings: Settings) -> Path:
    if settings.readly_watch_magazines_file:
        return Path(settings.readly_watch_magazines_file)
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "config" / "readly_watch_magazines.json"
        if candidate.is_file():
            return candidate
    return here.parents[2] / "config" / "readly_watch_magazines.json"


def load_readly_watch_magazines(settings: Settings | None = None) -> list[dict[str, str]]:
    settings = settings or load_settings()
    path = _manifest_path(settings)
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, dict) and item.get("name"):
            out.append(
                {
                    "id": str(item.get("id") or item["name"]),
                    "name": str(item["name"]),
                    "readly_query": str(item.get("readly_query") or item["name"]),
                }
            )
    return out


async def readly_health(settings: Settings | None = None) -> dict[str, Any]:
    base = readly_base_url(settings)
    if not base:
        return {"ok": False, "error": "readly_url_missing"}
    timeout = float((settings or load_settings()).readly_timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{base}/api/health")
            if resp.status_code != 200:
                return {"ok": False, "error": f"health_http_{resp.status_code}"}
            data = resp.json()
            live = await client.get(f"{base}/api/pipeline/liveness")
            liveness = live.json() if live.status_code == 200 else {}
            return {"ok": True, "health": data, "liveness": liveness}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc)}


async def readly_match_content(
    query: str,
    *,
    settings: Settings | None = None,
    magazines: list[str] | None = None,
) -> dict[str, Any]:
    """Ask readly-mcp to search watch magazines for articles matching query."""
    settings = settings or load_settings()
    block = assert_readly_usable(settings)
    if block is not None:
        return {"success": False, **block}
    base = readly_base_url(settings)
    if not base:
        return {"success": False, "error": "readly_url_missing"}

    if magazines is None:
        magazines = [m["readly_query"] for m in load_readly_watch_magazines(settings)]

    timeout = float(settings.readly_timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base}/api/content/match",
                json={"query": query, "magazines": magazines, "max_per_magazine": 3},
            )
            if resp.status_code >= 400:
                return {
                    "success": False,
                    "error": f"readly_http_{resp.status_code}",
                    "detail": resp.text[:300],
                    "silent_failure": False,
                }
            return {"success": True, **resp.json()}
    except httpx.HTTPError as exc:
        return {"success": False, "error": f"readly_unreachable: {exc}", "silent_failure": False}


def readly_coverage_for_depot(match_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize readly content/match into depot meta_json readly_coverage records."""
    if not match_payload.get("success"):
        return []
    hits: list[dict[str, Any]] = []
    for item in match_payload.get("hits") or []:
        hits.append(
            {
                "magazine": item.get("magazine"),
                "title": item.get("title"),
                "url": item.get("url") or "",
                "match_score": item.get("match_score"),
                "issue_title": item.get("issue_title"),
                "source": "readly_mcp",
            }
        )
    return hits[:10]


async def fetch_readly_depot_coverage(
    title: str,
    *,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Query readly-mcp for magazine articles related to a depot paper title."""
    settings = settings or load_settings()
    if not readly_enabled(settings) or not settings.readly_ingest_on_depot:
        return []
    query = (title or "").strip()
    if not query:
        return []

    magazines = settings.parsed_readly_ingest_magazines()
    if not magazines:
        magazines = [m["readly_query"] for m in load_readly_watch_magazines(settings)]
    if not magazines:
        return []

    match = await readly_match_content(query, settings=settings, magazines=magazines)
    return readly_coverage_for_depot(match)


def readly_hits_for_media(query: str, match_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize readly content/match into media traction hit records."""
    if not match_payload.get("success"):
        return []
    hits: list[dict[str, Any]] = []
    for item in match_payload.get("hits") or []:
        hits.append(
            {
                "source": "readly",
                "outlet": item.get("magazine") or "Readly",
                "title": item.get("title"),
                "url": item.get("url") or "",
                "issue_title": item.get("issue_title"),
                "match_score": item.get("match_score"),
                "readly_article_index": item.get("index"),
                "full_text_via": "readly_mcp_subscriber_session",
                "snippet_only": False,
            }
        )
    return hits
