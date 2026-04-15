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
- **`GET /api/categories`** — Static arXiv subject catalog (same data as MCP `listCategories`) for dashboard dropdowns.
- **Webapp (search):** Suggested starter queries (~12), **local query history** and **saved favorites** with topic tags (`localStorage`); load-a-query dropdown; inline errors and empty-state copy when search returns nothing.
- **Webapp (all main pages):** Shared **`PageHero`** intros; plain-language **depot** explanation (local library vs live arXiv search).
- **Vite `preview`:** Same **`/api`** and **`/mcp` proxy** as dev (port **10771**), so `npm run preview` can reach the backend on **10770**.

### Fixed
- **arXiv search / category listings:** The PyPI **`arxiv`** package exposes `Result.categories` as `list[str]` (v2.x). Server code no longer assumes `.term` on each entry, fixing **HTTP 500** on `/api/search` and related paths when using current `arxiv`.

### Documentation
- **Dual transport** for indexers: `glama.json` lists stdio + HTTP packages; **`GET /.well-known/mcp/manifest.json`**; `README`, `llms.txt`, `llms-full.txt`, `docs/TECHNICAL.md` aligned.

## [0.3.1] — 2026-03-24

### Summary
- FastMCP **3.1** stack; dual transport (stdio + streamable HTTP `/mcp`); dashboard **10770/10771**; Glama + MCPB metadata.

---

*Earlier history: see git log (`git log --oneline`).*
