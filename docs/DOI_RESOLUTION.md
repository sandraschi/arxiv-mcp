# DOI Resolution & the Publishing Ecosystem

arxiv-mcp can resolve DOIs (Digital Object Identifiers) to paper metadata and — when an open-access version exists — download the full text. This document explains how it works and how the academic publishing ecosystem fits together.

## What is a DOI?

A DOI is a persistent identifier for a scholarly work. It looks like:

```
10.1016/j.cell.2018.06.048
```

Unlike an arXiv ID (which is specific to arXiv), a DOI works across ALL publishers — Elsevier, Springer, IEEE, ACM, PLOS, MDPI, and thousands of others. If a paper has a DOI, it can be resolved regardless of where it's published.

## How DOI Resolution Works

arxiv-mcp uses a two-tier API pipeline:

```
[DOI input]
    ↓
[Tier 1: Unpaywall API]    ← primary, returns OA status + PDF URL
    ↓ (if closed / not found)
[Tier 2: Crossref API]     ← fallback, returns metadata + links
    ↓ (if PDF URL found)
[Download PDF → pypdf text extraction]
    ↓
[Optional: ingest to local FTS depot]
```

### Tier 1: Unpaywall (https://unpaywall.org)

Unpaywall is an open-data service that tracks open-access status across 50,000+ publishers. It harvests data from:

- **Publisher websites** — Gold OA, Hybrid OA, Bronze OA
- **Repository aggregators** — Green OA (author manuscripts in arXiv, PubMed Central, institutional repos)
- **Crossref** — metadata feeds

For a given DOI, it returns:

| Field | Meaning |
|-------|---------|
| `is_oa` | Whether an open-access copy exists |
| `oa_status` | Type of OA: `gold`, `hybrid`, `bronze`, `green`, `closed` |
| `best_oa_location.url_for_pdf` | Direct URL to the best available OA PDF |
| `z_authors` | Author list (given + family names) |
| `publisher` | Publisher name |

**No API key required.** Rate-limited via polite pool (identify yourself with an email).

### Tier 2: Crossref (https://crossref.org)

Crossref is the official DOI registration agency. It's the fallback when Unpaywall returns a closed/unknown result. Crossref returns:

- Title, authors, publisher
- `link[]` array with URLs to the publisher's version
- Content-type hints (`application/pdf`, `text/html`)

## OA Statuses Explained

| Status | Meaning | Example |
|--------|---------|---------|
| **gold** | Published in an OA journal | PLOS ONE, eLife |
| **hybrid** | Published in a subscription journal but author paid OA fee | Many Elsevier/Springer journals |
| **bronze** | Free to read on publisher site but no explicit OA license | Often older articles |
| **green** | Author manuscript available in a repository | arXiv, PubMed Central |
| **closed** | Behind a paywall, no known OA copy | Most subscription articles before ~2020 |

**Important:** arxiv-mcp does NOT bypass paywalls. It only fetches OA versions that publishers have chosen to make freely available. If a paper is `closed`, `resolve_doi` returns the metadata but no PDF link.

## What Makes a DOI Fetchable?

A DOI is fetchable when:

1. It exists in Unpaywall's index — most DOIs from 2010+ are covered
2. `is_oa = true` — any OA status works (gold, hybrid, bronze, green)
3. `best_oa_location.url_for_pdf` is present — a direct PDF link exists

Green OA papers on arXiv are a common fetchable case — the DOI resolves to the arXiv version.

## Limitations

- **No paywall bypass** — only OA versions are fetched
- **PDF quality varies** — some publisher PDFs are scans (no extractable text); pypdf will return empty text
- **Rate limits** — Unpaywall's polite pool is generous but not unlimited (~50 requests/day without API key)
- **No Sci-Hub** — arxiv-mcp does not support any illegal or legally ambiguous sources

## Tools

| Tool | Purpose |
|------|---------|
| `resolve_doi` | Takes a DOI string, returns metadata + OA status + PDF URL (no download) |
| `fetch_doi_content` | Takes a DOI string, resolves it, downloads the OA PDF, extracts text, optionally ingests to depot |

Both tools apply the same safety wrapping as arXiv content — text is wrapped with an adversarial safety boundary before reaching the LLM.

## Env Config

| Variable | Default | Purpose |
|----------|---------|---------|
| `ARXIV_MCP_UNPAYWALL_EMAIL` | *(required in `.env`)* | Email for Unpaywall polite pool (identifies your requests) |

## References

- Unpaywall API: https://unpaywall.org/products/api
- Crossref REST API: https://api.crossref.org
- pypdf: https://pypdf.readthedocs.io
