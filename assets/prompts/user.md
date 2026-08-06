# arxiv-mcp — user-facing guide (Claude Desktop)

## Getting started

1. Clone the repo and run **`uv sync --extra dev`** (or use **`just sync`**).
2. **Stdio MCP:** `uv run python -m arxiv_mcp --stdio`
3. **HTTP + dashboard:** `uv run python -m arxiv_mcp --serve` then from repo root **`.\start.ps1`** (syncs deps, clears ports, starts backend + Vite). Open **http://127.0.0.1:10771**.

## Typical conversations

### “What’s new in machine learning?”

1. Call **`list_category_latest`** with `category="cs.LG"` and `hours=48`, or **`getRecent`** for the HTML recent list.
2. For each interesting `paper_id`, **`get_paper_details`** then optional **`fetch_full_text`**.

### “Deep-read this arXiv id”

1. **`get_paper_details`** — confirm title, `html_url`, `pdf_url`.
2. **`fetch_full_text`** — if `html_available` is false, say so and suggest PDF pipeline or another version.
3. **`find_connected_papers`** — citations/references for context.
4. **`ingest_paper_to_corpus`** if the user wants local search later.

### “Search like Google but for arXiv”

- Broad keywords: **`search_papers`** or **`search`**.
- Field-specific: **`searchAdvanced`** with `title` / `abstract` / `author` / `id_arxiv` / dates.

### “Full paper text without PDF”

- Try **`fetch_full_text`** first (no third party).
- If insufficient, **`getContent`** (Jina) — warn that it is an external service.

## When to use sampling tools

- **`arxiv_agentic_assist`** — user gives a *goal*; you get a *plan* listing tool names. Use when the user wants a roadmap.
- **`arxiv_sampling_hint`** — user gives a *topic*; you get suggested query lines. Use when keywords are vague.

If sampling returns `success: false`, continue with non-sampling tools only.

## Dashboard

The web UI mirrors REST under `/api/*` and lists tools from the manifest. MCP over HTTP is mounted at **`/mcp`** when using `--serve`.

## Packaging

- **Glama:** `glama.json` at repo root.
- **MCPB:** `manifest.json`, `assets/icon.png`, `assets/prompts/*`. Pack with **`just mcpb-pack`** after installing the **`mcpb`** CLI.

---

*Expand with tutorials, screenshots references, and 100+ examples in `examples.json` for full SOTA alignment.*
