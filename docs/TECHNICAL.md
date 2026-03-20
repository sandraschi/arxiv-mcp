# arxiv-mcp — technical reference

Implementation details for contributors and integrators. User-oriented overview: [README.md](../README.md).

## Stack

- **MCP:** [FastMCP](https://github.com/jlowin/fastmcp) **3.1+** (async tools, prompts, bundled skills provider).
- **HTTP:** [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/); MCP mounted as ASGI (`http_app`) at `/mcp`.
- **arXiv:** [arxiv](https://pypi.org/project/arxiv/) (official API wrapper) with polite client delay.
- **Full text (preferred path):** arXiv **experimental / accessible HTML** at `https://arxiv.org/html/{arxiv_id}` → HTML → Markdown ([BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) + [html2text](https://pypi.org/project/html2text/)). Not every paper has HTML (404 → use PDF or another version externally).
- **Lineage:** [Semantic Scholar Graph API](https://api.semanticscholar.org/) for citations / references (optional API key for higher limits).
- **Corpus:** SQLite + markdown files under configurable data dir (default under repo `data/`; see `.env.example`).

## Ports (fleet standard)

| Service | Port |
|--------|------|
| Backend (REST + MCP HTTP) | **10770** |
| Vite dev (dashboard) | **10771** |

Registered in **mcp-central-docs** (`operations/WEBAPP_PORTS.md`, `webapp-registry.json`). Do not use 3000, 5173, 8000, 8080 for this app.

Endpoints (backend):

- `GET /api/health`
- `GET /api/search?q=...&limit=...&sort_by=...`
- `GET /api/paper?paper_id=...`
- `GET /api/corpus?limit=...`
- MCP streamable HTTP: **`/mcp`**

## CLI

```powershell
# stdio (Cursor, Claude Desktop, etc.)
uv run python -m arxiv_mcp --stdio

# Combined FastAPI + MCP HTTP
uv run python -m arxiv_mcp --serve

# Console script (after install)
arxiv-mcp --stdio
```

Environment: `MCP_TRANSPORT=http` also selects HTTP mode when not passing `--serve`.

## MCP tools

| Tool | Purpose |
|------|---------|
| `search_papers` | Query arXiv with optional categories and sort |
| `get_paper_details` | Metadata: title, abstract, authors, PDF/HTML links |
| `fetch_full_text` | Prefer HTML → Markdown; reports `html_available` |
| `list_category_latest` | Recent papers in a category (rolling window) |
| `find_connected_papers` | Semantic Scholar citations / references |
| `ingest_paper_to_corpus` | Persist markdown + metadata for local RAG |
| `compare_papers_convergence` | Bundle abstracts + structured adjudication prompt (LLM-side synthesis) |

## MCP prompts

- **`generate_summary_prompt`** — arguments include `lens`: `instrumental_convergence`, `qualia`, `methods_audit`, `general`; optional `paper_id`.

## Bundled skills

`src/arxiv_mcp/skills/arxiv-researcher/` is exposed via FastMCP **SkillsDirectoryProvider** (`skill://…` URIs in supporting clients).

## Configuration

See **`.env.example`**. Common variables:

| Variable | Role |
|----------|------|
| `ARXIV_MCP_HOST` | Bind address (default `127.0.0.1`) |
| `ARXIV_MCP_PORT` | Backend port (default `10770`) |
| `ARXIV_MCP_CLIENT_DELAY_SECONDS` | Pacing for arXiv API |
| `ARXIV_MCP_DATA_DIR` | Corpus root (optional) |
| `ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY` | Optional S2 API key |

## Development

```powershell
uv sync --extra dev
uv run ruff check src tests
uv run ruff format src tests
uv run pytest
```

## Repository

- **GitHub:** [github.com/sandraschi/arxiv-mcp](https://github.com/sandraschi/arxiv-mcp)
