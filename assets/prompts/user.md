# arxiv-mcp — User Guide

## Quick Start

### Prerequisites

- Python 3.11+ (Python 3.13 recommended)
- [uv](https://docs.astral.sh/uv/) for dependency management
- Git for cloning the repository

### Installation

```bash
git clone https://github.com/sandraschi/arxiv-mcp.git
cd arxiv-mcp
uv sync --extra dev
```

For RAG vector search support, also install the optional dependencies:

```bash
uv sync --extra rag
uv sync --extra apps    # For Prefab UI card rendering
```

### Environment Setup

Create a `.env` file in the project root:

```env
# Recommended: Semantic Scholar API key for citation graphs (100 req/s vs 10 req/s)
ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY=your_key_here

# Recommended: Email for Unpaywall DOI resolution polite pool
ARXIV_MCP_UNPAYWALL_EMAIL=your_email@example.com

# Optional: Calibre library for paper archival
ARXIV_MCP_CALIBRE_LIBRARY_PATH=C:\Calibre Libraries\Papers
ARXIV_MCP_CALIBREDB_PATH=C:\Program Files\Calibre2\calibredb.exe

# Optional: OpenAI-compatible endpoint for background epistemic analysis jobs
ARXIV_MCP_SAMPLING_BASE_URL=http://localhost:11434/v1
ARXIV_MCP_SAMPLING_MODEL=gemma3:1b

# Optional: data directory override (default ./data)
ARXIV_MCP_DATA_DIR=./data
```

### Running the Server

**Stdio mode (for Claude Desktop, Cursor, Windsurf):**

```bash
uv run python -m arxiv_mcp --stdio
```

**HTTP mode (for web dashboard and REST API):**

```bash
uv run python -m arxiv_mcp --serve
```

When running in HTTP mode:
- Backend API and MCP HTTP: `http://127.0.0.1:10770`
- React dashboard: `http://127.0.0.1:10771` (requires `cd web_sota && npm run dev` or `start.bat`)

### Registering in Claude Desktop

Add to your Claude Desktop configuration file (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "arxiv-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "arxiv_mcp", "--stdio"],
      "env": {
        "ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY": "your_key_here",
        "ARXIV_MCP_UNPAYWALL_EMAIL": "your_email@example.com",
        "ARXIV_MCP_SAMPLING_BASE_URL": "http://localhost:11434/v1"
      }
    }
  }
}
```

### Registering in Cursor / Windsurf

```json
{
  "mcpServers": {
    "arxiv-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "arxiv_mcp", "--stdio"],
      "env": {
        "ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY": "your_key_here",
        "ARXIV_MCP_UNPAYWALL_EMAIL": "your_email@example.com"
      }
    }
  }
}
```

### MCPB Bundle Installation

If you received a `.mcpb` bundle, install it via:

```bash
mcpb install dist/arxiv-mcp-v0.7.0.mcpb
```

### Verify Connectivity

After connecting, call `search_papers(query="attention mechanism", limit=3)`. You should see a response with paper titles, authors, and abstracts. If the server starts but returns errors, check that arXiv is reachable from your network and increase `ARXIV_MCP_CLIENT_DELAY` to `6.0` if you see rate limit warnings.

### Data Directory Structure

The server creates a data directory on first run (`ARXIV_MCP_DATA_DIR`, default `./data`):

| Path | Contents |
|------|----------|
| `arxiv_mcp.sqlite3` | Main depot database with FTS5 full-text search index. Stores ingested paper text, metadata, epistemic profiles, favorites, and the job queue |
| `depot/` | LanceDB vector store for semantic search (requires `uv sync --extra rag`) |
| `codehunt/tracking.sqlite3` | Code-hunt tracking database for open-weight model scanning |
| `firefront/` | Timestamped digest JSON files from firefront scans |
| `calibre/` | Temporary paper files staged for Calibre ingestion |

The data directory persists across restarts and grows as you ingest papers. To reset, stop the server and delete the relevant files — the server recreates them on startup.

---

## Tutorials

### Tutorial 1: Your First Paper Search

The most common workflow — discover what is new in a field using keyword and category filters.

```
Step 1: Broad search with keywords and categories
→ search_papers(query="diffusion model", categories=["cs.LG", "cs.CV"], limit=15, sort_by="submitted")
  Returns papers with titles, authors, abstracts, and arXiv IDs

Step 2: Get richer detail on a specific paper
→ get_paper_details(paper_id="2401.00001")
  Returns full metadata: title, abstract, complete author list, categories, links

Step 3: Show a visual card (in supporting clients)
→ show_paper_card(paper_id="2401.00001")
  Renders title, authors, abstract preview, PDF link as a Prefab card
