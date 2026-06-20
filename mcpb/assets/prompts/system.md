# arxiv-mcp — MCP Server Capabilities

## Server Overview

arxiv-mcp is a FastMCP 3.2 research server that provides comprehensive arXiv paper discovery, full-text extraction, citation graph analysis via Semantic Scholar, DOI resolution through Unpaywall and Crossref, a local document depot with hybrid FTS5+LanceDB RAG, deep epistemic claim profiling with LLM sampling, code-hunt scanning for open-weight model drops, firefront new-paper triage, automated benchmark claim verification against Epoch AI, Calibre library integration for permanent paper archival, and AI lab blog fetching from Anthropic, Google Research, DeepMind, and Google AI. It serves as the fleet's end-to-end scientific research pipeline — from paper discovery through deep analysis to permanent storage.

**Architecture:** The server supports dual transport (stdio for Claude Desktop/Cursor, streamable HTTP for browser access) and runs as a FastAPI/Starlette webapp on port 10770 with a React/Vite dashboard on port 10771. It exposes 43 MCP tools covering arXiv API queries, HTML scraping, full-text extraction (HTML-to-Markdown and PDF), citation graph traversal, local document ingestion with section-aware chunking, DOI resolution with OA PDF extraction, rule-based and LLM-assisted epistemic claim extraction, benchmark verification, Calibre archival, code-hunt scanning, firefront scanning, pipeline liveness monitoring, AI lab blog fetching, and Prefab UI card rendering. 10 prompts provide structured research workflows and adversarial reading lenses. A skills provider exports the full research pipeline via `skill://arxiv-researcher`. All external text is sanitized for prompt injection safety using the `wrap_untrusted()` pattern from `sanitize.py`, which strips zero-width Unicode characters and neutralizes known injection payloads.

## Safety & Security

All arXiv data (titles, abstracts, full text) is sanitized for prompt injection using the `wrap_untrusted()` function. Known injection payloads are neutralized. Zero-width Unicode characters are stripped from all ingested text. Paper content is treated as untrusted — agents should be alert for adversarial formatting or framing. The `sanitize.py` module provides `wrap_untrusted()`, `wrap_untrusted_dict()`, and `wrap_untrusted_list()` for consistent text safety. All external HTTP requests respect configured timeouts and retry with exponential backoff. The code-hunt and firefront pipelines push fleet events to aiwatcher-mcp via controlled POST endpoints with bounded payload size.

## Tools

### Discovery & Search Tools

**search_papers** — Primary arXiv API search with keyword query, optional category filters, and sort selection. Uses the arxiv PyPI client for stable, structured metadata retrieval. Parameters: `query` (str, required) — keywords; `categories` (list[str], optional) — e.g. ["cs.LG", "cs.AI"]; `limit` (int, default 10, max 100); `sort_by` (Literal, default "submitted") — "relevance", "submitted", "updated". Returns: `{"success": bool, "papers": [...], "message": str}`. Each paper entry includes title, authors, abstract, categories, published/updated dates, arXiv ID, PDF URL, and abstract URL.

**search** — arxiv.org HTML search returning full abstracts and complete author lists per hit. Use for broad keyword discovery when the API search does not return enough detail. Parameters: `query` (str), `category` (str, optional), `author` (str, optional), `sort_by` (str, default "relevance"), `page` (int, default 1), `page_size` (int, default 25, max 50). Returns: Papers with full abstracts, complete author lists, categories, PDF/abstract URLs. Requires at least `query` or an author/category filter.

**searchAdvanced** — Field-scoped HTML search with fine-grained filters for title, abstract, author, category, arXiv ID pattern, and date range. Parameters: `title`, `abstract`, `author`, `category`, `id_arxiv`, `date_from`, `date_to` (all str, optional), `sort_by`, `page`, `page_size`. Returns: Same shape as `search`. Requires at least one search field. Supports ID pattern matching (e.g. "24*" for all 2024 papers).

