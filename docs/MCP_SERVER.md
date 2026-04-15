# MCP Server Details

**arxiv-mcp** is a high-density research server built on **FastMCP 3.1+**. It exposes a variety of tools, prompts, and skills to help agents and researchers navigate the primary sources of AI and science.

---

## Tool Manifest

The server provides tools for discovery, extraction, and synthesis.

### Core arXiv Tools

| Tool | Purpose | Key Arguments |
| :--- | :--- | :--- |
| `search_papers` | Systematic arXiv query with sorting. | `query`, `categories`, `limit`, `sort_by` |
| `get_paper_details` | Full API metadata (abstract, authors, links). | `paper_id` |
| `fetch_full_text` | Prefer HTML→Markdown; falls back to Jina. | `paper_id`, `prefer_html` |
| `list_category_latest`| Rolling window of new papers in a category. | `category`, `limit`, `hours` |
| `find_connected_papers`| Citation graph via Semantic Scholar. | `paper_id`, `limit` |
| `ingest_paper_to_corpus`| Persist Markdown to local FTS depot. | `paper_id`, `markdown`, `source` |

### Blog & Lab Tools

| Tool | Purpose | Key Arguments |
| :--- | :--- | :--- |
| `fetch_lab_post` | Fetch from Anthropic, Google DeepMind, Google AI, etc. | `slug_or_url` |
| `list_lab_posts` | List recently published posts from lab blogs. | `source`, `limit` |

### Advanced Synthesis & Sampling

| Tool | Purpose | Key Arguments |
| :--- | :--- | :--- |
| `compare_papers_convergence`| Prepare multiple abstracts for LLM synthesis. | `paper_ids` |
| `show_paper_card` | Render a rich in-chat card (requires `[apps]` extra).| `paper_id` |
| `arxiv_agentic_assist`| **Sampling**: Generate a concrete tool plan for a goal. | `goal` |
| `arxiv_sampling_hint` | **Sampling**: Suggest queries/categories for a topic. | `topic` |

---

## Registered Prompts

Prompts are "starter instructions" that help you or your agent frame a research task.

- **`research_workflow_prompt`**: Onboarding guide with three modes: `quick`, `deep`, or `corpus`.
- **`generate_summary_prompt`**: Adversarial analyst lenses for a single paper (`methods_audit`, `qualia`, etc.).
- **`consciousness_survey_prompt`**: Maps theoretical frameworks (IIT, GWT, HOT, etc.) to arXiv papers.
- **`ai_consciousness_prompt`**: Analyzes AI sentience claims from specific philosophical stances.
- **`neurophilosophy_prompt`**: Traditions-based lens (eliminativist, enactivist, etc.) for neuro-papers.
- **`convergence_analysis_prompt`**: Maps contradictions and agreements across a set of papers.
- **`firefront_scan_prompt`**: Triage briefing for new papers over a specific time window.
- **`corpus_build_prompt`**: Systematic ingestion plan for a research topic.
- **`replication_audit_prompt`**: Reproducibility stress-test for methods and data.
- **`citation_map_prompt`**: Intellectual lineage traversal.

---

## Bundled Skills

The server includes an **`arxiv-researcher` skill**. In supporting clients, you can find this under `skill://arxiv-researcher/SKILL.md`. It provides:
- Expanded tool documentation.
- Common domain search strategies (e.g., finding state-of-the-art vision papers).
- Troubleshooting guides for common API issues.
