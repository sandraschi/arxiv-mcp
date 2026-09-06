# Changelog

All notable changes to **arxiv-mcp** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased] — 2026-08-27

### Fixed
- **RAG extras gap**: `uv sync --extra rag` had not been run in this checkout, so `fastembed`/`onnxruntime`/`tokenizers` were missing. `ingest_paper_to_corpus` was silently falling back to FTS-only (`vector_indexed: false, reason: "deps_missing"`) instead of failing loudly. Ran `uv sync --extra rag` (installed fastembed 0.8.0, onnxruntime 1.26.0, tokenizers 0.22.2, huggingface-hub 1.16.1, and related deps).
- **Reindex blocked pending service restart**: `reindex_depot_vectors` still throws `DLL load failed while importing lib` after the sync, because the running `arxiv-mcp` Windows service loaded its Python process before the new packages were installed and needs a restart to pick them up. Service restart attempted via MCP tooling failed with `Access is denied` (OpenSCManager) — needs an elevated/manual restart of the `arxiv-mcp` service, then rerun `reindex_depot_vectors`.

## [Unreleased] — 2026-07-04

### Added
- **Depot fullscreen toggle**: `Maximize2`/`Minimize2` button in reader header bar; expands to a fixed overlay with full viewport reading area and same Profile/Full text tab toggle.
- **CSS zoom fallback**: Ctrl+Scroll Wheel now works in dev browser via `document.documentElement.style.zoom` (not just Tauri setZoom).

### Fixed
- **Depot reader**: `max-h-[480px]` cap removed for the overlay mode; full text rendered as `max-w-3xl mx-auto` for comfortable reading.

### Added
- **arxiv-expert skill**: Complete SKILL.md at `skill://arxiv-expert/SKILL.md` covering 7 core workflows (paper discovery, full-text, ingest+analyze, depot RAG, code-hunt, benchmark verification, Readly bridge, fleet ingest). Discoverable via SkillsDirectoryProvider. Injected as system preprompt in webapp ChatPage.
- **Readly bridge** and **fleet events pipeline** documented in skill and prompts.

### Fixed
- **Lint green**: 25 pre-existing issues fixed (S110 try-except-pass → real logging, S311 random → time-based jitter, S314 xml → defusedxml, E501 line wraps, E402 import reorder, E701 multi-statement splits). 1 noqa remains (re-export in anthropic_blog.py — legitimate edge case).
- **fastmcp version**: Bumped from `>=3.2.0` to `>=3.4.2` in pyproject.toml.
- **`.mcpbignore`**: Added exclusions for native/, web_sota/, data/, lancedb/, cache/, http_cache/ — reduced mcpb package from 428 MB to 1.4 MB.
- **Manifest tool list**: Expanded from 18 to 42 tools (was missing epistemic, code-hunt, firefront, Prefab card, blog, Calibre, depot RAG tools).
- **SOTA 3-4-100 prompts**: system.md 1,594→3,665 words, user.md 1,343→4,414 words, examples.json 71→114 entries.
- **Root manifest.json**: Stale duplicate removed, BOM corruption fixed.
- **mcpb-pack recipe**: Added to justfile.
- **Stale artifacts**: `.bak` files and `__pycache__/` cleaned from `mcpb/src/`.

### Changed
- Registered `SkillsDirectoryProvider` scanning `src/arxiv_mcp/skills/` for skill discovery.
- Webapp ChatPage fetches skill as system preprompt on mount.

## [0.8.0] — 2026-06-05

