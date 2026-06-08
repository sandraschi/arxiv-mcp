# Configuration

Copy `.env.example` → `.env` in the repo root. Pydantic settings load at startup.

## Core server

| Variable | Default | Description |
|----------|---------|-------------|
| `ARXIV_MCP_HOST` | `127.0.0.1` | Bind address |
| `ARXIV_MCP_PORT` | `10770` | Backend HTTP + MCP mount |
| `ARXIV_MCP_DATA_DIR` | `data/arxiv_mcp` | SQLite corpus, markdown, LanceDB path |

## arXiv API pacing

| Variable | Default | Description |
|----------|---------|-------------|
| `ARXIV_MCP_CLIENT_DELAY_SECONDS` | `3.0` | Seconds between arXiv requests (polite pool) |
| `ARXIV_MCP_ARXIV_MAX_RETRIES` | `4` | Retries on 429/5xx |
| `ARXIV_MCP_ARXIV_BACKOFF_BASE_SECONDS` | `3.0` | Exponential backoff base |
| `ARXIV_MCP_ARXIV_BACKOFF_MAX_SECONDS` | `30.0` | Max backoff wait |
| `ARXIV_MCP_ARXIV_HTTP_TIMEOUT_SECONDS` | `30` | HTTP timeout for arxiv.org HTML search |
| `ARXIV_MCP_HTTP_CACHE_ENABLED` | `1` | Enable response cache |

## Full-text fetch

| Variable | Default | Description |
|----------|---------|-------------|
| `ARXIV_MCP_FETCH_FULL_TEXT_BUDGET_SECONDS` | `90` | Wall-clock budget per fetch |
| `ARXIV_MCP_FETCH_FULL_TEXT_MAX_BYTES` | `8000000` | Max HTML bytes before skip |
| `ARXIV_MCP_FETCH_FULL_TEXT_PDF_MAX_CHARS` | `100000` | PDF fallback char cap |
| `ARXIV_MCP_JINA_READER_BASE_URL` | `https://r.jina.ai` | Jina Reader fallback |

## Hybrid RAG depot

Requires `uv sync --extra rag`.

| Variable | Default | Description |
|----------|---------|-------------|
| `ARXIV_MCP_RAG_ENABLED` | `1` | Enable LanceDB vectors |
| `ARXIV_MCP_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | FastEmbed model |
| `ARXIV_MCP_DEPOT_SEARCH_MODE` | `hybrid` | `fts` · `semantic` · `hybrid` |

## Sampling & epistemic deep analysis

| Variable | Default | Description |
|----------|---------|-------------|
| `ARXIV_MCP_EPISTEMIC_DEEP_ENABLED` | `1` | Deep profiling features |
| `ARXIV_MCP_SAMPLING_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible API (Ollama) |
| `ARXIV_MCP_SAMPLING_MODEL` | `llama3.2` | Model name |
| `ARXIV_MCP_SAMPLING_API_KEY` | — | Optional Bearer token |
| `ARXIV_MCP_SAMPLING_MAX_TOKENS` | `2500` | Max tokens per sample |
| `ARXIV_MCP_SAMPLING_TIMEOUT_SECONDS` | `120` | Request timeout |

## DOI / Unpaywall

| Variable | Default | Description |
|----------|---------|-------------|
| `ARXIV_MCP_UNPAYWALL_EMAIL` | — | **Required** for `resolve_doi` / `fetch_doi_content` (polite pool) |

## External APIs

| Variable | Default | Description |
|----------|---------|-------------|
| `ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY` | — | Higher Semantic Scholar rate limits |
| `ARXIV_PREFAB_APPS` | `1` | Set `0` to disable prefab paper cards |

## Calibre bridge

| Variable | Description |
|----------|-------------|
| `ARXIV_MCP_CALIBRE_LIBRARY_PATH` | Calibre library path for `store_paper_to_calibre` |
| `ARXIV_MCP_CALIBREDB_PATH` | Path to `calibredb.exe` |
| `ARXIV_MCP_TEMP_DIR` | Temp dir for PDF staging |

## Code-hunt & fleet

| Variable | Default | Description |
|----------|---------|-------------|
| `ARXIV_MCP_CODEHUNT_CATEGORIES` | `cs.AI,cs.LG,cs.RO,cs.SD` | Categories scanned |
| `ARXIV_MCP_CODEHUNT_PRIORITY_CATEGORIES` | `cs.SD` | Always-push categories |
| `ARXIV_MCP_CODEHUNT_CHINA_ONLY_PUSH` | `1` | Filter aiwatcher pushes |
| `ARXIV_MCP_AIWATCHER_BASE_URL` | `http://localhost:10946` | aiwatcher-mcp ingest URL |
| `ARXIV_MCP_AIWATCHER_API_KEY` | — | Match aiwatcher `AIWATCHER_API_KEY` when auth enabled |

Watch authors: `config/codehunt_watch_authors.json`. Details: [CODEHUNT.md](./CODEHUNT.md), [FLEET_INTEGRATION.md](./FLEET_INTEGRATION.md).

## Readly & publications

See `.env.example` for Readly cross-connect (`ARXIV_MCP_READLY_*`) and licensed publication cookies ([PUBLICATION_AUTH.md](./PUBLICATION_AUTH.md)).

## MCP bridge

| Variable | Description |
|----------|-------------|
| `MCP_BRIDGE_URLS` | Comma-separated upstream MCP HTTP URLs to proxy |

## Setting variables in Claude Desktop

```json
{
  "mcpServers": {
    "arxiv-mcp": {
      "env": {
        "ARXIV_MCP_UNPAYWALL_EMAIL": "you@example.com",
        "ARXIV_MCP_RAG_ENABLED": "1"
      }
    }
  }
}
```

Config paths: Windows `%APPDATA%\Claude\claude_desktop_config.json` · macOS `~/Library/Application Support/Claude/claude_desktop_config.json`
