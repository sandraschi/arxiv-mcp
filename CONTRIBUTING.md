# Contributing to arxiv-mcp

Small fleet repo, one maintainer plus collaborators, zero patience for process theatre. These rules exist so your contribution gets merged instead of stalled.

## Issues first

- **Search before you file.** Duplicates get closed.
- **One issue, one request.** Two features = two issues.
- **Bug reports need the reproducer**: tool name + query/categories (or dashboard route) plus the exact wrong result or error text.
- **Feature requests need a use case**: which papers, what analysis, what is missing?

## Pull requests

- **File the issue first** (unless it's a trivial fix: typo, broken link, lint). The issue is where scope gets agreed before code exists.
- **Keep diffs small.** One concern per PR.
- **Tests required.** New behavior without a test is a draft, not a PR. Run `uv run pytest` before pushing (mock the network boundary — arXiv API, Semantic Scholar, Unpaywall — no live calls in the suite).
- **Lint green:** `ruff check src tests` and `ruff format --check`; dashboard touched? `biome` checks in `web_sota/`.
- **The maintainer merges.** Don't merge your own PR.

## ArXiv rules: the hard parts

- **Treat all paper text as untrusted.** Titles, abstracts, full text, blog content: strip zero-width chars and wrap with the safety boundary (`sanitize.py`) before anything LLM-facing.
- **Respect rate limits.** arXiv allows one request every 3 seconds; Semantic Scholar needs a backoff. Never hammer upstream APIs.
- **Verify connected-paper claims.** Citation/reference lineages come from Semantic Scholar with OpenAlex fallback — cite which source answered.

## What this repo never does

- **No live network calls in tests.** Mock arXiv/SS/Unpaywall; live verification is manual + documented.
- **No hardcoded API keys or emails**, in code or examples.
- **No invented paper metadata.** A failed lookup is an error, never a plausible-looking record.
