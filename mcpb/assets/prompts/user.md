# arxiv-mcp — User Guide

## Quick Start

### Installation

```bash
git clone https://github.com/sandraschi/arxiv-mcp.git
cd arxiv-mcp
uv sync --extra dev
```

### Configuration

Create a `.env` file in the project root or set environment variables:

```env
# Required for citation graphs (recommended — 100 req/s vs 10 req/s)
ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY=your_key_here
# Recommended for DOI resolution polite pool
ARXIV_MCP_UNPAYWALL_EMAIL=your_email@example.com
# Optional: Calibre library for paper archival
ARXIV_MCP_CALIBRE_LIBRARY_PATH=C:\Calibre Libraries\Papers
ARXIV_MCP_CALIBREDB_PATH=C:\Program Files\Calibre2\calibredb.exe
# Optional: OpenAI-compatible endpoint for background epistemic jobs
ARXIV_MCP_SAMPLING_BASE_URL=http://localhost:11434/v1
```

### Run the Server

**Stdio mode (for Claude Desktop, Cursor, Windsurf):**

```bash
uv run python -m arxiv_mcp --stdio
```

**HTTP mode (for web dashboard and REST API):**

```bash
uv run python -m arxiv_mcp --serve
```

Then open `http://127.0.0.1:10771` for the React dashboard, or use `http://127.0.0.1:10770` as the MCP streamable HTTP endpoint.

### Register in Claude Desktop

```json
{
  "mcpServers": {
    "arxiv-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "arxiv_mcp", "--stdio"],
      "env": {
        "ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY": "your_key_here"
      }
    }
  }
}
```

### Register in Cursor / Windsurf

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

### Data Directory

The server creates a data directory at `ARXIV_MCP_DATA_DIR` (default `./data`) on first run. This directory contains:

| Path | Contents |
|------|----------|
| `arxiv_mcp.sqlite3` | Main depot database with FTS5 full-text search index. Stores ingested paper text, metadata, epistemic profiles, and job queue state |
| `depot/` | LanceDB vector store directory (only created when `uv sync --extra rag` is installed). Contains embedding vectors for semantic search |
| `codehunt/tracking.sqlite3` | Code-hunt tracking database. Stores findings, liveness status, watch author hits, and media coverage flags |
| `codehunt/codehunt.log` | Code-hunt scan history log |
| `firefront/` | Firefront scan digest JSON files, timestamped per run (`digest_{topic}_{timestamp}.json`) |
| `calibre/` | Temporary paper files staged for Calibre ingestion |

The data directory persists across restarts. To reset, stop the server and delete the relevant files. The server recreates them on startup.

### MCPB Bundle Installation

If you have the `.mcpb` bundle, install it via the Claude Desktop MCP settings UI or run:

```bash
mcpb install dist/arxiv-mcp-v0.1.0.mcpb
```

The bundle includes pre-configured prompts, skills, and environment variable templates.

### Verify Connectivity

Call `search_papers(query="attention mechanism", limit=3)` to confirm. You should see a response with paper titles, authors, and abstracts. If the server starts but returns errors, check that arXiv is reachable from your network and increase `ARXIV_MCP_CLIENT_DELAY` if you see rate limit warnings.

## Tutorials

### Tutorial 1: Search for Recent Papers on a Topic

The most common workflow — discover what is new in a field. Use a combination of `search_papers` with category filters to narrow results.

```python
# Step 1: Broad search with keywords and category filters
results = search_papers(
    query="diffusion model",
    categories=["cs.LG", "cs.CV"],
    limit=15,
    sort_by="submitted"
)
for paper in results.get("papers", []):
    published = paper.get("published", "")[:10]
    aid = paper.get("id", paper.get("paper_id", ""))[:12]
    print(f"[{published}] {aid} — {paper.get('title', '')[:70]}")

# Step 2: If you want more detail on a specific paper
if results.get("papers"):
    first_aid = results["papers"][0].get("id", "")
    detail = get_paper_details(paper_id=first_aid)
    print(f"Authors: {', '.join(detail.get('paper', {}).get('authors', [])[:3])}")
    print(f"Abstract: {detail.get('paper', {}).get('abstract', '')[:200]}")
```

You can refine by category: try `categories=["cs.CV"]` for computer vision, `categories=["cs.CL", "cs.AI"]` for NLP and LLM papers, or omit categories entirely for an all-category search.

### Tutorial 2: Browse Recent Submissions in a Category

Use `list_category_latest` to see papers published in the last N hours in a specific arXiv category.

