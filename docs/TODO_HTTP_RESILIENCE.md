# TODO: HTTP Resilience Hardening

Status: P0–P2 done; P1.5 depot section-chunk ingest done (2026-06-02). Memops/OAI-PMH open.
Owner: Cursor (implementation) — spec by Claude, 2026-06-03
Priority: P0 (fetch_full_text hang) > P1 (API 429) > P2 (consolidation)

## Why

Observed in a live session on 2026-06-03 against real arXiv traffic:

1. `search_papers` / `get_paper_details` returned hard `HTTPError 429` on rapid
   successive calls, then succeeded unchanged a few minutes later. Transient
   rate-limit surfaced as a hard tool failure with no retry.
2. `fetch_full_text` (HTML -> Markdown) hung for ~4 minutes and timed out with
   no result, instead of failing cleanly or returning within a bounded time.

Both make the server unreliable as a general fleet research tool. The 429 is
arXiv's documented rate limiter doing its job; the bug is the absence of
resilience around it. The hang is a real defect: an unbounded, event-loop-
blocking conversion.

This is resilience work, not "make arXiv stop throttling." The goal: every
network tool either returns a useful result or a clean structured error within
a bounded time, and transient throttling is absorbed by backoff.

## Root causes (file-level, confirmed by reading the code)

### A. fetch_full_text hang — `src/arxiv_mcp/html_extract.py`
- `fetch_html_markdown()` GETs with `timeout=60.0`, then calls
  `html_to_markdown(resp.text)` which runs `BeautifulSoup(...)` +
  `html2text.HTML2Text().handle(...)` **synchronously on the event loop**.
- For large papers (MathML-heavy VLA/world-model reports) this conversion can
  take minutes and blocks the entire async runtime — not just this call, every
  concurrent tool call on the server.
- The httpx 60s timeout covers only the GET, not the conversion. There is no
  overall wall-clock budget and no input-size cap.

### B. API 429 — `src/arxiv_mcp/config.py` + `src/arxiv_mcp/services/papers.py`
- `config.py`: `client_delay_seconds: float = 1.0`. arXiv's API courtesy delay
  is ~3 seconds between requests. At the default we poll 3x too fast and earn
  429s.
- `papers.py`: `_client()` builds `arxiv.Client(delay_seconds=..., page_size=50)`
  with no `num_retries` and no backoff. The `arxiv` lib's internal retry does
  not do exponential backoff or honor `Retry-After`, and the synchronous `_run()`
  threads (`search_papers`, `get_paper_details`, `list_category_latest`) let any
  `HTTPError`/`arxiv.*` exception propagate straight up as a hard tool failure.
- No descriptive User-Agent on the API client. `html_extract.py` already sets a
  good UA (`DEFAULT_UA`); `papers.py` uses the `arxiv` lib default. Inconsistent;
  arXiv throttles generic clients harder.

### C. Inconsistent HTTP policy across modules
Each module rolls its own httpx client and timeout: `papers.find_connected_papers`
uses `timeout=45.0`, `html_extract` uses `60.0`, `arxiv_html.http_get_text_safe`
uses `settings.arxiv_http_timeout_seconds` (30.0, and correctly never raises).
No shared UA, retry, or backoff policy.

## Tasks

### P0 — Stop fetch_full_text from hanging (`html_extract.py`)
1. Offload the CPU-bound conversion off the event loop:
   wrap `html_to_markdown(resp.text)` in `await asyncio.to_thread(...)`.
2. Add an overall wall-clock budget around the whole fetch+convert operation:
   `await asyncio.wait_for(_fetch_and_convert(), timeout=settings.fetch_full_text_budget_seconds)`.
   On `asyncio.TimeoutError` return a structured failure
   `(False, "Conversion exceeded N s budget; paper too large for HTML->MD.", None, None)`
   matching the existing 4-tuple contract — never raise, never hang.
3. Add an input-size guard before conversion: if `len(resp.text)` (or the
   `Content-Length` header) exceeds a configurable cap (default ~8 MB), skip
   conversion and return a structured "document too large, use PDF pipeline"
   message rather than grinding.
4. Replace the hardcoded `timeout=60.0` default with
   `settings.arxiv_http_timeout_seconds` so it is configurable and consistent.

Acceptance: `fetch_full_text` on a large paper (use `2509.11766`, the one that
hung) returns a result or a clean structured error within the budget. It must
never exceed `fetch_full_text_budget_seconds + ~small slack`. Concurrent tool
calls must remain responsive during a large conversion (proves the to_thread
offload).

