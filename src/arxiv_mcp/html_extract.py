"""Fetch arXiv experimental HTML and convert to Markdown.

arXiv serves accessible HTML at ``https://arxiv.org/html/{arxiv_id}`` for many
(but not all) papers. When HTML is missing, callers should fall back to PDF
pipelines or source bundles.
"""

from __future__ import annotations

import html as html_lib
import re

import html2text
import httpx
from bs4 import BeautifulSoup

ARXIV_HTML_BASE = "https://arxiv.org/html"
DEFAULT_UA = "arxiv-mcp/0.1 (research bot; +https://arxiv.org/help/policies)"

# arXiv HTML often wraps the body in a main content region; strip chrome.
_SKIP_SELECTORS = ("header", "nav", "footer", "script", "style", "noscript")


def html_url_for_paper(arxiv_id: str) -> str:
    """Build the experimental HTML URL for a normalized id (may include ``vN``)."""
    return f"{ARXIV_HTML_BASE}/{arxiv_id}"


async def fetch_html_markdown(
    arxiv_id: str,
    *,
    timeout: float = 60.0,
    user_agent: str = DEFAULT_UA,
) -> tuple[bool, str, int | None, str | None]:
    """GET HTML and return ``(ok, markdown_or_message, http_status, content_type)``."""
    url = html_url_for_paper(arxiv_id)
    headers = {"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml"}
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        resp = await client.get(url, headers=headers)
    ctype = resp.headers.get("content-type")
    if resp.status_code == 404:
        return (
            False,
            "No experimental HTML for this paper yet (404). Try another version or PDF.",
            resp.status_code,
            ctype,
        )
    if resp.status_code >= 400:
        return (
            False,
            f"arXiv HTML fetch failed: HTTP {resp.status_code}",
            resp.status_code,
            ctype,
        )
    if "text/html" not in (ctype or "").lower():
        return (
            False,
            f"Unexpected content type for HTML endpoint: {ctype!r}",
            resp.status_code,
            ctype,
        )

    md = html_to_markdown(resp.text)
    if not md.strip():
        return False, "HTML was empty after extraction.", resp.status_code, ctype
    return True, md, resp.status_code, ctype


def html_to_markdown(html: str) -> str:
    """Extract main text from arXiv HTML page and convert to Markdown."""
    soup = BeautifulSoup(html, "html.parser")
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
    raw = h.handle(str(root))
    return _cleanup_markdown(raw)


def _cleanup_markdown(text: str) -> str:
    t = html_lib.unescape(text)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()