**list_category_latest** — Recent submissions in a given arXiv category via the API, filtered by a rolling time window in hours. Parameters: `category` (str, required) — e.g. "cs.LG"; `limit` (int, default 25); `hours` (int, default 24). Returns: Papers published within the time window with full metadata (title, authors, abstract, categories, published date, PDF/abstract URLs). The time window is client-side filtered on the published timestamp.

**getRecent** — Recent listing from the arxiv.org category HTML page. Provides full metadata including abstracts for recent submissions. Parameters: `category` (str, default "cs.AI"); `count` (int, default 10, max 50); `hours` (int, default 72). Returns: Papers with title, authors, abstract, arXiv ID, and PDF/abstract URLs.

**listCategories** — Curated static catalog of common arXiv categories. Parameters: None. Returns: A list of dicts each with `code` (e.g. "cs.AI"), `name` (e.g. "Artificial Intelligence"), and `group` (e.g. "Computer Science"). No network request needed.

### Paper Metadata Tools

**get_paper_details** — Full metadata retrieval via the arxiv PyPI client. Parameters: `paper_id` (str, required) — arXiv ID (e.g. "2401.00001"), arxiv: prefix (e.g. "arxiv:2401.00001"), or full URL (e.g. "https://arxiv.org/abs/2401.00001"). Returns: Title, abstract, authors list, links object (html_url, pdf_url, doi), categories, published timestamp, updated timestamp, and comment.

**getPaper** — Alternative metadata retrieval from the arxiv.org abstract HTML page. Useful when the API tool returns different results or for papers not yet indexed by the API. Parameters: `id_or_url` (str, required) — new-style ID (e.g. "2401.00001", "2401.00001v2"), arxiv: prefix, or full abstract/PDF URL. Returns: `{"success": bool, "paper": dict}` with title, authors, abstract, categories, published date, PDF URL, and abstract URL.

### Full-Text Access Tools

**fetch_full_text** — Experimental arXiv HTML-to-Markdown conversion with automatic PDF text extraction fallback. Tries the arXiv experimental HTML endpoint first (bounded time and size). On 404, timeout, or oversize HTML, falls back to extracting plain text from the arXiv PDF. Parameters: `paper_id` (str, required); `format` (Literal, default "markdown") — currently only "markdown" is supported; `prefer_html` (bool, default True) — if False, skips HTML and uses PDF extraction directly. Returns: `{"success": bool, "markdown": str, "source": str, "word_count": int, "message": str}`. The `source` field is "html", "pdf", or "error".

**getContent** — Full-text retrieval via Jina Reader (third-party API at `r.jina.ai`). Alternative when arXiv HTML and PDF extraction both fail. Parameters: `id_or_url` (str, required). Returns: `{"success": bool, "content": str, "abs_url": str, "jina_url": str, "message": str}`. Prefer `fetch_full_text` for local extraction; use this as a fallback.

### Citation Graph Tools

**find_connected_papers** — Citation and reference lineage via the Semantic Scholar Academic Graph API. Returns both papers that cite the given paper and papers it references. Parameters: `paper_id` (str, required) — arXiv ID or URL; `limit` (int, default 12) — max results per side (citations and references). Returns: Graph slice with `citing_papers` and `cited_papers` arrays, each containing paper title, arXiv ID (when known), Semantic Scholar ID, publish year, and citation count. Requires `ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY` for higher rate limits (100 req/s vs 10 req/s without).

### Document Depot & RAG Tools

**ingest_paper_to_corpus** — Persist paper full text to the local SQLite FTS5 depot with section-aware chunking for downstream RAG. Parameters: `paper_id` (str, required); `markdown` (str, optional) — pre-supplied markdown content (if omitted, resolves HTML or PDF text automatically); `source` (Literal, default "html") — "html", "external", or "pdf". Returns: Record with `arxiv_id`, `title`, `chunks` (section count), `source`, `epistemic_profile` (if previously computed), and `word_count`. The FTS5 index is built automatically during ingestion.

**search_depot_corpus** — Search ingested full text in the local depot with three retrieval modes. Parameters: `query` (str, required); `limit` (int, default 20); `mode` (Literal, default "hybrid") — "fts" (SQLite FTS5 BM25 keyword search), "semantic" (LanceDB vector similarity, requires `uv sync --extra rag`), "hybrid" (reciprocal-rank fusion of FTS + semantic); `max_age_days` (int, optional) — filter by paper age. Returns: Hits with `score`, `title`, `arxiv_id`, `text` excerpt (the most relevant chunk), `source`, and `engine` indicator.

