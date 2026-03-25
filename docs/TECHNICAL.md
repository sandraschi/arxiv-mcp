# arxiv-mcp — technical reference

Implementation details for contributors and integrators. User-oriented overview: [README.md](../README.md).

## Stack

- **MCP:** [FastMCP](https://github.com/jlowin/fastmcp) **3.1+** (async tools, prompts, bundled skills provider).
- **HTTP:** [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/); MCP mounted as ASGI (`http_app`) at `/mcp`.
- **arXiv:** [arxiv](https://pypi.org/project/arxiv/) (official API wrapper) with polite client delay.
- **Full text (preferred path):** arXiv **experimental / accessible HTML** at `https://arxiv.org/html/{arxiv_id}` → HTML → Markdown ([BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) + [html2text](https://pypi.org/project/html2text/)). Not every paper has HTML (404 → use PDF or another version externally).
- **Lineage:** [Semantic Scholar Graph API](https://api.semanticscholar.org/) for citations / references (optional API key for higher limits).
- **Corpus / depot:** SQLite (`papers`, `favorites`, **`chunks_fts` FTS5**) + markdown files under configurable data dir (default `data/arxiv_mcp` under cwd; see `.env.example`). Ingest chunks Markdown for **BM25** search (`/api/depot/search`).
- **Webapp:** React + Vite + Tailwind — **iron shell** (sidebar, header, logger panel) per **mcp-central-docs** `standards/WEBAPP_STANDARDS.md`. Routes: `/dashboard`, `/search`, `/semantic`, `/depot`, `/favorites`, `/tools`, `/apps`, `/help`, `/settings`.
- **Fleet:** `GET /api/fleet` reads `src/arxiv_mcp/data/fleet_default.json` (edit for your hosts). Root **`glama.json`** for Glama discovery.

## Ports (fleet standard)

| Service | Port |
|--------|------|
| Backend (REST + MCP HTTP) | **10770** |
| Vite dev (dashboard) | **10771** |

Registered in **mcp-central-docs** (`operations/WEBAPP_PORTS.md`, `webapp-registry.json`). Do not use 3000, 5173, 8000, 8080 for this app.

REST (backend):

- `GET /api/health` — liveness
- `GET /api/stats` — depot counts + `data_dir`
- `GET /api/search?q=&limit=&sort_by=&categories=` — arXiv API (categories comma-separated)
- `GET /api/category/latest?category=&limit=&hours=`
- `GET /api/paper?paper_id=`
- `GET /api/corpus?limit=`
- `GET /api/corpus/item?arxiv_id=` — full markdown + metadata
- `GET /api/depot/search?q=&limit=` — **FTS5** over ingested chunks
- `POST /api/depot/ingest` JSON `{ "paper_id": "…" }` — fetch HTML → ingest
- `GET /api/favorites` · `POST /api/favorites` JSON `{ arxiv_id, title?, note? }` · `DELETE /api/favorites/{arxiv_id}`
- `GET /api/tools` — MCP tool manifest (dashboard)
- `GET /api/fleet` — fleet hub list
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
| `search` | arxiv.org HTML search (query / author / category, pagination) |
| `searchAdvanced` | arxiv.org advanced HTML search (field + date filters) |
| `getPaper` | Metadata scraped from abs page HTML |
| `getContent` | Full text via [Jina Reader](https://r.jina.ai/) |
| `getRecent` | Category recent list (arxiv.org HTML) |
| `listCategories` | Common categories (code, name, group) |
| `search_papers` | Query arXiv with optional categories and sort |
| `get_paper_details` | Metadata: title, abstract, authors, PDF/HTML links |
| `fetch_full_text` | Prefer HTML → Markdown; reports `html_available` |
| `list_category_latest` | Recent papers in a category (rolling window) |
| `find_connected_papers` | Semantic Scholar citations / references |
| `ingest_paper_to_corpus` | Persist markdown + metadata + **FTS chunks** for depot search |
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
| `ARXIV_MCP_ARXIV_HTTP_TIMEOUT_SECONDS` | Timeout for arxiv.org HTML + Jina requests (default 30) |
| `ARXIV_MCP_JINA_READER_BASE_URL` | Jina Reader prefix for `getContent` (default `https://r.jina.ai`) |

## Development

```powershell
uv sync --extra dev
uv run ruff check src tests
uv run ruff format src tests
uv run pytest
uv run ty check src
```

**CI:** GitHub Actions (`.github/workflows/ci.yml`) runs Ruff + pytest on every push/PR. **[ty](https://docs.astral.sh/ty/)** (Astral beta type checker) runs on `src` with **`continue-on-error: true`** so the workflow stays green while ty matures and stubs improve.

## Repository

- **GitHub:** [github.com/sandraschi/arxiv-mcp](https://github.com/sandraschi/arxiv-mcp)
