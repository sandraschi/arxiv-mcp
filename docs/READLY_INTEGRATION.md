# Readly cross-connect

arxiv-mcp talks to **readly-mcp** for subscriber full-text across thousands of magazines (New Scientist, Nature, Scientific American, …).

## Architecture

```
arxiv-mcp (media traction)
    POST readly-mcp /api/content/match  {query, magazines}
         ▲
    readly-mcp Playwright + READLY_AUTH_TOKEN
         ▲
    Your Readly subscription (full issue text)

Parallel paths:
  • New Scientist **website** — RSS in codehunt_media_feeds + optional cookie auth
  • New Scientist **magazine** — Readly search + article list + extract
  • aiwatcher — READLY_ENABLED poll (existing)
```

## Enable

**readly-mcp** (port **10863** default):

```env
READLY_AUTH_TOKEN=...
WEB_PORT=10863
```

**arxiv-mcp**:

```env
ARXIV_MCP_READLY_ENABLED=1
ARXIV_MCP_READLY_MCP_URL=http://127.0.0.1:10863
ARXIV_MCP_READLY_VALID_TILL=2026-12-31
```

`VALID_TILL` is mandatory when Readly is enabled — expired subs raise **critical** alerts (no silent failure).

## Watch magazines

`config/readly_watch_magazines.json` — titles searched on Readly during media traction:

- New Scientist (default first)
- Scientific American, Nature, Science, MIT Technology Review

Override: `ARXIV_MCP_READLY_WATCH_MAGAZINES_FILE`

## Media traction

`probe_media_traction` / `check_codehunt_media_tool` adds `source: readly` hits when readly-mcp finds matching articles in watch magazines.

Hits include `full_text_via: readly_mcp_subscriber_session` — not anonymous scrape.

## Depot ingest

When `ARXIV_MCP_READLY_INGEST_ON_DEPOT=1`, `ingest_and_analyze_paper` queries readly-mcp after a successful depot ingest and stores `readly_coverage` on the paper's `meta_json`.

```env
ARXIV_MCP_READLY_INGEST_ON_DEPOT=1
ARXIV_MCP_READLY_INGEST_MAGAZINES=New Scientist,Nature,Scientific American,Wired
```

If `READLY_INGEST_MAGAZINES` is empty, `config/readly_watch_magazines.json` is used. Readly failures are logged and do not block ingest — the MCP response includes `readly_coverage: []` on miss.

## API

| Endpoint | Purpose |
|----------|---------|
| `GET /api/settings/readly` | Status, health, watch list |
| `GET /api/settings/publications` | Includes Readly row + alerts |
| readly-mcp `POST /api/content/match` | Magazine search + article match |
| readly-mcp `GET /api/magazines/open?url=` | Open issue in browser |
| readly-mcp `GET /api/pipeline/liveness` | Fleet probe |

## New Scientist

| Channel | How |
|---------|-----|
| Web news | RSS `https://www.newscientist.com/feed/home/` (metadata) |
| Web paywall | Optional `ARXIV_MCP_PUB_NEWSCIENTIST_*` cookie auth |
| Magazine issues | Readly — full issue text via scraper/extract |

## aiwatcher hub (optional)

```
arxiv → aiwatcher ← readly
```

Set `READLY_ENABLED=true` on aiwatcher for continuous magazine polling; arxiv adds **paper-correlated** Readly matches on media traction pass.