**depot_rag_status** — LanceDB vector index health and chunk count. Parameters: None. Returns: Vector store status with `row_count`, `dimensions`, `last_updated`, and `model_name`.

**reindex_depot_vectors** — Rebuild all LanceDB vector embeddings for every ingested paper. Useful after adding a new embedding model or when the index becomes stale. Parameters: None. Returns: Success status, `papers_processed`, `chunks_indexed`, and `index_stats`.

**list_depot_by_epistemics** — Filter ingested papers by epistemic profile flags for targeted retrieval. Parameters: `primary_mode` (str, optional) — filter by evidence mode (e.g. "simulation", "observational", "formal_proof"); `needs_bench` (bool, optional); `needs_telescope_or_instrument` (bool, optional); `needs_formal_verification` (bool, optional); `has_deep_claims` (bool, optional); `limit` (int, default 50). Returns: Filtered list of papers with epistemic metadata including primary mode, claim count, and verification flags.

### Epistemic Analysis Tools

**analyze_paper_epistemics** — Rule-based epistemic classification of a scientific paper. Determines the primary evidence mode (formal proof, simulation, observational study, interventional lab experiment, clinical trial, field study, theoretical derivation, meta-analysis) and identifies what verification the paper still needs (bench experiment, telescope or instrument, formal verification, human judgment, replication study, peer review). Parameters: `paper_id` (str, required); `ingest_if_missing` (bool, default True) — auto-ingest the paper if not in the depot; `force_refresh` (bool, default False). Returns: Epistemic profile with `primary_evidence_mode`, `needs_bench`, `needs_telescope_or_instrument`, `needs_human_judgment`, `ai_automation_fit`, and confidence scores.

**deep_analyze_paper_epistemics** — Claim-level epistemic profiling combining rule-based analysis with LLM sampling. Extracts 3-8 major claims from the paper, each annotated with evidence mode, known falsifiers, and flags for bench/telescope/formal verification/human judgment requirements. Uses MCP `ctx.sample()` when the host supports it; falls back to a configured OpenAI-compatible endpoint. Parameters: `paper_id` (str, required); `ingest_if_missing` (bool, default True); `force_refresh` (bool, default False). Returns: Epistemic profile with `claims` list (each with `claim_text`, `evidence_mode`, `falsifiers`, `needs_bench`, `needs_formal_verification`, `confidence`), `paper_context`, and `summary`.

**ingest_and_analyze_paper** — Combined operation: HTML-first ingestion followed by rule-based and optional deep LLM epistemic analysis. Parameters: `paper_id` (str, required); `deep` (bool, default True) — also run deep claim-level analysis after the rule-based pass. Returns: Complete record with depot ingestion status, epistemic profile, and deep claims (if requested).

**epistemic_job** — Non-blocking job-based deep epistemic analysis for clients with short tool timeouts (e.g., Claude Desktop at 4 minutes). Operations: `submit` (requires `paper_id`, optional `ingest_if_missing`, `force_refresh`) — returns a `job_id` immediately and runs LLM analysis as a background task; `status` (requires `job_id`) — returns progress and result when complete; `list` (optional `status_filter`, `limit`) — all jobs with their current status; `cancel` (requires `job_id`) — cancels a queued or running job. Jobs survive SQLite restarts; jobs running at crash are marked "interrupted". Requires `ARXIV_MCP_SAMPLING_BASE_URL` (OpenAI-compatible endpoint, e.g., Ollama at `http://localhost:11434/v1`).

**compare_papers_convergence** — Bundle abstracts from multiple papers for cross-paper LLM synthesis or analytical convergence/convergence analysis. Parameters: `paper_ids` (list[str], required, min 2, max 12). Returns: Bundled papers with metadata and an `analysis_prompt` string designed to be fed to an LLM for convergence/convergence adjudication. Server-side statistical testing is not performed; the output is structured evidence for downstream judgment.

