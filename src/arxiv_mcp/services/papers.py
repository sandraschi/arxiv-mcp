"""Shared arXiv + Semantic Scholar access for tools and REST API."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import arxiv

from arxiv_mcp.config import Settings, load_settings
from arxiv_mcp.http import get_text
from arxiv_mcp.http_policy import ArxivApiFailure, apply_arxiv_user_agent, arxiv_retry
from arxiv_mcp.ids import normalize_arxiv_id
from arxiv_mcp.sanitize import sanitize_text


def _arxiv_result_categories(r: object) -> list[str]:
    """arxiv 2.x uses ``list[str]`` on ``Result.categories``; older code expected objects with ``.term``."""
    cats = getattr(r, "categories", None) or []
    if not cats:
        return []
    first = cats[0]
    if isinstance(first, str):
        return list(cats)
    return [getattr(c, "term", str(c)) for c in cats]


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
    client = arxiv.Client(
        delay_seconds=settings.client_delay_seconds,
        page_size=50,
        num_retries=0,
    )
    apply_arxiv_user_agent(client)
    return client


def _result_to_summary(r: object) -> PaperSummary:
    pid = r.get_short_id()
    return PaperSummary(
        paper_id=pid,
        title=sanitize_text(r.title),
        authors=[sanitize_text(a.name) for a in r.authors],
        summary=sanitize_text(r.summary),
        categories=_arxiv_result_categories(r),
        published=r.published.isoformat() if r.published else None,
        updated=r.updated.isoformat() if r.updated else None,
        pdf_url=str(r.pdf_url) if r.pdf_url else None,
        abs_url=str(r.entry_id) if r.entry_id else None,
        html_url=f"https://arxiv.org/html/{pid}",
    )


def _raise_if_error(result: PaperSummary | list[PaperSummary] | dict[str, Any]) -> PaperSummary | list[PaperSummary]:
    if isinstance(result, dict) and result.get("success") is False:
        raise ArxivApiFailure(result)
    return result


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

    def _run() -> list[PaperSummary] | dict[str, Any]:
        def _inner() -> list[PaperSummary]:
            out: list[PaperSummary] = []
            for r in _client(settings).results(search):
                out.append(_result_to_summary(r))
                if len(out) >= limit:
                    break
            return out

        return arxiv_retry(settings, _inner)

    return _raise_if_error(await asyncio.to_thread(_run))


async def get_paper_details(
    paper_id: str,
    *,
    settings: Settings | None = None,
) -> PaperSummary:
    settings = settings or load_settings()
    aid = normalize_arxiv_id(paper_id)
    search = arxiv.Search(id_list=[aid])

    def _run() -> PaperSummary | dict[str, Any]:
        def _inner() -> PaperSummary:
            it = _client(settings).results(search)
            try:
                r = next(it)
            except StopIteration as e:
                raise LookupError(f"No arXiv record for id {aid!r}") from e
            return _result_to_summary(r)

        return arxiv_retry(settings, _inner)

    return _raise_if_error(await asyncio.to_thread(_run))


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
    search = arxiv.Search(
        query=f"cat:{cat}",
        max_results=min(max(limit * 4, 20), 300),
        sort_by=arxiv.SortCriterion.SubmittedDate,
    )
    cutoff = datetime.now(tz=UTC) - timedelta(hours=hours)

    def _run() -> list[PaperSummary] | dict[str, Any]:
        def _inner() -> list[PaperSummary]:
            out: list[PaperSummary] = []
            for r in _client(settings).results(search):
                pub = r.published
                if pub is not None and pub.tzinfo is None:
                    pub = pub.replace(tzinfo=UTC)
                if pub is not None and pub < cutoff:
                    continue
                out.append(_result_to_summary(r))
                if len(out) >= limit:
                    break
            return out

        return arxiv_retry(settings, _inner)

    return _raise_if_error(await asyncio.to_thread(_run))


_ARXIV_ID_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})(?:v\d+)?", re.IGNORECASE)
_BARE_ARXIV_RE = re.compile(r"\b([0-9]{4}\.[0-9]{4,5})(?:v\d+)?\b")


def _extract_arxiv_id(*candidates: object) -> str | None:
    """Pull a bare arXiv id (no version) out of URLs / ids / free text."""
    for cand in candidates:
        if not isinstance(cand, str) or not cand:
            continue
        m = _ARXIV_ID_RE.search(cand)
        if m:
            return m.group(1)
        if cand.startswith("arxiv:") or _BARE_ARXIV_RE.fullmatch(cand.strip()):
            m2 = _BARE_ARXIV_RE.search(cand)
            if m2:
                return m2.group(1)
    return None


def _openalex_work_to_item(work: dict[str, Any]) -> dict[str, Any]:
    """Normalize one OpenAlex work to the citation-graph item shape."""
    ids = work.get("ids") or {}
    primary = work.get("primary_location") or {}
    best_oa = work.get("best_oa_location") or {}
    locations = work.get("locations") or []
    loc_urls = [primary.get("landing_page_url"), primary.get("pdf_url"), best_oa.get("landing_page_url")]
    for loc in locations:
        if isinstance(loc, dict):
            loc_urls.append(loc.get("landing_page_url"))
            loc_urls.append(loc.get("pdf_url"))
    arxiv_id = _extract_arxiv_id(
        ids.get("arxiv"),
        work.get("doi"),
        work.get("id"),
        *loc_urls,
    )
    url = primary.get("landing_page_url") or best_oa.get("landing_page_url") or work.get("doi")
    if isinstance(url, str) and url.startswith("https://doi.org/"):
        pass  # keep DOI URL when no landing page
    return {
        "title": sanitize_text(str(work.get("title") or work.get("display_name") or "")),
        "year": work.get("publication_year"),
        "arxiv": arxiv_id,
        "url": url if isinstance(url, str) else None,
        "openalex_id": work.get("id"),
        "cited_by_count": work.get("cited_by_count"),
    }


async def _fetch_openalex_graph(
    ss_aid: str,
    aid: str,
    *,
    limit: int,
    settings: Settings,
) -> dict[str, Any]:
    """Resolve citation lineage via OpenAlex (no key required)."""
    from urllib.parse import quote, urlencode

    base = (settings.openalex_base_url or "https://api.openalex.org").rstrip("/")
    mailto = (settings.openalex_mailto or "").strip()
    suffix = f"?mailto={quote(mailto)}" if mailto else ""

    work_url = f"{base}/works/https://arxiv.org/abs/{ss_aid}{suffix}"
    work_payload = await get_text(
        work_url,
        settings=settings,
        cache_endpoint="openalex",
        accept="application/json",
        use_cache=True,
    )
    if not work_payload.ok or not work_payload.text:
        return {
            "found": False,
            "success": False,
            "source": "openalex",
            "arxiv_id": aid,
            "error": (work_payload.error or {}).get(
                "error", f"OpenAlex lookup failed (HTTP {work_payload.status_code})."
            ),
            "error_type": "OpenAlexUnavailable",
            "http_status": work_payload.status_code,
        }
    try:
        work = json.loads(work_payload.text)
    except (ValueError, TypeError) as exc:
        return {
            "found": False,
            "success": False,
            "source": "openalex",
            "arxiv_id": aid,
            "error": f"OpenAlex response was not JSON: {exc}",
            "error_type": "OpenAlexUnavailable",
        }
    if not isinstance(work, dict) or work.get("id") is None:
        return {
            "found": False,
            "success": False,
            "source": "openalex",
            "arxiv_id": aid,
            "error": "Paper not in OpenAlex graph (yet).",
            "error_type": "OpenAlexNotFound",
        }

    openalex_id = str(work.get("id"))
    short_oa_id = openalex_id.rsplit("/", 1)[-1]
    select = "id,title,display_name,publication_year,doi,primary_location,best_oa_location,locations,ids,cited_by_count"

    citations: list[dict[str, Any]] = []
    cites_url = (
        f"{base}/works?{urlencode({'filter': f'cites:{openalex_id}', 'per-page': max(limit, 1), 'select': select, 'sort': 'cited_by_count:desc'})}"
        + (f"&mailto={quote(mailto)}" if mailto else "")
    )
    cites_payload = await get_text(
        cites_url, settings=settings, cache_endpoint="openalex", accept="application/json", use_cache=True
    )
    if cites_payload.ok and cites_payload.text:
        try:
            cites_data = json.loads(cites_payload.text)
            for item in (cites_data.get("results") or [])[:limit]:
                if isinstance(item, dict):
                    citations.append(_openalex_work_to_item(item))
        except (ValueError, TypeError, AttributeError):
            pass  # partial graph is still useful; references below may succeed

    references: list[dict[str, Any]] = []
    ref_ids = [r for r in (work.get("referenced_works") or []) if isinstance(r, str)][: max(limit, 1)]
    if ref_ids:
        refs_url = (
            f"{base}/works?{urlencode({'filter': f'openalex:{"|".join(r.rsplit("/", 1)[-1] for r in ref_ids)}', 'per-page': len(ref_ids), 'select': select})}"
            + (f"&mailto={quote(mailto)}" if mailto else "")
        )
        refs_payload = await get_text(
            refs_url, settings=settings, cache_endpoint="openalex", accept="application/json", use_cache=True
        )
        if refs_payload.ok and refs_payload.text:
            try:
                refs_data = json.loads(refs_payload.text)
                by_id = {str(r.get("id")): r for r in (refs_data.get("results") or []) if isinstance(r, dict)}
                for rid in ref_ids:  # preserve original reference order
                    item = by_id.get(rid)
                    if isinstance(item, dict):
                        references.append(_openalex_work_to_item(item))
                    if len(references) >= limit:
                        break
            except (ValueError, TypeError, AttributeError):
                pass

    return {
        "found": True,
        "source": "openalex",
        "arxiv_id": aid,
        "openalex_id": openalex_id,
        "openalex_short_id": short_oa_id,
        "title": sanitize_text(str(work.get("title") or work.get("display_name") or "")),
        "year": work.get("publication_year"),
        "cited_by_count": work.get("cited_by_count"),
        "citations": citations[:limit],
        "references": references[:limit],
    }


async def find_connected_papers(
    paper_id: str,
    *,
    limit: int = 12,
    api_key: str | None = None,
    fallback_openalex: bool = True,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Resolve citations + references via Semantic Scholar, with OpenAlex fallback.

    Transparent for callers: Semantic Scholar is tried first (it has the
    richest citation contexts). On HTTP 429 / 5xx / timeout / 404 — or any
    transport failure — the lookup silently falls back to OpenAlex, which
    needs no API key. The returned envelope always carries ``source``
    (``semantic_scholar`` or ``openalex``) and ``fallback_used`` so agents
    and UI can display provenance without branching on errors.
    """
    aid = normalize_arxiv_id(paper_id)
    ss_aid = re.sub(r"v\d+$", "", aid, flags=re.IGNORECASE)
    key = api_key or ""
    settings = settings or load_settings()
    use_fallback = bool(fallback_openalex) and bool(settings.citation_fallback_enabled)
    fields = "title,year,externalIds,url"
    cite_fields = f"citations.{fields}"
    ref_fields = f"references.{fields}"
    url = f"https://api.semanticscholar.org/graph/v1/paper/ARXIV:{ss_aid}?fields={fields},{cite_fields},{ref_fields}"
    ss_headers = {"x-api-key": key} if key else None
    try:
        payload = await get_text(
            url,
            settings=settings,
            cache_endpoint="semantic_scholar",
            accept="application/json",
            extra_headers=ss_headers,
            use_cache=not bool(key),
        )
    except Exception:
        payload = None
    if payload is not None and payload.ok and payload.text is not None:
        data = json.loads(payload.text)

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
                        "title": sanitize_text(p.get("title", "")),
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
            "source": "semantic_scholar",
            "fallback_used": False,
            "arxiv_id": aid,
            "semantic_scholar_lookup_id": ss_aid,
            "title": sanitize_text(data.get("title", "")),
            "year": data.get("year"),
            "citations": _pick_papers("citations"),
            "references": _pick_papers("references"),
        }

    if payload is None:
        ss_status: int | None = None
        ss_error = "Citation lookup transport failed."
    else:
        ss_status = payload.status_code
        if ss_status == 404 and not use_fallback:
            return {
                "found": False,
                "success": True,
                "source": "semantic_scholar",
                "fallback_used": False,
                "message": "Paper not in Semantic Scholar graph (yet).",
                "arxiv_id": aid,
                "semantic_scholar_lookup_id": ss_aid,
            }
        if ss_status == 429 and not use_fallback:
            return {
                "found": False,
                "success": False,
                "source": "semantic_scholar",
                "fallback_used": False,
                "error": "Semantic Scholar rate limit (HTTP 429).",
                "error_type": "SemanticScholarRateLimit",
                "arxiv_id": aid,
                "recovery_options": [
                    "Set ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY for higher rate limits.",
                    "Retry after a short delay.",
                ],
            }
        err = payload.error or {}
        ss_error = str(err.get("error") or f"Semantic Scholar lookup failed (HTTP {ss_status}).")

    if use_fallback:
        try:
            oa_graph = await _fetch_openalex_graph(ss_aid, aid, limit=limit, settings=settings)
        except Exception as exc:
            oa_graph = {
                "found": False,
                "success": False,
                "source": "openalex",
                "arxiv_id": aid,
                "error": f"OpenAlex fallback failed: {exc}",
                "error_type": "OpenAlexUnavailable",
            }
        if oa_graph.get("found"):
            oa_graph["fallback_used"] = True
            oa_graph["semantic_scholar_status"] = ss_status
            oa_graph["semantic_scholar_error"] = ss_error
            oa_graph["notice"] = (
                "Semantic Scholar unavailable "
                f"(HTTP {ss_status}); served transparently from OpenAlex (no key required)."
            )
            return oa_graph
        return {
            "found": False,
            "success": False,
            "source": "openalex",
            "fallback_used": True,
            "error": "Citation graph unavailable from Semantic Scholar and OpenAlex.",
            "error_type": "CitationGraphUnavailable",
            "arxiv_id": aid,
            "semantic_scholar_status": ss_status,
            "semantic_scholar_error": ss_error,
            "openalex_error": oa_graph.get("error"),
            "recovery_options": [
                "Retry after a short delay (both providers rate-limit).",
                "Set ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY for higher S2 limits.",
                "Check https://status.api.semanticscholar.org/ for S2 incidents.",
            ],
        }

    status = ss_status
    if status == 404:
        return {
            "found": False,
            "message": "Paper not in Semantic Scholar graph (yet).",
            "arxiv_id": aid,
            "semantic_scholar_lookup_id": ss_aid,
        }
    if status == 429:
        return {
            "found": False,
            "success": False,
            "error": "Semantic Scholar rate limit (HTTP 429).",
            "error_type": "SemanticScholarRateLimit",
            "arxiv_id": aid,
            "recovery_options": [
                "Set ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY for higher rate limits.",
                "Retry after a short delay.",
            ],
        }
    return {
        "found": False,
        "success": False,
        "arxiv_id": aid,
        **(payload.error or {} if payload else {}),
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
