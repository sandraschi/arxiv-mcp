"""Wikipedia research companion — page summaries, section content, and search.

Uses public Wikimedia REST API v1 and Action API (no API key required):
  - /api/rest_v1/page/summary/{title}  — page summary with thumbnail
  - /api/rest_v1/page/sections/{title} — page section structure
  - /w/api.php?action=opensearch       — search suggestions
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from arxiv_mcp.sanitize import sanitize_text

log = logging.getLogger("arxiv_mcp.wikipedia")

_WIKI_REST = "https://en.wikipedia.org/api/rest_v1"
_WIKI_ACTION = "https://en.wikipedia.org/w/api.php"
_TIMEOUT = 20.0
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def _clean(text: str) -> str:
    return sanitize_text(" ".join(text.split()))


def _slugify(title: str) -> str:
    return title.strip().replace(" ", "_")


async def fetch_wikipedia_summary(title: str) -> dict[str, Any]:
    """Fetch Wikipedia page summary via REST API v1.

    Returns page title, description, extract (~first paragraph), thumbnail,
    full URL, and a markdown-formatted page summary.
    """
    slug = _slugify(title)
    url = f"{_WIKI_REST}/page/summary/{slug}"
    timestamp = datetime.now(UTC).isoformat()

    async with httpx.AsyncClient(headers=_HEADERS, follow_redirects=True, timeout=_TIMEOUT) as client:
        try:
            r = await client.get(url)
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": f"Wikipedia API timeout after {_TIMEOUT}s",
                "title": title,
                "recovery_options": [
                    "Try a more specific page title.",
                    "Use search_wikipedia to find the correct title.",
                ],
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "title": title,
                "recovery_options": [
                    "Try a more specific page title.",
                    "Use search_wikipedia to find the correct title.",
                ],
            }

    if r.status_code == 404:
        return {
            "success": False,
            "error": "Page not found on Wikipedia",
            "title": title,
            "recovery_options": [
                "Use search_wikipedia to find the correct title.",
                "Check your spelling — titles are case-sensitive.",
            ],
        }
    if r.status_code != 200:
        return {
            "success": False,
            "error": f"Wikipedia HTTP {r.status_code}",
            "title": title,
            "recovery_options": ["Wikipedia API may be rate-limiting. Try again shortly."],
        }

    data = r.json()
    page_title = _clean(data.get("title", title))
    description = _clean(data.get("description", ""))
    extract = _clean(data.get("extract", ""))
    page_url = (
        data.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{slug}")
    )
    thumbnail = data.get("thumbnail", {}).get("source") if data.get("thumbnail") else None

    md = f"# {page_title}\n\n"
    if description:
        md += f"*{description}*\n\n"
    md += extract

    return {
        "success": True,
        "title": page_title,
        "description": description,
        "extract": extract,
        "url": page_url,
        "thumbnail": thumbnail,
        "markdown": md,
        "word_count": len(extract.split()),
        "fetch_timestamp": timestamp,
    }


async def search_wikipedia(query: str, limit: int = 10) -> dict[str, Any]:
    """Search Wikipedia via the opensearch Action API.

    Returns ranked results with title, description, and URL.
    """
    timestamp = datetime.now(UTC).isoformat()
    cap = min(max(limit, 1), 50)

    async with httpx.AsyncClient(headers=_HEADERS, timeout=_TIMEOUT) as client:
        try:
            r = await client.get(
                _WIKI_ACTION,
                params={
                    "action": "opensearch",
                    "search": query,
                    "limit": str(cap),
                    "namespace": "0",
                    "format": "json",
                },
            )
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query,
            }

    if r.status_code != 200:
        return {
            "success": False,
            "error": f"Wikipedia API HTTP {r.status_code}",
            "query": query,
        }

    data = r.json()
    if not isinstance(data, list) or len(data) < 4:
        return {
            "success": True,
            "query": query,
            "results": [],
            "count": 0,
        }

    titles = data[1] if len(data) > 1 else []
    descriptions = data[2] if len(data) > 2 else []
    urls = data[3] if len(data) > 3 else []

    results = []
    for i in range(min(len(titles), len(urls))):
        title = _clean(titles[i])
        page_url = urls[i] if i < len(urls) else f"https://en.wikipedia.org/wiki/{_slugify(title)}"
        desc = _clean(descriptions[i] if i < len(descriptions) else "")
        results.append({
            "title": title,
            "url": page_url,
            "description": desc,
        })

    return {
        "success": True,
        "query": query,
        "results": results,
        "count": len(results),
        "fetch_timestamp": timestamp,
    }


async def fetch_wikipedia_sections(title: str) -> dict[str, Any]:
    """Fetch the section structure of a Wikipedia page.

    Returns a tree of section titles and indices that can be used
    for targeted content retrieval.
    """
    slug = _slugify(title)
    url = f"{_WIKI_REST}/page/sections/{slug}"

    async with httpx.AsyncClient(headers=_HEADERS, follow_redirects=True, timeout=_TIMEOUT) as client:
        try:
            r = await client.get(url)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "title": title,
            }

    if r.status_code != 200:
        return {
            "success": False,
            "error": f"Wikipedia HTTP {r.status_code}",
            "title": title,
            "recovery_options": ["Try fetch_wikipedia_summary for the extract instead."],
        }

    data = r.json()
    sections: list[dict[str, Any]] = []
    for section in data if isinstance(data, list) else []:
        sec_title = _clean(section.get("line", ""))
        sec_id = section.get("id", "")
        sec_level = section.get("level", 0)
        if sec_title:
            sections.append({
                "id": sec_id,
                "title": sec_title,
                "level": sec_level,
                "anchor": section.get("anchor", ""),
            })

    return {
        "success": True,
        "title": title,
        "sections": sections,
        "count": len(sections),
    }
