# SPEC: DOI Resolution & Auto-Retrieval Pipeline

**Status**: Implemented (2026-05-03)
**Date**: 2026-05-03
**Scope**: arxiv-mcp expansion — DOI → metadata → PDF → text → RAG

## Problem

The server can search arXiv and pull full text from `arxiv.org/html/{id}`, but only for papers on arXiv. Many papers exist only behind DOIs — paywalled journal articles, conference proceedings, or papers on other repositories. An AI agent or researcher pasting a DOI gets nothing.

## Solution

Two-tier DOI resolution using Unpaywall (primary) and Crossref (fallback):

```
[DOI input] → [Unpaywall API] → {is_oa, best_oa_location.url_for_pdf, title, authors}
                     ↓ (if closed or not found)
              [Crossref API] → {title, author, link[] with content-type}
                     ↓ (if PDF URL found)
              [Download PDF] → [Extract text via pypdf] → [Return text or ingest to depot]
```

## APIs

### Tier 1: Unpaywall (https://api.unpaywall.org/v2/{doi}?email={email})

- Free, no API key required (email for rate limiting — 50/day without key via polite pool)
- Returns JSON with `is_oa`, `best_oa_location.url_for_pdf`, `title`, `z_authors`, `oa_status`
- Covers 50,000+ publishers and repositories

### Tier 2: Crossref (https://api.crossref.org/works/{doi})

- Free, no API key, "polite" rate limit (50 req/s with `mailto:` header)
- Returns structured metadata with `link` array containing `content-type: application/pdf` URLs
- Used as fallback when Unpaywall returns `is_oa: false`

## New Modules

### `src/arxiv_mcp/doi_resolver.py`

```
class DOIResolver:
    doi_regex: re.Pattern
    email: str
    
    extract_doi(raw: str) -> str | None
    query_unpaywall(doi: str) -> dict | None      # async httpx
    query_crossref(doi: str) -> dict | None        # async httpx
    resolve(raw_input: str) -> DOIResult | None    # triaged pipeline
```

### `DOIResult` (dataclass)

```python
@dataclass
class DOIResult:
    doi: str
    title: str
    authors: list[str]
    is_oa: bool
    oa_status: str           # gold | hybrid | bronze | green | closed
    pdf_url: str | None
    publisher: str | None
```

## New MCP Tools

### `resolve_doi` (READ_ONLY)
- **Input**: `doi: str` — raw DOI (`10.1016/j.cell.2018.06.048`) or DOI URL
- **Output**: `DOIResult` dict — metadata + OA status + PDF URL if available
- **No PDF download** — fast, used for discovery

### `fetch_doi_content` (READ_ONLY)
- **Input**: `doi: str`, `ingest_to_depot: bool = False`
- **Pipeline**: resolve DOI → download PDF from `pdf_url` → `pypdf` text extraction
- **Output**: `{doi, title, authors, text, word_count, ingested}` 
- When `ingest_to_depot=True`, also stores in local FTS corpus

## Safety

All text ingested from external PDF sources gets the same safety wrapping as arXiv content:
- `wrap_untrusted()` applied to title, author names, and extracted text before returning to the LLM
- PDF content is untrusted — it can contain prompt injections in paper body
- `sanitize_text()` for zero-width character stripping

## Dependencies

- `httpx` (already used)
- `pypdf` (new — `uv add pypdf`)
- No cloud APIs, no API keys required

## Error Modes

| Failure | Behavior |
|---------|----------|
| Invalid DOI | `resolve_doi` returns structured error with `error_type: "ValidationError"` |
| Unpaywall unreachable | Falls back to Crossref |
| Crossref unreachable | Returns error with `recovery_options: ["Retry later", "Verify DOI is correct"]` |
| PDF download fails (403/404) | Returns partial result with `pdf_error` and `recovery_options` |
| PDF text extraction fails | Returns partial result with `extraction_error` |

## Integration Points

1. **Unpaywall URL**: `https://api.unpaywall.org/v2/{doi}?email={ARXIV_MCP_UNPAYWALL_EMAIL}` — configurable via env
2. **Crossref URL**: `https://api.crossref.org/works/{doi}` — static
3. **PDF download**: Transient — stream to temp, extract text, delete PDF
4. **Depot ingestion**: Reuses `corpus.ingest_markdown()` — same FTS index

## What This Does NOT Do

- Does NOT bypass paywalls — only fetches OA or author-posted versions
- Does NOT handle libgen/Sci-Hub or any legally ambiguous sources
- Does NOT cache PDFs — text is extracted and PDF is deleted
- Does NOT support batch DOI resolution (single DOIs only — composable by caller)

## Test Plan

| Test | Scope |
|------|-------|
| `test_extract_doi` | Regex: bare DOI, DOI URL, DOI in text, invalid inputs |
| `test_query_unpaywall_oa` | Mock httpx: known OA paper → returns pdf_url |
| `test_query_unpaywall_closed` | Mock httpx: closed paper → falls back to Crossref |
| `test_query_crossref_fallback` | Mock httpx: Crossref link array with PDF |
| `test_resolve_full` | End-to-end: DOI → resolve → metadata |
| `test_resolve_invalid` | Bad DOI → structured error |
