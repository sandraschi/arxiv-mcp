# arxiv-mcp — Copilot instructions

This repo is the arXiv research MCP server (FastMCP, ports 10770 backend / 10771 web).
Before starting work: check depot state with `search_depot_corpus` and pipeline health with `pipeline_liveness_tool`.
Key tools: `search_papers`, `fetch_full_text`, `find_connected_papers`, `ingest_paper_to_corpus`, `run_codehunt_scan_tool`.
At end of work: ingest papers you read, run `uv run ruff check src/` and `uv run pytest -q`, leave the tree clean.