```

**When to use which search tool:**
- `search_papers` (API): fast, structured, good for programmatic pipelines and bulk sweeps
- `search` (HTML): full abstracts in every result, better for discovery browsing
- `searchAdvanced` (HTML): field-scoped — search within titles, abstracts, by author, by date range

### Tutorial 2: Browse What Is New in Your Field

Monitor recent submissions in specific arXiv categories to stay current.

```
→ list_category_latest(category="cs.LG", hours=24, limit=25)
  Last 24 hours of machine learning papers

→ getRecent(category="cs.AI", count=15, hours=72)
  Alternative HTML-based recent listing for AI papers

→ listCategories()
  List all arXiv category codes — find the right categories for your field

For multi-category monitoring:
→ list_category_latest(category="cs.CV", hours=48, limit=30)
→ list_category_latest(category="cs.CL", hours=48, limit=30)
→ list_category_latest(category="cs.RO", hours=48, limit=30)
```

Pro tip: Bookmark the categories relevant to your research. Common ones: `cs.AI` (AI), `cs.LG` (ML), `cs.CV` (vision), `cs.CL` (NLP), `cs.RO` (robotics), `q-bio.NC` (neuroscience), `stat.ML` (statistics/ML).

### Tutorial 3: Get Full Text and Build Your Local Corpus

This is the core research workflow: find papers, extract their full text, and persist them for future search.

```
Step 1: Find candidates
→ search_papers(query="reinforcement learning human feedback", categories=["cs.LG"], limit=10)

Step 2: Get metadata for a paper you are interested in
→ get_paper_details(paper_id="2401.00001")

Step 3: Extract full text (HTML preferred, PDF fallback)
→ fetch_full_text(paper_id="2401.00001", prefer_html=true)
  On success: source="html" or source="pdf" tells you where content came from

Step 4: Ingest to local depot for persistent search
→ ingest_paper_to_corpus(paper_id="2401.00001", source="html")
  Paper is chunked along section boundaries and indexed in FTS5

Step 5: Now search your local corpus
→ search_depot_corpus(query="attention mechanism alignment", mode="hybrid", limit=10)
  Returns scored hits with relevant text excerpts from your ingested papers
```

**Fallback chain for full text:**
1. `fetch_full_text(paper_id, prefer_html=true)` — experimental HTML → PDF fallback
2. `fetch_full_text(paper_id, prefer_html=false)` — PDF directly
3. `getContent(paper_id)` — Jina Reader as last resort (50 req/hr free tier)

### Tutorial 4: Understand the Citation Graph Around a Paper

Discover the intellectual neighborhood — who cites this paper, and what does it cite?

```
→ find_connected_papers(paper_id="2401.00001", limit=12)
  Returns: citing_papers (forward) + cited_papers (backward)

Interpretation:
  - Many forward citations = influential paper
  - Highly-cited references = paper builds on important foundations
  - Zero citations on a recent paper = normal, give it time
  - Zero citations on a 2022 paper = limited impact

Visual inspection:
→ show_citation_graph_card(paper_id="2401.00001", limit=8)
  Prefab card with scrollable citation and reference lists

Deep dive:
→ get_paper_details(paper_id=interesting_citing_paper_id)
→ fetch_full_text(paper_id=interesting_citing_paper_id)
```

**Note:** New arXiv papers take 1-4 weeks to appear in Semantic Scholar. If `find_connected_papers` returns empty, the paper may not be indexed yet. Setting `ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY` gives you 100 requests/second instead of 10.

### Tutorial 5: Run Epistemic Analysis on a Paper

Understand what kind of evidence a paper uses and what it would take to verify or falsify its claims.

```
Quick rule-based classification:
→ analyze_paper_epistemics(paper_id="2401.00001")
  Returns: primary_evidence_mode, needs_bench, needs_human_judgment, ai_automation_fit

Deep claim-level analysis (requires LLM sampling):
→ deep_analyze_paper_epistemics(paper_id="2401.00001", force_refresh=true)
  Returns: 3-8 claims, each with evidence_mode, falsifiers, verification flags

Combined: ingest and analyze in one call:
→ ingest_and_analyze_paper(paper_id="2401.00001", deep=true)

For long-running analysis (Claude Desktop 4-minute timeout):
→ epistemic_job(operation="submit", paper_id="2401.00001")
  Returns job_id immediately
→ epistemic_job(operation="status", job_id="returned_job_id")
  Poll until status="complete", then read result.epistemic_profile
```

**Background jobs require** `ARXIV_MCP_SAMPLING_BASE_URL` pointing to an OpenAI-compatible endpoint (e.g. Ollama at `http://localhost:11434/v1`). Jobs use `ARXIV_MCP_SAMPLING_MODEL` (default `gemma3:1b`). Max 20 concurrent jobs.

### Tutorial 6: Filter Your Corpus by Evidence Type

