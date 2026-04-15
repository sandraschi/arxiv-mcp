# arXiv Context & Philosophy

Research on arXiv requires a different mindset than traditional library search. This document explains how **arxiv-mcp** interacts with the source and how you should interpret the results.

## HTML vs PDF

arXiv traditionally serves papers as PDFs. However, PDFs are "frozen" layouts that are often difficult for AI models to parse accurately (multi-column layouts, tables, math formulas).

**arxiv-mcp** prioritizes the **arXiv Experimental HTML** project.
- When available, we fetch the `https://arxiv.org/html/{id}` version.
- This HTML is converted directly to clean, structured **Markdown**.
- If HTML is not available (404), the system will indicate this. You can then use external tools (like Jina Reader) to attempt a PDF-to-text conversion.

## Citation Intelligence

We use the [Semantic Scholar Graph API](https://api.semanticscholar.org/) to provide citation and reference data.
- **Tools**: `find_connected_papers` leverages this API.
- **Limits**: Without an API key, Semantic Scholar has low rate limits. If you plan on doing a lot of citation mapping, we recommend getting a free API key and adding it to your `.env` as `ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY`.

---

## A Note on arXiv Currency (The AI Decay Rate)

arXiv is a preprint server with no peer review and no correction mechanism. In fast-moving fields like **Artificial Intelligence** and **Machine Learning**, the relevance of a paper can decay rapidly.

### Practical Guidance
1. **Recency Weights**: In AI, a paper from 6 months ago may already be superseded by newer benchmarks or model generations.
2. **Author Prestige**: Even papers by famous researchers can become obsolete within months due to the empirical reality of the field moving faster than the writing cycle.
3. **Filtering**: Use the `list_category_latest` tool or the `max_age_days` filter in the Depot search to focus on fresh findings.
4. **No "Superseded" Tag**: arXiv does not automatically tag papers as "obsolete." You must supply the judgment of whether a 2023 capability claim still holds true in 2026.

**Recommendation**: For AI-specific research, treat papers older than **180 days** as historical context rather than current SOTA.
