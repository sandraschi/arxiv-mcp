---
name: arxiv-researcher
description: >
  Expert workflow for arXiv research using arxiv-mcp. Covers discovery,
  metadata, full text, corpus, citation graph, Prefab cards, sampling-assisted
  planning, and structured analysis prompts. Specialisations: AI/ML, philosophy
  of mind, consciousness, neurophilosophy, MCP/agent systems.
tags: [arxiv, research, papers, llm, ai, consciousness, neurophilosophy, mcp]
---

# arXiv Researcher (arxiv-mcp)

## Tool reference

### Discovery

| Tool | When to use |
|------|-------------|
| `search_papers` | Primary — arXiv API, cleanest structured results, category filter |
| `search` | HTML scrape, supports author filter and pagination |
| `searchAdvanced` | Field-scoped: title, abstract, author, category, id, date range |
| `getRecent` | Latest submissions for one category (list page; often no abstracts) |
| `list_category_latest` | Rolling time window in hours for a category |
| `listCategories` | Full subject catalog — use for filter/dropdown selection |
| `arxiv_sampling_hint` | Ask host LLM to suggest queries and categories for a topic |

### Metadata & display

| Tool | When to use |
|------|-------------|
| `get_paper_details` | Preferred — arXiv PyPI client, structured fields |
| `getPaper` | HTML abs-page scrape — same pipeline as HTML search |
| `show_paper_card` | **Rich Prefab card**: title, authors, category badges, date, abstract, links |

### Full text

1. `fetch_full_text` — arXiv experimental HTML → Markdown. Check `html_available` in response.
2. `getContent` — Jina Reader (third-party, longer timeout). Use when `html_available: false`.

Neither extracts PDF. For PDF-only papers, obtain externally and pass `markdown=` to `ingest_paper_to_corpus`.

### Citation graph + corpus

| Tool | Purpose |
|------|---------|
| `find_connected_papers` | Citations + references via Semantic Scholar |
| `compare_papers_convergence` | Bundle abstracts (up to 12) for cross-paper LLM synthesis |
| `ingest_paper_to_corpus` | Persist Markdown + metadata to local SQLite FTS depot |

### Agentic / sampling

| Tool | When |
|------|------|
| `arxiv_agentic_assist` | Generate a multi-step research plan; requires host MCP sampling |
| `arxiv_sampling_hint` | Get suggested queries/categories for a topic |

If sampling returns `success: false`, use this skill as the manual fallback.

### Anthropic blog / research

| Tool | Purpose |
|------|---------|
| `fetch_anthropic_post` | Fetch + parse a single post → title, date, summary, markdown body |
| `list_anthropic_posts` | Scrape index listing for research or news section |

**Known short keys** (pass to `fetch_anthropic_post`):
`model-welfare`, `claude-character`, `alignment-faking`, `taking-ai-welfare-seriously`,
`core-views`, `claude-soul`, `model-spec`, `interpretability-monosemanticity`.

**Workflow** — fetch and ingest to corpus:
```
result = fetch_anthropic_post('model-welfare')
ingest_paper_to_corpus(paper_id=result['url'], markdown=result['markdown'], source='external')
```

---

## Standard research workflow

```
1. arxiv_sampling_hint(topic)            # query/category suggestions if sampling available
2. search_papers(query, categories, limit=10)
3. show_paper_card(paper_id)             # preview shortlisted papers
4. get_paper_details(paper_id)           # full metadata for confirmed candidates
5. fetch_full_text(paper_id)             # full content
   └─ fallback: getContent(paper_id)     # Jina Reader if HTML unavailable
6. find_connected_papers(paper_id)       # citation/reference lineage
7. compare_papers_convergence([ids])     # cross-synthesis across shortlist
8. ingest_paper_to_corpus(paper_id)      # persist to local corpus
```

---

## Domain search strategies

### AI / LLM / agent systems
Useful category combinations:
- `cs.AI` + `cs.LG` — core ML and AI
- `cs.CL` — NLP, language models
- `cs.MA` — multi-agent systems
- `cs.RO` — robotics and embodied agents

Key queries: `"large language model"`, `"chain of thought"`, `"tool use agents"`,
`"model context protocol"`, `"agentic workflow"`, `"reinforcement learning from human feedback"`,
`"emergent capabilities"`, `"scaling laws"`.