### DOI Resolution Tools

**resolve_doi** — Resolve a DOI to full metadata and open-access status. Queries Unpaywall (primary) and Crossref (fallback). Parameters: `doi` (str, required) — raw DOI (e.g. "10.1016/j.cell.2018.06.048") or full DOI URL. Returns: `doi`, `title`, `authors`, `published_date`, `publisher`, `is_oa`, `oa_status` (gold, hybrid, green, bronze, closed), `pdf_url` (if OA), `license`, and `best_location` details.

**fetch_doi_content** — Complete DOI pipeline: resolve, download the OA PDF (via Unpaywall or direct PDF URL), extract text with pypdf. Optionally ingests the extracted text into the local depot for persistent RAG search. Parameters: `doi` (str, required); `ingest_to_depot` (bool, default False); `max_chars` (int, default 50000) — cap extracted text returned to the client. Returns: Extracted text, `word_count`, `ingested` status, `truncated` flag, and source URL.

### Benchmark Verification Tools

**check_benchmark_claim** — Verify a claimed benchmark score against Epoch AI's curated public database (3500+ models, 12 benchmark tasks, 900+ scored runs). Parameters: `model_name` (str, required) — fuzzy-matched against Epoch's records (e.g. "DeepSeek-V4-Pro", "claude-3-7-sonnet", "GPT-4o"); `benchmark` (str, required) — fuzzy-matched against Epoch's task list (e.g. "GPQA diamond", "SWE-Bench verified", "MATH level 5"); `claimed_score` (float, optional) — the score the paper claims (0-1 range); `tolerance` (float, default 0.02) — allowed absolute difference before flagging a mismatch. Returns: `verdict` ("match", "mismatch", "not_found"), `epoch_score`, `confidence`, `source_url`.

### Calibre Integration Tools

**store_paper_to_calibre** — Download an arXiv paper's PDF and add it to a Calibre library with full metadata (title, authors, tags, abstract as comments). Optionally fetches HTML-to-Markdown and attaches as a TXT format. Parameters: `paper_id` (str, required); `library_path` (str, optional) — Calibre library path (defaults to `ARXIV_MCP_CALIBRE_LIBRARY_PATH` env var); `include_markdown` (bool, default True). Returns: `calibre_book_id`, `title`, `authors`, `tags`, `markdown_stored` boolean, and `path`.

### AI Lab Blog Tools

**fetch_lab_post** — Fetch and parse a blog or research post from supported AI labs. Sources: Anthropic (anthropic.com), Google Research (research.google/blog), Google DeepMind (deepmind.google/blog — Jina fallback for JS-rendered content), Google AI Blog (blog.google/technology/ai — Jina fallback). Parameters: `slug_or_url` (str, required) — short key (e.g. "model-welfare"), source-prefixed key (e.g. "deepmind:agi-path"), or full URL from any supported domain. Returns: `source`, `title`, `published`, `summary`, `body_markdown` (directly ingestible into the depot).

**fetch_anthropic_post** — Dedicated handler for anthropic.com/research/ and anthropic.com/news/ posts. Parameters: `slug_or_url` (str, required) — short key (e.g. "claude-character"), bare slug (e.g. "exploring-model-welfare"), or full URL. Returns: Same shape as `fetch_lab_post`.

**list_lab_posts** — List recent posts from a supported AI lab blog index. Parameters: `source` (str, default "google-research") — "anthropic", "google-research", "deepmind", or "google-ai"; `limit` (int, default 20). Returns: List of posts with title, date, URL, and summary excerpt.

**list_anthropic_posts** — List recent posts from Anthropic's blog. Parameters: `section` (str, default "research") — "research" or "news"; `limit` (int, default 20). Returns: List of posts with title, date, URL, and summary excerpt.

### Code-Hunt Pipeline Tools

