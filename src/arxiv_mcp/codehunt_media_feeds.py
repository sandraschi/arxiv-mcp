"""Tech-magazine RSS for media traction - syndication only, never publisher HTML scrape."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

import httpx
from defusedxml.ElementTree import fromstring as fromstring_xml

from arxiv_mcp.config import Settings, load_settings

log = logging.getLogger(__name__)

_ARXIV_ID_RE = re.compile(r"\d{4}\.\d{4,5}(?:v\d+)?", re.I)
_RSS_UA = "arxiv-mcp-codehunt/1.0 (RSS syndication reader; metadata-only; no article scrape)"

# Publishers that block bots - we only ever use their RSS/API surfaces, never fetch articles.
SNIPPET_ONLY_DOMAINS: frozenset[str] = frozenset(
    {
        "arstechnica.com",
        "www.arstechnica.com",
        "theverge.com",
        "www.theverge.com",
        "technologyreview.com",
        "www.technologyreview.com",
        "wired.com",
        "www.wired.com",
        "techcrunch.com",
        "spectrum.ieee.org",
    }
)


def _repo_config_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "config" / "codehunt_media_feeds.json"
        if candidate.is_file():
            return candidate
    return here.parents[2] / "config" / "codehunt_media_feeds.json"


def load_media_feeds(settings: Settings | None = None) -> list[dict[str, str]]:
    settings = settings or load_settings()
    paths: list[Path] = []
    if settings.codehunt_media_feeds_file:
        paths.append(Path(settings.codehunt_media_feeds_file))
    data_path = settings.resolved_data_dir() / "codehunt" / "media_feeds.json"
    if data_path.is_file():
        paths.append(data_path)
    paths.append(_repo_config_path())
    for path in paths:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, list):
            continue
        feeds: list[dict[str, str]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            feeds.append(
                {
                    "id": str(item.get("id") or url),
                    "outlet": str(item.get("outlet") or item.get("id") or "rss"),
                    "url": url,
                }
            )
        if feeds:
            return feeds
    return []


def _cache_path(settings: Settings) -> Path:
    p = settings.resolved_data_dir() / "codehunt" / "media_feed_cache.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _parse_rss_items(xml_text: str, *, feed_id: str, outlet: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    try:
        root = fromstring_xml(xml_text)
    except Exception:
        return entries
    for item in root.findall(".//item"):
        title = (item.findtext("title") or item.findtext("{*}title") or "").strip()
        link = (item.findtext("link") or item.findtext("{*}link") or "").strip()
        desc = (item.findtext("description") or item.findtext("{*}description") or "").strip()
        pub = (item.findtext("pubDate") or item.findtext("{*}pubDate") or "").strip()
        blob = f"{title} {link} {desc}".lower()
        entries.append(
            {
                "feed_id": feed_id,
                "outlet": outlet,
                "title": title,
                "url": link,
                "published": pub,
                "blob": blob,
                "arxiv_ids": list({m.group(0).lower() for m in _ARXIV_ID_RE.finditer(blob)}),
            }
        )
    return entries


async def refresh_media_feed_cache(
    *,
    settings: Settings | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Poll configured RSS feeds into a local JSON cache (metadata only)."""
    settings = settings or load_settings()
    cache_file = _cache_path(settings)
    ttl_s = max(1, int(settings.codehunt_media_feed_cache_hours)) * 3600
    if not force and cache_file.is_file():
        try:
            existing = json.loads(cache_file.read_text(encoding="utf-8"))
            if time.time() - float(existing.get("fetched_at") or 0) < ttl_s:
                return {
                    "success": True,
                    "cached": True,
                    "entries": len(existing.get("entries") or []),
                    "fetched_at": existing.get("fetched_at"),
                }
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

    feeds = load_media_feeds(settings)
    if not feeds:
        return {"success": True, "cached": False, "entries": 0, "feeds": 0}

    headers = {"User-Agent": _RSS_UA, "Accept": "application/rss+xml, application/xml, text/xml"}
    entries: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    timeout = float(settings.codehunt_media_timeout_seconds)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        for feed in feeds:
            try:
                resp = await client.get(feed["url"])
                if resp.status_code >= 400:
                    errors.append({"feed": feed["id"], "error": f"HTTP {resp.status_code}"})
                    continue
                entries.extend(
                    _parse_rss_items(
                        resp.text,
                        feed_id=feed["id"],
                        outlet=feed["outlet"],
                    )
                )
            except httpx.HTTPError as exc:
                errors.append({"feed": feed["id"], "error": str(exc)})

    payload = {
        "fetched_at": time.time(),
        "feeds_polled": len(feeds),
        "entries": entries,
        "errors": errors,
        "strategy": "rss_metadata_only",
    }
    cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "success": True,
        "cached": False,
        "entries": len(entries),
        "feeds": len(feeds),
        "errors": errors,
    }


def search_feed_cache(
    *,
    paper_id: str,
    title: str,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Match arXiv id / title tokens against cached RSS entries."""
    settings = settings or load_settings()
    cache_file = _cache_path(settings)
    if not cache_file.is_file():
        return []
    try:
        cache = json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    aid = paper_id.strip().lower()
    m = _ARXIV_ID_RE.search(aid)
    if m:
        aid = m.group(0).lower()
    title_words = [
        w for w in re.findall(r"[a-z0-9]{4,}", title.lower()) if w not in ("with", "from", "using", "paper", "model")
    ][:5]

    hits: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in cache.get("entries") or []:
        blob = str(entry.get("blob") or "")
        if aid and aid in (entry.get("arxiv_ids") or []):
            matched = True
        elif aid and aid in blob:
            matched = True
        elif "arxiv" in blob and title_words and any(w in blob for w in title_words[:3]):
            matched = True
        else:
            matched = False
        if not matched:
            continue
        url = str(entry.get("url") or "")
        if url in seen:
            continue
        seen.add(url)
        domain = ""
        if "://" in url:
            domain = url.split("/")[2].lower()
        hits.append(
            {
                "source": "tech_rss",
                "outlet": entry.get("outlet") or entry.get("feed_id"),
                "title": entry.get("title"),
                "url": url,
                "feed_id": entry.get("feed_id"),
                "snippet_only": True,
                "fetch_policy": "rss_metadata_only",
                "publisher_blocks_scrape": any(d in domain for d in SNIPPET_ONLY_DOMAINS),
            }
        )
    return hits[:8]
