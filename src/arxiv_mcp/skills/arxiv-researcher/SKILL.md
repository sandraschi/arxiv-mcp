---
name: arxiv-researcher
description: Use arxiv-mcp for discovery (API + HTML), full text (experimental HTML or Jina), corpus ingest, S2 lineage, and sampling-assisted planning when available.
---

# arXiv research (arxiv-mcp)

## Discovery

**API (stable metadata):** `search_papers`, `list_category_latest`

**HTML (rich snippets, pagination, `parse_stats`):** `search`, `searchAdvanced`, `getRecent`, `listCategories`

## Metadata

- `get_paper_details` — arxiv PyPI client (preferred for ids/URLs).
- `getPaper` — abs-page HTML scrape (same names as HTML search pipeline).

## Full text

1. `fetch_full_text` — experimental `arxiv.org/html/{id}` → Markdown when available.
2. `getContent` — Jina Reader (third party); response is a **dict** with `success` and `content` or structured error.

## Graph + corpus

- `find_connected_papers` — Semantic Scholar citations/references.
- `ingest_paper_to_corpus` — local SQLite FTS depot.
- `compare_papers_convergence` — bundle abstracts for LLM adjudication.

## Sampling (FastMCP 3.1)

When the host supports MCP sampling: `arxiv_agentic_assist` (multi-step plan), `arxiv_sampling_hint` (query hints). If `success` is false, run tools manually using this skill.

## Prompts

MCP prompt `generate_summary_prompt` — `lens`: `instrumental_convergence` | `qualia` | `methods_audit` | `general`; optional `paper_id`.