```python
# Last 24 hours in machine learning
recent = list_category_latest(category="cs.LG", hours=24, limit=25)
print(f"Found {len(recent.get('papers', []))} papers in the last 24 hours")
for paper in recent.get("papers", []):
    aid = paper.get("paper_id", "")[:15]
    print(f"[{aid}] {paper.get('title', '')[:70]}")

# Using the HTML recent listing as an alternative source
html = getRecent(category="cs.AI", count=15, hours=72)
for paper in html.get("papers", []):
    print(f"{paper.get('title', '')} — {paper.get('authors', [])[0] if paper.get('authors') else 'Unknown'}")

# Browse multiple categories
for cat in ["cs.AI", "cs.LG", "cs.RO"]:
    batch = list_category_latest(category=cat, hours=48, limit=10)
    print(f"\n### {cat} — {len(batch.get('papers', []))} papers")
```

### Tutorial 3: Get Full Text of a Paper and Ingest It

This is the core ingestion workflow: find a paper, get its metadata, extract full text, and persist it for search.

```python
# Step 1: Get metadata
meta = get_paper_details(paper_id="2401.00001")
paper = meta.get("paper", {})
print(f"Title: {paper.get('title')}")
print(f"Authors: {', '.join(paper.get('authors', [])[:5])}")
print(f"Categories: {', '.join(paper.get('categories', []))}")

# Step 2: Fetch full text (HTML preferred, PDF fallback)
text = fetch_full_text(paper_id="2401.00001", prefer_html=True)
if text.get("success"):
    print(f"Full text fetched from {text.get('source', '?')}: {len(text.get('markdown', ''))} chars")
else:
    print(f"HTML unavailable: {text.get('message', '')}")
    # Fallback: try PDF-only
    text = fetch_full_text(paper_id="2401.00001", prefer_html=False)

# Step 3: Ingest to local depot for persistent search
result = ingest_paper_to_corpus(paper_id="2401.00001", source="html")
print(f"Ingested {result.get('chunks', 0)} chunks ({result.get('word_count', 0)} words)")

# Step 4: Now search the depot
search = search_depot_corpus(query="attention mechanism", mode="hybrid")
for hit in search.get("hits", []):
    print(f"[{hit.get('score', 0):.2f}] {hit.get('title', '')[:60]}")
```

### Tutorial 4: Run an Epistemic Analysis on a Paper

Analyze what kind of scientific evidence a paper uses and what verification it still needs.

```python
# Quick rule-based analysis
profile = analyze_paper_epistemics(paper_id="2401.00001")
if profile.get("success"):
    ep = profile.get("epistemic_profile", {})
    print(f"Primary evidence mode: {ep.get('primary_evidence_mode')}")
    print(f"Needs bench experiment: {ep.get('needs_bench')}")
    print(f"Needs human judgment: {ep.get('needs_human_judgment')}")
    print(f"AI automation fit: {ep.get('ai_automation_fit')}")

# Deep claim-level analysis with LLM
deep = deep_analyze_paper_epistemics(paper_id="2401.00001", force_refresh=True)
if deep.get("success"):
    claims = deep.get("epistemic_profile", {}).get("claims", [])
    print(f"\nExtracted {len(claims)} claims:")
    for c in claims:
        print(f"  - {c.get('claim_text', '')[:100]}")
        print(f"    Evidence: {c.get('evidence_mode')}, Falsifier: {c.get('falsifier', 'N/A')}")

# Combined: ingest and analyze in one call
combined = ingest_and_analyze_paper(paper_id="2401.00001", deep=True)
print(f"Ingested: {combined.get('ingested', False)}")
print(f"Claims: {len(combined.get('epistemic_profile', {}).get('claims', []))}")
```

### Tutorial 5: Find Citations and References for a Paper

Discover the citation graph around a paper: which papers cite it (forward citations) and which it references (backward citations).

```python
# Get citation graph
graph = find_connected_papers(paper_id="2401.00001", limit=15)
print(f"Citing papers (forward): {len(graph.get('citations', []))}")
for c in graph.get("citations", [])[:5]:
    print(f"  [{c.get('year', '????')}] {c.get('title', 'Untitled')[:70]}")
    print(f"         ({c.get('arxiv_id', 'no arXiv ID')})")

print(f"\nReferences (backward): {len(graph.get('references', []))}")
for r in graph.get("references", [])[:5]:
    print(f"  [{r.get('year', '????')}] {r.get('title', 'Untitled')[:70]}")

# Render as a Prefab card in the chat
await show_citation_graph_card(paper_id="2401.00001", limit=8)
```

### Tutorial 6: Use the Code-Hunt to Track Open-Weight Model Drops

The code-hunt pipeline scans recent arXiv submissions for links to open-weight model repositories, training code, and "code coming soon" promises.

