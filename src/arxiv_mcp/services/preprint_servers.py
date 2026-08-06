"""Multi-server preprint search: bioRxiv, medRxiv, ChemRxiv, Research Square.

Each server exposes a unified ``search()`` function that returns ``list[Paper]``.
The ``search_all()`` fan-out queries selected servers in parallel and merges
results deduplicated by DOI (or paper_id).
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request as _req
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Paper:
    """Unified preprint paper schema used by all server backends."""

    paper_id: str  # server-specific id (e.g. "2025.01.01.123456" for bioRxiv)
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    published: str | None  # ISO date string
    server: str  # "arxiv", "biorxiv", "medrxiv", "chemrxiv", "researchsquare"
    html_url: str | None
    pdf_url: str | None
    doi: str | None = None


# ── bioRxiv / medRxiv (Cold Spring Harbor Lab API) ──────────────────────────


def _biorxiv_date_filter(hours: int) -> str:
    """Return YYYY-MM-DD string for 'hours' ago."""
    from datetime import UTC, datetime, timedelta

    since = datetime.now(UTC) - timedelta(hours=hours)
    return since.strftime("%Y-%m-%d")


def search_biorxiv(
    query: str,
    server: str = "biorxiv",
    limit: int = 20,
    hours: int = 720,
) -> list[Paper]:
    """Search bioRxiv or medRxiv via their content API.

    The API returns summaries of recent articles. Keyword filtering is done
    client-side on title + abstract because the native API is content-dump only.
    """
    base = (
        "https://api.biorxiv.org/details/biorxiv" if server == "biorxiv" else "https://api.medrxiv.org/details/medrxiv"
    )

    results: list[Paper] = []
    query_lower = query.lower()

    # bioRxiv API uses date ranges: {base}/{from_date}/{to_date}/{cursor}
    to_date = time.strftime("%Y-%m-%d")
    from_date = _biorxiv_date_filter(hours)

    try:
        url = f"{base}/{from_date}/{to_date}/0"
        req = _req.Request(url, headers={"User-Agent": "arxiv-mcp/0.7.0"})  # noqa: S310
        with _req.urlopen(req, timeout=30) as resp:  # noqa: S310
            data = json.loads(resp.read().decode())
    except Exception as e:
        logger.warning("%s API error: %s", server, e)
        return results

    for item in data.get("collection", []):
        title = item.get("title", "")
        abstract = item.get("abstract", "")
        combined = f"{title} {abstract}".lower()
        if query_lower and query_lower not in combined and not all(w in combined for w in query_lower.split()):
            continue

        doi = item.get("doi", "")
        paper_id = doi or item.get("id", "")
        authors_raw = []
        if isinstance(item.get("authors"), dict):
            authors_raw = item["authors"].get("author", [])
        results.append(
            Paper(
                paper_id=paper_id,
                title=title,
                summary=abstract,
                authors=[a.get("author", "") for a in authors_raw],
                categories=["q-bio"] if server == "biorxiv" else ["q-med"],
                published=item.get("date"),
                server=server,
                html_url=f"https://www.{server}.org/content/10.1101/{doi}" if doi else None,
                pdf_url=f"https://www.{server}.org/content/10.1101/{doi}.full.pdf" if doi else None,
                doi=doi,
            )
        )
        if len(results) >= limit:
            break

    return results


def search_medrxiv(query: str, limit: int = 20, hours: int = 720) -> list[Paper]:
    """Search medRxiv (wrapper around bioRxiv API)."""
    return search_biorxiv(query, server="medrxiv", limit=limit, hours=hours)


# ── ChemRxiv / Research Square ──────────────────────────────────────────────


def search_chemrxiv(query: str, limit: int = 20, hours: int = 720) -> list[Paper]:
    """Search ChemRxiv via the Research Square API.

    ChemRxiv is hosted on the Research Square platform. The API is the same
    as researchsquare.com's preprint search.
    """
    return _search_research_square(query, "chemrxiv", limit, hours)


def search_research_square(query: str, limit: int = 20, hours: int = 720) -> list[Paper]:
    """Search Research Square preprints (multidisciplinary)."""
    return _search_research_square(query, "researchsquare", limit, hours)


def _search_research_square(query: str, server: str, limit: int, hours: int) -> list[Paper]:
    """Shared search for Research Square-hosted preprint servers."""
    results: list[Paper] = []

    try:
        params = {
            "query": query,
            "limit": str(min(limit, 50)),
            "sort": "date:desc",
            "server": server,
        }
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"https://api.researchsquare.com/v1/preprints?{qs}"
        req = _req.Request(url, headers={"User-Agent": "arxiv-mcp/0.7.0"})
        with _req.urlopen(req, timeout=30) as resp:  # noqa: S310
            data = json.loads(resp.read().decode())
    except Exception as e:
        logger.warning("%s API error: %s", server, e)
        return results

    for item in data.get("data", data.get("preprints", [])):
        doi = item.get("doi", "")
        title = item.get("title", "") or item.get("name", "")
        authors = []
        if isinstance(item.get("authors"), list):
            authors = [a.get("fullName", "") for a in item["authors"]]
        cats = item.get("categories") or [item.get("category", "general")]
        if not isinstance(cats, list):
            cats = [cats]
        domain = "chemrxiv.org" if server == "chemrxiv" else "researchsquare.com"
        results.append(
            Paper(
                paper_id=doi or item.get("id", ""),
                title=title,
                summary=item.get("abstract", "") or item.get("description", ""),
                authors=authors,
                categories=cats,
                published=item.get("publishedDate") or item.get("publicationDate"),
                server=server,
                html_url=f"https://www.{domain}/article/{doi}" if doi else None,
                pdf_url=f"https://www.{domain}/article/{doi}.pdf" if doi else None,
                doi=doi,
            )
        )
        if len(results) >= limit:
            break

    return results


# ── Fan-out search ────────────────────────────────────────────────────────────

SERVER_FUNCTIONS: dict[str, callable] = {
    "arxiv": None,  # handled by existing papers.py
    "biorxiv": search_biorxiv,
    "medrxiv": search_medrxiv,
    "chemrxiv": search_chemrxiv,
    "researchsquare": search_research_square,
}

SERVER_LABELS: dict[str, str] = {
    "arxiv": "arXiv",
    "biorxiv": "bioRxiv",
    "medrxiv": "medRxiv",
    "chemrxiv": "ChemRxiv",
    "researchsquare": "Research Square",
}


def search_all(
    query: str,
    servers: list[str] | None = None,
    limit: int = 20,
    hours: int = 720,
) -> dict[str, list[Paper]]:
    """Search selected preprint servers in parallel.

    Args:
        query: Search keywords.
        servers: List of server keys to search (default: all non-arxiv).
        limit: Max results per server.
        hours: Lookback window.

    Returns:
        Dict mapping server key to its list of results.
    """
    import concurrent.futures

    if servers is None:
        servers = ["biorxiv", "medrxiv", "chemrxiv", "researchsquare"]

    results: dict[str, list[Paper]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        future_map = {}
        for srv in servers:
            fn = SERVER_FUNCTIONS.get(srv)
            if fn:
                future_map[pool.submit(fn, query, limit, hours)] = srv

        for future in concurrent.futures.as_completed(future_map):
            srv = future_map[future]
            try:
                results[srv] = future.result()
            except Exception as e:
                logger.error("%s search failed: %s", srv, e)
                results[srv] = []

    return results


def merge_results(results: dict[str, list[Paper]], total_limit: int = 50) -> list[Paper]:
    """Merge multi-server results, deduplicating by DOI + paper_id.

    Results are interleaved: one paper from each server in round-robin
    to avoid one server dominating the result list.
    """
    seen: set[str] = set()
    merged: list[Paper] = []

    # Round-robin interleave
    all_papers = list(results.values())
    max_len = max((len(p) for p in all_papers), default=0)

    for i in range(max_len):
        for srv_papers in all_papers:
            if i < len(srv_papers):
                p = srv_papers[i]
                key = p.doi or p.paper_id
                if key and key not in seen:
                    seen.add(key)
                    merged.append(p)
                    if len(merged) >= total_limit:
                        return merged

    return merged
