"""Citation graph Prefab card for Semantic Scholar lineage."""

from __future__ import annotations

import logging
from typing import Annotated

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
from pydantic import Field

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
    @mcp.tool(app=True, annotations={"readOnlyHint": True, "openWorldHint": True})
    async def show_citation_graph_card(
        paper_id: Annotated[str, Field(description="arXiv id or URL.")],
        limit: Annotated[int, Field(description="Max nodes per side (citations and references).")] = 8,
    ) -> PrefabApp:
        """SHOW_CITATION_GRAPH_CARD - Semantic Scholar citations/references as Prefab card.

        Calls find_connected_papers (Semantic Scholar first, OpenAlex fallback on
        HTTP 429 / 5xx / timeout). The card shows the ``source`` badge so the
        fallback is transparent; recovery options appear only when both providers fail.

        ## Return Format
        PrefabApp card rendered inline in the conversation (title + structured view).

        ## Examples
        `show_citation_graph_card(paper_id="2401.00001")` -> PrefabApp with citing/reference lists.
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
        source = str(graph.get("source") or "semantic_scholar")
        source_label = "OpenAlex fallback" if source == "openalex" else "Semantic Scholar lineage"
        cites = graph.get("citations") or []
        refs = graph.get("references") or []

        with Card(css_class="max-w-2xl") as view:
            with CardHeader():
                CardTitle(title)
                CardDescription(f"arXiv:{aid} · {source_label}")
            with CardContent():
                if graph.get("notice"):
                    Text(str(graph["notice"]), css_class="text-xs text-muted-foreground")
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
                Badge(source, variant="outline")

        return PrefabApp(view=view, title=title)