```python
# Run a manual code-hunt scan
scan = run_codehunt_scan_tool(
    categories=["cs.AI", "cs.LG", "cs.RO"],
    days=3,
    limit_per_category=50,
    push=False   # Do not push to aiwatcher for testing
)
print(f"Scan complete: {scan.get('summary', {})}")
print(f"Total findings: {scan.get('total', 0)}")
print(f"Live drops: {scan.get('live_drops', 0)}")
print(f"Code promises: {scan.get('promises', 0)}")

# Check current tracking stats
stats = codehunt_stats_tool()
print(f"Status breakdown: {stats.get('by_status', {})}")
print(f"China-signal papers: {stats.get('china_count', 0)}")

# Re-poll promised repos for liveness
repoll = repoll_codehunt_tool(limit=100, push=False)
print(f"Re-checked {repoll.get('checked', 0)} promises")
print(f"Newly live: {repoll.get('newly_live', 0)}")

# Check media coverage of tracked papers
media = check_codehunt_media_tool(limit=20, push=False)
print(f"Media hits found: {len(media.get('hits', []))}")
```

The code-hunt is designed for periodic scheduled runs (every 6-12 hours). Install with the included scheduled task script or call manually.

### Tutorial 7: Search Ingested Papers by Keywords or Semantics

Once papers are ingested into the depot, search across their full text using three retrieval modes.

```python
# FTS5 keyword search (always available, BM25 ranking)
fts = search_depot_corpus(query="reinforcement learning human feedback", mode="fts", limit=10)
print(f"FTS results: {len(fts.get('hits', []))}")
for hit in fts.get("hits", []):
    print(f"  [{hit.get('score', 0):.2f}] {hit.get('title', '')[:60]}")
    print(f"     Excerpt: {hit.get('text', '')[:120]}")

# Semantic search (requires uv sync --extra rag for LanceDB)
sem = search_depot_corpus(query="how agents learn from reward signals", mode="semantic", limit=5)
print(f"\nSemantic results: {len(sem.get('hits', []))}")

# Hybrid search (reciprocal-rank fusion of both, default)
hybrid = search_depot_corpus(query="RLHF alignment", mode="hybrid", limit=10)
print(f"\nTop hybrid result: {hybrid.get('hits', [{}])[0].get('title', 'N/A')}")

# Filter by paper age
recent = search_depot_corpus(query="transformer", max_age_days=90, limit=10)
print(f"Recent papers (90d): {len(recent.get('hits', []))}")

# Check depot index health
status = depot_rag_status()
print(f"Vector index: {status.get('row_count', 0)} rows, {status.get('dimensions', 0)}d")
```

### Tutorial 8: Check a Claimed Benchmark Score

Cross-check benchmark claims from papers against Epoch AI's curated public database.

```python
# Verify a specific claim
verdict = check_benchmark_claim(
    model_name="DeepSeek-V4-Pro",
    benchmark="GPQA diamond",
    claimed_score=0.89,
    tolerance=0.02
)
print(f"Model: DeepSeek-V4-Pro, Benchmark: GPQA diamond")
print(f"Claimed: 0.89, Epoch score: {verdict.get('epoch_score')}")
print(f"Verdict: {verdict.get('verdict')}")  # match, mismatch, not_found
if verdict.get("verdict") == "mismatch":
    print(f"Difference: {verdict.get('difference', 0):.3f}")
    print(f"Source: {verdict.get('source_url', 'N/A')}")

# Check a score without comparison (just look up what is tracked)
score = check_benchmark_claim(
    model_name="gpt-4o",
    benchmark="MATH level 5"
)
print(f"GPT-4o on MATH L5: {score.get('epoch_score')} (confidence: {score.get('confidence')})")

# Check multiple benchmarks for the same model
for bench in ["GPQA diamond", "MATH level 5", "SWE-Bench verified"]:
    v = check_benchmark_claim(model_name="claude-3-7-sonnet", benchmark=bench)
    print(f"  {bench}: {v.get('epoch_score', 'not found')}")
```

### Tutorial 9: Fetch and Analyze an Anthropic Blog Post

Retrieve blog posts from AI research labs for direct analysis and optional depot ingestion.

```python
# Fetch by short key
post = fetch_anthropic_post(slug_or_url="model-welfare")
if post.get("success"):
    print(f"Title: {post.get('title')}")
    print(f"Published: {post.get('published')}")
    print(f"Summary: {post.get('summary')[:300]}")
    # The body_markdown is directly ingestible
    print(f"Body length: {len(post.get('body_markdown', ''))} chars")

# Fetch with source prefix (DeepMind)
dm_post = fetch_lab_post(slug_or_url="deepmind:agi-path")
print(f"Source: {dm_post.get('source')} — {dm_post.get('title')}")

# Fetch with full URL
url_post = fetch_lab_post(
    slug_or_url="https://research.google/blog/pathways-asynchronous-distributed-training/"
)
print(f"Title: {url_post.get('title')}")

# List recent posts
anthropic_posts = list_anthropic_posts(section="research", limit=10)
for p in anthropic_posts.get("posts", []):
    print(f"  {p.get('date', '')[:10]} — {p.get('title')}")

lab_posts = list_lab_posts(source="google-research", limit=15)
for p in lab_posts.get("posts", []):
    print(f"  {p.get('title')} ({p.get('date', '')[:10]})")
```

