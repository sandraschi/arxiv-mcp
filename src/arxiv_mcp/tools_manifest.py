"""Static MCP tool catalog for dashboard / fleet (mirrors server registrations)."""

from __future__ import annotations

from typing import Any

MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "search",
        "description": "arxiv.org HTML search; JSON with success, papers, parse_stats, or structured error.",
        "params": {
            "query": "str",
            "category": "str | optional",
            "author": "str | optional",
            "sort_by": "str",
            "page": "int",
            "page_size": "int",
        },
    },
    {
        "name": "searchAdvanced",
        "description": "arxiv.org advanced HTML search (field filters, dates).",
        "params": {
            "title": "str | optional",
            "abstract": "str | optional",
            "author": "str | optional",
            "category": "str | optional",
            "id_arxiv": "str | optional",
            "date_from": "str | optional",
            "date_to": "str | optional",
            "sort_by": "str",
            "page": "int",
            "page_size": "int",
        },
    },
    {
        "name": "getPaper",
        "description": "Abs-page HTML metadata; success + paper dict or structured error.",
        "params": {"id_or_url": "str"},
    },
    {
        "name": "getContent",
        "description": "Jina Reader full text; success + content/abs_url/jina_url or structured error.",
        "params": {"id_or_url": "str"},
    },
    {
        "name": "getRecent",
        "description": "Category recent list HTML; includes parse_stats; structured errors.",
        "params": {"category": "str", "count": "int"},
    },
    {
        "name": "listCategories",
        "description": "Static category catalog; success + categories array.",
        "params": {},
    },
    {
        "name": "search_papers",
        "description": "Query arXiv with optional categories and sort order.",
        "params": {
            "query": "str",
            "categories": "list[str] | optional",
            "limit": "int",
            "sort_by": "str",
        },
    },
    {
        "name": "get_paper_details",
        "description": "Full metadata, abstract, authors, PDF/HTML links.",
        "params": {"paper_id": "str"},
    },
    {
        "name": "fetch_full_text",
        "description": "Experimental HTML → Markdown when available.",
        "params": {"paper_id": "str", "format": "markdown", "prefer_html": "bool"},
    },
    {
        "name": "list_category_latest",
        "description": "Recent papers in an arXiv category (rolling window).",
        "params": {"category": "str", "limit": "int", "hours": "int"},
    },
    {
        "name": "find_connected_papers",
        "description": "Semantic Scholar citations and references.",
        "params": {"paper_id": "str", "limit": "int"},
    },
    {
        "name": "ingest_paper_to_corpus",
        "description": "Persist Markdown + FTS + LanceDB chunks in local depot.",
        "params": {"paper_id": "str", "markdown": "str | optional", "source": "html|external|pdf"},
    },
    {
        "name": "run_firefront_scan_tool",
        "description": "Scan recent category submissions, write firefront digest JSON, optional depot ingest.",
        "params": {
            "topic": "str",
            "categories": "list[str] | optional",
            "days": "int",
            "limit_per_category": "int",
            "ingest_top_n": "int",
        },
    },
    {
        "name": "ingest_and_analyze_paper",
        "description": "HTML-first ingest plus epistemic profile (knowing type + human/physical loop).",
        "params": {"paper_id": "str"},
    },
    {
        "name": "analyze_paper_epistemics",
        "description": "Classify evidence mode and what still needs bench/telescope/human review.",
        "params": {"paper_id": "str", "ingest_if_missing": "bool"},
    },
    {
        "name": "deep_analyze_paper_epistemics",
        "description": "Claim-level epistemic profile: rule tags + LLM claim table (MCP sampling or HTTP LLM).",
        "params": {
            "paper_id": "str",
            "ingest_if_missing": "bool",
            "force_refresh": "bool",
        },
    },
    {
        "name": "list_depot_by_epistemics",
        "description": "Filter ingested papers by primary_mode and aggregate needs (bench, telescope, formal, deep claims).",
        "params": {
            "primary_mode": "str | optional",
            "needs_bench": "bool | optional",
            "needs_telescope_or_instrument": "bool | optional",
            "needs_formal_verification": "bool | optional",
            "has_deep_claims": "bool | optional",
            "limit": "int",
        },
    },
    {
        "name": "search_depot_corpus",
        "description": "Search ingested depot: fts, semantic (LanceDB), or hybrid RRF.",
        "params": {
            "query": "str",
            "limit": "int",
            "mode": "fts|semantic|hybrid",
            "max_age_days": "int | optional",
        },
    },
    {
        "name": "depot_rag_status",
        "description": "LanceDB vector index status and indexed chunk count.",
        "params": {},
    },
    {
        "name": "reindex_depot_vectors",
        "description": "Rebuild LanceDB embeddings for all ingested papers.",
        "params": {},
    },
    {
        "name": "compare_papers_convergence",
        "description": "Bundle abstracts for cross-paper synthesis.",
        "params": {"paper_ids": "list[str]"},
    },
    {
        "name": "arxiv_agentic_assist",
        "description": "Research plan via MCP sampling (ctx.sample); names concrete tools.",
        "params": {"goal": "str"},
    },
    {
        "name": "arxiv_sampling_hint",
        "description": "Suggested queries/categories via MCP sampling.",
        "params": {"topic": "str"},
    },
    {
        "name": "show_paper_card",
        "kind": "app",
        "description": "Render a rich Prefab card (title, authors, badges, abstract, links) in Claude Desktop.",
        "params": {"paper_id": "str"},
    },
    {
        "name": "show_depot_rag_status_card",
        "kind": "app",
        "description": "Prefab status card: LanceDB health, indexed chunks, embedding model.",
        "params": {},
    },
    {
        "name": "show_depot_stats_card",
        "kind": "app",
        "description": "Prefab stats card: depot papers, FTS chunks, favorites, RAG summary.",
        "params": {},
    },
    {
        "name": "show_citation_graph_card",
        "kind": "app",
        "description": "Prefab card: Semantic Scholar citations and references for a paper.",
        "params": {"paper_id": "str", "limit": "int"},
    },
    {
        "name": "show_epistemic_profile_card",
        "kind": "app",
        "description": "Prefab claims card: epistemic profile with evidence-mode flags per claim.",
        "params": {"paper_id": "str"},
    },
    {
        "name": "fetch_lab_post",
        "description": "Fetch and parse a post from Anthropic, Google Research, DeepMind, or Google AI Blog.",
        "params": {"slug_or_url": "str (short key, source:key, path, or full URL)"},
    },
    {
        "name": "list_lab_posts",
        "description": "List posts from any supported AI lab blog index.",
        "params": {"source": "anthropic|google-research|deepmind|google-ai", "limit": "int"},
    },
    {
        "name": "fetch_anthropic_post",
        "description": "Fetch an Anthropic blog post (backward-compat alias for fetch_lab_post).",
        "params": {"slug_or_url": "str"},
    },
    {
        "name": "list_anthropic_posts",
        "description": "List Anthropic blog posts (backward-compat alias for list_lab_posts).",
        "params": {"section": "research|news", "limit": "int"},
    },
]