After ingesting many papers, find specific subsets by their epistemic profile.

```
Find papers needing bench verification:
→ list_depot_by_epistemics(needs_bench=true, limit=20)

Find simulation-based papers:
→ list_depot_by_epistemics(primary_mode="simulation", limit=10)

Find papers needing both bench and formal verification:
→ list_depot_by_epistemics(needs_bench=true, needs_formal_verification=true, limit=10)

Find papers with deep claim extraction completed:
→ list_depot_by_epistemics(has_deep_claims=true, limit=50)
```

Useful for systematic reviews: first ingest papers broadly, then filter by verification needs to find the papers most in need of experimental follow-up.

### Tutorial 7: Search Your Ingested Papers with Keywords and Semantics

Once papers are in the depot, search across their full text using three modes.

```
FTS5 keyword search (always available, BM25 ranking):
→ search_depot_corpus(query="reinforcement learning reward model", mode="fts", limit=10)

Semantic vector search (requires uv sync --extra rag):
→ search_depot_corpus(query="how agents learn from human preferences", mode="semantic", limit=5)

Hybrid search (reciprocal-rank fusion, best quality):
→ search_depot_corpus(query="RLHF alignment techniques", mode="hybrid", limit=10)

Filter by paper age:
→ search_depot_corpus(query="transformer architecture", max_age_days=90, limit=10)

Check index health:
→ depot_rag_status()
  Returns: row_count, dimensions, last_updated, model_name

Rebuild vector index after adding embedding deps:
→ reindex_depot_vectors()
```

**When to use each mode:**
- `fts`: You know the exact terminology used in the papers (e.g. "KL divergence", "Adam optimizer")
- `semantic`: You are searching for concepts, not exact keywords (e.g. "how to reduce overfitting")
- `hybrid`: Best of both worlds — use by default

### Tutorial 8: Resolve a DOI and Get the Full Text

For non-arXiv papers behind DOIs, resolve metadata and download open-access PDFs.

```
Step 1: Resolve the DOI for metadata and OA status
→ resolve_doi(doi="10.1016/j.cell.2018.06.048")
  Returns: title, authors, is_oa, oa_status (gold/hybrid/green/bronze/closed), pdf_url

Step 2: If OA, fetch full text and optionally ingest
→ fetch_doi_content(doi="10.1016/j.cell.2018.06.048", ingest_to_depot=true, max_chars=50000)
  Returns: extracted text, word_count, ingested status, truncated flag

Resolve and check OA status without fetching:
→ resolve_doi(doi="10.1038/s41586-024-07155-5")
  Check is_oa and oa_status first — only fetch content if OA is available

Batch DOI workflow:
  1. resolve_doi for each DOI
  2. Filter for is_oa=true
  3. fetch_doi_content for each OA DOI, ingest_to_depot=true
```

**Requires** `ARXIV_MCP_UNPAYWALL_EMAIL` for the Unpaywall polite pool. `fetch_doi_content` needs an actual OA PDF URL from the resolution step — not all papers have open-access versions.

### Tutorial 9: Verify a Claimed Benchmark Score

Cross-check benchmark claims from papers or press releases against Epoch AI's database.

```
Verify a specific claim:
→ check_benchmark_claim(model_name="DeepSeek-V4-Pro", benchmark="GPQA diamond", claimed_score=0.89)
  Returns: verdict (match/mismatch/not_found), epoch_score, confidence, source_url

Check a score without comparison (just look up what is tracked):
→ check_benchmark_claim(model_name="gpt-4o", benchmark="MATH level 5")
  Omit claimed_score — returns Epoch's tracked score without comparison

Check multiple benchmarks for the same model:
For each benchmark in ["GPQA diamond", "MATH level 5", "SWE-Bench verified", "MMLU"]:
  → check_benchmark_claim(model_name="claude-3-7-sonnet", benchmark=benchmark)

Fuzzy matching handles variations:
  "GPT-4o" matches "gpt-4o-2024-05-13" in Epoch's records
  "Claude 3.7 Sonnet" matches "claude-3-7-sonnet-20250219"
```

**Tracked benchmarks:** GPQA diamond, MATH level 5, SWE-Bench verified, MMLU, MMLU-Pro, HumanEval, GSM8K, ARC, BIG-bench, HellaSwag, WinoGrande, ImageNet top-1.

### Tutorial 10: Fetch and Analyze AI Lab Blog Posts

Stay current with AI research outside arXiv — blog posts from Anthropic, Google Research, DeepMind, and Google AI.