### Tutorial 10: Store a Paper in Calibre for Offline Reading

Add an arXiv paper as a book in your Calibre library with full metadata.

```python
# Basic store (PDF + metadata)
result = store_paper_to_calibre(
    paper_id="2401.00001",
    include_markdown=True  # Also attach markdown as TXT format
)
if result.get("success"):
    print(f"Added to Calibre — Book ID: {result.get('calibre_book_id')}")
    print(f"Title: {result.get('title')}")
    print(f"Authors: {', '.join(result.get('authors', []))}")
    print(f"Tags: {', '.join(result.get('tags', []))}")
    print(f"Markdown stored: {result.get('markdown_stored', False)}")
else:
    print(f"Calibre error: {result.get('error', '')}")
    print(f"Check ARXIV_MCP_CALIBRE_LIBRARY_PATH and ARXIV_MCP_CALIBREDB_PATH")

# Store without markdown (PDF only)
result_pdf = store_paper_to_calibre(
    paper_id="2301.00001",
    include_markdown=False
)
```

Calibre integration requires a configured library path. Set `ARXIV_MCP_CALIBRE_LIBRARY_PATH` to an existing Calibre library directory and `ARXIV_MCP_CALIBREDB_PATH` to the `calibredb.exe` executable path (typically `C:\Program Files\Calibre2\calibredb.exe` on Windows, `/usr/bin/calibredb` on Linux).

### Tutorial 11: Resolve a DOI to PDF and Ingest It

For non-arXiv papers behind DOIs, resolve the DOI, download the open-access PDF, extract text, and optionally ingest to the depot.

```python
# Step 1: Resolve the DOI
doi_info = resolve_doi(doi="10.1016/j.cell.2018.06.048")
print(f"Title: {doi_info.get('title')}")
print(f"Open Access: {doi_info.get('is_oa')} ({doi_info.get('oa_status')})")
print(f"Publisher: {doi_info.get('publisher')}")

# Step 2: If OA, fetch the full text
if doi_info.get("is_oa") and doi_info.get("pdf_url"):
    content = fetch_doi_content(
        doi="10.1016/j.cell.2018.06.048",
        ingest_to_depot=True,
        max_chars=50000
    )
    print(f"Extracted {content.get('word_count', 0)} words")
    print(f"Ingested to depot: {content.get('ingested', False)}")
    print(f"Truncated: {content.get('truncated', False)}")

# Resolve a Nature journal DOI
nature = resolve_doi(doi="10.1038/s41586-024-07155-5")
print(f"Nature paper: {nature.get('title')}")
print(f"OA: {nature.get('is_oa')}, status: {nature.get('oa_status')}")

# Resolve and ingest in one step
fetch_doi_content(
    doi="10.1038/s41586-024-07155-5",
    ingest_to_depot=True,
    max_chars=50000
)
```

### Tutorial 12: Run a Firefront Scan Across Multiple Categories

The firefront scanner collects recent papers across categories and produces a digest JSON for scheduled triage.

```python
# Run a firefront scan
digest = run_firefront_scan_tool(
    topic="weekly-ai-ml",
    categories=["cs.AI", "cs.LG", "q-bio.NC"],
    days=7,
    limit_per_category=25,
    ingest_top_n=0  # Set > 0 to auto-ingest top papers
)
print(f"Digest saved to: {digest.get('file_path')}")
print(f"Papers per category: {digest.get('per_category', {})}")
print(f"Total unique papers: {digest.get('total', 0)}")

# The digest file is a timestamped JSON at data/arxiv_mcp/firefront/
# Use the firefront_scan_prompt for LLM triage of the digest
```

### Tutorial 13: Use Agentic Assist for a Multi-Step Research Plan

When you are unsure how to approach a research task, let the LLM plan the multi-step workflow using the available arXiv MCP tools.

