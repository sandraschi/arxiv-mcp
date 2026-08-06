"""Fetch arXiv experimental HTML and convert to Markdown."""

from __future__ import annotations

import asyncio
import html as html_lib
import re
from typing import Any

import html2text
from bs4 import BeautifulSoup, NavigableString

from arxiv_mcp.config import Settings, load_settings
from arxiv_mcp.http import USER_AGENT, get_text
from arxiv_mcp.sanitize import sanitize_text

ARXIV_HTML_BASE = "https://arxiv.org/html"
DEFAULT_UA = USER_AGENT

_SKIP_SELECTORS = ("header", "nav", "footer", "script", "style", "noscript")


def html_url_for_paper(arxiv_id: str) -> str:
    return f"{ARXIV_HTML_BASE}/{arxiv_id}"


def _replace_math_with_tex(soup: BeautifulSoup) -> int:
    replaced = 0
    for math in soup.find_all("math"):
        tex: str | None = None
        for ann in math.find_all("annotation"):
            enc = (ann.get("encoding") or "").lower()
            if "x-tex" in enc or enc == "application/x-tex":
                tex = (ann.string or ann.get_text() or "").strip()
                if tex:
                    break
        if not tex:
            tex = (math.get("alttext") or "").strip()
        if not tex:
            continue
        display = math.get("display") == "block" or "display" in (math.get("class") or [])
        math.replace_with(NavigableString(f"$${tex}$$" if display else f"${tex}$"))
        replaced += 1
    return replaced


def assess_conversion_quality(html: str, markdown: str, *, tex_replaced: int) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    math_nodes = len(soup.find_all("math"))
    tex_annotations = len(soup.find_all("annotation", encoding=lambda v: v and "tex" in v.lower()))
    html_len = max(len(html), 1)
    ratio = len(markdown.strip()) / html_len
    degraded = math_nodes >= 8 and (tex_replaced < math_nodes // 2 or ratio < 0.02)
    return {
        "math_node_count": math_nodes,
        "tex_annotation_count": tex_annotations,
        "tex_injected_count": tex_replaced,
        "markdown_to_html_ratio": round(ratio, 4),
        "conversion": "degraded" if degraded else "ok",
    }


async def fetch_html_markdown(
    arxiv_id: str,
    *,
    timeout: float | None = None,
    user_agent: str = USER_AGENT,
    settings: Settings | None = None,
) -> tuple[bool, str, int | None, str | None, dict[str, Any]]:
    del user_agent
    settings = settings or load_settings()
    http_timeout = timeout if timeout is not None else settings.arxiv_http_timeout_seconds
    budget = settings.fetch_full_text_budget_seconds
    max_bytes = settings.fetch_full_text_max_bytes

    async def _fetch_and_convert() -> tuple[bool, str, int | None, str | None, dict[str, Any]]:
        url = html_url_for_paper(arxiv_id)
        payload = await get_text(
            url,
            settings=settings,
            timeout=http_timeout,
            cache_endpoint="arxiv_html",
        )
        if not payload.ok or payload.text is None:
            err = payload.error or {}
            return (
                False,
                err.get("error", "arXiv HTML fetch failed"),
                payload.status_code,
                payload.content_type,
                {"from_cache": payload.from_cache},
            )

        ctype = payload.content_type
        status = payload.status_code
        if status == 404:
            return (
                False,
                "No experimental HTML for this paper yet (404). Try another version or PDF.",
                status,
                ctype,
                {"from_cache": payload.from_cache},
            )
        if status is not None and status >= 400:
            return (
                False,
                f"arXiv HTML fetch failed: HTTP {status}",
                status,
                ctype,
                {"from_cache": payload.from_cache},
            )
        if "text/html" not in (ctype or "").lower():
            return (
                False,
                f"Unexpected content type for HTML endpoint: {ctype!r}",
                status,
                ctype,
                {"from_cache": payload.from_cache},
            )

        raw_html = payload.text
        body_len = len(raw_html.encode("utf-8"))
        cl = payload.headers.get("content-length")
        if cl:
            try:
                if int(cl) > max_bytes:
                    body_len = int(cl)
            except ValueError:
                pass
        if body_len > max_bytes:
            return (
                False,
                (
                    f"HTML document too large ({body_len} bytes > {max_bytes} cap). "
                    "Use PDF pipeline or store_paper_to_calibre instead of HTML→Markdown."
                ),
                status,
                ctype,
                {"from_cache": payload.from_cache, "conversion": "skipped_size"},
            )

        md, meta = await asyncio.to_thread(_html_to_markdown_with_meta, raw_html)
        meta["from_cache"] = payload.from_cache
        if not md.strip():
            return False, "HTML was empty after extraction.", status, ctype, meta
        return True, md, status, ctype, meta

    try:
        return await asyncio.wait_for(_fetch_and_convert(), timeout=budget)
    except TimeoutError:
        return (
            False,
            (
                f"Conversion exceeded {budget:.0f}s budget; paper too large for HTML→MD. "
                "Try a smaller paper, raise ARXIV_MCP_FETCH_FULL_TEXT_BUDGET_SECONDS, or use PDF."
            ),
            None,
            None,
            {"conversion": "timeout"},
        )


def _html_to_markdown_with_meta(html: str) -> tuple[str, dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    tex_replaced = _replace_math_with_tex(soup)
    for tag in soup.select(",".join(_SKIP_SELECTORS)):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.find(role="main")
    root = main if main else soup.body
    if root is None:
        root = soup

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.body_width = 0
    h.unicode_snob = True
    md = _cleanup_markdown(h.handle(str(root)))
    quality = assess_conversion_quality(html, md, tex_replaced=tex_replaced)
    return md, quality


def html_to_markdown(html: str) -> str:
    md, _ = _html_to_markdown_with_meta(html)
    return md


def _cleanup_markdown(text: str) -> str:
    t = html_lib.unescape(text)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return sanitize_text(t.strip())
