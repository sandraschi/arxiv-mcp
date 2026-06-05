# Code-hunt — open-weight repo tracking

Code-hunt scans recent arXiv submissions for **repository and weights links** (GitHub, Gitee, HuggingFace, ModelScope, `*.github.io`) and **“code coming soon”** promises. Findings are stored locally and re-polled until repos go live; live drops can push to **aiwatcher-mcp** as fleet events.

## Why it exists

Chinese and open-weight labs often publish the paper first and drop code hours or days later on Gitee/ModelScope before GitHub. Western-only RSS misses that timing. Code-hunt closes the loop with:

1. **Scan** — extract links/promises from abstracts (+ bounded full-text for promise-only papers)
2. **Tag** — China affiliation keywords, VLA title signals, **watch-list authors**
3. **Re-poll** — HTTP liveness on promised URLs (12h scheduled task recommended)
4. **Push** — `POST http://localhost:10946/api/fleet/ingest` when a repo resolves

## MCP tools

| Tool | Purpose |
|------|---------|
| `run_codehunt_scan_tool` | Full category scan + optional immediate re-poll |
| `repoll_codehunt_tool` | Re-check `promised` findings only |
| `codehunt_stats_tool` | SQLite totals, China/watch counts, recent live |
| `pipeline_liveness_tool` | Stale digest + aiwatcher reachability |
| `arxiv_help` | This documentation inside the MCP client |

## REST (port 10770)

| Method | Path |
|--------|------|
| POST | `/api/codehunt/scan` |
| POST | `/api/codehunt/repoll` |
| GET | `/api/codehunt/stats` |
| GET | `/api/pipeline/liveness` |
| GET | `/api/help` / `/api/help/{topic}` |

## Configuration (`.env`)

| Variable | Default | Meaning |
|----------|---------|---------|
| `ARXIV_MCP_CODEHUNT_CATEGORIES` | `cs.AI,cs.LG,cs.RO,cs.SD` | Categories to scan |
| `ARXIV_MCP_CODEHUNT_PRIORITY_CATEGORIES` | `cs.SD` | Always push live drops in these cats (FunASR/audio) |
| `ARXIV_MCP_CODEHUNT_CHINA_ONLY_PUSH` | `1` | If `1`, only push China / watch-author / VLA / priority-cat drops |
| `ARXIV_MCP_CODEHUNT_FULLTEXT_MAX_PAPERS` | `12` | Full-text budget for promise-without-link |
| `ARXIV_MCP_AIWATCHER_BASE_URL` | — | e.g. `http://localhost:10946` |
| `ARXIV_MCP_AIWATCHER_API_KEY` | — | **Same value as** `AIWATCHER_API_KEY` when auth is on |
| `ARXIV_MCP_CODEHUNT_WATCH_AUTHORS_FILE` | — | Optional JSON path (see below) |
| `ARXIV_MCP_CODEHUNT_WATCH_AUTHORS_EXTRA` | — | Comma-separated extra names |

## Tiered affiliations (universities & labs)

Matches institutions and companies in title/abstract/fulltext against
`config/codehunt_affiliations.json`:

- **tier_a_universities** — Tsinghua, University of Tokyo, MIT, Stanford, …
- **tier_a_companies** — Anthropic, DeepMind, OpenAI, Google Research, Meta AI, …
- **tier_b_universities** — solid schools (optional; set `ARXIV_MCP_CODEHUNT_AFFILIATION_MIN_TIER=b`)

Papers from tier-A affiliations are tracked even without repo links (`status: watch_affiliation`).
Live code drops from those papers push to aiwatcher like watch-list authors.

Short tokens (e.g. `mit`) use word-boundary matching to avoid false positives like “commit”.

Override: `data/arxiv_mcp/codehunt/affiliations.json` or `ARXIV_MCP_CODEHUNT_AFFILIATIONS_FILE`.

## Watch-list authors

High-signal researchers (Yann LeCun, Fei-Fei Li, …) are listed in:

`config/codehunt_watch_authors.json`

Override per machine:

`data/arxiv_mcp/codehunt/watch_authors.json`

**Behavior:**

- Papers by watch-list authors are tracked even **without** a repo link (`status: watch_author`).
- When code goes live, pushes to aiwatcher like China/VLA signals (urgency ~8.5).
- `codehunt_stats` reports `watch_author_signal` and `watch_authors_configured`.

Add names via env: `ARXIV_MCP_CODEHUNT_WATCH_AUTHORS_EXTRA=Your Name,Colleague Name`

## Media traction (~1 week after arXiv)

For tracked high-signal papers, a **daily** pass probes:

- **Hacker News** (Algolia API) for arXiv ID / story links
- **Google News RSS** for tech/MSM headlines mentioning the paper
- **Tech magazine RSS** (Ars Technica, Verge, MIT TR, Wired, TechCrunch AI, IEEE Spectrum)

Default window: **7–45 days** after publication (`ARXIV_MCP_CODEHUNT_MEDIA_MIN_AGE_DAYS` / `MAX_AGE_DAYS`).

MCP: `check_codehunt_media_tool` | REST: `POST /api/codehunt/media-check`

Pushes `[media-traction]` fleet events to aiwatcher (`source: arxiv-codehunt-media`).

Scheduled task: `ArxivCodehuntMedia` (daily 09:00) via `install_codehunt_tasks.ps1`.

### Bot-blocking publishers (Ars Technica, anti-AI outlets, etc.)

Many tech sites now return **403 / bot challenges** on direct article HTML fetch. Code-hunt **does not scrape publisher pages** for traction.

**Strategy:**

| Layer | What we use | What we avoid |
|-------|-------------|---------------|
| Aggregators | HN Algolia, Google News RSS | — |
| Syndication | Official outlet RSS feeds (`config/codehunt_media_feeds.json`) | `arstechnica.com` article HTML |
| Metadata only | Title, link, pubDate from RSS | Full article body, paywall bypass |

RSS entries are cached locally (`data/arxiv_mcp/codehunt/media_feed_cache.json`, TTL `ARXIV_MCP_CODEHUNT_MEDIA_FEED_CACHE_HOURS`, default 6h). Hits are tagged `snippet_only: true` and `fetch_policy: rss_metadata_only`.

Override feeds: `ARXIV_MCP_CODEHUNT_MEDIA_FEEDS_FILE` or copy to `data/arxiv_mcp/codehunt/media_feeds.json`.

If a future path needs article text, enable **Ignore bot blocks** in Settings (or `ARXIV_MCP_CODEHUNT_MEDIA_IGNORE_BOTBLOCKS=1`) to use **Jina Reader** on RSS hits—with explicit user consent. See `docs/BOTBLOCK_ANTIPATTERN.md` / `arxiv_help(topic="botblocks")`.

## Push policy (when `CHINA_ONLY_PUSH=1`)

A live repo drop is pushed if **any** of:

- China affiliation keywords detected
- Watch-list author on the paper
- Tier-A (or B) affiliation match (Tsinghua, Anthropic, DeepMind, …)
- VLA keywords in title (Wall-OSS, X-VLA, LeRobot, …)
- Paper category in `CODEHUNT_PRIORITY_CATEGORIES` (default `cs.SD`)

## Storage

- SQLite: `data/arxiv_mcp/codehunt/tracking.sqlite3`
- Digests: `data/arxiv_mcp/codehunt/digest_codehunt_*.json`

## Scheduler (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File D:\Dev\repos\arxiv-mcp\tools\install_codehunt_tasks.ps1
```

Runs scan + re-poll on a repeating schedule.

## Agent prompts

- “Run `run_codehunt_scan_tool` for cs.RO and cs.SD, last 3 days, then `codehunt_stats_tool`.”
- “Call `repoll_codehunt_tool` and list anything that went live.”
- “If `pipeline_liveness_tool` shows stale digests, reinstall scheduled tasks.”