```python
# Get a step-by-step research plan
plan = arxiv_agentic_assist(
    goal="Survey vision-language model architectures from 2024 to 2025, find the most cited papers, read their full text, and check their benchmark claims"
)
if plan.get("success"):
    print("Research plan:")
    print(plan.get("response", plan.get("plan", "")))
    # The plan names concrete tools like search_papers, find_connected_papers,
    # fetch_full_text, check_benchmark_claim
else:
    # Fallback: manual workflow
    print("Agentic assist unavailable — using manual search")
    results = search_papers(
        query="vision-language model",
        categories=["cs.CV", "cs.AI", "cs.LG"],
        limit=30,
        sort_by="submitted"
    )

# Get search hints for a topic
hints = arxiv_sampling_hint(topic="mechanistic interpretability of transformer attention heads")
print("Suggested queries:")
for q in hints.get("queries", []):
    print(f"  - {q}")
print("Recommended categories:")
for c in hints.get("categories", []):
    print(f"  - {c}")
```

### Tutorial 14: Compare Multiple Papers for Convergence

Bundle papers together for cross-paper LLM analysis. Useful for literature reviews and identifying convergent findings.

```python
# Bundle 2-12 papers for comparison
comparison = compare_papers_convergence(
    paper_ids=["2401.00001", "2401.00002", "2401.00003"]
)
print(f"Bundled {len(comparison.get('papers', []))} papers")
for p in comparison.get("papers", []):
    print(f"  [{p.get('arxiv_id', '')}] {p.get('title', '')[:60]}")

# The analysis prompt is ready to feed to an LLM
analysis_prompt = comparison.get("analysis_prompt", "")
print(f"\nAnalysis prompt ({len(analysis_prompt)} chars) ready for LLM")

# Use the convergence_analysis_prompt for deeper synthesis
```

### Tutorial 15: Job-Based Analysis for Slow Papers

For long-running deep epistemic analysis, use the job system to avoid tool timeouts.

```python
# Submit a background job
import time
job = epistemic_job(operation="submit", paper_id="2401.00001")
print(f"Job submitted: {job.get('job_id')}")

# Poll for results
while True:
    status = epistemic_job(operation="status", job_id=job["job_id"])
    state = status.get("status", "")
    print(f"Status: {state}")
    if state == "complete":
        profile = status.get("result", {}).get("epistemic_profile", {})
        print(f"Claims extracted: {len(profile.get('claims', []))}")
        for c in profile.get("claims", [])[:3]:
            print(f"  - {c.get('claim_text', '')[:100]}")
        break
    elif state in ("failed", "cancelled"):
        print(f"Job ended: {status.get('message', status.get('error', ''))}")
        break
    time.sleep(5)

# List recent jobs
jobs = epistemic_job(operation="list", status_filter="queued", limit=20)
print(f"Queued jobs: {len(jobs.get('jobs', []))}")
```

### Tutorial 16: Use HTML Search with Advanced Filters

For fine-grained discovery, use the field-scoped HTML search.

```python
# Standard HTML search with full abstracts
results = search(query="transformer", category="cs.LG", sort_by="date_desc", page_size=30)
for p in results.get("papers", []):
    print(f"{p.get('id_arxiv', '')}: {p.get('title', '')[:60]} — {p.get('authors', [''])[0]}")

# Advanced field-specific search
adv = searchAdvanced(
    title="attention",
    abstract="transformer",
    category="cs.AI",
    date_from="2024-01-01",
    date_to="2024-12-31",
    sort_by="date_desc"
)
print(f"Found {len(adv.get('papers', []))} papers matching title+abstract filters")

# Search by author and date range
author_results = searchAdvanced(
    author="Bengio",
    date_from="2024-01-01",
    date_to="2024-06-30"
)
print(f"Bengio papers H1 2024: {len(author_results.get('papers', []))}")

# Search by arXiv ID pattern
id_results = searchAdvanced(category="cs.AI", id_arxiv="24*")
print(f"2024 cs.AI papers: {len(id_results.get('papers', []))}")
```

### Tutorial 17: Understand the Difference Between API and HTML Search Tools

Knowing when to use `search_papers` (API) vs `search` / `searchAdvanced` (HTML) is important for efficient discovery.

```python
# API search: fast, structured, ideal for programmatic queries
api_results = search_papers(
    query="reinforcement learning", categories=["cs.LG"], limit=10
)
# Returns: {id, title, authors (list), published, pdf_url, abstract_url}
# Note: abstracts are not always returned by the API in list form

# HTML search: richer snippets, full abstracts, more results per page
html_results = search(
    query="reinforcement learning", category="cs.LG",
    sort_by="date_desc", page_size=50
)
# Returns: {id_arxiv, title, authors (list, full), abstract (full text),
#           categories, published_date}
# The HTML version always includes the full abstract in results

# When to use each:
# - Use search_papers for: broad sweeps, automated pipelines, known queries
# - Use search for: discovery, browsing, when you need full abstracts
# - Use searchAdvanced for: field-specific queries (title matches,
#   author matches, date ranges, arXiv ID patterns)

# Example: find papers with "attention" in the title AND "transformer" in the abstract
adv = searchAdvanced(title="attention", abstract="transformer", date_from="2024-06-01")
print(f"Found {len(adv.get('papers', []))} papers matching both fields")
```