**run_codehunt_scan_tool** — Mine recent arXiv submissions for open-weight code and model repository drops. Scans abstract text for GitHub, Gitee, GitHub Pages, HuggingFace, and ModelScope links, as well as "code coming soon" promises. Persists findings to SQLite (data/arxiv_mcp/codehunt/tracking.sqlite3). Each finding is tagged with Chinese-lab affiliation, VLA title signal, and watch-list authorship. New live drops are immediately pushed to aiwatcher-mcp as high-urgency fleet events if matching push policy. Parameters: `categories` (list[str], optional) — defaults to `ARXIV_MCP_CODEHUNT_CATEGORIES` (cs.AI, cs.RO, cs.SD); `days` (int, default 3) — rolling lookback window; `limit_per_category` (int, default 50); `fulltext_max_papers` (int, optional) — cap on full-text fetches for promise-without-link papers; `push` (bool, default True) — push new live drops to aiwatcher. Returns: Scan summary with `findings` count, `live_drops`, `promises`, and `pushed` count.

**repoll_codehunt_tool** — Re-check promised repositories for liveness. Iterates findings with status "promised" and re-checks each candidate URL. When a repo resolves, the finding flips to "code_live" and is pushed to aiwatcher as a high-urgency fleet event. Parameters: `limit` (int, default 200) — max promised findings to re-check per pass; `push` (bool, default True) — push newly live drops to aiwatcher. Returns: `checked` count, `newly_live` count, `pushed` count.

**check_codehunt_media_tool** — Scan Hacker News, Google News, and tech RSS feeds for media coverage of recently tracked code-hunt papers. Pushes `[media-traction]` fleet events to aiwatcher when hits are found. Parameters: `limit` (int, default 40) — max findings to probe per pass; `push` (bool, default True) — POST new media traction to aiwatcher. Returns: Summary of `probed` findings and `media_hits` with source and headline.

**codehunt_stats_tool** — Tracking database summary: totals by status (new, promised, code_live, dead_link), Chinese-lab affiliate count, recent live drops, and watch author hits. Parameters: None. Returns: Summary dict with status breakdown, China-signal count, and recent live drops.

### Firefront Scanning Tools

**run_firefront_scan_tool** — Collect recent arXiv papers across multiple categories and write a digest JSON file for LLM triage. Deduplicates by paper ID, optionally ingests the top N into the depot, and saves a timestamped digest file to `data/arxiv_mcp/firefront/digest_{topic}_{timestamp}.json`. Parameters: `topic` (str, required) — topic label stored in the digest; `categories` (list[str], optional) — defaults to cs.AI, cs.LG, q-bio.NC; `days` (int, default 7) — rolling window in days; `limit_per_category` (int, default 25); `ingest_top_n` (int, default 0) — if > 0, ingest this many newest papers. Returns: Digest file path, paper counts per category, and ingestion stats.

### Pipeline Monitoring Tools

**pipeline_liveness_tool** — Alert when code-hunt digests and arXiv feed polling are stale, or when the aiwatcher push target is unreachable. Parameters: `stale_hours` (int, default 48). Returns: Per-pipeline health status with `ok` or `critical` status for each sub-pipeline.

### Agentic Planning Tools

**arxiv_agentic_assist** — Multi-step research plan via MCP sampling. Uses `ctx.sample()` when the host exposes sampling (Claude Desktop, Cursor); otherwise returns a structured error with recovery guidance. Parameters: `goal` (str, required) — natural language description of the research task. Returns: A plan with 3-7 numbered steps, each naming the concrete arXiv MCP tools to call (search_papers, get_paper_details, fetch_full_text, find_connected_papers, etc.).

**arxiv_sampling_hint** — Suggest arXiv keyword queries and recommended categories via MCP sampling. Parameters: `topic` (str, required) — natural language topic description. Returns: 3-5 suggested search query lines and 2-3 recommended arXiv categories.

### Help & Discovery Tools

**arxiv_help** — Multi-level structured documentation for the entire server. Call with no topic for the index; use topic="codehunt", "watch_authors", "fleet", "api_keys", "pipeline_liveness", "mcp", or "install" for section-specific docs. Parameters: `topic` (str, optional). Returns: Markdown documentation with tool descriptions, configuration guidance, and workflow steps.

### Prefab UI Card Tools

