# arxiv-mcp — technical reference

Implementation details for contributors and integrators. User-oriented overview: [README.md](../README.md).

## Stack

- **MCP:** [FastMCP](https://github.com/jlowin/fastmcp) **3.1+** (async tools, prompts, **sampling** tools `arxiv_agentic_assist` / `arxiv_sampling_hint`, bundled **skills** provider).
- **HTTP:** [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/); MCP mounted as ASGI (`http_app`) at `/mcp`.
- **arXiv:** [arxiv](https://pypi.org/project/arxiv/) (official API wrapper) with polite client delay. **Compatibility:** PyPI `arxiv` **2.x** returns categories on each result as **`list[str]`**; service code normalizes that shape (and legacy `.term` objects if they appear).
- **Full text (preferred path):** arXiv **experimental / accessible HTML** at `https://arxiv.org/html/{arxiv_id}` → HTML → Markdown ([BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) + [html2text](https://pypi.org/project/html2text/)). Not every paper has HTML (404 → use PDF or another version externally).
- **Lineage:** [Semantic Scholar Graph API](https://api.semanticscholar.org/) for citations / references (optional API key for higher limits).
- **Corpus / depot:** SQLite (`papers`, `favorites`, **`chunks_fts` FTS5**) + markdown files under configurable data dir (default `data/arxiv_mcp` under cwd; see `.env.example`). Ingest chunks Markdown for **BM25** search (`/api/depot/search`).
- **Webapp:** React + Vite + Tailwind — **iron shell** (sidebar, header, logger panel) per **mcp-central-docs** `standards/WEBAPP_STANDARDS.md`. Routes: `/dashboard`, `/search`, `/semantic`, `/depot`, `/favorites`, `/tools`, `/apps`, `/help`, `/settings`. **Search** uses `/api/categories` for subject dropdowns; suggested queries, history, and saved favorites are **browser-local** only. **`vite preview`** proxies `/api` and `/mcp` to the backend like **`vite dev`** (see `web_sota/vite.config.ts`).
- **Fleet:** `GET /api/fleet` reads `src/arxiv_mcp/data/fleet_default.json` (edit for your hosts). Root **`glama.json`** for Glama discovery.
- **Fleet packaging:** root **`justfile`** (sync, lint, test, serve, `mcpb-pack`), **`llms.txt`** + **`llms-full.txt`**, **`manifest.json`** + **`assets/`** (MCPB prompts + icon), **`assets/prompts/`** (`system.md`, `user.md`, `examples.json`).

## Ports (fleet standard)

| Service | Port |
|--------|------|
| Backend (REST + MCP HTTP) | **10770** |
| Vite dev (dashboard) | **10771** |

Registered in **mcp-central-docs** (`operations/WEBAPP_PORTS.md`, `webapp-registry.json`). Do not use 3000, 5173, 8000, 8080 for this app.

REST (backend):

- `GET /api/health` — liveness
- `GET /api/stats` — depot counts + `data_dir`
- `GET /api/categories` — static subject catalog (`code`, `name`, `group`) for UIs; same list as MCP `listCategories`
- `GET /api/search?q=&limit=&sort_by=&categories=` — arXiv API (categories comma-separated)
- `GET /api/category/latest?category=&limit=&hours=`
- `GET /api/paper?paper_id=`
- `GET /api/corpus?limit=`
- `GET /api/corpus/item?arxiv_id=` — full markdown + metadata
- `GET /api/depot/search?q=&limit=&max_age_days=` — **FTS5** over ingested chunks; `max_age_days` filters out papers older than N days (recommended: 180 for AI/ML topics)
- `POST /api/depot/ingest` JSON `{ "paper_id": "…" }` — fetch HTML → ingest
- `GET /api/favorites` · `POST /api/favorites` JSON `{ arxiv_id, title?, note? }` · `DELETE /api/favorites/{arxiv_id}`
- `GET /api/tools` — MCP tool manifest (dashboard)
- `GET /api/fleet` — fleet hub list
- MCP streamable HTTP: **`/mcp`**
- Dual-transport discovery: **`GET /.well-known/mcp/manifest.json`** — JSON with stdio command and HTTP MCP URL (for indexers and clients that probe well-known URLs).

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
| `arxiv_agentic_assist` | MCP **sampling**: research plan naming concrete tools (`ctx.sample`) |
| `arxiv_sampling_hint` | MCP **sampling**: suggested queries/categories for a topic |

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
pre-commit install
# or: just sync
uv run ruff check src tests
uv run ruff format src tests
uv run pytest
uv run ty check src
```

**Pre-commit:** `.pre-commit-config.yaml` runs **Ruff** (lint + format) and **pytest** on each commit. Run `pre-commit run --all-files` once to verify the whole tree.

**CI:** GitHub Actions (`.github/workflows/ci.yml`) runs Ruff + pytest on every push/PR. **[ty](https://docs.astral.sh/ty/)** (Astral beta type checker) runs on `src` with **`continue-on-error: true`** so the workflow stays green while ty matures and stubs improve.

## A note on arXiv currency — especially for AI papers

arXiv is a preprint server with no peer review, no correction mechanism, no
below-the-line comments, and no retraction pathway for papers superseded by events
rather than by being wrong. This matters more for AI research than almost any other
field, because the subject is iterating faster than the publication cycle.

**Practical guidance when using this tool to research AI topics:**

arXiv spans fields where the relevance decay rate of a paper varies by orders of
magnitude — a mathematics paper from 1994 is as valid today as when it was posted;
a structural engineering paper from 2019 is probably still largely sound; a paper
on AI model capabilities from 2023 may be an artifact of a system that no longer
exists in any meaningful sense. arXiv's interface treats all of these identically.
Nothing in the presentation tells you whether you're reading something with a
half-life of decades or of quarters. You have to supply that judgment yourself.

For AI capability and tooling papers specifically: anything older than ~6 months
should be treated as historical rather than current, regardless of author prestige.
The field moves fast enough that a Q1 2025 benchmark result can be genuinely obsolete
by Q3 2025 — not because the paper was wrong, but because the thing it measured no
longer exists in the same form. A famous name on the author list does not change this.
Geoffrey Hinton, Yann LeCun, and various Apple researchers have all put their names on
arXiv papers in the last two years that were superseded within months by empirical
reality. The arxiv-mcp `list_category_latest` and `search_papers` tools return
publication dates — use them, and weight recency heavily for AI capability claims.

The structural problem: arXiv has no `[SUPERSEDED BY EVENTS]` tag, no living document
mechanism, no way for authors to append "we ran this again six months later and the
numbers reversed." A preprint just sits there accumulating citations regardless of
whether the underlying conditions still hold. This makes arXiv's AI corpus a
sediment of findings from tool and model generations that no longer exist — each
one still citable, still showing up in blog post footnotes, still being wielded in
arguments about what AI can and cannot do.

The `ingest_paper_to_corpus` tool stores publication dates in the corpus. The depot
search endpoint now supports date filtering directly:

```
GET /api/depot/search?q=agentic+coding&max_age_days=180
```

For AI/ML queries, 180 days (six months) is a reasonable default. For foundational
ML theory, mathematics, or engineering domains, omit the filter entirely.

## Repository

- **GitHub:** [github.com/sandraschi/arxiv-mcp](https://github.com/sandraschi/arxiv-mcp)