### Tutorial 18: Filter the Depot by Epistemic Profile

After ingesting many papers, use epistemic filters to find papers needing specific verification.

```python
# Find papers that need bench verification
bench_papers = list_depot_by_epistemics(
    needs_bench=True,
    limit=20
)
print(f"Papers needing bench: {len(bench_papers.get('papers', []))}")
for p in bench_papers.get("papers", []):
    print(f"  {p.get('title', '')[:60]}")

# Find simulation-based papers
sim_papers = list_depot_by_epistemics(
    primary_mode="simulation",
    limit=10
)
print(f"\nSimulation evidence papers: {len(sim_papers.get('papers', []))}")

# Filter by multiple criteria
critical = list_depot_by_epistemics(
    needs_bench=True,
    needs_formal_verification=True,
    limit=10
)
```

## REST API Reference

The HTTP server exposes REST endpoints at `http://127.0.0.1:10770` for web dashboard and programmatic access:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server health check. Returns `{"status": "ok", "version": "x.y.z"}` |
| `/api/stats` | GET | Depot statistics: paper count, chunk count, RAG index status |
| `/api/categories` | GET | List all registered arXiv categories |
| `/api/search` | GET | Search papers. Params: `q` (query), `categories` (comma-separated), `limit` (int), `sort_by` |
| `/api/category-latest` | GET | Recent submissions. Params: `category`, `hours`, `limit` |
| `/api/search-advanced` | GET | Advanced field-scoped search. Params: `title`, `abstract`, `author`, `category`, `date_from`, `date_to` |
| `/api/papers/{paper_id}` | GET | Paper metadata |
| `/api/papers/{paper_id}/content` | GET | Paper full text |
| `/api/doi/resolve` | GET | Resolve a DOI. Params: `doi` |
| `/api/doi/content` | GET | Fetch OA PDF content from DOI. Params: `doi`, `ingest_to_depot`, `max_chars` |
| `/api/depot/search` | GET | Search ingested papers. Params: `q`, `mode` (fts/semantic/hybrid), `limit` |
| `/api/depot/stats` | GET | Depot and RAG index statistics |
| `/api/benchmark/verify` | GET | Verify benchmark claim. Params: `model`, `benchmark`, `claimed_score` |
| `/api/epistemic/{paper_id}` | GET | Epistemic profile for a paper |
| `/api/codehunt/stats` | GET | Code-hunt tracking statistics |
| `/api/codehunt/scan` | POST | Trigger a code-hunt scan |
| `/api/lab-posts` | GET | List AI lab blog posts. Params: `source`, `limit` |
| `/api/lab-posts/{source}` | GET | Fetch a specific lab blog post. Params: `slug` |

All API endpoints return JSON. Use `http://127.0.0.1:10771` for the React dashboard.

### REST API Authentication

The HTTP server can optionally require authentication via the `ARXIV_MCP_API_KEY` environment variable. When set, all requests must include an `Authorization: Bearer <key>` header or an `X-API-Key: <key>` header. Set to empty (default) for open access.

### REST API Rate Limits

HTTP requests use the same rate limiting as MCP tools. arXiv API endpoints enforce the client delay (`ARXIV_MCP_CLIENT_DELAY`, default 3 seconds). The `/api/search`, `/api/category-latest`, `/api/papers/*` endpoints each consume one arXiv API request. Plan your polling cadence accordingly. The `/health`, `/api/stats`, `/api/depot/*`, and `/api/codehunt/*` endpoints do not call arXiv and have no external rate limits.

## Troubleshooting

### "Rate limited by arXiv API"

The server uses a client-side delay of 3 seconds by default (configurable via `ARXIV_MCP_CLIENT_DELAY`). If you hit arXiv HTTP 429 responses, increase this delay (e.g., `ARXIV_MCP_CLIENT_DELAY=6.0`). Retries are automatic with exponential backoff. Reduce request frequency or batch your queries.

### "Experimental HTML not available"

Not all arXiv papers have experimental HTML format. Older papers (pre-2022) and some newer papers may only have PDF. Use `prefer_html=False` to skip HTML and extract text from the PDF directly. As a third fallback, use `getContent` which leverages Jina Reader at `r.jina.ai` (50 requests/hour free tier).

### "Semantic Scholar returns empty citation graph"

If `find_connected_papers` returns empty results, the paper may not be indexed in the Semantic Scholar graph yet. New arXiv papers take 1-4 weeks to appear. For higher rate limits, set `ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY` (100 requests/second vs 10 without). Check the paper has an arXiv ID that Semantic Scholar recognizes.

