"""Paper abstract card — @mcp.tool(app=True) with PrefabApp."""

from __future__ import annotations

import logging
from typing import Any

from fastmcp.tools import ToolResult
from prefab_ui.app import PrefabApp
from prefab_ui.components import (
    Badge,
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
    Markdown,
    Separator,
    Text,
)

from arxiv_mcp.services import papers

log = logging.getLogger("arxiv_mcp.prefab.paper_card")

_ABSTRACT_MAX = 800


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return cut + " …"


def _fmt_date(published: str) -> str:
    """Return YYYY-MM-DD from ISO timestamp, or the raw string if parsing fails."""
    try:
        return published[:10]
    except Exception:
        return published


def register_paper_card_tool(mcp) -> None:  # noqa: ANN001
    """Register show_paper_card on the given FastMCP instance."""

    @mcp.tool(app=True)
    async def show_paper_card(paper_id: str) -> Any:
        """SHOW_PAPER_CARD — Render arXiv paper metadata as a rich in-chat Prefab card.

        Fetches title, authors, categories, published date, and abstract for
        the given paper and displays them as a structured card. Works with any
        arXiv id, URL, or arxiv: prefix form accepted by get_paper_details.

        Args:
            paper_id: arXiv id (e.g. 2401.00001), URL, or arxiv: prefix form.

        Returns:
            ToolResult with plain-text content (always) + PrefabApp card (when supported).
        """
        try:
            p = await papers.get_paper_details(paper_id)
            d = papers.paper_summary_to_dict(p)
        except Exception as exc:
            return ToolResult(
                content=f"Error fetching paper {paper_id!r}: {exc}",
                structured_content=None,
            )

        title: str = d.get("title") or paper_id
        authors: list[str] = d.get("authors") or []
        categories: list[str] = d.get("categories") or []
        abstract: str = d.get("abstract") or d.get("summary") or "(no abstract)"
        published: str = _fmt_date(d.get("published") or "")
        url_abs: str = d.get("url_abstract") or f"https://arxiv.org/abs/{d.get('paper_id', paper_id)}"
        url_pdf: str = d.get("url_pdf") or ""

        authors_str = ", ".join(authors[:6]) + (" et al." if len(authors) > 6 else "")
        abstract_short = _truncate(abstract, _ABSTRACT_MAX)

        # Plain-text fallback.
        plain = (
            f"{title}\n"
            f"{authors_str}\n"
            f"Published: {published}  |  {' '.join(categories[:5])}\n\n"
            f"{abstract_short}\n\n"
            f"Abstract: {url_abs}"
            + (f"\nPDF: {url_pdf}" if url_pdf else "")
        )

        # Prefab card.
        links_md = f"[Abstract]({url_abs})" + (f"  ·  [PDF]({url_pdf})" if url_pdf else "")

        with Card(css_class="max-w-2xl") as view:
            with CardHeader():
                CardTitle(title)
                CardDescription(authors_str)
            with CardContent():
                # Meta row: date + category badges
                Text(f"Published: {published}", css_class="text-sm text-muted-foreground mb-1")
                for cat in categories[:5]:
                    Badge(cat, variant="secondary")
                Separator(spacing=3)
                # Abstract
                Text("Abstract", css_class="font-semibold text-sm mb-1")
                Markdown(abstract_short)
                Separator(spacing=3)
                # Links
                Markdown(links_md)

        return ToolResult(
            content=plain,
            structured_content=PrefabApp(view=view, title=title),
        )