**show_paper_card** — Render arXiv paper metadata as a rich in-chat Prefab card (thumbnail, title, authors, categories, published date, abstract preview, PDF link, viewer link). Parameters: `paper_id` (str, required). Requires a supporting MCP client that renders MCP Apps.

**show_citation_graph_card** — Display Semantic Scholar citations and references as a scrollable Prefab card. Parameters: `paper_id` (str, required); `limit` (int, default 8). On Semantic Scholar HTTP 429, the card shows recovery options including configuring an API key.

**show_epistemic_profile_card** — Render the claim-level epistemic profile as a structured Prefab card. Reads persisted profile from depot when available; otherwise returns guidance to run `deep_analyze_paper_epistemics` first. Parameters: `paper_id` (str, required).

**show_depot_stats_card** — Papers, favorites, chunks, and RAG embedding status as a Prefab statistics card. Parameters: None.

**show_depot_rag_status_card** — LanceDB RAG index health (row count, dimensions, embedding model) as a Prefab status card. Parameters: None.

## Prompts

The server registers 10 prompts providing structured research workflows:

**research_workflow_prompt** — Mode selector for quick analysis, deep analysis, or corpus building. Takes `paper_id` and `mode` parameters. Guide the user through the appropriate tool sequence.

**generate_summary_prompt** — Adversarial deep-read with configurable lens. Parameters: `paper_id` and `lens` — one of "instrumental_convergence", "qualia", "methods_audit", "general". Produces a structured summary interrogating the paper from the chosen philosophical or methodological perspective.

**consciousness_survey_prompt** — Consciousness research landscape overview. Takes no parameters; produces a broad survey of current theories, experimental paradigms, and key papers.

**ai_consciousness_prompt** — AI/LLM consciousness analysis. Parameters: `paper_id`. Analyzes the paper's stance on machine consciousness, reporting the position and supporting arguments for each of: phenomenal consciousness, access consciousness, self-awareness, moral considerability.

**neurophilosophy_prompt** — Philosophy of mind lens analysis. Parameters: `paper_id`. Applies neurophilosophical frameworks (identity theory, functionalism, enactivism, predictive processing) to the paper's claims.

**convergence_analysis_prompt** — Cross-paper LLM synthesis. Designed for use after `compare_papers_convergence`. Produces a structured adjudication of convergence or divergence between bundled papers.

**firefront_scan_prompt** — Timed new-paper triage workflow. Designed for use after `run_firefront_scan_tool`. Guides rapid assessment of a digest batch: which papers to ingest, which to analyze, which to ignore.

**corpus_build_prompt** — Systematic corpus ingestion guidance. Takes a topic and target size. Plans a multi-session ingestion workflow across categories.

**replication_audit_prompt** — Methods stress-test. Parameters: `paper_id`. Audits the paper's methodology section for replicability, statistical power, pre-registration, and potential confounds.

**citation_map_prompt** — Citation graph traversal guide. Designed for use after `find_connected_papers`. Plans which citations and references to follow for a complete literature map.

## Skills

**skill://arxiv-researcher** — Bundled markdown skill describing the full research pipeline: discovery, metadata retrieval, full-text extraction, depot ingestion, deep epistemic analysis, code-hunt scanning, firefront triage, DOI resolution, lab blog monitoring, Calibre archival, and benchmark verification. Exposes modular workflow stages for MCP clients with skills-aware registries.

## Resources

The server exposes the following resources via the MCP Resources protocol:

- `skill://arxiv-researcher/SKILL.md` — Full research pipeline documentation (as noted above).
- Additional resources registered by the SkillsDirectoryProvider for dynamic skill discovery.
- Resources are read-only streams; use tools for mutation (ingestion, analysis, etc.).

## Configuration