### "Calibre integration fails"

Ensure `ARXIV_MCP_CALIBRE_LIBRARY_PATH` points to an existing Calibre library directory (it must contain a `metadata.db` file). Ensure `ARXIV_MCP_CALIBREDB_PATH` points to the `calibredb` executable. On Windows this is typically `C:\Program Files\Calibre2\calibredb.exe`. Use `include_markdown=False` if the markdown attachment step is failing. Verify Calibre is installed and the library directory is writable.

### "Depot search returns no results"

First check that papers have been ingested with `ingest_paper_to_corpus`. The FTS5 index is built during ingestion — no separate step needed. For semantic (vector) search, run `uv sync --extra rag` to install LanceDB dependencies, then call `reindex_depot_vectors()` to build the vector index. Use `depot_rag_status()` to verify the index has rows.

### "Epistemic analysis returns empty claims"

Deep claim-level analysis requires MCP sampling (`ctx.sample()`) or a configured `ARXIV_MCP_SAMPLING_BASE_URL` (OpenAI-compatible endpoint). If neither is available, the analysis falls back to rule-based classification only, which does not extract individual claims. Set up an Ollama instance or an OpenAI API endpoint for full claim extraction.

### "Background epistemic job never completes"

Jobs require `ARXIV_MCP_SAMPLING_BASE_URL` pointing to an OpenAI-compatible API (e.g., Ollama at `http://localhost:11434/v1`). Ensure the endpoint is reachable and the model specified by `ARXIV_MCP_SAMPLING_MODEL` (default `gemma3:1b`) is available. Check `data/arxiv_mcp.sqlite3` for job status — jobs running at server crash are marked "interrupted" and must be re-submitted.

### "Code-hunt finds no repositories"

The code-hunt scans abstracts for repository URLs (GitHub, Gitee, HuggingFace, ModelScope) and "code coming soon" language. Not all submissions include these. Run on at least 3-7 days of recent papers for meaningful results. Increase `limit_per_category` or add more categories. The scan is tuned for cs.AI, cs.LG, cs.RO, cs.SD, and cs.CV.

### "Firefront digest has no papers"

The firefront scanner uses `list_category_latest` for each category. If a category has no recent submissions (e.g., weekends, conference deadline lulls), the digest will be sparse. Increase the `days` parameter or add more categories.

## FAQ

**Q: What is the difference between search_papers and search?**
A: `search_papers` uses the official arXiv API (stable, structured metadata, no abstracts directly in results). `search` uses the arxiv.org HTML search interface (full abstracts, complete author lists, richer snippets per hit). Prefer the API for programmatic workflows and HTML for discovery and browsing.

**Q: Can I use this server without a Semantic Scholar API key?**
A: Yes. The citation graph tool works without one but at 10 requests/second limit. With an API key, the limit is 100 requests/second. Without the key, you may hit rate limits during batch processing.

**Q: How do I get full text for an old paper?**
A: `fetch_full_text` tries the arXiv experimental HTML endpoint first (available for most papers from 2022+). For older papers, HTML often returns 404 and the tool falls back to PDF text extraction automatically. As a third option, use `getContent` for Jina Reader. Very old papers (pre-2007) may have no digital full text available through any of these methods.

**Q: What is the local depot and why use it?**
A: The depot is a SQLite database with FTS5 full-text search that stores ingested paper content. It enables persistent, searchable access to full paper texts without re-fetching from arXiv. Optional LanceDB vector search adds semantic similarity queries. Without the depot, you must re-fetch paper text every time.

**Q: How is paper content sanitized?**
A: All arXiv data passes through `wrap_untrusted()` which strips zero-width Unicode characters, normalizes whitespace, and neutralizes known prompt injection patterns. Paper content is treated as untrusted — agents should be alert for adversarial formatting or framing embedded in paper text.

**Q: Can I export papers to my Calibre library?**
A: Yes. Use `store_paper_to_calibre()` with a configured library path. The tool downloads the PDF, adds it with full metadata (title, authors, categories as tags, abstract as comments), and optionally attaches the HTML-to-Markdown text as a TXT format.

**Q: What prompts are available and how do I use them?**
A: The server registers 10 prompts accessible via the MCP Prompts protocol. They cover: research workflow mode selection, adversarial summary generation with configurable lens, consciousness research surveys, AI consciousness analysis, neurophilosophy analysis, cross-paper convergence analysis, firefront scan triage, corpus building guidance, replication audit, and citation map traversal. Use `prompts/list` and `prompts/get` on the MCP transport to access them.

