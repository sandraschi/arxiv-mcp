# Changelog

All notable changes to **arxiv-mcp** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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

## [Unreleased]

### Added
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
