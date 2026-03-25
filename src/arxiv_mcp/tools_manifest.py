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
        "description": "Persist Markdown + FTS chunks in local depot.",
        "params": {"paper_id": "str", "markdown": "str | optional", "source": "html|external"},
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
        "name": "generate_summary_prompt",
        "kind": "prompt",
        "description": "Structured analyst brief (MCP prompt).",
        "params": {"lens": "str", "paper_id": "str | optional"},
    },
]