**Q: What is epistemic analysis?**
A: Epistemic analysis classifies scientific papers by their evidence type and verification requirements. The rule-based mode identifies the primary evidence mode (formal proof, simulation, observational study, interventional lab experiment, clinical trial, etc.) and flags what the paper still needs (bench experiment, telescope, formal verification, human judgment). The deep mode uses an LLM to extract 3-8 individual claims from the paper, each annotated with evidence mode, known falsifiers, and verification flags.

**Q: What is the code-hunt pipeline?**
A: The code-hunt scans recent arXiv submissions for repository links (GitHub, Gitee, HuggingFace, ModelScope) and "code coming soon" promises. It tracks findings in a dedicated SQLite database, tags Chinese-lab affiliated papers, respects a watch list of authors, and pushes newly live drops to the fleet's aiwatcher-mcp for alerting. It is designed for scheduled runs every 6-12 hours.

**Q: What is the firefront scanner?**
A: The firefront scanner collects recent papers across configurable categories, deduplicates them, optionally ingests the top N, and writes a timestamped digest JSON file. Designed for daily morning triage — pair it with the `firefront_scan_prompt` for LLM-assisted review.

**Q: What is the difference between fetch_lab_post and fetch_anthropic_post?**
A: `fetch_lab_post` supports multiple AI lab sources (Anthropic, Google Research, DeepMind, Google AI Blog) and accepts source-prefixed slugs like "deepmind:agi-path". `fetch_anthropic_post` is a dedicated handler specifically for anthropic.com that also supports bare slugs and short keys.

**Q: How do I search across ingested papers?**
A: Use `search_depot_corpus` with three modes: `fts` (keyword BM25, always available), `semantic` (vector similarity, requires `uv sync --extra rag`), and `hybrid` (reciprocal-rank fusion of both, default). Filter by paper age with `max_age_days`.

**Q: Can I verify benchmark claims from papers?**
A: Yes. `check_benchmark_claim` cross-references claimed scores against the Epoch AI database of 3500+ models across 12 benchmarks with 900+ scored runs. Supports fuzzy model and benchmark name matching. Must know the model name and benchmark name as cited in the paper.

**Q: What image models are available for benchmark verification?**
A: The Epoch AI database covers image classification (ImageNet top-1, ImageNet v2), language understanding (MMLU, MMLU-Pro, GPQA diamond), mathematics (MATH, GSM8K), coding (SWE-Bench verified, HumanEval), and general reasoning (ARC, BIG-bench, HellaSwag, WinoGrande).

**Q: Is there a way to batch-ingest multiple papers at once?**
A: There is no single batch tool, but you can sequentially call `ingest_paper_to_corpus` for each paper ID. The FTS5 index is updated incrementally — no re-indexing needed after each ingest. For bulk operations, call from a script looping over paper IDs with a small delay between calls.

**Q: How do I clear or reset the local depot?**
A: Stop the server, delete the SQLite database at `{ARXIV_MCP_DATA_DIR}/arxiv_mcp.sqlite3`, and optionally delete `{ARXIV_MCP_DATA_DIR}/depot/` for LanceDB vectors. Restart the server — it will create fresh depot files. There is no in-tool reset operation to prevent accidental data loss.

**Q: Can I use this server with a proxy or VPN?**
A: The server uses standard httpx for HTTP requests and respects the `HTTP_PROXY` and `HTTPS_PROXY` environment variables. Set these before starting the server. arXiv and Semantic Scholar must still be reachable from your network — some academic networks block these.

**Q: How do I update the watch authors list for code-hunt?**
A: Create a JSON file at the path specified by `ARXIV_MCP_CODEHUNT_WATCH_AUTHORS_PATH`. The format is a flat list of author name strings: `["Yoshua Bengio", "Fei-Fei Li", "Ilya Sutskever"]`. The server reads this at startup and when manually reloaded via `arxiv_help(topic="codehunt")` guidance.

**Q: What happens when Semantic Scholar rate limits are hit?**
A: `find_connected_papers` receives HTTP 429 from Semantic Scholar. The tool returns a clear error with `recovery_options` suggesting you set `ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY`. Without a key, the limit is 10 requests/second with bursts up to 100. With a key, it is 100 requests/second with bursts up to 1000.

**Q: Is there a way to preview a paper card without ingesting it?**
A: Yes. Use `show_paper_card(paper_id="2401.00001")` to render a rich Prefab card with title, authors, abstract preview, and links. This does not ingest the paper into the depot — it is a pure metadata read with a visual display.

**Q: Can I use the server purely as a REST API without MCP?**
A: Yes. Start the server with `--serve` (HTTP mode). All MCP tools are also accessible via the REST endpoints listed in the REST API Reference section above. You do not need an MCP client to use the server's features.
