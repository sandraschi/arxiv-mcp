"""Section-aware chunking from arXiv LaTeXML HTML (P1.5 depot ingest)."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from arxiv_mcp.html_extract import _html_to_markdown_with_meta, _replace_math_with_tex
from arxiv_mcp.services.corpus import _chunk_text, _chunk_text_sliding

_CHUNK_SIZE = 1400
_CHUNK_OVERLAP = 180


def _section_body_text(node) -> str:
    parts: list[str] = []
    for el in node.find_all(["p", "li", "pre", "blockquote", "div"], recursive=True):
        if el.find_parent(["script", "style", "nav", "header", "footer"]):
            continue
        t = el.get_text("\n", strip=True)
        if t and len(t) > 2:
            parts.append(t)
    if parts:
        return "\n\n".join(parts)
    return node.get_text("\n", strip=True)


def chunk_texts_from_html_dom(
    html: str,
    *,
    size: int = _CHUNK_SIZE,
    overlap: int = _CHUNK_OVERLAP,
) -> list[str] | None:
    """Build ingest chunks from HTML section structure; None if structure is too flat."""
    soup = BeautifulSoup(html, "html.parser")
    _replace_math_with_tex(soup)
    root = soup.find("main") or soup.find("article") or soup.find(role="main") or soup.body
    if root is None:
        return None

    blocks: list[tuple[str, str]] = []

    for sec in root.find_all("section"):
        classes = " ".join(sec.get("class") or [])
        if "ltx_section" in classes or sec.find(["h1", "h2", "h3", "h4"]):
            head = sec.find(["h1", "h2", "h3", "h4"])
            title = head.get_text(strip=True) if head else "Section"
            body = _section_body_text(sec)
            if body:
                blocks.append((title, body))

    if len(blocks) < 2:
        current_title = "Introduction"
        current_parts: list[str] = []
        for el in root.find_all(["h1", "h2", "h3", "h4", "p"]):
            if el.name in {"h1", "h2", "h3", "h4"}:
                if current_parts:
                    blocks.append((current_title, "\n\n".join(current_parts)))
                current_title = el.get_text(strip=True) or "Section"
                current_parts = []
            else:
                t = el.get_text("\n", strip=True)
                if t:
                    current_parts.append(t)
        if current_parts:
            blocks.append((current_title, "\n\n".join(current_parts)))

    if len(blocks) < 2:
        return None

    out: list[str] = []
    for heading, body in blocks:
        piece = f"## {heading}\n\n{body}".strip()
        if len(piece) <= size:
            out.append(piece)
        else:
            out.extend(_chunk_text_sliding(piece, size=size, overlap=overlap))
    return out if out else None


def prepare_ingest_from_html(raw_html: str) -> tuple[str, list[str], dict[str, Any]]:
    """Markdown file body + vector/FTS chunks + quality metadata."""
    md, quality = _html_to_markdown_with_meta(raw_html)
    dom_chunks = chunk_texts_from_html_dom(raw_html)
    if dom_chunks:
        chunks = dom_chunks
        quality["chunk_strategy"] = "html_sections"
    else:
        chunks = _chunk_text(md)
        quality["chunk_strategy"] = "markdown_headings"
    quality["chunk_count"] = len(chunks)
    return md, chunks, quality


def prepare_ingest_from_plaintext(text: str, *, source: str = "pdf") -> tuple[str, list[str], dict[str, Any]]:
    md = text.strip()
    chunks = _chunk_text(md)
    return md, chunks, {"chunk_strategy": "plaintext_sliding", "chunk_count": len(chunks), "conversion": source}
