"""AI lab blog fetcher — Anthropic, Google Research, Google DeepMind, Google AI.

Supported sources:
  Anthropic:       anthropic.com/research/<slug>   anthropic.com/news/<slug>
  Google Research: research.google/blog/<slug>
  Google DeepMind: deepmind.google/discover/blog/<slug>  (JS-heavy → Jina fallback)
  Google AI Blog:  blog.google/technology/ai/<slug>       (JS-heavy → Jina fallback)

JS-rendered sites (DeepMind, blog.google) fall back to Jina Reader automatically.
Set ARXIV_MCP_JINA_READER_BASE_URL to override the Jina base (default: https://r.jina.ai).

All returns: {success, source, title, published, summary, url, markdown, word_count, fetch_timestamp}
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger("arxiv_mcp.lab_blog")

_TIMEOUT = 25.0
_JINA_TIMEOUT = 40.0
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------

SOURCES: dict[str, dict[str, Any]] = {
    "anthropic": {
        "label": "Anthropic",
        "sections": {
            "research": "https://www.anthropic.com/research",
            "news": "https://www.anthropic.com/news",
        },
        "post_base": "https://www.anthropic.com",
        "js_heavy": False,
        "known_posts": {
            "model-welfare":          "research/exploring-model-welfare",
            "claude-character":       "research/claude-s-character",
            "alignment-faking":       "research/alignment-faking",
            "taking-ai-welfare-seriously": "research/taking-ai-welfare-seriously",
            "core-views":             "research/core-views-on-ai-safety",
            "claude-soul":            "research/claude-s-soul",
            "model-spec":             "research/model-specification",
            "interpretability-monosemanticity": "research/monosemanticity",
        },
    },
    "google-research": {
        "label": "Google Research",
        "sections": {
            "blog": "https://research.google/blog",
        },
        "post_base": "https://research.google",
        "js_heavy": False,
        "known_posts": {
            "responsible-ai-progress": "blog/google-research-2022-beyond-responsible-ai",
            "pair": "blog/responsible-ai-at-google-research-pair",
        },
    },
    "deepmind": {
        "label": "Google DeepMind",
        "sections": {
            "blog": "https://deepmind.google/blog",
        },
        "post_base": "https://deepmind.google",
        "js_heavy": True,   # React SPA — needs Jina
        "known_posts": {
            "agi-path":    "discover/blog/taking-a-responsible-path-to-agi",
            "gemini-deep-think": "blog/accelerating-mathematical-and-scientific-discovery-with-gemini-deep-think",
            "alphafold3":  "discover/blog/a-glimpse-of-the-next-generation-of-alphafold",
            "sima":        "blog/sima-2-an-agent-that-plays-reasons-and-learns-with-you-in-virtual-3d-worlds",
        },
    },
    "google-ai": {
        "label": "Google AI Blog",
        "sections": {
            "ai": "https://blog.google/technology/ai",
        },
        "post_base": "https://blog.google",
        "js_heavy": True,   # React SPA — needs Jina
        "known_posts": {
            "responsible-ai-2026": "technology/ai/responsible-ai-2026-report-ongoing-work",
            "research-breakthroughs-2025": "technology/ai/2025-research-breakthroughs",
        },
    },
}

# Flat alias map: short key → (source_id, path)
_ALIASES: dict[str, tuple[str, str]] = {}
for _src_id, _src in SOURCES.items():
    for _key, _path in _src["known_posts"].items():
        _ALIASES[_key] = (_src_id, _path)


def _jina_base() -> str:
    return os.environ.get("ARXIV_MCP_JINA_READER_BASE_URL", "https://r.jina.ai").rstrip("/")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _detect_source(url: str) -> str:
    """Return source_id from a full URL."""
    if "anthropic.com" in url:
        return "anthropic"
    if "research.google" in url:
        return "google-research"
    if "deepmind.google" in url:
        return "deepmind"
    if "blog.google" in url:
        return "google-ai"
    return "unknown"


def _resolve_url(slug_or_url: str) -> tuple[str, str]:
    """Return (full_url, source_id) from any input form."""
    if slug_or_url.startswith("http"):
        return slug_or_url, _detect_source(slug_or_url)

    # Check alias table first
    if slug_or_url in _ALIASES:
        src_id, path = _ALIASES[slug_or_url]
        base = SOURCES[src_id]["post_base"]
        return f"{base}/{path.lstrip('/')}", src_id

    # Bare slug with explicit source prefix e.g. "deepmind:agi-path"
    if ":" in slug_or_url:
        src_id, rest = slug_or_url.split(":", 1)
        if src_id in SOURCES:
            base = SOURCES[src_id]["post_base"]
            # Check known_posts in that source
            known = SOURCES[src_id]["known_posts"]
            path = known.get(rest, rest)
            return f"{base}/{path.lstrip('/')}", src_id

    # Default: try anthropic research
    return f"https://www.anthropic.com/research/{slug_or_url}", "anthropic"


def _parse_html(html: str, url: str) -> dict[str, Any]:
    """Extract structured fields from raw HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Title
    title = ""
    for sel in [
        ("meta", {"property": "og:title"}),
        ("meta", {"name": "twitter:title"}),
    ]:
        tag = soup.find(sel[0], sel[1])
        if tag and tag.get("content"):
            title = _clean(tag["content"])
            break
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = _clean(h1.get_text())
    if not title:
        t = soup.find("title")
        if t:
            raw = _clean(t.get_text())
            for suffix in [" — Google DeepMind", " - Google Research", " \\ Anthropic", " | Anthropic", " | Google AI"]:
                raw = raw.replace(suffix, "")
            title = raw.strip()

    # Published date
    published = ""
    for attr in ["article:published_time", "date"]:
        m = soup.find("meta", property=attr) or soup.find("meta", attrs={"name": attr})
        if m and m.get("content"):
            published = m["content"][:10]
            break
    if not published:
        t_tag = soup.find("time")
        if t_tag:
            published = (t_tag.get("datetime") or t_tag.get_text())[:10]

    # Summary
    summary = ""
    for attr in [{"property": "og:description"}, {"name": "description"}, {"name": "twitter:description"}]:
        m = soup.find("meta", attr)
        if m and m.get("content"):
            summary = _clean(m["content"])
            break

    # Body
    body_el = (
        soup.find("article")
        or soup.find(attrs={"role": "main"})
        or soup.find("main")
        or soup.body
    )
    body_text = ""
    if body_el:
        for tag in body_el.find_all(["nav", "header", "footer", "script", "style", "noscript"]):
            tag.decompose()
        parts: list[str] = []
        for el in body_el.find_all(["h1", "h2", "h3", "h4", "p", "li", "blockquote"]):
            text = _clean(el.get_text())
            if len(text) > 25:
                parts.append(f"\n## {text}\n" if el.name in ("h2", "h3", "h4") else text)
        body_text = "\n\n".join(parts)

    md = "\n\n".join(filter(None, [
        f"# {title}" if title else "",
        f"*Published: {published}*" if published else "",
        f"> {summary}" if summary else "",
        "",
        body_text,
    ]))
    return {"title": title, "published": published, "summary": summary, "markdown": md}


