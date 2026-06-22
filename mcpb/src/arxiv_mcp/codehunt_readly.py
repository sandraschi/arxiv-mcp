"""Readly cross-connect for code-hunt media traction."""

from __future__ import annotations

import logging
from typing import Any

from arxiv_mcp.config import Settings, load_settings
from arxiv_mcp.readly_client import (
    assert_readly_usable,
    readly_enabled,
    readly_hits_for_media,
    readly_match_content,
)

log = logging.getLogger(__name__)


async def probe_readly_for_paper(
    *,
    paper_id: str,
    title: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Search readly-mcp watch magazines for coverage related to an arXiv paper."""
    settings = settings or load_settings()
    if not readly_enabled(settings):
        return {"success": True, "skipped": True, "reason": "readly_disabled", "hits": []}

    block = assert_readly_usable(settings)
    if block is not None:
        return {
            "success": False,
            "skipped": False,
            "hits": [],
            "readly_error": block,
            "silent_failure": False,
        }

    query = f"{title} {paper_id}"
    match = await readly_match_content(query, settings=settings)
    if not match.get("success"):
        return {
            "success": False,
            "hits": [],
            "readly_error": match,
            "silent_failure": False,
        }

    hits = readly_hits_for_media(query, match)
    return {
        "success": True,
        "hits": hits,
        "readly_match_count": match.get("count", 0),
        "magazines_searched": match.get("magazines_searched"),
    }