```
Discover what is available:
→ list_lab_posts(source="anthropic", limit=10)
→ list_lab_posts(source="google-research", limit=15)
→ list_lab_posts(source="deepmind", limit=10)
→ list_anthropic_posts(section="research", limit=10)

Fetch by short key:
→ fetch_anthropic_post(slug_or_url="model-welfare")
→ fetch_anthropic_post(slug_or_url="claude-character")

Fetch with source prefix:
→ fetch_lab_post(slug_or_url="deepmind:agi-path")
→ fetch_lab_post(slug_or_url="google-research:pair")

Fetch by full URL:
→ fetch_lab_post(slug_or_url="https://research.google/blog/pathways-asynchronous-distributed-training/")

Ingest blog content to depot:
1. post = fetch_lab_post(slug_or_url="model-welfare")
2. ingest_paper_to_corpus(paper_id=post.url, markdown=post.markdown, source="external")
```

Known Anthropic short keys include: `model-welfare`, `claude-character`, `alignment-faking`, `taking-ai-welfare-seriously`, `core-views`, `interpretability-monosemanticity`.

### Tutorial 11: Store Papers in Calibre for Offline Reading

Build a permanent, metadata-rich paper library in Calibre that syncs across devices.

```
Prerequisites:
  - Calibre installed
  - ARXIV_MCP_CALIBRE_LIBRARY_PATH set to an existing Calibre library folder
  - ARXIV_MCP_CALIBREDB_PATH set to calibredb.exe path

Store with both PDF and markdown:
→ store_paper_to_calibre(paper_id="2401.00001", include_markdown=true)
  Returns: calibre_book_id, title, authors, tags (arXiv categories), markdown_stored

Store PDF only (no markdown attachment):
→ store_paper_to_calibre(paper_id="2301.00001", include_markdown=false)

Store to a specific library (override env var):
→ store_paper_to_calibre(paper_id="2201.00001", library_path="C:\\Calibre Libraries\\AI Papers")
```

Tags are derived from arXiv categories (e.g. `cs.LG` becomes `Machine Learning`, `cs.AI` becomes `Artificial Intelligence`). The abstract is stored as an HTML comment in the book metadata.

### Tutorial 12: Run the Code-Hunt for Open-Weight Model Drops

Scan recent arXiv submissions for links to code repositories and "code coming soon" promises.

```
Run a manual scan (testing, no fleet push):
→ run_codehunt_scan_tool(
    categories=["cs.AI", "cs.LG", "cs.RO"],
    days=3,
    limit_per_category=50,
    push=false
  )

Run with fleet push enabled (for production monitoring):
→ run_codehunt_scan_tool(
    categories=["cs.AI", "cs.LG", "cs.RO"],
    days=3,
    push=true
  )

Check current tracking stats:
→ codehunt_stats_tool()
  Returns: status breakdown (new/promised/code_live/dead_link), China-signal count, recent drops

Re-check promised repos for liveness:
→ repoll_codehunt_tool(limit=100, push=false)
  Iterates "promised" findings, re-checks URLs, flips to "code_live" when repos resolve

Check media coverage of tracked papers:
→ check_codehunt_media_tool(limit=20, push=false)
  Scans Hacker News, Google News, tech RSS for coverage
```

The code-hunt is designed for scheduled runs every 6-12 hours. Configure watch authors via `ARXIV_MCP_CODEHUNT_WATCH_AUTHORS_PATH` pointing to a JSON file of author names.

### Tutorial 13: Run a Firefront Scan for Daily Research Triage

Collect recent papers across categories and produce a digest for LLM-assisted review.

```
Run a daily scan:
→ run_firefront_scan_tool(
    topic="weekly-ml-review",
    categories=["cs.LG", "cs.AI", "stat.ML"],
    days=7,
    limit_per_category=25,
    ingest_top_n=5
  )

Run a focused scan for a specific field:
→ run_firefront_scan_tool(
    topic="neuroscience-weekly",
    categories=["q-bio.NC"],
    days=7,
    limit_per_category=30,
    ingest_top_n=3
  )

The digest is saved to data/arxiv_mcp/firefront/digest_{topic}_{timestamp}.json
Use the firefront_scan_prompt for LLM-assisted triage of the digest file.

Check pipeline health:
→ pipeline_liveness_tool(stale_hours=48)
  Returns: per-pipeline health status (ok/critical)
```

### Tutorial 14: Compare Multiple Papers for Convergence

Bundle papers together for cross-paper synthesis — useful for literature reviews.

```
Compare 2 papers:
→ compare_papers_convergence(paper_ids=["2401.00001", "2401.00002"])

Compare a set of related papers:
→ compare_papers_convergence(paper_ids=["2401.00001", "2401.00002", "2401.00003"])

Up to 12 papers at once:
→ compare_papers_convergence(paper_ids=[...up to 12 IDs])

Returns bundled metadata plus an analysis_prompt ready for LLM synthesis.
Combine with the convergence_analysis_prompt for domain-specific questioning.
```

