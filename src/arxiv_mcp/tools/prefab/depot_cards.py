"""Prefab status/stats cards for depot and RAG (fleet mandate)."""

from __future__ import annotations

import logging

from prefab_ui.app import PrefabApp
from prefab_ui.components import Badge, Card, CardContent, CardHeader, CardTitle, Separator, Text

from arxiv_mcp.services import corpus
from arxiv_mcp.services.vector_rag import vector_rag_status

log = logging.getLogger("arxiv_mcp.prefab.depot_cards")


def register_depot_prefab_tools(mcp) -> None:
    @mcp.tool(app=True)
    async def show_depot_rag_status_card() -> PrefabApp:
        """SHOW_DEPOT_RAG_STATUS_CARD - LanceDB RAG health as an in-chat Prefab card."""
        status = vector_rag_status()
        available = bool(status.get("available"))
        with Card(css_class="max-w-xl") as view:
            with CardHeader():
                CardTitle("Depot RAG status")
            with CardContent():
                Badge("available" if available else "unavailable", variant="secondary")
                Text(f"Model: {status.get('model', '-')}", css_class="text-sm mt-2")
                Text(f"Indexed chunks: {status.get('indexed_chunks', 0)}", css_class="text-sm")
                Text(f"DB: {status.get('db_path', '-')}", css_class="text-xs text-muted-foreground mt-1 break-all")
                if status.get("install_hint"):
                    Text(str(status["install_hint"]), css_class="text-xs text-muted-foreground mt-2")
        return PrefabApp(view=view, title="Depot RAG")

    @mcp.tool(app=True)
    async def show_depot_stats_card() -> PrefabApp:
        """SHOW_DEPOT_STATS_CARD - Papers, favorites, chunks, and RAG summary."""
        stats = corpus.depot_stats()
        rag = stats.get("rag") or {}
        with Card(css_class="max-w-xl") as view:
            with CardHeader():
                CardTitle("Depot statistics")
            with CardContent():
                Text(f"Papers: {stats.get('papers', 0)}", css_class="text-sm")
                Text(f"FTS chunks: {stats.get('chunks', 0)}", css_class="text-sm")
                Text(f"Favorites: {stats.get('favorites', 0)}", css_class="text-sm")
                Separator(spacing=2)
                Text(
                    f"Vectors: {rag.get('indexed_chunks', 0)} ({'OK' if rag.get('available') else 'n/a'})",
                    css_class="text-sm",
                )
                Text(str(stats.get("data_dir", "")), css_class="text-xs text-muted-foreground mt-2 break-all")
        return PrefabApp(view=view, title="Depot stats")
