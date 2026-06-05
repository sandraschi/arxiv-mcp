# arxiv-mcp — Full Assessment (2026-06-02)

Reviewer: Claude (peer review against mcd SOTA standards v12.1 / WEBAPP_SOTA v1.0).
Scope: source tree, FastMCP server surface, FastAPI layer, RAG/corpus services,
epistemic pipeline, Prefab UI, webapp, packaging, CI, docs. Local clone at
`D:\Dev\repos\arxiv-mcp`, version `0.6.0` (pyproject).

---

## 1. Verdict

This is one of the stronger servers in the fleet on *capability* and easily the
most interesting on *concept*. The epistemic-profiling layer (rule + LLM claim
table, evidence-mode classification, "what still needs a bench/telescope/human"
flags) is genuinely novel and well factored. Prompt-injection defense is real and
applied consistently at the tool-return boundary. Dual transport, DOI resolution,
lab-blog fetchers, hybrid RAG, and ten serious analysis prompts make this a
broad, useful surface.

It is held back by **version incoherence across metadata**, **incomplete
adherence to two fleet mandates** (Prefab coverage and the startup probe), an
**embedding-model deviation from the RAG standard**, and **local repo hygiene**
(a large pile of `.bak` files — gitignored, so cosmetic, but they pollute every
agent `directory_tree` and grep). None of these are architecture-level; they are
the gap between "works well" and "fleet-grade DONE."

Rough grade against fleet tiers: **high B / low A-**. The fixes below are mostly
hours, not days.

---

## 2. What the server actually is

- **Tools (~28)**: arXiv API discovery (`search_papers`, `get_paper_details`,
  `list_category_latest`, `find_connected_papers`), arxiv.org HTML scrape surface
  (`search`, `searchAdvanced`, `getPaper`, `getContent` via Jina, `getRecent`,
  `listCategories`), full-text (`fetch_full_text` HTML to MD), corpus
  (`ingest_paper_to_corpus`, `search_depot_corpus`, `depot_rag_status`,
  `reindex_depot_vectors`), epistemics (`analyze_paper_epistemics`,
  `ingest_and_analyze_paper`, `deep_analyze_paper_epistemics`,
  `list_depot_by_epistemics`), DOI (`resolve_doi`, `fetch_doi_content`),
  lab blogs (`fetch_lab_post`, `list_lab_posts`, + Anthropic compat shims),
  Calibre bridge (`store_paper_to_calibre`), sampling
  (`arxiv_agentic_assist`, `arxiv_sampling_hint`), Prefab (`show_paper_card`),
  synthesis (`compare_papers_convergence`).
- **Prompts (12)**: workflow, adversarial summary, consciousness survey,
  AI-consciousness, neurophilosophy, convergence, firefront scan, corpus build,
  replication audit, citation map, epistemic profile. Strong, opinionated, and
  aligned to Sandra's research interests.
- **Storage**: SQLite (`papers`, `favorites`, `chunks_fts` FTS5) + optional
  LanceDB vectors; hybrid RRF merge.
- **Transports**: stdio and streamable HTTP (`/mcp` mounted on FastAPI), ports
  10770/10771.
- **Webapp**: React/Vite, 11 routes.

---

## 3. Strengths (keep, don't regress)

1. **Epistemic layer is the differentiator.** `epistemic_deep.py` is clean:
   strict JSON schema, fence-stripping, claim normalization, mode-vote to set
   `primary_mode`, rule+LLM merge with an honest `analyzer` label
   (`rule_v1+mcp_sample`). Dual sampling path (MCP `ctx.sample` first, then
   OpenAI-compatible HTTP fallback) is the right design and degrades correctly.
2. **Prompt-injection defense is not theater.** Two layers (zero-width strip +
   `wrap_untrusted` boundary), applied at the tool-return boundary across 18+
   tools, with a documented threat model and named infected-paper IDs.
   Correctly *not* applied to REST responses (human readers). This is ahead of
   most of the fleet.
3. **Honest failure contracts.** Tools return structured
   `{success, error, error_type, recovery_options}` rather than throwing; the
   `prefer_html=false` and `html_available` paths tell the truth about what
   wasn't extracted. Matches IMPLEMENTATION_HONESTY_STANDARD.
4. **Dual-transport discovery done properly.** `glama.json` lists both packages;
   `/.well-known/mcp/manifest.json` exists; FastMCP `http_app` mounted at `/mcp`.