### Tutorial 15: Use Agentic Assist for Research Planning

When you are unsure how to approach a complex research task, let the LLM plan the workflow.

```
Get a step-by-step research plan:
→ arxiv_agentic_assist(goal="Survey vision-language models from 2024-2025, find the most cited papers, read full text, check benchmark claims")

Returns a 3-7 step plan naming concrete tools like search_papers, find_connected_papers, fetch_full_text, check_benchmark_claim.

Get search query suggestions for a topic:
→ arxiv_sampling_hint(topic="mechanistic interpretability of transformer attention heads")

Returns 3-5 suggested search queries and 2-3 recommended arXiv categories.

If sampling is unavailable, the tools return clear error messages with recovery suggestions.
```

### Tutorial 16: Use HTML Advanced Search for Precision

For fine-grained discovery, use field-scoped HTML search that the API cannot match.

```
Search for "attention" in titles AND "transformer" in abstracts:
→ searchAdvanced(title="attention", abstract="transformer")

Search by author and date range:
→ searchAdvanced(author="Bengio", date_from="2024-01-01", date_to="2024-06-30")

Search by category and arXiv ID pattern:
→ searchAdvanced(category="cs.AI", id_arxiv="24*")
  Finds all 2024 cs.AI papers

Search with multiple date filters:
→ searchAdvanced(
    title="reinforcement learning",
    category="cs.LG",
    date_from="2024-01-01",
    date_to="2024-12-31",
    sort_by="date_desc"
  )

Standard HTML search with full abstracts:
→ search(query="transformer", category="cs.LG", sort_by="date_desc", page_size=30)
```

### Tutorial 17: Build a Systematic Research Corpus

Ingest papers systematically for a literature review or research project.

```
Phase 1 — Discover (from corpus_build_prompt):
  → arxiv_sampling_hint(topic="graph neural networks molecules")
  → search_papers(query="graph neural network molecular", categories=["cs.LG", "physics.chem-ph"], limit=30)
  → searchAdvanced(title="graph", abstract="molecule", category="cs.LG")

Phase 2 — Deduplicate and score:
  → get_paper_details(paper_id=candidate_id) for each candidate
  Eliminate duplicates, score by relevance + recency + citation signals

Phase 3 — Ingest (deep mode):
  For each shortlisted paper:
    → fetch_full_text(paper_id)
    → ingest_paper_to_corpus(paper_id)

Phase 4 — Expand via citations:
  → find_connected_papers(paper_id=top_paper) for top 5 by relevance
  Add new high-relevance papers from references to ingest queue

Phase 5 — Analyze the corpus:
  → search_depot_corpus(query="molecular property prediction", mode="hybrid")
  → list_depot_by_epistemics(primary_mode="simulation", limit=20)
```

### Tutorial 18: Audit a Paper for Reproducibility

Use the replication audit workflow to stress-test a paper's methods.

```
Load the replication audit prompt:
  Use the replication_audit_prompt with paper_id="2401.00001"

Workflow:
1. fetch_full_text(paper_id) — get the full text
2. Read the methods section in detail
3. Score each checklist item: PASS / PARTIAL / FAIL / N/A
   - Data: source, size, splits, preprocessing, contamination
   - Model: architecture, hyperparameters, initialisation, ablations
   - Compute: hardware, time, cost
   - Evaluation: metrics, statistics, baselines, code release
   - Release: code, weights, data
4. Assign overall replicability: HIGH / MEDIUM / LOW / UNREPLICABLE
5. List blocking issues and minimum resource requirements
```

---

## Example Conversations

### Conversation 1: "What is new in ML this week?"

> **User:** Show me the most interesting ML papers from the last 7 days.

```
→ search_papers(query="", categories=["cs.LG"], limit=20, sort_by="submitted")
→ search_papers(query="", categories=["cs.AI"], limit=20, sort_by="submitted")
→ For each top paper: show_paper_card(paper_id=id)
  Summarize: 1-2 sentence per paper, what is new, why it matters
```

### Conversation 2: "Deep-dive on a specific paper"

> **User:** I want to understand paper 2404.12345 in depth. Get the full text, analyze the evidence, find related papers.

```
→ get_paper_details(paper_id="2404.12345")
→ fetch_full_text(paper_id="2404.12345")
→ find_connected_papers(paper_id="2404.12345", limit=15)
→ ingest_and_analyze_paper(paper_id="2404.12345", deep=true)
  Summarize: key claims, evidence strength, how it relates to cited/citing papers
```

### Conversation 3: "Fact-check this benchmark claim"

> **User:** A press release claims "Gemini 2.5 Pro achieves 92% on MMLU-Pro." Is this accurate?