### Added
- **`epistemic_job` tool** — Job-based deep epistemic analysis (P2: Claude Desktop's 4-minute tool timeout killed `ingest_and_analyze_paper(deep=True)` / `deep_analyze_paper_epistemics` when sampling is slow). Portmanteau: `submit` returns a `job_id` immediately and runs the LLM claim extraction as a background asyncio task; `status` polls (returns full result when complete); `list` with optional status filter; `cancel` for queued/running jobs. New `services/epistemic_jobs.py` (leanforge-mcp JobManager pattern): SQLite persistence via stdlib `sqlite3` + `asyncio.to_thread` (no new dependency), WAL mode, jobs stranded as `running` at process death are marked `interrupted` on next start. Honesty constraint enforced: background jobs cannot use MCP `ctx.sample` (request context dies at submit-return), so submission fails fast with recovery options unless `ARXIV_MCP_SAMPLING_BASE_URL` is set; the synchronous `deep_analyze_paper_epistemics` keeps the `ctx.sample` path. Tests: `tests/test_epistemic_jobs.py` (9 tests, stubbed analysis — submit/complete, failure persistence, exception boundary, cancel, fail-fast gate, list filters, interrupted-on-restart).

### Fixed
- **Fleet cold-start / RAG deps:** `web_sota/start.ps1` runs `uv sync --extra dev --extra rag` so STARTUP PROBE no longer warns about missing `fastembed`/`pyarrow` when RAG is enabled by default.
- **Fleet probe log capture:** Backend/frontend launch via `Start-FleetDetachedShell` when `FLEET_PROBE_RUN=1` (redirected logs, no `-NoExit` orphan consoles); skips hidden browser poller in probe mode.

### Changed
- **Documentation:** Fleet README structure — short README with TOC; root `INSTALL.md` Options A–D; new `docs/CONFIGURATION`, `TOOLS`, `CURSOR-MCP`, `DEVELOPMENT`, `TROUBLESHOOTING`, `README` index; `MCP_SERVER.md` → `TOOLS.md`.
- **`scripts/FleetStartMode.ps1`:** Synced with fleet standard (`Start-FleetDetachedShell`).

## [0.8.0] — 2026-06-05

### Added
- **Code Hunt** — media traction pipeline (`codehunt_service`, `codehunt_media*`, `codehunt_readly`, `codehunt_affiliations`, `codehunt_watch_authors`); RSS feeds + author watchlists; optional Readly full-text match.
- **Readly bridge** — `readly_client.py`, `POST /api/content/match` consumer; `docs/READLY_INTEGRATION.md`.
- **Fleet ingest** — code-hunt drops push to aiwatcher `POST /api/fleet/ingest`; `docs/FLEET_INTEGRATION.md` (API-key matrix, data-flow diagram).
- **`GET /api/pipeline/liveness`** — `pipeline_liveness_service.py`; probed by `fleet-agent-mcp` `pipeline_liveness` coworker task.
- **Publication subscriptions** — `publication_subscriptions.py`, `publication_auth_fetch.py`, `brighthand_fetch.py`, `firefront_service.py`.
- **HTTP resilience** — shared `http.py` / `http_policy.py` (retries, cache, size caps); tests for extract budgets.
- **Help routing** — `help_content.py` maps `fleet`, `readly`, `api_keys` topics to integration docs.

### Changed
- **Intel lane** — arxiv-mcp positioned as research submarine feeding aiwatcher carrier (fleet philosophy P5).
- **Readly match** — probes readly-mcp `/api/pipeline/liveness` before content match.

### Fleet integration (P5 gap closure)
- **`fleet-registry.json`** — `arxiv-mcp` on **10770** / **10771** in merged 143-entry catalog.
- **`fleet_bridge`** — `arxiv` alias unchanged; morning-brief / day-prep intel flows consume `search_papers` + pipeline probes.

### Documentation
- `docs/CODEHUNT.md`, `docs/PUBLICATION_AUTH.md`, `docs/BOTBLOCK_ANTIPATTERN.md`, `docs/TODO_HTTP_RESILIENCE.md`.

> **Note:** Package version remains **0.7.0** in `pyproject.toml` until next tagged release; this section documents the working-tree fleet-intel drop.

## [0.7.0] — 2026-06-02

### Added
- **Prefab cards**: `show_depot_rag_status_card`, `show_depot_stats_card`, `show_epistemic_profile_card`.
- **`GET /api/capabilities`**, **`GET /api/skills`**, **`GET /api/llm/discover`** — runtime introspection + local LLM scan.
- **Webapp pages**: Chat, Logs, Skills, API docs (Swagger iframe); Tools page uses capabilities.
- **Playwright e2e** smoke (`web_sota/e2e/`).
- **Tests**: capabilities shape, sanitize boundary, DOI truncation helpers.

### Changed
- **RAG stack**: FastEmbed + `BAAI/bge-small-en-v1.5` (fleet standard); **breaking** — reindex after upgrade.
- **Version** unified at **0.7.0**.

## [0.6.0] — 2026-06-02

### Added
- **Deep epistemic profiling (v2)** — `deep_analyze_paper_epistemics`, `list_depot_by_epistemics`, LLM claim tables merged with rule tags (`epistemic_deep.py`).
- **REST**: `POST /api/depot/deep-analyze`, `GET /api/depot/epistemics`, epistemic filters on `GET /api/corpus`.
- **MCP prompt** `epistemic_profile_prompt` for claim-level workflow guidance.
- **Depot UI**: claim table, deep analyze / re-run, epistemic list filters.
- **Startup connectivity probes** — arxiv.org reachability + RAG deps check at lifespan boot (`startup_probe.py`).

### Changed
- **Version coherence** — `0.6.0` propagated to `manifest.json`, `glama.json`, FastAPI, well-known manifest.
- **Personal paths removed from code defaults** — Calibre, temp dir, Unpaywall email now env-overridable (`ARXIV_MCP_*`).
- **CORS** scoped to dashboard origins (`127.0.0.1:10771` / `localhost:10771`); credentials disabled.
- **`manifest.json` stdio args** fixed to `uv run python -m arxiv_mcp --stdio`.

### Fixed
- **`list_ingested_filtered`** — papers without profiles no longer leak into positive epistemic filters.

## [0.5.0] — 2026-06-01

### Added
- **LanceDB hybrid RAG** — vector index on ingest, semantic + hybrid RRF search, reindex tool/API.
- **Section-aware chunking** for depot ingest (`##` headings).
- **Rule-based epistemic profile** — `analyze_paper_epistemics`, `ingest_and_analyze_paper`, depot metadata.

## [0.4.0] — 2026-04-14

### Added
- **`fetch_lab_post`** / **`list_lab_posts`** — generalised multi-source lab blog fetcher covering Anthropic, Google Research (`research.google/blog`), Google DeepMind (`deepmind.google/blog`, Jina fallback for JS-rendered content), and Google AI Blog (`blog.google/technology/ai`, Jina fallback). Source-prefixed keys: `deepmind:agi-path`, `google-research:pair`. Backward-compat wrappers `fetch_anthropic_post` / `list_anthropic_posts` preserved.
- **`src/arxiv_mcp/lab_blog.py`** — new multi-source fetcher; `anthropic_blog.py` reduced to a shim re-exporting from it.
- **Backend**: `GET /api/lab/sources`, `GET /api/lab/posts`, `POST /api/lab/fetch` added alongside existing `/api/anthropic/*` endpoints.
- **Webapp**: "Anthropic" page → "Lab Blogs" with source selector tabs (Anthropic / Google Research / Google DeepMind / Google AI Blog); JS-heavy sources show advisory banner; known-key quick-fetch buttons update per source; source badge on fetch results.

- **`research_workflow_prompt`** — second MCP prompt; mode: `quick` / `deep` / `corpus`; onboarding + tool-order guidance for agents and clients.
- **`consciousness_survey_prompt`** — maps consciousness research landscape; frameworks: IIT, GWT, HOT, predictive_processing, free_energy, comparative, general; scope: empirical / theoretical / both.
- **`ai_consciousness_prompt`** — analyses AI/LLM consciousness claims; stances: sceptic, functionalist, illusionist, open_question, moral_weight; optional `paper_id`.
- **`neurophilosophy_prompt`** — philosophy of mind lens; traditions: eliminativist, phenomenological, analytical, embodied, enactivist, general; optional `paper_id`.
- **`convergence_analysis_prompt`** — cross-paper synthesis and contradiction map; domains: consciousness, ai_capabilities, neuroscience, mcp_agents, general.
- **`firefront_scan_prompt`** — timed new-paper triage briefing; args: `topic`, `days`.
- **`corpus_build_prompt`** — systematic corpus ingestion plan; args: `topic`, `depth` (shallow/deep).
- **`replication_audit_prompt`** — reproducibility and methods stress-test; optional `paper_id`.
- **`citation_map_prompt`** — citation graph traversal and intellectual lineage; args: `paper_id`, `direction` (references/citations/both).
- **`arxiv-researcher` skill substantially enriched** — full tool reference table, domain search strategies (AI/LLM, consciousness, neurophilosophy, MCP/agents), standard 8-step workflow, all prompts documented, error handling table.

- **Prefab paper card** (`show_paper_card`) — `@mcp.tool(app=True)` tool that renders a rich in-chat card via `prefab-ui`: `CardTitle` (title), `CardDescription` (authors), date + `Badge` chips per category, `Separator` between sections, `Markdown` abstract (800-char truncation, word-safe), `Markdown` links row (Abstract · PDF).
- **`[apps]` optional dependency extra** — `prefab-ui>=0.14.0`; install with `uv sync --extra apps`. Core tools unaffected if extra is absent.
- **`ARXIV_PREFAB_APPS` env toggle** — set to `0` to skip registering the prefab tool (CI, minimal images).
- **`src/arxiv_mcp/tools/prefab/`** module — `__init__.py` (`register_prefab_tools`), `paper_card.py` (`register_paper_card_tool`); wired from `server.py` inside `try/except`.
- **fastmcp floor raised** to `>=3.2.0` (was `>=3.1.0,<4`) for security fixes (GHSA-vv7q-7jx5-f767, CVE-2026-32597).

### Added (0.4.x follow-up, previously unreleased)
- **`resolve_doi`** / **`fetch_doi_content`** — DOI resolution via Unpaywall (primary) + Crossref (fallback). Extracts metadata, OA status, and OA PDF URL. `fetch_doi_content` downloads the PDF, extracts text via pypdf, and optionally ingests to the local FTS depot.
- **`src/arxiv_mcp/doi_resolver.py`** — new module with `DOIResolver` class and `DOIResult` dataclass.
- **`sanitize.py`** — new module with adversarial safety boundary wrapping (`wrap_untrusted`) for prompt injection defense on all LLM-facing content.
- **`GET /api/searchAdvanced`** — REST endpoint mirroring the MCP `searchAdvanced` tool for field-scoped searches (title, abstract, author, category, id).
- **Webapp (search):** Single paper lookup card — paste an arXiv ID, URL, or paper title; retrieves full metadata via API or title search.

### Changed
- **arXiv URL builders** — removed deprecated `size` parameter (arXiv removed it → HTTP 400). `/search/advanced` with `terms-0-*` params deprecated; rewritten to use unified `query` + `searchtype` format.
- **Prefab `__init__.py` and `paper_card.py`** — cleaned up unused noqa directives and imports.
- **Start script** — Root `start.ps1` now delegates to `web_sota\start.ps1` which handles all deps (uv sync, npm install, port clearing, backend + Vite launch).
- **Config** — added `unpaywall_email` setting.

### Fixed
- **Frontend fetch timeout** — added 30s AbortController timeout to all API calls, with human-readable "Request timed out" error.
- **Frontend parseErr** — reads response body once (text first, then JSON parse), preventing "body stream already read" errors.
- **TypeScript clean** — removed unused `Boxes` import in AppLayout, fixed `sortBy` type widening in sweep import, fixed non-null assertions and label associations.
- **Logging** — added module-level `log` to server.py, removed inline `import logging as _log` from except block.

### Documentation
- **`docs/SPEC_DOI.md`** — spec for DOI resolution pipeline.
- **Project page** — `mcp-central-docs/projects/arxiv-mcp/README.md`.
- **`INSTALL.md`** — clarified `web_sota\start.bat` path, simplified quick start.
- **`README.md`** — clarified backend-only vs full-stack install paths.

### Security
- **Prompt injection defense** — new two-layer sanitization: (1) zero-width Unicode stripping (all data paths), (2) adversarial safety boundary wrapping on all MCP tool returns (arxiv titles, abstracts, full text, blog content, DOI metadata). Applied at 6+ intake layers covering 18+ MCP tools. arXiv API entry points also sanitized via `arxiv_html.py` parsers.
- **Safety wrapping** on arXiv HTML search results (`arxiv_org_search_html`, `arxiv_org_search_advanced_html`, `arxiv_abs_metadata_from_html`, `jina_reader_fetch`, `arxiv_category_recent_html`).
- **Safety wrapping** on blog content (`fetch_lab_post`, `list_lab_posts`, `fetch_anthropic_post`, `list_anthropic_posts`).
- **Safety wrapping** on DOI metadata and extracted PDF text.

### Fixed
- **arXiv search / category listings:** The PyPI **`arxiv`** package exposes `Result.categories` as `list[str]` (v2.x). Server code no longer assumes `.term` on each entry, fixing **HTTP 500** on `/api/search` and related paths when using current `arxiv`.

### Documentation
- **Dual transport** for indexers: `glama.json` lists stdio + HTTP packages; **`GET /.well-known/mcp/manifest.json`**; `README`, `llms.txt`, `llms-full.txt`, `docs/TECHNICAL.md` aligned.

## [0.3.1] — 2026-03-24

### Summary
- FastMCP **3.1** stack; dual transport (stdio + streamable HTTP `/mcp`); dashboard **10770/10771**; Glama + MCPB metadata.

---

*Earlier history: see git log (`git log --oneline`).*