MCP_PROMPTS: list[dict[str, Any]] = [
    {
        "name": "research_workflow_prompt",
        "description": "Tool-order guide for a session.",
        "params": {"mode": "quick | deep | corpus"},
        "tags": ["workflow", "onboarding"],
    },
    {
        "name": "generate_summary_prompt",
        "description": "Adversarial deep-read brief for a single paper.",
        "params": {
            "lens": "general | methods_audit | instrumental_convergence | qualia",
            "paper_id": "str (optional)",
        },
        "tags": ["analysis", "adversarial"],
    },
    {
        "name": "consciousness_survey_prompt",
        "description": "Map the consciousness research landscape on arXiv.",
        "params": {
            "framework": "IIT | GWT | HOT | predictive_processing | free_energy | comparative | general",
            "scope": "empirical | theoretical | both",
        },
        "tags": ["consciousness", "survey", "neurophilosophy"],
    },
    {
        "name": "ai_consciousness_prompt",
        "description": "Analyse AI / LLM consciousness claims with a specified stance.",
        "params": {
            "stance": "sceptic | functionalist | illusionist | open_question | moral_weight",
            "paper_id": "str (optional)",
        },
        "tags": ["ai_consciousness", "moral_status"],
    },
    {
        "name": "neurophilosophy_prompt",
        "description": "Philosophy of mind lens for arXiv papers.",
        "params": {
            "tradition": "eliminativist | phenomenological | analytical | embodied | enactivist | general",
            "paper_id": "str (optional)",
        },
        "tags": ["neurophilosophy", "philosophy_of_mind"],
    },
    {
        "name": "convergence_analysis_prompt",
        "description": "Cross-paper synthesis and contradiction map.",
        "params": {"domain": "consciousness | ai_capabilities | neuroscience | mcp_agents | general"},
        "tags": ["synthesis", "meta-analysis"],
    },
    {
        "name": "firefront_scan_prompt",
        "description": "Timed new-paper triage briefing for a topic.",
        "params": {"topic": "str", "days": "int (default 7)"},
        "tags": ["triage", "monitoring"],
    },
    {
        "name": "corpus_build_prompt",
        "description": "Systematic corpus ingestion plan.",
        "params": {"topic": "str", "depth": "shallow | deep"},
        "tags": ["corpus", "ingestion"],
    },
    {
        "name": "replication_audit_prompt",
        "description": "Reproducibility and methods stress-test checklist.",
        "params": {"paper_id": "str (optional)"},
        "tags": ["reproducibility", "methods"],
    },
    {
        "name": "epistemic_profile_prompt",
        "description": "Claim-level epistemic workflow: ingest, deep analyze, interpret claim flags.",
        "params": {"paper_id": "str", "max_claims": "int"},
        "tags": ["epistemics", "claims", "analysis"],
    },
    {
        "name": "citation_map_prompt",
        "description": "Citation graph traversal and intellectual lineage analysis.",
        "params": {"paper_id": "str", "direction": "references | citations | both"},
        "tags": ["citations", "lineage"],
    },
]
