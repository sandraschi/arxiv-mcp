"""Shared arXiv + Semantic Scholar access for tools and REST API."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import arxiv
import httpx

from arxiv_mcp.config import Settings, load_settings
from arxiv_mcp.ids import normalize_arxiv_id


@dataclass
class PaperSummary:
    paper_id: str
    title: str
    authors: list[str]
    summary: str
    categories: list[str]
    published: str | None
    updated: str | None
    pdf_url: str | None
    abs_url: str | None
    html_url: str | None


def _sort_key(name: str) -> arxiv.SortCriterion:
    mapping = {
        "relevance": arxiv.SortCriterion.Relevance,
        "submitted": arxiv.SortCriterion.SubmittedDate,
        "updated": arxiv.SortCriterion.LastUpdatedDate,
    }
    return mapping.get(name.lower(), arxiv.SortCriterion.SubmittedDate)


def _client(settings: Settings) -> arxiv.Client:
    return arxiv.Client(delay_seconds=settings.client_delay_seconds, page_size=50)


def build_query(base: str, categories: list[str] | None) -> str:
    q = base.strip() or "all:*"
    if not categories:
        return q
    cat_expr = " OR ".join(f"cat:{c.strip()}" for c in categories if c.strip())
    if not cat_expr:
        return q
    return f"({q}) AND ({cat_expr})"


async def search_papers(
    query: str,
    *,
    categories: list[str] | None = None,
    limit: int = 10,
    sort_by: str = "submitted",
    settings: Settings | None = None,
) -> list[PaperSummary]:
    settings = settings or load_settings()
    q = build_query(query, categories)
    search = arxiv.Search(
        query=q,
        max_results=min(max(limit, 1), 100),
        sort_by=_sort_key(sort_by),
    )

    def _run() -> list[PaperSummary]:
        out: list[PaperSummary] = []
        for r in _client(settings).results(search):
            pid = r.get_short_id()
            out.append(
                PaperSummary(
                    paper_id=pid,
                    title=r.title,
                    authors=[a.name for a in r.authors],
                    summary=r.summary.strip(),
                    categories=[c.term for c in r.categories],
                    published=r.published.isoformat() if r.published else None,
                    updated=r.updated.isoformat() if r.updated else None,
                    pdf_url=str(r.pdf_url) if r.pdf_url else None,
                    abs_url=str(r.entry_id) if r.entry_id else None,
                    html_url=f"https://arxiv.org/html/{pid}",
                )
            )
            if len(out) >= limit:
                break
        return out

    return await asyncio.to_thread(_run)


async def get_paper_details(
    paper_id: str,
    *,
    settings: Settings | None = None,
) -> PaperSummary:
    settings = settings or load_settings()
    aid = normalize_arxiv_id(paper_id)
    search = arxiv.Search(id_list=[aid])

    def _run() -> PaperSummary:
        it = _client(settings).results(search)
        try:
            r = next(it)
        except StopIteration as e:
            raise LookupError(f"No arXiv record for id {aid!r}") from e
        pid = r.get_short_id()
        return PaperSummary(
            paper_id=pid,
            title=r.title,
            authors=[a.name for a in r.authors],
            summary=r.summary.strip(),
            categories=[c.term for c in r.categories],
            published=r.published.isoformat() if r.published else None,
            updated=r.updated.isoformat() if r.updated else None,
            pdf_url=str(r.pdf_url) if r.pdf_url else None,
            abs_url=str(r.entry_id) if r.entry_id else None,
            html_url=f"https://arxiv.org/html/{pid}",
        )

    return await asyncio.to_thread(_run)


async def list_category_latest(
    category: str,
    *,
    limit: int = 25,
    hours: int = 24,
    settings: Settings | None = None,
) -> list[PaperSummary]:
    """Return recent papers in a category, filtered to roughly the last ``hours``."""
    settings = settings or load_settings()
    cat = category.strip()
    if not cat:
        raise ValueError("category is required")
    # Pull a wider window then filter by published time (API lacks hour-precision filters).
    search = arxiv.Search(
        query=f"cat:{cat}",
        max_results=min(max(limit * 4, 20), 300),
        sort_by=arxiv.SortCriterion.SubmittedDate,
    )
    cutoff = datetime.now(tz=UTC) - timedelta(hours=hours)

    def _run() -> list[PaperSummary]:
        out: list[PaperSummary] = []
        for r in _client(settings).results(search):
            pub = r.published
            if pub is not None and pub.tzinfo is None:
                pub = pub.replace(tzinfo=UTC)
            if pub is not None and pub < cutoff:
                continue
            pid = r.get_short_id()
            out.append(
                PaperSummary(
                    paper_id=pid,
                    title=r.title,
                    authors=[a.name for a in r.authors],
                    summary=r.summary.strip(),
                    categories=[c.term for c in r.categories],
                    published=r.published.isoformat() if r.published else None,
                    updated=r.updated.isoformat() if r.updated else None,
                    pdf_url=str(r.pdf_url) if r.pdf_url else None,
                    abs_url=str(r.entry_id) if r.entry_id else None,
                    html_url=f"https://arxiv.org/html/{pid}",
                )
            )
            if len(out) >= limit:
                break
        return out

    return await asyncio.to_thread(_run)


async def find_connected_papers(
    paper_id: str,
    *,
    limit: int = 12,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Resolve citations + references via Semantic Scholar (arXiv lineage)."""
    aid = normalize_arxiv_id(paper_id)
    ss_aid = re.sub(r"v\d+$", "", aid, flags=re.IGNORECASE)
    key = api_key or ""
    headers: dict[str, str] = {}
    if key:
        headers["x-api-key"] = key
    fields = "title,year,externalIds,url"
    cite_fields = f"citations.{fields}"
    ref_fields = f"references.{fields}"
    url = (
        "https://api.semanticscholar.org/graph/v1/paper/"
        f"ARXIV:{ss_aid}"
        f"?fields={fields},{cite_fields},{ref_fields}"
    )
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.get(url, headers=headers)
    if resp.status_code == 404:
        return {
            "found": False,
            "message": "Paper not in Semantic Scholar graph (yet).",
            "arxiv_id": aid,
            "semantic_scholar_lookup_id": ss_aid,
        }
    resp.raise_for_status()
    data = resp.json()

    def _pick_papers(bucket: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for item in data.get(bucket, []) or []:
            if not isinstance(item, dict):
                continue
            p = item.get("paper") or item.get("citingPaper") or item.get("citedPaper") or item
            if not isinstance(p, dict):
                continue
            eid = (p.get("externalIds") or {}).get("ArXiv")
            out.append(
                {
                    "title": p.get("title"),
                    "year": p.get("year"),
                    "arxiv": eid,
                    "url": p.get("url"),
                }
            )
            if len(out) >= limit:
                break
        return out

    return {
        "found": True,
        "arxiv_id": aid,
        "semantic_scholar_lookup_id": ss_aid,
        "title": data.get("title"),
        "year": data.get("year"),
        "citations": _pick_papers("citations"),
        "references": _pick_papers("references"),
    }


def paper_summary_to_dict(p: PaperSummary) -> dict[str, Any]:
    return {
        "paper_id": p.paper_id,
        "title": p.title,
        "authors": p.authors,
        "summary": p.summary,
        "categories": p.categories,
        "published": p.published,
        "updated": p.updated,
        "pdf_url": p.pdf_url,
        "abs_url": p.abs_url,
        "html_url": p.html_url,
    }
