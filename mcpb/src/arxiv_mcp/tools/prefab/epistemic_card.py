"""Prefab epistemic claims card — flagship deep-analysis UI."""

from __future__ import annotations

import logging

from prefab_ui.app import PrefabApp
from prefab_ui.components import Badge, Card, CardContent, CardDescription, CardHeader, CardTitle, Markdown, Separator, Text

from arxiv_mcp.services import corpus

log = logging.getLogger("arxiv_mcp.prefab.epistemic_card")

_FLAG_LABELS = {
    "needs_bench": "bench",
    "needs_telescope_or_instrument": "telescope",
    "needs_formal_verification": "formal",
    "needs_simulation_compute": "compute",
    "needs_human_judgment": "human",
}


def register_epistemic_prefab_tool(mcp) -> None:
    @mcp.tool(app=True)
    async def show_epistemic_profile_card(paper_id: str) -> PrefabApp:
        """SHOW_EPISTEMIC_PROFILE_CARD — Claim-level epistemic profile as Prefab card.

        Reads persisted profile from depot when available; otherwise returns guidance
        to run deep_analyze_paper_epistemics first.
        """
        row = corpus.get_paper_markdown(paper_id)
        if not row:
            with Card(css_class="max-w-2xl") as view:
                with CardContent():
                    Text(f"Paper {paper_id!r} not in depot.", css_class="text-destructive")
                    Text("Ingest first, then deep_analyze_paper_epistemics.", css_class="text-sm mt-2")
            return PrefabApp(view=view, title="Epistemic profile")

        profile = (row.get("meta") or {}).get("epistemic_profile")
        title = row.get("title") or paper_id
        if not profile:
            with Card(css_class="max-w-2xl") as view:
                with CardHeader():
                    CardTitle(title)
                with CardContent():
                    Text("No epistemic profile yet.", css_class="text-sm")
                    Text("Run deep_analyze_paper_epistemics for claim-level analysis.", css_class="text-xs mt-2")
            return PrefabApp(view=view, title=title)

        mode = str(profile.get("primary_mode", "mixed")).replace("_", " ")
        summary = profile.get("deep_summary") or profile.get("summary") or ""
        claims = profile.get("claims") or []
        analyzer = profile.get("analyzer", "")

        with Card(css_class="max-w-2xl") as view:
            with CardHeader():
                CardTitle(title)
                CardDescription(f"{mode} · {analyzer or 'rule profile'}")
            with CardContent():
                if summary:
                    Markdown(summary[:900] + ("…" if len(summary) > 900 else ""))
                Separator(spacing=2)
                if not claims:
                    Text("Rule-only profile — no LLM claim table.", css_class="text-sm text-muted-foreground")
                for idx, claim in enumerate(claims[:8], start=1):
                    flags = [
                        _FLAG_LABELS[k]
                        for k in _FLAG_LABELS
                        if claim.get(k)
                    ]
                    line = f"**{idx}.** {claim.get('claim', '')[:280]}"
                    if claim.get("evidence_mode"):
                        line += f" _({str(claim['evidence_mode']).replace('_', ' ')})_"
                    Markdown(line)
                    for flag in flags:
                        Badge(flag, variant="secondary")
                    if claim.get("falsifier"):
                        Text(f"Falsifier: {str(claim['falsifier'])[:200]}", css_class="text-xs text-muted-foreground")
                    Separator(spacing=1)

        return PrefabApp(view=view, title=f"Epistemic · {paper_id}")
