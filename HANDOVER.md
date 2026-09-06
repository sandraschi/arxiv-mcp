---
updated: 2026-08-30T13:55:00+02:00
agent: claude
status: in-progress
tags: [arxiv-mcp, fastmcp, rag, lancedb, bug, high]
---

# Handover

See `mcp-central-docs/standards/HANDOVER_STANDARD.md` for the schema and rules before
editing this file.

## What's happening right now

Confirmed and root-caused Sandra's "chunking's ok, then crickets" report. RAG retrieval
itself (FTS/semantic/hybrid via `search_depot_corpus`) works correctly end-to-end for
fully-embedded content — verified live with real queries returning relevant hits. The
actual bug: 4 of 21 papers in the depot have only 32-44% of their chunks embedded into
LanceDB despite 100% making it into the SQLite FTS index. Embedding silently stops
partway through per-paper with no error surfaced.

## Last concrete action

Cross-referenced `corpus.sqlite3` (`chunks_fts` table, per-`arxiv_id` counts) against
the LanceDB `paper_chunks` table (`count_rows(filter=...)` per id) via a one-off script
run with `uv run --no-sync python` (NOT `uv run` plain — that triggers a `uv sync` that
fights the live server for a locked pyarrow DLL, confirmed this session).

Results:
- Short: `2505.20286v1` (112 FTS / 38 LanceDB), `2506.01056v4` (132/44),
  `2510.23601v1` (153/49), `2608.23552v1` (101/44). First three have mtimes ~27 seconds
  apart — one batch run, embedding failed partway through each in the same pattern.
- Excess/orphaned: `2402.08954v1` (+3), `2603.26524v1` (+4), `2605.13841v1` (+8) —
  LanceDB has more rows than FTS, i.e. stale duplicate vectors from a re-chunk that was
  never cleaned up on the vector side.
- Everything else (17 papers, including all 10 ingested earlier today) matches exactly.
- Tried `arxiv-mcp:reindex_depot_vectors` as the built-in fix — it fails outright,
  bare "Tool execution failed", no detail.
- While inspecting LanceDB directly: `tbl.to_pandas()` throws `The lance library is
  required... pip install pylance` — `pylance` isn't installed even though basic
  `lancedb` calls (connect/count/filter) work fine. Root-cause candidate:
  `reindex_depot_vectors` almost certainly hits the same missing dependency
  internally, which is why the self-heal tool has been silently broken the whole time
  this bug existed — nobody could have fixed it by just clicking reindex.

## Next step

Add `pylance` to `arxiv-mcp`'s dependencies (pyproject.toml), then `uv sync` on a
**server restart, not hot** — `uv run` already fought this session for a DLL lock held
by the live MCP process. After that, re-run `reindex_depot_vectors`: it should either
backfill the 4 short papers or finally throw a real error instead of a bare failure.

## Blockers

Can't safely `uv sync` while the arxiv-mcp MCP server is live (connected right now in
this Claude session) — the venv's pyarrow DLL is locked by the running process. Needs a
window where the server isn't connected.

## Context the next agent needs

- The arXiv-only `ingest_paper_to_corpus` gap noted earlier this session is still real
  and still worth fixing, but is now secondary to the embedding-completeness bug above.
- Don't trust `reindex_depot_vectors` succeeding silently as proof of a fix — given it
  currently fails outright, confirm with the same FTS-vs-LanceDB count cross-check
  script pattern (see Last concrete action) before declaring this closed.
- The 3 papers with orphaned excess rows need a separate cleanup pass (delete stale
  vector rows for those `arxiv_id`s, don't just re-embed on top) — not the same fix as
  the 4 short papers.
