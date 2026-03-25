# Changelog

All notable changes to **arxiv-mcp** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