```
→ check_benchmark_claim(model_name="Gemini 2.5 Pro", benchmark="MMLU-Pro", claimed_score=0.92)
  If verdict="mismatch": report the actual tracked score and the source
  If verdict="not_found": suggest the benchmark may not be in Epoch AI's database
```

### Conversation 4: "Build me a reading list on mechanistic interpretability"

> **User:** I am new to mechanistic interpretability. Build me a reading list of the top 10 papers.

```
→ arxiv_sampling_hint(topic="mechanistic interpretability transformer circuits")
→ search_papers(query="mechanistic interpretability", categories=["cs.LG", "cs.AI"], limit=30, sort_by="relevance")
→ For top 10: get_paper_details(paper_id=id)
→ find_connected_papers(paper_id=most_cited_id)
  Output: ranked list with title, authors, year, one-sentence summary, why read
```

### Conversation 5: "Check if there are any new open-weight LLMs this week"

> **User:** Scan arXiv for any new open-weight model releases this week.

```
→ run_codehunt_scan_tool(categories=["cs.AI", "cs.LG"], days=7, push=false)
→ codehunt_stats_tool()
  Report: new findings, live drops with repo URLs, promises to watch
```

---

## Troubleshooting

### "Rate limited by arXiv API"

The server enforces a 3-second delay between arXiv requests (configurable via `ARXIV_MCP_CLIENT_DELAY`). If you hit HTTP 429, increase the delay. Retries are automatic with exponential backoff. Reduce request frequency or batch queries.

### "Experimental HTML not available for this paper"

Not all arXiv papers have experimental HTML format. Papers before 2022 and some newer papers only have PDF. Use `fetch_full_text(paper_id, prefer_html=false)` to extract from PDF directly. As a third fallback, use `getContent(paper_id)` via Jina Reader — but note the 50 req/hr free tier limit.

### "Semantic Scholar returns empty citation graph"

New arXiv papers take 1-4 weeks to appear in Semantic Scholar's index. If the paper is very recent, wait and retry. Ensure the paper ID format is correct. With `ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY` you get higher rate limits (100 req/s vs 10).

### "Calibre integration fails"

Verify `ARXIV_MCP_CALIBRE_LIBRARY_PATH` points to an existing Calibre library directory containing a `metadata.db` file. Verify `ARXIV_MCP_CALIBREDB_PATH` is the full path to `calibredb.exe` (typically `C:\Program Files\Calibre2\calibredb.exe` on Windows, `/usr/bin/calibredb` on Linux). Use `include_markdown=false` if the markdown attachment step is failing.

### "Depot search returns no results"

Check that papers have been ingested with `ingest_paper_to_corpus`. The FTS5 index builds during ingestion — no separate step needed. For semantic (vector) search, install `uv sync --extra rag`, then `reindex_depot_vectors()`. Check `depot_rag_status()` to verify the index has rows.

### "Deep epistemic analysis returns empty or incomplete claims"

Deep claim extraction requires MCP sampling (`ctx.sample()`) or a configured `ARXIV_MCP_SAMPLING_BASE_URL`. If neither is available, falls back to rule-based classification only (no individual claims). Set up Ollama at `http://localhost:11434/v1` or configure an OpenAI-compatible endpoint.

### "Background epistemic job never completes"

Jobs require `ARXIV_MCP_SAMPLING_BASE_URL` pointing to a working OpenAI-compatible API. Ensure the endpoint is reachable and `ARXIV_MCP_SAMPLING_MODEL` (default `gemma3:1b`) is available. Check job status with `epistemic_job(operation="status", job_id=...)`. Jobs running at server crash are marked "interrupted" — re-submit them.

### "Code-hunt finds no repositories"

The code-hunt scans abstract text for repository URLs and "code coming soon" language. Not all submissions include these. Run on at least 3-7 days of recent papers. Increase `limit_per_category` or add more categories. The scan is tuned for `cs.AI`, `cs.LG`, `cs.RO`, `cs.SD`, and `cs.CV`.

### "Firefront digest has no papers"

The firefront scanner uses `list_category_latest` for each category. If a category has no recent submissions (weekends, conference deadlines), the digest will be sparse. Increase `days` or add more categories.

### "Prefab cards do not render"

Prefab UI tools (`show_paper_card`, etc.) require a supporting MCP client and `uv sync --extra apps` (which installs `prefab-ui>=0.14.0`). In unsupported clients, the text fallback summary is always included. Set `ARXIV_PREFAB_APPS=0` to disable prefab registration entirely.

---

## FAQ

**Q: What is the difference between search_papers and search?**
A: `search_papers` uses the official arXiv API — fast, structured, good for pipelines. `search` scrapes arxiv.org HTML — provides full abstracts and complete author lists in every result, better for discovery and browsing. `searchAdvanced` adds field-scoped filters (title, abstract, author, date range, ID patterns).

