# arxiv-mcp

**Repository:** [github.com/sandraschi/arxiv-mcp](https://github.com/sandraschi/arxiv-mcp)

FastMCP **3.1** server + **web dashboard** for arXiv: search, metadata, **experimental HTML → Markdown**, Semantic Scholar lineage, local corpus ingest, and structured comparison prompts.

## Experimental HTML

arXiv publishes accessible HTML for many papers at `https://arxiv.org/html/{arxiv_id}` (not 100% coverage). `fetch_full_text` uses this path first—avoiding PDF parsing when HTML exists.

## Cursor (stdio)

From repo root:

```powershell
uv sync
uv run python -m arxiv_mcp --stdio
```

Point Cursor MCP at that command (or `arxiv-mcp` console script after install).

## Web + MCP HTTP

Reserved ports: **10770** (API + MCP), **10771** (Vite). Adjacent pair per central docs.

```powershell
uv sync
uv run python -m arxiv_mcp --serve
```

Dashboard:

```powershell
.\start.ps1
```

- Health: `http://127.0.0.1:10770/api/health`
- MCP (streamable HTTP): `http://127.0.0.1:10770/mcp`

## Tools

| Tool | Role |
|------|------|
| `search_papers` | Query + categories + sort |
| `get_paper_details` | Title, abstract, authors, links |
| `fetch_full_text` | HTML→Markdown (experimental) |
| `list_category_latest` | Rolling window listing |
| `find_connected_papers` | Semantic Scholar citations/refs |
| `ingest_paper_to_corpus` | SQLite + markdown on disk |
| `compare_papers_convergence` | Abstract bundle + adjudication prompt |

## Prompts

- `generate_summary_prompt` — lenses: `instrumental_convergence`, `qualia`, `methods_audit`, `general`

## Config

See `.env.example`. Key vars: `ARXIV_MCP_HOST`, `ARXIV_MCP_PORT`, `ARXIV_MCP_CLIENT_DELAY_SECONDS`, `ARXIV_MCP_DATA_DIR`, `ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY`.

## Dev

```powershell
uv sync --extra dev
uv run ruff check src tests
uv run ruff format src tests
uv run pytest
```

## License

MIT