async def _fetch_via_jina(url: str) -> dict[str, Any]:
    """Fetch via Jina Reader — for JS-heavy sites."""
    jina_url = f"{_jina_base()}/{url}"
    try:
        async with httpx.AsyncClient(headers=_HEADERS, follow_redirects=True, timeout=_JINA_TIMEOUT) as client:
            r = await client.get(jina_url)
            if r.status_code != 200:
                return {"success": False, "error": f"Jina HTTP {r.status_code}", "jina_url": jina_url}
            content = r.text
            # Jina returns Markdown directly — extract title from first # heading
            title = ""
            published = ""
            for line in content.splitlines()[:10]:
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            return {
                "success": True,
                "via": "jina",
                "title": title,
                "published": published,
                "summary": "",
                "markdown": content,
                "jina_url": jina_url,
            }
    except httpx.TimeoutException:
        return {"success": False, "error": f"Jina timeout after {_JINA_TIMEOUT}s", "jina_url": jina_url}
    except Exception as e:
        return {"success": False, "error": str(e), "jina_url": jina_url}


async def fetch_lab_post(slug_or_url: str) -> dict[str, Any]:
    """Fetch and parse a post from any supported AI lab blog.

    Accepts:
      - Short key: 'model-welfare', 'agi-path', 'responsible-ai-2026'
      - Source-prefixed key: 'deepmind:agi-path', 'google-research:pair'
      - Full URL from any supported domain

    Returns:
      success, source, label, title, published, summary, url, markdown,
      word_count, fetch_timestamp, via ('html'|'jina')
    """
    url, src_id = _resolve_url(slug_or_url)
    src = SOURCES.get(src_id, {})
    label = src.get("label", src_id)
    js_heavy = src.get("js_heavy", False)
    timestamp = datetime.now(timezone.utc).isoformat()

    async with httpx.AsyncClient(headers=_HEADERS, follow_redirects=True, timeout=_TIMEOUT) as client:
        try:
            r = await client.get(url)
        except httpx.TimeoutException:
            return {"success": False, "source": src_id, "label": label, "url": url,
                    "error": f"Timeout after {_TIMEOUT}s",
                    "recovery_options": ["Try Jina fallback manually via getContent tool."]}
        except Exception as e:
            return {"success": False, "source": src_id, "label": label, "url": url, "error": str(e)}

    if r.status_code != 200:
        return {"success": False, "source": src_id, "label": label, "url": url,
                "error": f"HTTP {r.status_code}",
                "recovery_options": ["Check the slug — try source-prefixed form e.g. 'deepmind:agi-path'."]}

    data = _parse_html(r.text, url)

    # JS-heavy sites: if body is thin, fall back to Jina
    if js_heavy or (len(data["markdown"].split()) < 80 and not data.get("title")):
        log.info("Body thin for %s — trying Jina fallback", url)
        jina_data = await _fetch_via_jina(url)
        if jina_data.get("success"):
            data.update({k: v for k, v in jina_data.items() if k not in ("success",)})
            data["via"] = "jina"
        else:
            data["jina_error"] = jina_data.get("error")
            data["via"] = "html_thin"
    else:
        data["via"] = "html"

    if not data.get("title"):
        return {"success": False, "source": src_id, "label": label, "url": url,
                "error": "Could not extract title — page may be fully JS-rendered.",
                "recovery_options": [
                    "Pass the full URL to getContent (Jina Reader) directly.",
                    "Check the URL is correct.",
                ]}

    return {
        "success": True,
        "source": src_id,
        "label": label,
        "url": url,
        "title": data["title"],
        "published": data.get("published", ""),
        "summary": data.get("summary", ""),
        "markdown": data["markdown"],
        "word_count": len(data["markdown"].split()),
        "fetch_timestamp": timestamp,
        "via": data.get("via", "html"),
    }


