# AGENTS.md — arxiv-mcp

## Project Identity
- **Name**: arxiv-mcp
- **Purpose**: arXiv research pipe — search, full-text extraction, citation graphs, DOI resolution, local RAG depot
- **Stack**: FastMCP 3.2+, FastAPI, Starlette, SQLite FTS5, pypdf
- **Ports**: 10770 (backend + MCP HTTP), 10771 (Vite dashboard)
- **Transports**: stdio (`--stdio`) and streamable HTTP (`--serve`)

## Key Files

| File | Purpose |
|------|---------|
| `src/arxiv_mcp/server.py` | MCP tool registrations (20+ tools, 10 prompts) |
| `src/arxiv_mcp/app.py` | FastAPI REST + MCP HTTP mount at `/mcp` |
| `src/arxiv_mcp/services/papers.py` | arXiv API + Semantic Scholar |
| `src/arxiv_mcp/arxiv_html.py` | arxiv.org HTML scraping (search/advanced/getPaper/getContent/getRecent) |
| `src/arxiv_mcp/sanitize.py` | Prompt injection defense — `wrap_untrusted()` on all LLM-facing text |
| `src/arxiv_mcp/doi_resolver.py` | DOI → OA PDF via Unpaywall + Crossref |
| `src/arxiv_mcp/html_extract.py` | arXiv experimental HTML → Markdown |
| `src/arxiv_mcp/lab_blog.py` | Multi-source blog fetcher (Anthropic, Google Research, DeepMind, Google AI) |
| `src/arxiv_mcp/config.py` | All settings via env (prefix `ARXIV_MCP_`) |
| `src/arxiv_mcp/services/corpus.py` | SQLite FTS5 depot — ingest, search, favorites |
| `web_sota/` | React/Vite dashboard; start with `start.bat` or `npm run dev` |

## Tool Modules

| Module | Tools |
|--------|-------|
| `services/papers.py` | `search_papers`, `get_paper_details`, `list_category_latest`, `find_connected_papers` |
| `arxiv_html.py` | `search`, `searchAdvanced`, `getPaper`, `getContent`, `getRecent`, `listCategories` |
| `html_extract.py` | `fetch_full_text` |
| `doi_resolver.py` | `resolve_doi`, `fetch_doi_content` |
| `lab_blog.py` | `fetch_lab_post`, `list_lab_posts`, `fetch_anthropic_post`, `list_anthropic_posts` |
| `tools/prefab/paper_card.py` | `show_paper_card` (Prefab UI) |
| `server.py` | `ingest_paper_to_corpus`, `compare_papers_convergence`, `arxiv_agentic_assist`, `arxiv_sampling_hint` |

## Prompt Modules

| Prompt | Purpose |
|--------|---------|
| `research_workflow_prompt` | Quick / deep / corpus mode |
| `generate_summary_prompt` | Adversarial deep-read with lenses |
| `consciousness_survey_prompt` | Consciousness research landscape |
| `ai_consciousness_prompt` | AI/LLM consciousness with stances |
| `neurophilosophy_prompt` | Philosophy of mind lens |
| `convergence_analysis_prompt` | Cross-paper synthesis |
| `firefront_scan_prompt` | Timed new-paper triage |
| `corpus_build_prompt` | Systematic corpus ingestion |
| `replication_audit_prompt` | Methods stress-test |
| `citation_map_prompt` | Citation graph traversal |

## Security

- All external text (titles, abstracts, full text, blog content, DOI metadata) wrapped with adversarial safety boundary before returning to LLM
- Zero-width Unicode character stripping on all ingested text
- See `sanitize.py` for the `wrap_untrusted()` pattern — apply to any new MCP tool that returns untrusted external text

## Testing

```powershell
uv run pytest            # full suite
uv run pytest tests/ -v  # verbose
```

## Linting

```powershell
# Python
ruff check src/ tests/
ruff format src/ tests/

# Frontend (from web_sota/)
biome lint src/
biome check --write src/
```

Install docs: follow mcp-central-docs/standards/AGENT_INSTALL_REFERENCE.md
