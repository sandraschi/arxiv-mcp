"""Optional enrichment when user opts into ignore-botblocks (Jina, then Bright Hand)."""

from __future__ import annotations

import logging
from typing import Any

from arxiv_mcp.arxiv_html import jina_reader_fetch
from arxiv_mcp.brighthand_fetch import brighthand_fetch_markdown
from arxiv_mcp.config import Settings, load_settings
from arxiv_mcp.publication_auth_fetch import try_publication_for_url
from arxiv_mcp.publication_subscriptions import resolve_publication
from arxiv_mcp.runtime_settings import media_ignore_botblocks, media_use_brighthand

log = logging.getLogger(__name__)

_EXCERPT_CHARS = 480


def _content_text(raw: Any) -> str:
    if raw is None:
        return ""
    return str(raw).strip()


async def _try_jina(url: str, settings: Settings) -> dict[str, Any] | None:
    try:
        result = await jina_reader_fetch(url, settings=settings)
    except Exception as exc:  # noqa: BLE001
        log.debug("jina enrich failed for %s: %s", url, exc)
        return None
    if not result.get("success"):
        return None
    text = _content_text(result.get("content"))
    if not text:
        return None
    return {
        "enriched": True,
        "enriched_via": "jina",
        "enrich_attempted": True,
        "excerpt": text[:_EXCERPT_CHARS],
        "jina_url": result.get("jina_url"),
        "fetch_policy": "jina_reader_with_user_consent",
    }


async def _try_brighthand(url: str, settings: Settings) -> dict[str, Any] | None:
    if not media_use_brighthand(settings):
        return None
    try:
        result = await brighthand_fetch_markdown(url, settings=settings)
    except Exception as exc:  # noqa: BLE001
        log.debug("brighthand enrich failed for %s: %s", url, exc)
        return {"enrich_attempted": True, "enrich_error": str(exc), "brighthand_attempted": True}
    if not result.get("success"):
        return {
            "enrich_attempted": True,
            "enrich_error": result.get("error"),
            "brighthand_attempted": True,
        }
    text = _content_text(result.get("content"))
    if not text:
        return {"enrich_attempted": True, "enrich_error": "brighthand_empty", "brighthand_attempted": True}
    return {
        "enriched": True,
        "enriched_via": "brighthand",
        "enrich_attempted": True,
        "brighthand_attempted": True,
        "excerpt": text[:_EXCERPT_CHARS],
        "provider": result.get("provider"),
        "fetch_policy": "brightdata_unlocker_with_user_consent",
    }


async def enrich_snippet_hits(
    hits: list[dict[str, Any]],
    *,
    settings: Settings | None = None,
    force: bool | None = None,
) -> list[dict[str, Any]]:
    """When ignore-botblocks is on: Jina first, Bright Hand if justified and enabled."""
    settings = settings or load_settings()
    if force is None:
        if not media_ignore_botblocks(settings):
            return hits
    elif not force:
        return hits

    out: list[dict[str, Any]] = []
    for hit in hits:
        if not hit.get("snippet_only"):
            out.append(hit)
            continue
        url = str(hit.get("url") or "").strip()
        if not url.startswith("http"):
            out.append(hit)
            continue

        pub = resolve_publication(url, settings)
        if pub is not None:
            pub_result = await try_publication_for_url(url, settings=settings)
            if pub_result is not None:
                if pub_result.get("success"):
                    out.append(
                        {
                            **hit,
                            **{k: v for k, v in pub_result.items() if k != "content"},
                            "enrich_attempted": True,
                        }
                    )
                    continue
                out.append(
                    {
                        **hit,
                        **pub_result,
                        "enrich_attempted": True,
                        "publication_fetch_failed": True,
                    }
                )
                continue

        enriched = await _try_jina(url, settings)
        if enriched:
            out.append({**hit, **enriched})
            continue

        brighthand = await _try_brighthand(url, settings)
        if brighthand and brighthand.get("enriched"):
            out.append({**hit, **brighthand, "jina_failed": True})
            continue

        err_bits: dict[str, Any] = {"enrich_attempted": True, "jina_failed": True}
        if brighthand:
            err_bits.update(brighthand)
        else:
            err_bits["enrich_error"] = "jina_failed_brighthand_disabled"
        out.append({**hit, **err_bits})

    return out
