---
name: session-context
description: Lightweight arXiv session start prompt — auto-injected via AGENTS.md, loaded on demand as a skill
---

## Session Context (arXiv Research)

You have access to arXiv paper search, full-text extraction, and Semantic Scholar citation graphs. 20+ tools for academic research.

**Before starting work:**
1. Search: `search_papers(query="<topic>", limit=10)`
2. Check recents: `getRecent(category="cs.AI", count=10)`

**At end of work, save findings:**
- `ingest_paper_to_corpus(paper_id="...")`
- `store_paper_to_calibre(paper_id="...")`

**For deeper workflows, load the `arxiv-expert` skill.**