5. **Sensible chunking.** Section-aware (`## ` heading split) before sliding
   window with overlap — better retrieval than naive fixed windows.

---

## 4. Gaps and defects

### 4.1 Version incoherence (HIGH — trivial fix, real confusion)

The project reports at least **four different versions** depending on where you look:

| Source | Version string |
|---|---|
| `pyproject.toml` | `0.6.0` |
| `manifest.json` | `0.4.0` |
| `glama.json` | `0.3.1` (and description still says "FastMCP **3.1**") |
| `app.py` FastAPI `version=` | `0.4.0` |
| `app.py` root `/` + `/.well-known` | `0.3.1` |
| `CHANGELOG.md` top entry | `0.4.0` (with a stale `[Unreleased]` block holding 0.5/0.6-era work) |

A consumer reading `glama.json` is told this is a FastMCP 3.1 / 0.3.1 beta; the
code is FastMCP 3.2 / 0.6.0. Pick `0.6.0`, propagate everywhere, and fold the
`[Unreleased]` block into a real `0.5.0`/`0.6.0` section. `glama.json`
description and the `fastmcp-3.1` keyword are factually wrong now.

### 4.2 Prefab coverage below the fleet mandate (HIGH)

AGENT_PROTOCOLS §2.2 / TOOL_DESIGN §4 make Prefab surfaces **mandatory for
list / status / stats tools**. The server has exactly one Prefab tool
(`show_paper_card`). Missing cards that the standard requires:

- `depot_rag_status` -> status card (LanceDB health, indexed chunks, model, db path)
- `depot_stats` / dashboard stats -> stats card (papers, favorites, chunks, RAG state)
- `list_depot_by_epistemics` / `list_ingested` -> list card
- `find_connected_papers` -> a citation-graph list card is the obvious high-value add
- a claims/epistemic-profile card for `deep_analyze_paper_epistemics` — this is the
  flagship feature and currently returns raw JSON

The infrastructure is already there (`register_prefab_tools`, the `[apps]` extra,
the env toggle). This is additive work, ~half a day for the high-value three.

### 4.3 Missing FastMCP 3.2 startup probe (MEDIUM)

`fastmcp-3.2-startup-probes.md` mandates a shallow connectivity probe in the
lifespan. `app.py` uses `lifespan=mcp_http.lifespan` verbatim — no arXiv / Jina /
Semantic Scholar reachability check, no LanceDB import check at boot. A stdio
client gets no early signal that, e.g., outbound HTTPS is blocked or the `rag`
extra is missing until the first tool call fails. Add a wrapping lifespan that
does one cheap `HEAD`/tiny GET against arxiv.org and logs RAG-deps availability,
then yields to the MCP lifespan.

### 4.4 Embedding model deviates from RAG standard (MEDIUM)

`ai-rag-2026.md` sets the fleet default to **LanceDB + FastEmbed +
`bge-small-en-v1.5`**. arxiv-mcp uses **`sentence-transformers` +
`all-MiniLM-L6-v2`** (config default and `vector_rag.DEFAULT_MODEL`). Two
problems: (a) different embedding space from the rest of the fleet, so a future
shared/federated index can't mix arxiv-mcp vectors with calibreops/docsops
vectors; (b) `sentence-transformers` pulls a much heavier dependency tree than
FastEmbed. If there's a deliberate reason to stay on MiniLM, document it in the
repo; otherwise migrate to the standard stack. Note this is a **breaking index
change** — requires `reindex_depot_vectors` after switching.

### 4.5 `manifest.json` stdio command is wrong (MEDIUM — breaks MCPB install)

```json
"args": ["python", "-m", "arxiv_mcp", "--stdio"]   // missing "run"
```

Everywhere else (README, glama.json, well-known) the command is
`uv run python -m arxiv_mcp --stdio`. As written the MCPB manifest would invoke
`uv python -m ...`, which is not a valid uv invocation. Also `manifest_version`
is `0.2`; confirm against current MCPB CLI `validate` — the rest of the fleet is
on a newer schema.

### 4.6 Hardcoded personal paths in a public tool (MEDIUM — privacy + portability)

`store_paper_to_calibre` hardcodes:
- default `library_path = r"L:\Multimedia Files\...\Calibre-Bibliothek IT"`
- `calibredb = r"C:\Program Files\Calibre2\calibredb.exe"`
- temp dir `r"D:\Dev\repos\temp"`

