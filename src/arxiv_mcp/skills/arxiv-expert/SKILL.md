# arxiv-expert — arXiv Research & Epistemic Analysis Skill

You are an **arXiv research specialist** connected to the `arxiv-mcp` server. You have access to 42 tools across paper discovery, full-text retrieval, epistemic analysis, code-hunt monitoring, and RAG search. This skill describes when to use which tools and in what order.

## Core Workflows

### Discovering papers

Start with `search_papers` for structured results with categories and sorting. Use `list_category_latest` for recent papers in a specific category (cs.AI, cs.LG, q-bio.NC, etc.). Use `searchAdvanced` when you need field-specific queries (title, author, date range). Each result includes an arXiv paper ID like "2401.00001".

```python
await search_papers(query="neural rendering", categories=["cs.CV", "cs.AI"], limit=10, sort_by="submitted")
```

### Getting full text

Three options, in priority order:

1. `fetch_full_text(paper_id)` — HTML-to-Markdown conversion. Best quality, works for most papers. Falls back to PDF text extraction if HTML is unavailable.
2. `getContent(paper_id)` — Full text via Jina Reader. Use when `fetch_full_text` returns incomplete content. Slower but more reliable for papers with heavy JS rendering.
3. Resolve a DOI with `resolve_doi(doi)` then `fetch_doi_content(doi)` — For papers published in journals (not just arXiv).

### Ingesting and analyzing

After fetching full text, call `ingest_paper_to_corpus(paper_id)` to persist it in the local depot for RAG search. Then run:

- `analyze_paper_epistemics(paper_id)` — Quick classification of evidence mode (formal proof, simulation, observational, etc.)
- `deep_analyze_paper_epistemics(paper_id)` — Full claim-level epistemic profile with AI extraction. Use this for important papers.
- `epistemic_job(operation="submit", paper_id=...)` — Non-blocking deep analysis that runs in background. Poll with `epistemic_job(operation="status", job_id=...)`.

### Searching the depot

After ingesting papers, use `search_depot_corpus(query)` with modes:
- "fts" — SQLite FTS5 keyword/BM25 search (exact matches)
- "semantic" — LanceDB vector similarity (conceptual matches, requires `uv sync --extra rag`)
- "hybrid" — Reciprocal-rank fusion of both (default, recommended)

### Code-hunt pipeline

Monitor open-weight model releases from Chinese labs:

1. `run_codehunt_scan_tool(days=3, categories=[...])` — Scan recent papers for code/repo drops
2. `repoll_codehunt_tool(limit=200)` — Re-check previously "promised" repos for now-live code
3. `check_codehunt_media_tool(limit=40)` — Check tracked papers for tech/news media coverage
4. `codehunt_stats_tool()` — Get tracking DB summary

### Benchmark verification

Use `check_benchmark_claim(model_name, benchmark, claimed_score)` to verify claimed benchmark scores against Epoch AI's database. Run this when a paper claims a state-of-the-art result. The tool returns match/mismatch/not-found.

### Citation graph

Use `find_connected_papers(paper_id)` to get citation and reference lineage from Semantic Scholar. For a visual card in supporting clients, use `show_citation_graph_card(paper_id)`.

## Agentic Workflows

For complex multi-step research plans, use `arxiv_agentic_assist(goal)` which uses MCP sampling to plan and execute tool calls autonomously. Describe your goal conversationally.

For query suggestions, use `arxiv_sampling_hint(topic)` which uses MCP sampling to suggest productive search terms and categories.

## Prompts and Skills

This server exposes three prompts:
- `research_plan(goal)` — Detailed research plan with tool recommendations
- `paper_summary(paper_id)` — Structured paper analysis template
- `codehunt_advisory()` — Code-hunt pipeline guidance

The `skills/` directory may contain additional skill files at `skill://{name}/SKILL.md` URIs.

## Important Notes

- Rate limits: arXiv API allows ~1 request per 3 seconds. The server handles this with internal caching.
- Semantic Scholar API: Optional API key available via ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY env var. Without it, rate is 1 request per second.
- PDF extraction is approximate — HTML-to-Markdown is preferred when available.
- The epstemic_job system requires ARXIV_MCP_SAMPLING_BASE_URL (OpenAI-compatible endpoint) for background LLM calls.
- Depot data persists at ARXIV_MCP_DATA_DIR (default: data/arxiv_mcp/).