### Consciousness & philosophy of mind
Primary categories: `q-bio.NC` (computational neuroscience), `cs.AI`, `physics.bio-ph`.
Note: philosophy of mind papers often appear in `cs.AI` with consciousness keywords,
or on PhilArchive/PhilPapers (not arXiv). Use arXiv for the empirical and computational side.

Key queries: `"consciousness"`, `"qualia"`, `"integrated information theory"`,
`"global workspace theory"`, `"higher order theory"`, `"predictive processing"`,
`"free energy principle"`, `"neural correlates of consciousness"`,
`"phenomenal consciousness"`, `"hard problem"`, `"self-model"`, `"metacognition"`.

### AI consciousness & machine sentience
This is an active and contested area. Expect: empirical proxy papers, theoretical frameworks,
and speculative position papers — all mixed together.

Key queries: `"AI consciousness"`, `"machine consciousness"`, `"artificial sentience"`,
`"LLM introspection"`, `"model self-awareness"`, `"substrate independence"`,
`"functionalism consciousness"`, `"moral status AI"`, `"sentience detection"`,
`"consciousness in transformers"`, `"IIT artificial systems"`, `"attention consciousness"`.

Recommended search combination:
```
search_papers("consciousness language model", categories=["cs.AI"], sort_by="submitted")
search_papers("machine sentience substrate independence", categories=["cs.AI", "q-bio.NC"])
searchAdvanced(abstract="qualia artificial", category="cs.AI")
```

### Neurophilosophy & computational neuroscience
Categories: `q-bio.NC`, `q-bio.BM`, `eess.SP` (neural signal processing).

Key queries: `"predictive coding"`, `"active inference"`, `"Bayesian brain"`,
`"neural binding problem"`, `"temporal integration consciousness"`,
`"thalamocortical"`, `"default mode network"`, `"oscillatory synchrony"`,
`"Integrated Information"`, `"Tononi"`, `"Friston free energy"`,
`"perceptual inference"`, `"embodied cognition"`.

### MCP / agent infrastructure
Key queries: `"model context protocol"`, `"tool-augmented LLM"`,
`"multi-agent LLM"`, `"LLM orchestration"`, `"autonomous agent benchmark"`,
`"function calling"`, `"ReAct agent"`, `"tool use evaluation"`.

---

## MCP prompts available

Load these via `get_prompt(name, {args})` before analysis. All return plain text for injection.

| Prompt | Description | Key args |
|--------|-------------|----------|
| `research_workflow_prompt` | Tool-order guide for a session | `mode`: quick/deep/corpus |
| `generate_summary_prompt` | Deep adversarial read of a paper | `lens`, `paper_id` |
| `consciousness_survey_prompt` | Map the consciousness research landscape | `framework`, `scope` |
| `ai_consciousness_prompt` | Analyse AI/LLM consciousness claims | `stance`, `paper_id` |
| `neurophilosophy_prompt` | Neurophilosophy + philosophy of mind lens | `tradition`, `paper_id` |
| `convergence_analysis_prompt` | Cross-paper synthesis and contradiction map | `domain` |
| `firefront_scan_prompt` | Daily/weekly new-paper triage for a topic | `topic`, `days` |
| `corpus_build_prompt` | Systematic corpus ingestion plan | `topic`, `depth` |
| `replication_audit_prompt` | Reproducibility and methods stress-test | `paper_id` |
| `citation_map_prompt` | Citation graph traversal and lineage analysis | `paper_id`, `direction` |

### Lens quick reference for `generate_summary_prompt`

- `general` — problem, approach, key results, limitations, related work
- `methods_audit` — dataset, splits, baselines, metrics, reproducibility
- `instrumental_convergence` — optimization targets, power-seeking assumptions, omitted failure modes
- `qualia` — phenomenology claims, introspection vs third-person evidence, falsifiability

---

## Error handling

| Symptom | Fix |
|---------|-----|
| `search`/`searchAdvanced` sparse results | Check `parse_stats.parsed_ok` vs `blocks_seen` |
| `fetch_full_text` → `html_available: false` | Use `getContent` or external PDF pipeline |
| `find_connected_papers` thin graph | Paper too recent for Semantic Scholar; retry in a week |
| Sampling tools → `success: false` | Host lacks sampling; run tools manually per this skill |
| `compare_papers_convergence` with >12 ids | Batch into groups of ≤12 |
| `ingest_paper_to_corpus` fails | Check `ARXIV_MCP_DATA_DIR` is writable |