### P1 — Absorb API 429 (`config.py` + `services/papers.py`)
1. `config.py`: change `client_delay_seconds` default `1.0 -> 3.0`. Add:
   - `arxiv_max_retries: int = 4`
   - `arxiv_backoff_base_seconds: float = 3.0`
   - `arxiv_backoff_max_seconds: float = 30.0`
   - `fetch_full_text_budget_seconds: float = 90.0`
   - `fetch_full_text_max_bytes: int = 8_000_000`
2. `papers.py`: add a retry helper used by all three `_run()` thread bodies
   (`search_papers`, `get_paper_details`, `list_category_latest`). It must:
   - catch transient errors: HTTP 429/5xx, `arxiv.UnexpectedEmptyPageError`,
     `arxiv.HTTPError`, `requests`/`urllib` connection/timeout errors;
   - exponential backoff with jitter: `min(base * 2**attempt, max) + random(0..base)`;
   - honor `Retry-After` if present on the response;
   - stop after `arxiv_max_retries`, then return a structured error envelope
     (same shape as `arxiv_html.tool_error`) — do NOT re-raise to the caller.
   Keep the retry inside the thread (sync) or convert to an async retry around
   `asyncio.to_thread`; either is fine, but the tool must return a dict error,
   not throw.
3. Set a descriptive User-Agent on the API client. `arxiv` 2.x uses a `requests`
   session internally; set `client._session.headers["User-Agent"]` to the same
   value as `html_extract.DEFAULT_UA` (lift it to a shared constant — see P2).
   If a future `arxiv` version blocks session access, fall back to P2's own
   Atom client.

Acceptance: a loop of 5 rapid `get_paper_details` calls completes with zero hard
errors (backoff absorbs any 429). Add a unit test that mocks 429-then-200 and
asserts the call returns the 200 payload after retrying.

### P2 — Consolidate HTTP policy (optional, do after P0/P1 green)
1. New `src/arxiv_mcp/http.py`: single source of truth for
   - `USER_AGENT` constant (replace `html_extract.DEFAULT_UA` and the API UA),
   - an `async get_text(url, *, timeout, retries, follow_redirects)` helper with
     the shared backoff/Retry-After logic and structured-error return,
   - a tiny on-disk response cache keyed by `(endpoint, arxiv_id)` under
     `settings.resolved_data_dir()` (arXiv records are immutable; cache cuts both
     latency and repeat-429 risk). Cache abstracts/metadata indefinitely; cache
     HTML->MD too.
   Route `papers.find_connected_papers`, `html_extract.fetch_html_markdown`,
   `arxiv_html.http_get_text_safe`, `doi_resolver`, `anthropic_blog`, `lab_blog`
   through it.
2. Semantic Scholar path (`find_connected_papers`): SS rate-limits aggressively
   without an API key. Apply the same backoff and, on 429, return a clear
   structured message advising `ARXIV_MCP_SEMANTIC_SCHOLAR_API_KEY`.

## Tests to add (`tests/`)
- `test_papers_retry.py`: mock transport 429 then 200 -> success after retry;
  mock persistent 429 -> structured error, bounded attempts, no raise.
- `test_html_extract_budget.py`: monkeypatch `html_to_markdown` to sleep past the
  budget -> `fetch_html_markdown` returns structured timeout, does not hang.
- `test_html_extract_size_cap.py`: oversized body -> structured "too large"
  result, conversion skipped.

## Conformance
Implementation must follow the repo's existing conventions and the fleet
standards (read before coding):
- `D:\Dev\repos\mcp-central-docs\standards\AGENT_PROTOCOLS.md`
- `D:\Dev\repos\mcp-central-docs\standards\WEBAPP_SOTA_STANDARDS.md`
Reuse existing patterns already in the repo: the `tool_error(...)` structured
envelope in `arxiv_html.py`, pydantic `Settings` in `config.py`, and the
`asyncio.to_thread` offload pattern already used in `papers.py`. No new heavy
dependencies; `httpx` + stdlib only.

## P1.5 — Conversion fidelity + chunk from structure (`html_extract.py`, depot)

`html_to_markdown()` runs `html2text` over arXiv HTML, then the depot chunks and
embeds that flattened Markdown. Two problems compound:

1. arXiv HTML (LaTeXML/ar5iv) renders equations as **MathML**, which `html2text`
   does not understand — it drops or garbles them. Math-heavy papers produce
   broken Markdown, and that broken text gets embedded into the LanceDB index,
   silently corrupting retrieval and downstream analysis.
2. Flattening HTML -> Markdown discards the clean section structure LaTeXML
   already produced, which the chunker then has to reconstruct from Markdown
   heading regex — destroying structure only to rebuild a worse version of it.

Key realization: LanceDB and the embedder (`bge-small-en-v1.5`) are
format-agnostic — they embed whatever text they are handed. Markdown is NOT
"easier to ingest" at the model level. arXiv HTML is already the higher-fidelity
source (real section nesting + math). Markdown's genuine value is narrow and
downstream: (a) readable retrieval payloads for the agent (never dump raw HTML
tags into context), (b) simple sqlite FTS, (c) fleet Markdown convention. None of
those is the vector index. arXiv did the hard part (LaTeX -> structured content);
do not throw it away in a lossy second hop.

So treat Markdown as a *derived product*, not the chunking substrate:

1. Source of truth = the artifact arXiv gave us. Persist the HTML (and/or the PDF
   via the existing `download_pdf_to_file` / `store_paper_to_calibre` path) in the
   depot as the archival record. The record is never the lossy conversion.
2. Chunk for the vector index *from the HTML DOM's section structure* (section /
   subsection boundaries from the LaTeXML markup), not from flattened Markdown.
   Section-aware chunks are coherent and come for free from structure we already
   have. Carry math as TeX (see 3) into the chunk text.
3. Math-aware text: extract the original TeX from arXiv MathML
   (`<annotation encoding="application/x-tex">`, `alttext`) and emit `$...$` /
   `$$...$$`. Use `html2text` only as the fallback for non-arXiv HTML lacking
   MathML.
4. Emit Markdown as one *output* of the pipeline (for reading + FTS), rendered
   from the same structured intermediate — not as the thing you chunk.
5. Conversion-quality gate: count `<math>` nodes / TeX annotations to gauge math
   density. On high density + low conversion confidence, flag the depot record
   (`conversion=degraded`) and prefer PDF-text extraction for the chunks rather
   than embedding garbled MathML. Surface the flag in `fetch_full_text`'s return.

Implementation note: the depot ingest path (`ingest_paper_to_corpus` /
`depot_service` / `vector_rag`) should accept a structured intermediate
(sections -> {heading, text-with-TeX}) rather than a single Markdown blob; the
Markdown file becomes a sibling artifact. If a full structured rewrite is too
large for one pass, the minimum viable first step is: (a) math-aware conversion so
the Markdown is at least faithful, then (b) section-aware splitting using the HTML
headings before flattening. Chunk-from-structure is the target end state.

Priority: between P1 and P2 — corpus correctness + retrieval quality, not just
ergonomics.

## Error-return & docstring conventions (applies to every task here)

- Every failure path added by this work must return the structured
  `tool_error(..., recovery_options=[...])` envelope with *actionable* guidance,
  never a bare status. The error content is consumed by the calling model and
  decides whether it recovers or burns a retry loop. Specifically, the 429 /
  retry-exhausted path (P1) must return e.g.: "arXiv is rate-limiting;
  auto-retried N times honoring a ~3s courtesy delay. Retry in ~Ns, or raise
  ARXIV_MCP_CLIENT_DELAY_SECONDS." A bare "HTTP 429" is the defect we are fixing.
- FastMCP docstring gotcha: the free-form text above `Args:` becomes the tool
  description the model sees; `Returns:` / `Raises:` / `Example:` sections are
  parsed out and **excluded** from that description. Failure-mode guidance the
  model should have *before* calling therefore belongs in the free-form
  description (or the runtime error payload) — NOT in a `Raises:` block, which the
  model never sees. This is best-practice/convention, not a hard MCP protocol rule.

## Out of scope
- Replacing the `arxiv` PyPI lib with a hand-rolled Atom client. Only do this if
  P1.3's session-based UA injection proves impossible on the installed `arxiv`
  version; otherwise it is unnecessary churn.
- PDF extraction pipeline changes.

## Estimated effort (AI-assisted)
P0: ~1-2 h. P1: ~2-3 h incl. tests. P2: ~half a day. P0+P1 are the reliability
fix and should land together; P2 is cleanup.
