# Troubleshooting

## Server doesn't appear in Cursor / Claude Desktop

**Cause:** Invalid JSON, wrong path, or missing uv
**Fix:** Validate config. Use absolute `--directory` path. `winget install Astral.uv`. Restart host. See [CURSOR-MCP.md](./CURSOR-MCP.md).

## Dashboard shows "Search failed" / backend offline

**Cause:** Backend not running on **10770**
**Fix:** Run `.\start.ps1` or `just dev`. Check `GET http://127.0.0.1:10770/api/health`.

## Port 10770 or 10771 already in use

**Cause:** Another fleet server or stale process
**Fix:** Set `ARXIV_MCP_PORT` in `.env`. Update proxy target in `web_sota/vite.config.ts` if frontend port changes.

## arXiv 403 / rate limited

**Cause:** Too many requests to arXiv API
**Fix:** Increase `ARXIV_MCP_CLIENT_DELAY_SECONDS` (default 3s). Reduce parallel fetches. See [ARXIV.md](./ARXIV.md).

## Semantic / hybrid search unavailable

**Cause:** RAG extra not installed
**Fix:** `uv sync --extra rag`. Confirm `ARXIV_MCP_RAG_ENABLED=1`. Startup probe warns if LanceDB deps missing.

## `resolve_doi` fails

**Cause:** Missing Unpaywall email
**Fix:** Set `ARXIV_MCP_UNPAYWALL_EMAIL` in `.env` or MCP `env`. See [DOI_RESOLUTION.md](./DOI_RESOLUTION.md).

## SQLite / depot errors

**Cause:** `ARXIV_MCP_DATA_DIR` not writable
**Fix:** Ensure directory exists and user has write permission. Default: `data/arxiv_mcp`.

## Full-text fetch timeout

**Cause:** Large HTML or slow network
**Fix:** Tune `ARXIV_MCP_FETCH_FULL_TEXT_BUDGET_SECONDS` and `ARXIV_MCP_FETCH_FULL_TEXT_MAX_BYTES`.

## Sampling / epistemic deep analysis fails

**Cause:** Ollama not running or wrong URL
**Fix:** Start Ollama. Set `ARXIV_MCP_SAMPLING_BASE_URL` / `ARXIV_MCP_SAMPLING_MODEL`. Or disable with `ARXIV_MCP_EPISTEMIC_DEEP_ENABLED=0`.

## Code-hunt push to aiwatcher fails

**Cause:** aiwatcher down or API key mismatch
**Fix:** Start aiwatcher-mcp. Match `ARXIV_MCP_AIWATCHER_API_KEY` to aiwatcher's key. See [FLEET_INTEGRATION.md](./FLEET_INTEGRATION.md).

## `just` not found

**Fix:** `winget install Casey.Just` — or use [INSTALL.md](../INSTALL.md) Option B/C without just.

## Dependencies out of sync

**Fix:** `uv sync --extra dev --extra rag` and `Set-Location web_sota; npm install`

## In-chat help

From MCP host or REST:

```
arxiv_help(topic="install")
arxiv_help(topic="codehunt")
GET /api/help/fleet
```

## Still stuck

[Open a GitHub issue](https://github.com/sandraschi/arxiv-mcp/issues) with `/api/health` output (no secrets).
