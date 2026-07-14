"""Detect post-arXiv media traction (HN, Google News RSS, tech feeds) ~1 week after pub."""

from __future__ import annotations

import logging
import re
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote_plus

import httpx
from defusedxml.ElementTree import ParseError, fromstring

from arxiv_mcp.codehunt_media_enrich import enrich_snippet_hits
from arxiv_mcp.codehunt_media_feeds import search_feed_cache
from arxiv_mcp.codehunt_readly import probe_readly_for_paper
from arxiv_mcp.config import Settings, load_settings
from arxiv_mcp.runtime_settings import media_ignore_botblocks, media_use_brighthand

log = logging.getLogger(__name__)

_ARXIV_ID_RE = re.compile(r"\d{4}\.\d{4,5}(?:v\d+)?", re.I)
_HN_API = "https://hn.algolia.com/api/v1/search"
_GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"


def _parse_published_ts(published: str | None) -> float | None:
    if not published:
        return None
    try:
        dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.timestamp()
    except ValueError:
        return None


def _paper_age_days(published: str | None, *, now: float | None = None) -> float | None:
    ts = _parse_published_ts(published)
    if ts is None:
        return None
    now = now or time.time()
    return (now - ts) / 86400.0


def _normalize_arxiv_id(paper_id: str) -> str:
    raw = paper_id.strip()
    m = _ARXIV_ID_RE.search(raw)
    return m.group(0) if m else raw


async def _search_hackernews(client: httpx.AsyncClient, paper_id: str, title: str) -> list[dict[str, Any]]:
    aid = _normalize_arxiv_id(paper_id)
    hits: list[dict[str, Any]] = []
    for query in (aid, f"arxiv {aid}"):
        try:
            resp = await client.get(
                _HN_API,
                params={"query": query, "tags": "story", "hitsPerPage": 8},
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
        except (httpx.HTTPError, ValueError):
            continue
        for item in data.get("hits") or []:
            story_title = str(item.get("title") or "")
            url = str(item.get("url") or "")
            if aid.lower() not in story_title.lower() and aid.lower() not in url.lower():
                if "arxiv" not in url.lower():
                    continue
            hits.append(
                {
                    "source": "hackernews",
                    "title": story_title,
                    "url": url or f"https://news.ycombinator.com/item?id={item.get('objectID')}",
                    "points": item.get("points"),
                    "comments": item.get("num_comments"),
                }
            )
        if hits:
            break
    return hits[:5]


def _parse_google_news_rss(xml_text: str, *, paper_id: str, title: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    aid = _normalize_arxiv_id(paper_id).lower()
    title_words = [w for w in re.findall(r"[a-z0-9]{4,}", title.lower()) if w not in ("with", "from", "using")][:6]
    try:
        root = fromstring(xml_text)
    except ParseError:
        return hits
    for item in root.findall(".//item"):
        item_title = (item.findtext("title") or item.findtext("{*}title") or "").strip()
        link = (item.findtext("link") or item.findtext("{*}link") or "").strip()
        source_el = item.find("source")
        if source_el is None:
            source_el = item.find("{*}source")
        source_name = source_el.text.strip() if source_el is not None and source_el.text else ""
        blob = f"{item_title} {link}".lower()
        matched = (
            aid in blob
            or f"arxiv.org/abs/{aid}" in blob
            or ("arxiv" in blob and any(w in blob for w in title_words[:4]))
        )
        if not matched:
            continue
        hits.append(
            {
                "source": "google_news",
                "outlet": source_name or "news",
                "title": item_title,
                "url": link,
            }
        )
    return hits[:8]


async def _search_google_news(client: httpx.AsyncClient, paper_id: str, title: str) -> list[dict[str, Any]]:
    aid = _normalize_arxiv_id(paper_id)
    queries = [
        f"arxiv {aid}",
        f'"{title[:80]}" arxiv' if len(title) > 12 else f"arxiv {aid} AI",
    ]
    all_hits: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for q in queries:
        url = f"{_GOOGLE_NEWS_RSS}?q={quote_plus(q)}&hl=en-US&gl=US&ceid=US:en"
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                continue
            for hit in _parse_google_news_rss(resp.text, paper_id=paper_id, title=title):
                u = hit.get("url") or ""
                if u in seen_urls:
                    continue
                seen_urls.add(u)
                all_hits.append(hit)
        except httpx.HTTPError:
            continue
        if len(all_hits) >= 5:
            break
    return all_hits[:8]


async def probe_media_traction(
    *,
    paper_id: str,
    title: str,
    published: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Query HN + Google News + cached tech RSS for coverage of an arXiv paper."""
    settings = settings or load_settings()
    age = _paper_age_days(published)
    min_age = max(1, int(settings.codehunt_media_min_age_days))
    max_age = max(min_age + 1, int(settings.codehunt_media_max_age_days))
    if age is not None and age < min_age:
        return {
            "success": True,
            "skipped": True,
            "reason": f"paper_age_days={round(age, 1)} < min {min_age}",
            "hits": [],
            "media_signal": False,
        }
    if age is not None and age > max_age:
        return {
            "success": True,
            "skipped": True,
            "reason": f"paper_age_days={round(age, 1)} > max {max_age}",
            "hits": [],
            "media_signal": False,
        }

    rss_hits = search_feed_cache(paper_id=paper_id, title=title, settings=settings)
    ignore_blocks = media_ignore_botblocks(settings)
    if ignore_blocks and rss_hits:
        rss_hits = await enrich_snippet_hits(rss_hits, settings=settings)

    timeout = float(settings.codehunt_media_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        hn = await _search_hackernews(client, paper_id, title)
        news = await _search_google_news(client, paper_id, title)
    readly_result = await probe_readly_for_paper(paper_id=paper_id, title=title, settings=settings)
    readly_hits = readly_result.get("hits") or []
    if readly_result.get("readly_error"):
        log.warning(
            "Readly probe for %s: %s",
            paper_id,
            readly_result["readly_error"].get("message") or readly_result["readly_error"],
        )

    hits = hn + news + rss_hits + readly_hits
    return {
        "success": True,
        "skipped": False,
        "paper_id": paper_id,
        "paper_age_days": round(age, 1) if age is not None else None,
        "hits": hits,
        "media_signal": len(hits) > 0,
        "hackernews_count": len(hn),
        "news_count": len(news),
        "tech_rss_count": len(rss_hits),
        "readly_count": len(readly_hits),
        "readly_error": readly_result.get("readly_error"),
        "media_ignore_botblocks": ignore_blocks,
        "media_use_brighthand": media_use_brighthand(settings) if ignore_blocks else False,
        "fetch_policy": (
            "rss_metadata_jina_then_brighthand_unlocker"
            if ignore_blocks and media_use_brighthand(settings)
            else "rss_metadata_plus_optional_jina_reader"
            if ignore_blocks
            else "aggregators_and_rss_metadata_only"
        ),
    }
