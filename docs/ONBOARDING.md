# ONBOARDING — arxiv-mcp

First-timer path from zero to first paper search in under 10 minutes.
No account, no API key, no wrappee install required: arXiv and OpenAlex
are public APIs. (Semantic Scholar key is optional, for higher rate limits.)

## What this is

arxiv-mcp is a research pipe for agents and humans: search arXiv, extract
full text (experimental HTML with PDF fallback), walk citation graphs,
resolve DOIs to open-access PDFs, and keep a local full-text depot (SQLite
FTS5 + optional LanceDB vectors) for repeat research.

## Cost / accounts

- Money: $0. No credit card anywhere in this flow.
- Accounts: none required. Optional: `SEMANTIC_SCHOLAR_API_KEY` in `.env`
  (raises Semantic Scholar rate limits for citation graphs).
- Install surface: Python 3.11+ via `uv`, or the `.mcpb` bundle for
  Claude Desktop (see README one-liner).

## Install (pick one)

**A. From source (developers):**

```powershell
git clone https://github.com/sandraschi/arxiv-mcp
cd arxiv-mcp
uv sync
uv run pytest tests/ -q   # expect 160 passed
```

**B. Claude Desktop bundle:**

Download `arxiv-mcp.mcpb` + `install.ps1` from the latest GitHub release,
run `install.ps1`. No build step, no Python needed.

## Connect an agent client

Stdio (Claude Desktop / Claude Code):

```json
{ "mcpServers": { "arxiv-mcp": { "command": "uv", "args": ["run", "python", "-m", "arxiv_mcp"] } } }
```

HTTP (webapp dashboard + remote agents): `start.ps1` launches the backend
on **10770** and the Vite dashboard on **10771**. Health: `GET /api/health`.

## Sanity check (do this now)

1. MCP: call `search_papers(query="diffusion language models", limit=3)` —
   expect `{"success": true, "papers": [...]}`.
2. Depot: call `ingest_paper_to_corpus(paper_id="2501.00001")` —
   expect `{"success": true, ...}`.
3. Recall: call `search_depot_corpus(query="diffusion", mode="fts")` —
   expect your ingested paper back.
4. Dashboard: open `http://127.0.0.1:10771/dashboard` — backend dot green.

If step 1 429s: the server retries with backoff automatically; wait 60s and
retry (see issue #1 for the long-term rate-limit work).

## Pitfalls

- First `fetch_full_text` on a paper without experimental HTML falls back to
  PDF extraction — slower, plain text, no sections. Normal, not an error.
- `find_connected_papers` needs the paper to exist in the Semantic Scholar
  graph; very new preprints may return `found: false` with recovery options.
- LanceDB vector search needs `uv sync --extra rag`; FTS works out of the box.
- Never hardcode ports: backend 10770 / webapp 10771 per
  `mcp-central-docs/operations/WEBAPP_PORTS.md`.

## Next steps

- Skim `docs/TOOLS.md` for the full tool table, `docs/CODEHUNT.md` for the
  open-weight code-drop scanner, `docs/CONFIGURATION.md` for env vars.
- Webapp tour: Dashboard → Search arXiv → Inbox (triage) → Your library.