**Q: Can I use this without a Semantic Scholar API key?**
A: Yes. Citation graphs work at 10 requests/second without a key. With `ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY`, the limit is 100 req/s. Without the key, you may hit rate limits during batch processing.

**Q: How do I get full text for older papers (pre-2022)?**
A: Pre-2022 papers rarely have experimental HTML. Use `fetch_full_text(paper_id, prefer_html=false)` for PDF extraction, or `getContent(paper_id)` for Jina Reader. Very old papers (pre-2007) may have no digital full text available through any method.

**Q: What is the local depot and why use it?**
A: The depot is a SQLite database with FTS5 full-text search storing ingested paper content locally. It enables persistent, searchable access without re-fetching from arXiv. Optional LanceDB vector search adds semantic similarity queries. Without the depot, you re-fetch paper text every time.

**Q: How is paper content sanitized for safety?**
A: All arXiv data passes through `wrap_untrusted()` which strips zero-width Unicode characters, normalizes whitespace, and neutralizes known prompt injection patterns. Paper content is treated as untrusted — be alert for adversarial formatting in paper text.

**Q: Can I export papers to Calibre?**
A: Yes. Use `store_paper_to_calibre()` with configured library path and calibredb path. Downloads the PDF, adds it with full metadata (title, authors, categories as tags, abstract as comments), and optionally attaches the HTML-to-Markdown text as a TXT format.

**Q: What is epistemic analysis?**
A: Epistemic analysis classifies papers by evidence type and verification requirements. Rule-based mode identifies primary evidence mode (formal proof, simulation, observational, etc.) and flags what verification the paper needs. Deep mode uses an LLM to extract individual claims with falsifiers and verification flags.

**Q: What is the code-hunt pipeline?**
A: Code-hunt scans recent arXiv submissions for repository URLs (GitHub, Gitee, HuggingFace, ModelScope) and "code coming soon" promises. Tracks findings in SQLite, tags Chinese-lab papers, watches specific authors, and pushes live drops to aiwatcher for alerting. Designed for scheduled runs every 6-12 hours.

**Q: What is the firefront scanner?**
A: Firefront collects recent papers across configurable categories, deduplicates them, and writes a timestamped digest JSON. Designed for daily morning triage — pair with `firefront_scan_prompt` for LLM-assisted review.

**Q: How do I search across ingested papers?**
A: Use `search_depot_corpus` with three modes: `fts` (keyword BM25, always available), `semantic` (vector similarity, requires `uv sync --extra rag`), and `hybrid` (reciprocal-rank fusion of both, default). Filter by paper age with `max_age_days`.

**Q: Can I verify benchmark claims from papers?**
A: Yes. `check_benchmark_claim` cross-references against Epoch AI's database of 3500+ models, 12 benchmarks, 900+ scored runs. Supports fuzzy name matching.

**Q: Can I batch-ingest multiple papers at once?**
A: There is no single batch tool, but you can loop over `ingest_paper_to_corpus` for each paper ID. The FTS5 index updates incrementally. For bulk ops, script a loop with small delays between calls.

**Q: How do I clear the local depot?**
A: Stop the server, delete `{ARXIV_MCP_DATA_DIR}/arxiv_mcp.sqlite3`, and optionally delete `{ARXIV_MCP_DATA_DIR}/depot/` for LanceDB vectors. Restart the server for fresh files. No in-tool reset (prevents accidental data loss).

**Q: Can I use the server as a REST API without MCP?**
A: Yes. Start with `--serve` for HTTP mode. The REST API at `http://127.0.0.1:10770` exposes endpoints for search, paper metadata, full text, DOI resolution, depot search, benchmark verification, and more.

**Q: Is there a way to preview a paper card without ingesting?**
A: Yes. `show_paper_card(paper_id="2401.00001")` renders a Prefab card with metadata preview. Pure metadata read — no ingestion.

**Q: What prompts are available?**
A: 10 prompts: `research_workflow_prompt` (quick/deep/corpus modes), `generate_summary_prompt` (adversarial lenses), `consciousness_survey_prompt` (framework survey), `ai_consciousness_prompt` (AI sentience stances), `neurophilosophy_prompt` (philosophy traditions), `convergence_analysis_prompt` (cross-paper synthesis), `firefront_scan_prompt` (triage workflow), `corpus_build_prompt` (systematic ingestion), `replication_audit_prompt` (methods stress-test), `citation_map_prompt` (graph traversal). Access via `prompts/list` and `prompts/get`.

**Q: How do I use MCP sampling features?**
A: `arxiv_agentic_assist` and `arxiv_sampling_hint` use `ctx.sample()` automatically when the MCP client supports it (Claude Desktop, Cursor with sampling enabled). `deep_analyze_paper_epistemics` uses sampling for claim extraction. All sampling tools fall back to clear error messages with recovery guidance when sampling is unavailable.