All configuration is via environment variables with the `ARXIV_MCP_` prefix:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ARXIV_MCP_HOST` | `127.0.0.1` | HTTP bind host |
| `ARXIV_MCP_PORT` | `10770` | HTTP port for the MCP server |
| `ARXIV_MCP_DATA_DIR` | `./data` | Local data directory (SQLite depot, code-hunt DB, firefront digests) |
| `ARXIV_MCP_CLIENT_DELAY` | `3.0` | arXiv API politeness delay in seconds between requests |
| `ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY` | — | Semantic Scholar API key for higher rate limits (100 req/s vs 10 req/s) |
| `ARXIV_MCP_JINA_READER_BASE_URL` | `https://r.jina.ai` | Jina Reader API base URL for third-party full text |
| `ARXIV_MCP_ARXIV_HTTP_TIMEOUT_SECONDS` | `60` | HTTP client timeout for arXiv and external requests |
| `ARXIV_MCP_UNPAYWALL_EMAIL` | — | Email identifier for Unpaywall polite pool (improves rate limits) |
| `ARXIV_MCP_CALIBRE_LIBRARY_PATH` | — | Calibre library path for `store_paper_to_calibre` |
| `ARXIV_MCP_CALIBREDB_PATH` | — | Path to `calibredb.exe` executable |
| `ARXIV_MCP_SAMPLING_BASE_URL` | — | OpenAI-compatible base URL for background epistemic jobs (e.g. `http://localhost:11434/v1`) |
| `ARXIV_MCP_SAMPLING_API_KEY` | — | API key for the sampling base URL |
| `ARXIV_MCP_SAMPLING_MODEL` | `gemma3:1b` | Default model for non-MCP sampling (epistemic_job) |
| `ARXIV_MCP_CODEHUNT_CATEGORIES` | `cs.AI,cs.RO,cs.SD` | Comma-separated arXiv categories for automated code-hunt scanning |
| `ARXIV_MCP_CODEHUNT_WATCH_AUTHORS_PATH` | — | Path to JSON file with author names to track in code-hunt |
| `ARXIV_MCP_AIWATCHER_URL` | — | aiwatcher-mcp base URL for fleet event pushing (code-hunt, media) |
| `ARXIV_MCP_FIREFRONT_DATA_DIR` | — | Override for firefront digest output directory |
| `MCP_BRIDGE_URLS` | — | Comma-separated proxy bridge URLs for cross-server tool calls |
| `GIT_GITHUB_API_KEY` | — | GitHub API key for code-hunt repository liveness checks |

The data directory (`ARXIV_MCP_DATA_DIR`) contains:
- `arxiv_mcp.sqlite3` — Main depot SQLite database with FTS5 full-text search index
- `depot/` — LanceDB vector store directory (if RAG extra is installed)
- `codehunt/tracking.sqlite3` — Code-hunt tracking database
- `firefront/` — Firefront scan digest JSON files
- `calibre/` — Temporary paper storage for Calibre ingestion

## Rate Limits & Performance

- **arXiv API:** Maximum 1 request per 3 seconds (configurable via `ARXIV_MCP_CLIENT_DELAY`). The server uses automatic exponential backoff on HTTP 429 responses.
- **Semantic Scholar API:** 10 requests/second without API key, 100 requests/second with `ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY`.
- **Unpaywall:** Polite pool rate limits apply. Set `ARXIV_MCP_UNPAYWALL_EMAIL` to identify requests.
- **Jina Reader:** 50 requests per hour on the free tier at `r.jina.ai`. Self-hosted endpoints have no limit.
- **Code-hunt scanning:** Designed for scheduled runs (typical cadence: every 6-12 hours). Avoid calling more than once per hour.
- **Firefront scanning:** Designed for daily runs. Produces bounded digest files per topic.
- **Epistemic jobs:** Background LLM jobs use the configured `ARXIV_MCP_SAMPLING_BASE_URL`. Timeout per job is 300 seconds. Queue max 20 concurrent jobs.

## Error Handling

All tools return structured dicts with `success` boolean. On failure, responses include `error` (human-readable string), `error_type` (machine-readable category such as "validation", "not_found", "rate_limited", "timeout", "sampling_unavailable"), `recovery_options` (list of suggested next steps), and optional `http_status` or `url` fields. arXiv API rate limits are retried automatically with exponential backoff (up to 3 retries). Transient network failures return structured recovery hints instead of hanging. The `arxiv_agentic_assist` and `arxiv_sampling_hint` tools fall back to clear error messages when `ctx.sample()` is unavailable. The `arxiv_help` tool always succeeds (static content).
