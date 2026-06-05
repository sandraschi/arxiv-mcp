"""DOI resolution via Unpaywall + Crossref APIs.

Resolution pipeline:

    [DOI input] → [Unpaywall API] → {is_oa, pdf_url, title, authors}
                         ↓ (closed / not found)
                  [Crossref API] → {title, link[] with pdf}

Usage:
    from arxiv_mcp.doi_resolver import DOIResolver

    resolver = DOIResolver(email="you@example.com")
    result = await resolver.resolve("10.1016/j.cell.2018.06.048")
    if result and result.pdf_url:
        # result has .doi, .title, .authors, .oa_status, .pdf_url
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

import httpx

log = logging.getLogger(__name__)

_DOI_PATTERN = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.IGNORECASE)

_UA = "arxiv-mcp-doi/0.1 (mailto:{email})"


@dataclass
class DOIResult:
    doi: str
    title: str
    authors: list[str] = field(default_factory=list)
    is_oa: bool = False
    oa_status: str = "unknown"
    pdf_url: str | None = None
    publisher: str | None = None


class DOIResolver:
    """Resolve DOIs to metadata and OA PDF URLs via Unpaywall + Crossref."""

    def __init__(self, email: str = ""):
        if not email.strip():
            raise ValueError(
                "Unpaywall email required — set ARXIV_MCP_UNPAYWALL_EMAIL in .env "
                "(Unpaywall polite pool; use your contact address)."
            )
        self.email = email.strip()
        self._http = httpx.AsyncClient(
            headers={"User-Agent": _UA.format(email=email)},
            timeout=15.0,
            follow_redirects=True,
        )

    async def close(self) -> None:
        await self._http.aclose()

    def extract_doi(self, text: str) -> str | None:
        match = _DOI_PATTERN.search(text.strip())
        if not match:
            return None
        return match.group(1).rstrip(".")

    async def query_unpaywall(self, doi: str) -> dict[str, Any] | None:
        url = f"https://api.unpaywall.org/v2/{quote(doi)}?email={quote(self.email)}"
        try:
            resp = await self._http.get(url)
            if resp.status_code == 200:
                return resp.json()
            log.warning("Unpaywall HTTP %s for DOI %s", resp.status_code, doi)
        except httpx.TimeoutException:
            log.warning("Unpaywall timeout for DOI %s", doi)
        except httpx.RequestError as exc:
            log.warning("Unpaywall request error for DOI %s: %s", doi, exc)
        return None

    async def query_crossref(self, doi: str) -> dict[str, Any] | None:
        url = f"https://api.crossref.org/works/{quote(doi)}"
        try:
            resp = await self._http.get(url)
            if resp.status_code == 200:
                return resp.json()
            log.warning("Crossref HTTP %s for DOI %s", resp.status_code, doi)
        except httpx.TimeoutException:
            log.warning("Crossref timeout for DOI %s", doi)
        except httpx.RequestError as exc:
            log.warning("Crossref request error for DOI %s: %s", doi, exc)
        return None

    async def resolve(self, raw_input: str) -> DOIResult | None:
        """Triaged pipeline: Unpaywall → Crossref fallback."""
        doi = self.extract_doi(raw_input)
        if not doi:
            return None

        # Tier 1: Unpaywall
        up = await self.query_unpaywall(doi)
        if up and up.get("is_oa") is not None:
            pdf_url = None
            best_loc = up.get("best_oa_location") or {}
            if best_loc:
                pdf_url = best_loc.get("url_for_pdf") or best_loc.get("url")
            authors = _parse_authors(up.get("z_authors", []))
            return DOIResult(
                doi=doi,
                title=up.get("title", ""),
                authors=authors,
                is_oa=up.get("is_oa", False),
                oa_status=up.get("oa_status", "unknown"),
                pdf_url=pdf_url,
                publisher=up.get("publisher"),
            )

        # Tier 2: Crossref fallback
        cr = await self.query_crossref(doi)
        if cr and "message" in cr:
            msg = cr["message"]
            pdf_url = None
            for link in msg.get("link", []):
                if link.get("content-type") in ("application/pdf", "unspecified"):
                    pdf_url = link.get("url")
                    break
            authors = _parse_crossref_authors(msg.get("author", []))
            return DOIResult(
                doi=doi,
                title=msg.get("title", [""])[0] if msg.get("title") else "",
                authors=authors,
                is_oa=pdf_url is not None,
                oa_status="bronze" if pdf_url else "unknown",
                pdf_url=pdf_url,
                publisher=msg.get("publisher"),
            )

        return DOIResult(doi=doi, title="", oa_status="unknown")

    async def fetch_pdf_text(self, pdf_url: str, max_chars: int = 100_000) -> str | None:
        """Download PDF from url, extract text with pypdf."""
        try:
            resp = await self._http.get(pdf_url)
            resp.raise_for_status()
        except httpx.RequestError as exc:
            log.warning("PDF download failed for %s: %s", pdf_url, exc)
            return None
        try:
            from io import BytesIO

            from pypdf import PdfReader

            reader = PdfReader(BytesIO(resp.content))
            parts: list[str] = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    parts.append(text)
                if sum(len(p) for p in parts) > max_chars:
                    break
            return "\n\n".join(parts)[:max_chars]
        except Exception as exc:
            log.warning("PDF text extraction failed: %s", exc)
            return None


def _parse_authors(authors_raw: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for a in authors_raw:
        given = (a.get("given") or "").strip()
        family = (a.get("family") or "").strip()
        name = f"{given} {family}".strip()
        if name:
            out.append(name)
    return out


def _parse_crossref_authors(authors_raw: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for a in authors_raw:
        given = (a.get("given") or "").strip()
        family = (a.get("family") or "").strip()
        name = f"{given} {family}".strip()
        if name:
            out.append(name)
    return out