`config.py` also ships `unpaywall_email = "sandraschipal@hotmail.com"` as a
committed default. For a server published to Glama/GitHub this leaks a personal
email and bakes in machine-specific paths that no other user can satisfy. Move
all of these to `Settings` (env-overridable), default the Calibre paths to
`None` with a clear "not configured" error, and make the Unpaywall email a
required-at-runtime setting (Unpaywall's API politely wants a real contact, but
it shouldn't be *your* address by default).

### 4.7 CORS `allow_origins=["*"]` with `allow_credentials=True` (LOW–MEDIUM)

In `build_app()` this combination is rejected by browsers (and is a smell even
for a localhost dashboard). Since the dashboard is same-origin-ish on a fixed
port, scope origins to `http://127.0.0.1:10771` / `localhost:10771` or drop
`allow_credentials`.

### 4.8 Repo hygiene — `.bak` sprawl (LOW, but pervasive friction)

`directory_tree` shows ~70+ `*.bak` / `*.py.bak` / `*.tsx.bak` / `*.ps1.bak`
files plus `pyproject.toml.bak`, three `ARCHITECTURE_*.md.bak`, etc. They are
**gitignored** (`*.bak`, `data/`), so this is not a published-repo problem — but
every agent that runs a tree or a recursive grep wades through them, and a couple
(`pyproject.toml.bak`) sit at repo root. Git history already is the backup; these
are an editor/agent artifact. Sweep them (`Get-ChildItem -Recurse -Filter *.bak |
Remove-Item`) and, if some are wanted, stash them outside the repo. The
`_dashboard/` dir is also gitignored yet present locally — confirm it's dead.

### 4.9 Single-file `server.py` at ~1900 lines (LOW — maintainability)

All tool and prompt registrations live in one module. The fleet portmanteau/
modular pattern would split tools by domain (discovery / corpus / epistemics /
doi / blogs / prefab) into `tools/*.py` with a `register_*` per module, matching
what `AGENTS.md` already *claims* the layout is (it lists "Tool Modules" that
don't exist as separate files). Either refactor to match the doc, or fix the doc.
Not urgent, but it's the kind of thing that rots.

### 4.10 Webapp standard gaps (LOW–MEDIUM)

Against WEBAPP_SOTA_STANDARDS:
- **No LLM Chat page** — mandatory in the blueprint; current routes are
  dashboard/search/semantic/depot/favorites/tools/anthropic/apps/help/settings.
- **No API Docs page** — this is a FastAPI server, so §IX mandates an `/api-docs`
  route embedding Swagger/ReDoc with the dark-theme override. Easy win and it's
  the whole reason to be on FastAPI.
- **No `/logs` page** (WEBAPP_LOGS_PAGE) — there's a `LoggerContext` but no
  dedicated logs route per the standard.
- **No Skill page** — the server *does* expose a skill
  (`skills/arxiv-researcher` via `SkillsDirectoryProvider`), so §V applies:
  `GET /api/skills` + a render page are expected.
- **Local-intelligence "Glom On"** (§VI) — couldn't confirm the 11434/1234 scan;
  verify SettingsPage implements auto-discovery + GPU-opportunity prompt.
- No `GET /api/capabilities` endpoint (capability introspection pattern).

### 4.11 Testing depth (LOW)

Seven test files, mostly unit (ids, doi, corpus fts/rag, epistemic, arxiv_html).
Gaps: no test exercises the MCP tool layer end-to-end (tool -> service -> return
shape with `wrap_untrusted` present), and no Playwright e2e for the webapp
(mandatory per `playwright_e2e_sota.md` for any repo with a webapp). `respx` is
already a dep — good — so HTTP doubles for the arxiv/Jina/Unpaywall paths are
cheap to add.

### 4.12 Minor correctness notes

- `fetch_doi_content` returns the full extracted PDF body as `text` with no size
  cap; a 40-page OA PDF can blow the tool-response budget. Add a `max_chars` /
  truncation flag like the other full-text tools.
- `_profile_matches_filters` returns `True` for a profile-less paper only when
  the first three filters are `None` but ignores `needs_formal_verification` /
  `has_deep_claims` in that early branch — a paper with no profile can leak into
  a `needs_formal_verification=False` query inconsistently. Tighten the guard.
- `search` tool silently drops rows that fail HTML parse (documented), but
  `parse_stats` is referenced in the manifest/tools description and isn't in the
  actual `search` return shape shown — verify the contract matches the docstring.
- `list_category_latest` (API) and `getRecent` (HTML) overlap heavily; consider
  consolidating or cross-referencing in docstrings so an agent picks correctly.

---

## 5. Possible improvements (beyond fixing gaps)

These are genuinely additive, ordered by value-to-effort.

1. **Prefab claims card for the epistemic profile.** The flagship output deserves
   a rich card: per-claim rows with evidence-mode badges, confidence, and the
   bench/telescope/formal/human flags as icon chips, plus the `deep_summary`.
   This is the single highest-impact UI addition.
2. **Persist deep epistemic profiles to the corpus by default.** `merge_profiles`
   produces a claims table; `persist_epistemic_profile` exists; wire
   `deep_analyze_paper_epistemics` to persist so `list_depot_by_epistemics` can
   filter on `has_deep_claims` without a re-run. (Check it isn't already and just
   undocumented.)
3. **A `firefront` background/scheduled mode.** The prompt exists; a thin tool
   that runs the firefront scan for a saved topic list and writes a digest to the
   depot (or hands off to aiwatcher-mcp) would make the daily-triage use case
   real rather than prompt-only.
4. **Memory/federation hook.** Given memops + the federation-hub work, expose the
   epistemic claims and corpus hits in a shape memops can ingest, so "papers I've
   read, classified by knowing-type" becomes cross-session queryable.
5. **arXiv `listing` / OAI-PMH for true recency.** `list_category_latest` filters
   client-side on published time from a normal query; the arXiv OAI-PMH or the
   per-category `/list/<cat>/recent` endpoints give exact daily firefronts without
   guessing the window.
6. **PDF fallback for `fetch_full_text`.** Right now non-HTML papers dead-end with
   a recommendation to use an external pipeline. `pypdf` is already a dependency
   (used by the DOI path); reuse it to extract PDF text when HTML is absent,
   closing the "html_available=false" gap.
7. **`bge` migration + FastEmbed** (see 4.4) doubles as a perf win — FastEmbed is
   ONNX and lighter than sentence-transformers, and unifies the embedding space
   with the rest of the fleet for a future shared index.
8. **Capability endpoint + dynamic Tools page.** `tools_manifest.py` is a
   hand-maintained static mirror of the real registrations — it *will* drift
   (it's already missing the DOI tools' presence in some counts). Generate it
   from `mcp.list_tools()` at runtime via `GET /api/capabilities`, and have the
   webapp consume that, killing the drift class entirely.

---

## 6. Suggested fix order (fast path to fleet-grade DONE)

**Session 1 (~1 day) — coherence + mandates**
1. Unify version to `0.6.0` everywhere; fix `glama.json` description/keywords
   (3.1->3.2); fold `[Unreleased]` into real changelog sections. (4.1)
2. Fix `manifest.json` stdio args (`uv run python ...`); re-run `mcpb validate`. (4.5)
3. Move hardcoded Calibre paths + Unpaywall email to env-overridable settings;
   default Calibre to `None`. (4.6)
4. `.bak` sweep + confirm `_dashboard/` is dead. (4.8)
5. Add the startup connectivity probe to the lifespan. (4.3)

**Session 2 (~1 day) — Prefab + UI mandates**
6. Prefab cards: `depot_rag_status` (status), `depot_stats` (stats),
   epistemic claims card. (4.2, 5.1)
7. API Docs page + `/api/capabilities` + dynamic Tools page. (4.10, 5.8)

**Session 3 (~0.5–1 day) — RAG + tests**
8. Migrate to `bge-small-en-v1.5` + FastEmbed; reindex; document the break. (4.4, 5.7)
9. Add MCP-layer integration tests (return-shape + `wrap_untrusted`) and a
   Playwright smoke for the webapp routes. (4.11)

PDF fallback (5.6), firefront scheduled mode (5.3), and server.py modular split
(4.9) are follow-ups, not blockers.

---

## 8. Corollary — Release deliverables & Tauri packaging (added 2026-06-02)

Added after review discussion. The 0.6.0 release ships **three artifacts**: MCPB
(primary Claude Desktop install), a Python **wheel**, and a **Tauri desktop app**
(porting an established pattern already used in other fleet repos). Notes below
are constraints for whoever builds these, to be confirmed in the handover note.

### 8.1 MCPB
- Fix the stdio args first (see 4.5: `uv run python ...`), then `mcpb validate`
  and `mcpb pack`. Do **not** use `mcpb init`/`publish`.
- Confirm `manifest_version` against the current CLI; bump if the schema moved.

### 8.2 Wheel
- Free deliverable: build-backend is already setuptools, so `uv build` emits sdist
  + wheel. Attach to the GitHub release. This is the artifact for the `uvx`/
  `pip install` install tier and for library use.

### 8.3 Tauri app — backend strategy (the real decision)

Context that changes the design: the **HTTP backend is intended to run
permanently**, started and supervised by `mcp-federation-hub` as one of its
important always-on servers. That makes the steady state "one backend on 10770,
already up" rather than "Tauri must boot its own."

**There is no port conflict between a stdio backend and the HTTP backend.** When
Claude Desktop runs `--stdio`, that process binds **no port** — it talks over
stdin/stdout. The `--serve` HTTP mode (10770) is separate. So two processes never
fight over the port. The only shared resource is **on disk**: the SQLite depot
(`corpus.sqlite3`) and the LanceDB dir. SQLite serializes writers; LanceDB and the
ingest path are **not** built for two concurrent writers. That, not ports, is the
hazard.

**Chosen approach — probe-then-attach (don't blindly spawn):**
1. On launch, Tauri probes `http://127.0.0.1:10770/api/health`.
2. If it answers and identifies as arxiv-mcp (hub-managed backend, the normal
   case) → Tauri is a **pure webview shell**, spawns **no** sidecar.
3. Only if nothing answers (cold start, hub not running) → spawn a sidecar as
   fallback.

This is strictly better than "always spawn a sidecar": in the expected
deployment Tauri never starts a second backend, so the double-writer hazard
effectively disappears (everyone shares the hub's single backend).

### 8.4 Tauri app — teardown / zombie killer (mandatory)

The `start.ps1` scripts clear the port on launch; the Tauri shell needs the same
discipline **plus** lifecycle teardown the scripts don't have to worry about:
- Kill the sidecar on app exit — including OS-level window close, app crash, and
  forced kill, not just clean menu-quit (use Tauri exit hooks / `on_window_event`).
- **Only kill a sidecar we spawned.** If Tauri attached to the hub-managed backend
  (8.3 step 2), it must **never** kill it on exit — that backend belongs to the
  hub. Track a "did I spawn this?" flag and gate teardown on it.
- Port-already-bound check before spawning: "is 10770 mine, the hub's, or stale?"
  Attach in the first two cases; only spawn if genuinely free.

### 8.5 Embedding model in the bundle (depends on 4.4)

Decision: **do not bundle** the embedding model. Rationale: the model is likely
to change, so baking it into the installer creates stale-artifact risk.
- Model name lives in `.env` (`ARXIV_MCP_EMBEDDING_MODEL`, already in `config.py`).
- First run downloads it from HF with a visible progress state in the dashboard.
- FastEmbed caches locally, so subsequent launches are offline.
- **First-run-offline must fail soft** to FTS-only — the hybrid RRF path in
  `corpus.py` already degrades to `sqlite_fts5` when semantic is unavailable, so
  wire the Tauri/first-run path to honor that rather than block app start.
- Consequence: "no models bundled" and "semantic search works offline on first
  launch" cannot both hold. Accepted — first launch needs network for the model;
  document it.

### 8.6 Federation consequence (flag, not a defect)

If the hub runs the HTTP backend permanently, Claude Desktop should ideally point
at that backend over **HTTP/streamable** rather than also spawning its own
`--stdio` process — otherwise the double-writer hazard returns via the back door
(stdio process + hub process, same depot). This is a **fleet-config decision tied
to the federation rollout**, not an arxiv-mcp code defect, but it should be
settled before the always-on hub deployment so the depot has a single writer in
practice.

### 8.7 Standards follow-up (separate from this repo)

`LLM_AND_INSTALL_TIERS` predates the Tauri work and does not yet describe Tauri
as an install tier. It needs a small amendment: a Tauri tier entry covering the
sidecar/probe-then-attach strategy, the acceptable bundle-size envelope (few
hundred MB, **models excluded**), the teardown/own-sidecar-only rule, and the
first-run model-download pattern. This is an **mcd standards edit**, not part of
arxiv-mcp's handover — tracked here so it isn't lost.

---

## 9. One-line summary

Conceptually excellent and security-conscious; needs a version/metadata cleanup,
the two outstanding fleet mandates (Prefab coverage + startup probe), the RAG
embedding-model alignment, and removal of hardcoded personal paths before it's
clean DONE — all measured in hours.
