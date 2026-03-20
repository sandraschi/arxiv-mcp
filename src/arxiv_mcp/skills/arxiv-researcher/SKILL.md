---
name: arxiv-researcher
description: Use arxiv-mcp for discovery, experimental HTML full text, corpus ingest, and graph lineage.
---

# arXiv research (arxiv-mcp)

## Flow

1. `search_papers` or `list_category_latest` for discovery.
2. `get_paper_details` for metadata and links (`html_url`, `pdf_url`).
3. `fetch_full_text` — prefers **experimental HTML** (`https://arxiv.org/html/{id}`) → Markdown. If `html_available` is false, bring your own PDF pipeline or try another version.
4. `find_connected_papers` for Semantic Scholar citations/references.
5. `ingest_paper_to_corpus` to persist Markdown for local RAG.
6. `compare_papers_convergence` to bundle abstracts for adjudication (LLM-side synthesis).

## Prompts

Use MCP prompt `generate_summary_prompt` with `lens` = `instrumental_convergence`, `qualia`, `methods_audit`, or `general`.
