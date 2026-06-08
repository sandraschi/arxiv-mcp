# MCP Tool Reference

**arxiv-mcp** is a high-density research server built on **FastMCP 3.2**. It exposes tools, prompts, and skills for discovery, extraction, synthesis, and fleet code-hunt pipelines.

## Core arXiv tools

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `search_papers` | Systematic arXiv query with sorting | `query`, `categories`, `limit`, `sort_by` |
| `get_paper_details` | Full API metadata | `paper_id` |
| `fetch_full_text` | HTML→Markdown; Jina fallback | `paper_id`, `prefer_html` |
| `getRecent` | Recent papers in a category | `category`, `count`, `hours` |
| `list_category_latest` | Rolling window of new papers | `category`, `limit`, `hours` |
| `find_connected_papers` | Citation graph (Semantic Scholar) | `paper_id`, `limit` |
| `ingest_paper_to_corpus` | Persist Markdown to local depot | `paper_id`, `markdown`, `source` |
| `store_paper_to_calibre` | PDF + metadata into Calibre | `paper_id`, `library_path`, `include_markdown` |

## Blog & lab tools

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `fetch_lab_post` | Anthropic, DeepMind, Google AI, etc. | `slug_or_url` |
| `list_lab_posts` | Recent lab blog posts | `source`, `limit` |

## DOI tools

| Tool | Purpose |
|------|---------|
| `resolve_doi` | Metadata + OA link via Unpaywall/Crossref |
| `fetch_doi_content` | Full text when OA available |

Requires `ARXIV_MCP_UNPAYWALL_EMAIL`. See [DOI_RESOLUTION.md](./DOI_RESOLUTION.md).

## Synthesis & sampling

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `compare_papers_convergence` | Multi-abstract synthesis prep | `paper_ids` |
| `show_paper_card` | Rich in-chat card (`apps` extra) | `paper_id` |
| `arxiv_agentic_assist` | Sampling: tool plan for a goal | `goal` |
| `arxiv_sampling_hint` | Sampling: query/category hints | `topic` |

## Code-hunt & fleet

| Tool | Purpose |
|------|---------|
| `run_codehunt_scan_tool` | Scan categories for repo/weights links |
| `repoll_codehunt_tool` | Re-check promised repos; push to aiwatcher |
| `codehunt_stats_tool` | SQLite tracking summary |
| `pipeline_liveness_tool` | Stale digests + aiwatcher reachability |
| `arxiv_help` | In-chat docs — `topic=codehunt`, `fleet`, `api_keys`, … |

REST: `GET /api/help/{topic}`. See [CODEHUNT.md](./CODEHUNT.md), [FLEET_INTEGRATION.md](./FLEET_INTEGRATION.md).

## Registered prompts

- `research_workflow_prompt` — quick / deep / corpus modes
- `generate_summary_prompt` — adversarial analyst lenses
- `consciousness_survey_prompt` — IIT, GWT, HOT frameworks
- `ai_consciousness_prompt` — AI sentience claims
- `neurophilosophy_prompt` — eliminativist, enactivist, etc.
- `convergence_analysis_prompt` — contradictions across papers
- `firefront_scan_prompt` — triage briefing for new papers
- `corpus_build_prompt` — systematic ingestion plan
- `replication_audit_prompt` — reproducibility stress-test
- `citation_map_prompt` — intellectual lineage

## Bundled skills

**`arxiv-researcher`** — `skill://arxiv-researcher/SKILL.md`

Expanded tool docs, domain search strategies, API troubleshooting.

## Resources

Capability summary and transport URLs exposed via FastMCP resources — see [FASTMCP_FEATURES.md](./FASTMCP_FEATURES.md).
