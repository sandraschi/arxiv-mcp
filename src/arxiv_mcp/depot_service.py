"""Orchestrate HTML fetch + corpus ingest for REST/MCP."""

from __future__ import annotations

from typing import Any

from arxiv_mcp.html_extract import fetch_html_markdown
from arxiv_mcp.services import corpus, papers


async def ingest_paper_html(paper_id: str) -> dict[str, Any]:
    """Fetch experimental HTML and ingest into depot (chunks + FTS)."""
    meta = await papers.get_paper_details(paper_id)
    aid = meta.paper_id
    ok, payload, status, ctype = await fetch_html_markdown(aid)
    if not ok:
        return {
            "success": False,
            "error": payload,
            "arxiv_id": aid,
            "http_status": status,
            "content_type": ctype,
        }
    rec = corpus.ingest_markdown(
        aid,
        meta.title,
        payload,
        source="html",
        meta={"authors": meta.authors, "categories": meta.categories},
    )
    return {"success": True, "arxiv_id": aid, "title": meta.title, **rec}
