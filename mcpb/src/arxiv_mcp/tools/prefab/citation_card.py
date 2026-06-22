"""Citation graph Prefab card for Semantic Scholar lineage."""

from __future__ import annotations

import logging

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

from arxiv_mcp.config import load_settings
from arxiv_mcp.sanitize import wrap_untrusted
from arxiv_mcp.services import papers

log = logging.getLogger("arxiv_mcp.prefab.citation_card")


def _node_line(item: dict) -> str:
    title = str(item.get("title") or "(no title)")[:120]
    year = item.get("year")
    arxiv = item.get("arxiv")
    yr = f" ({year})" if year else ""
    ax = f" · [{arxiv}](https://arxiv.org/abs/{arxiv})" if arxiv else ""
    return f"- {title}{yr}{ax}"


def register_citation_prefab_tool(mcp) -> None:
    @mcp.tool(app=True)
    async def show_citation_graph_card(
        paper_id: str,
        limit: int = 8,
    ) -> PrefabApp:
        """SHOW_CITATION_GRAPH_CARD — Semantic Scholar citations/references as Prefab card.

        Calls find_connected_papers (with retry/backoff). On Semantic Scholar HTTP 429,
        the card shows recovery_options including ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY.

        Args:
            paper_id: arXiv id or URL.
            limit: Max nodes per side (citations and references).
        """
        settings = load_settings()
        try:
            graph = await papers.find_connected_papers(
                paper_id,
                limit=limit,
                api_key=settings.semantic_scholar_api_key,
            )
        except Exception as exc:
            with Card(css_class="max-w-2xl") as view:
                with CardContent():
                    Text(f"Graph fetch failed: {exc}", css_class="text-destructive")
            return PrefabApp(view=view, title="Citation graph")

        if not graph.get("found"):
            msg = graph.get("message") or graph.get("error") or "Not in Semantic Scholar graph."
            with Card(css_class="max-w-2xl") as view:
                with CardContent():
                    Text(msg, css_class="text-sm")
                    for opt in graph.get("recovery_options") or []:
                        Text(opt, css_class="text-xs text-muted-foreground")
            return PrefabApp(view=view, title="Citation graph")

        title = wrap_untrusted(str(graph.get("title") or paper_id), "s2_title")
        aid = graph.get("arxiv_id") or paper_id
        cites = graph.get("citations") or []
        refs = graph.get("references") or []

        with Card(css_class="max-w-2xl") as view:
            with CardHeader():
                CardTitle(title)
                CardDescription(f"arXiv:{aid} · Semantic Scholar lineage")
            with CardContent():
                Text(f"Citing papers ({len(cites)})", css_class="font-semibold text-sm")
                if cites:
                    Markdown("\n".join(_node_line(c) for c in cites[:limit]))
                else:
                    Text("None listed.", css_class="text-xs text-muted-foreground")
                Separator(spacing=2)
                Text(f"References ({len(refs)})", css_class="font-semibold text-sm")
                if refs:
                    Markdown("\n".join(_node_line(r) for r in refs[:limit]))
                else:
                    Text("None listed.", css_class="text-xs text-muted-foreground")
                Separator(spacing=2)
                Badge("find_connected_papers", variant="secondary")

        return PrefabApp(view=view, title=title)
