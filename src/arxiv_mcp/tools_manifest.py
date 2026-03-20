"""Static MCP tool catalog for dashboard / fleet (mirrors server registrations)."""

from __future__ import annotations

from typing import Any

MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_papers",
        "description": "Query arXiv with optional categories and sort order.",
        "params": {"query": "str", "categories": "list[str] | optional", "limit": "int", "sort_by": "str"},
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
        "description": "Persist Markdown + FTS chunks in local depot.",
        "params": {"paper_id": "str", "markdown": "str | optional", "source": "html|external"},
    },
    {
        "name": "compare_papers_convergence",
        "description": "Bundle abstracts for cross-paper synthesis.",
        "params": {"paper_ids": "list[str]"},
    },
    {
        "name": "generate_summary_prompt",
        "kind": "prompt",
        "description": "Structured analyst brief (MCP prompt).",
        "params": {"lens": "str", "paper_id": "str | optional"},
    },
]