**Q: What is the difference between get_paper_details and getPaper?**
A: `get_paper_details` uses the official arXiv PyPI API for structured metadata. `getPaper` scrapes the arxiv.org abstract HTML page. They may return slightly different results for the same paper ID depending on indexing status. Use `get_paper_details` as primary, `getPaper` as fallback or when you need the HTML page's exact rendering.

**Q: How do I use the arxiv-mcp dashboard?**
A: The React/Vite dashboard at `http://127.0.0.1:10771` provides a visual interface for browsing the depot, searching papers, viewing RAG status, and monitoring the code-hunt pipeline. Start it with `cd web_sota && npm run dev` or use `start.bat`. The dashboard auto-discovers backend APIs at `http://127.0.0.1:10770`.

**Q: What blog sources does fetch_lab_post support?**
A: Anthropic (`anthropic.com/research/` and `/news/`), Google Research (`research.google/blog`), Google DeepMind (`deepmind.google/blog` — uses Jina fallback for JS-rendered content), and Google AI Blog (`blog.google/technology/ai` — also Jina fallback). Use source-prefixed keys like `"deepmind:agi-path"` or `"google-research:pair"` for non-Anthropic sources.

**Q: How does the hybrid search ranking work?**
A: Hybrid search (`mode="hybrid"` in `search_depot_corpus`) uses reciprocal-rank fusion: it runs both FTS5 keyword search and LanceDB semantic search independently, then merges results by averaging the reciprocal of each document's rank in both result sets. This gives high rank to documents that score well in both keyword and semantic relevance, reducing the weaknesses of either approach alone.

**Q: How do I automate the firefront and code-hunt pipelines?**
A: Both are designed for scheduled execution. Create a cron job / scheduled task that runs `run_firefront_scan_tool` daily and `run_codehunt_scan_tool` every 6-12 hours. Monitor health with `pipeline_liveness_tool(stale_hours=48)` to detect when scans are not running. Results persist to SQLite and digest JSON files in the data directory.

**Q: Why does deep_analyze_paper_epistemics require ctx as a parameter?**
A: This FastMCP 3.2 tool uses `ctx.sample()` to call back to the connected LLM for claim extraction. The `ctx: Context` parameter is injected automatically by FastMCP when the MCP client supports sampling (Claude Desktop, Cursor). When sampling is unavailable, the server falls back to `ARXIV_MCP_SAMPLING_BASE_URL`. You cannot pass `ctx` manually — the framework handles it.

**Q: Can I use arxiv-mcp on macOS or Linux?**
A: Yes. The server is cross-platform. All paths in this guide use Windows conventions for the primary target platform (Windows 11). On macOS/Linux, adjust Calibre paths accordingly (`/usr/bin/calibredb`), use forward slashes, and note that some Windows-specific features (SAPI5 TTS) are not relevant to arxiv-mcp.

## REST API Reference

When running in HTTP mode (`--serve`), the server exposes REST endpoints for programmatic access at `http://127.0.0.1:10770`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server health: `{"status": "ok", "version": "x.y.z"}` |
| `/mcp` | POST | MCP streamable HTTP endpoint for MCP clients |
| `/api/search` | GET | Search papers: `?q=query&categories=cs.LG,cs.AI&limit=10&sort_by=submitted` |
| `/api/category-latest` | GET | Recent submissions: `?category=cs.LG&hours=24&limit=25` |
| `/api/papers/{paper_id}` | GET | Paper metadata |
| `/api/papers/{paper_id}/content` | GET | Paper full text |
| `/api/doi/resolve` | GET | Resolve DOI: `?doi=10.1016/j.cell.2018.06.048` |
| `/api/doi/content` | GET | DOI full text: `?doi=...&ingest_to_depot=true&max_chars=50000` |
| `/api/depot/search` | GET | Search depot: `?q=query&mode=hybrid&limit=20` |
| `/api/depot/stats` | GET | Depot and RAG statistics |
| `/api/benchmark/verify` | GET | Verify benchmark: `?model=gpt-4o&benchmark=MATH+level+5&claimed_score=0.90` |
| `/api/epistemic/{paper_id}` | GET | Epistemic profile |
| `/api/codehunt/stats` | GET | Code-hunt statistics |
| `/api/codehunt/scan` | POST | Trigger code-hunt scan |
| `/api/lab-posts` | GET | List lab blog posts: `?source=anthropic&limit=20` |

All REST endpoints return JSON. Rate limits match MCP tool limits. The `/health` and `/api/depot/*` endpoints do not call arXiv and have no external rate limits. Authentication via `ARXIV_MCP_API_KEY` (optional) requires `Authorization: Bearer <key>` or `X-API-Key: <key>` headers when set.