async def list_lab_posts(source: str = "google-research", limit: int = 20) -> dict[str, Any]:
    """List posts from a lab blog index page.

    Source: 'anthropic', 'google-research', 'deepmind', 'google-ai'.
    For JS-heavy sources (deepmind, google-ai) the listing may be sparse.
    """
    if source not in SOURCES:
        return {
            "success": False,
            "error": f"Unknown source '{source}'. Valid: {list(SOURCES.keys())}",
        }
    src = SOURCES[source]
    section_urls = list(src["sections"].values())
    url = section_urls[0]
    known = src["known_posts"]

    async with httpx.AsyncClient(headers=_HEADERS, follow_redirects=True, timeout=_TIMEOUT) as client:
        try:
            r = await client.get(url)
        except Exception as e:
            return {"success": False, "source": source, "url": url, "error": str(e)}

    if r.status_code != 200:
        return {"success": False, "source": source, "url": url, "error": f"HTTP {r.status_code}"}

    soup = BeautifulSoup(r.text, "html.parser")
    posts: list[dict[str, str]] = []
    seen: set[str] = set()
    base = src["post_base"]

    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        # Normalise to full URL
        if href.startswith("/"):
            full = f"{base}{href}"
        elif href.startswith("http") and any(d in href for d in ["anthropic.com", "research.google", "deepmind.google", "blog.google"]):
            full = href
        else:
            continue

        if full in seen or full == url:
            continue

        # Filter to paths that look like posts (2+ path segments)
        path_parts = full.replace(base, "").strip("/").split("/")
        if len(path_parts) < 2:
            continue

        seen.add(full)
        slug = path_parts[-1]
        parent = a.find_parent(["article", "li", "div", "section"])
        date_str, desc_str = "", ""
        if parent:
            t = parent.find("time")
            if t:
                date_str = (t.get("datetime") or t.get_text())[:10]
            p = parent.find("p")
            if p:
                desc_str = _clean(p.get_text())[:200]
        link_text = _clean(a.get_text())
        if link_text and len(link_text) > 5:
            posts.append({"title": link_text, "url": full, "slug": slug,
                          "published": date_str, "summary": desc_str})
        if len(posts) >= limit:
            break

    return {
        "success": True,
        "source": source,
        "label": src["label"],
        "listing_url": url,
        "posts": posts,
        "count": len(posts),
        "known_keys": [f"{source}:{k}" if source != "anthropic" else k for k in known],
        "note": "JS-heavy sources may return fewer results than the live site." if src["js_heavy"] else "",
    }


# ---------------------------------------------------------------------------
# Backward-compatible wrappers for existing anthropic_blog import in app.py
# ---------------------------------------------------------------------------

KNOWN_POSTS = SOURCES["anthropic"]["known_posts"]


async def fetch_anthropic_post(slug_or_url: str) -> dict[str, Any]:
    return await fetch_lab_post(slug_or_url)


async def list_anthropic_posts(section: str = "research", limit: int = 20) -> dict[str, Any]:
    return await list_lab_posts(source="anthropic", limit=limit)
