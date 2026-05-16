"""Tests for DOI resolver module."""
from __future__ import annotations

import pytest

from arxiv_mcp.doi_resolver import DOIResolver


@pytest.fixture
def resolver() -> DOIResolver:
    return DOIResolver(email="test@example.com")


class TestExtractDOI:
    def test_bare_doi(self, resolver: DOIResolver) -> None:
        assert resolver.extract_doi("10.1016/j.cell.2018.06.048") == "10.1016/j.cell.2018.06.048"

    def test_doi_url(self, resolver: DOIResolver) -> None:
        assert resolver.extract_doi("https://doi.org/10.1234/abcd.5678") == "10.1234/abcd.5678"

    def test_doi_in_text(self, resolver: DOIResolver) -> None:
        result = resolver.extract_doi("See doi:10.1000/xyz123 for details")
        assert result == "10.1000/xyz123"

    def test_no_doi(self, resolver: DOIResolver) -> None:
        assert resolver.extract_doi("just some random text") is None
        assert resolver.extract_doi("") is None

    def test_doi_trailing_period(self, resolver: DOIResolver) -> None:
        result = resolver.extract_doi("10.1016/j.cell.2018.06.048.")
        assert result == "10.1016/j.cell.2018.06.048"

    def test_doi_with_special_chars(self, resolver: DOIResolver) -> None:
        assert resolver.extract_doi("10.1007/s00159-024-00001-2") == "10.1007/s00159-024-00001-2"


@pytest.mark.asyncio
class TestQueryUnpaywall:
    async def test_unpaywall_oa_success(self, respx_mock, resolver: DOIResolver) -> None:
        url = "https://api.unpaywall.org/v2/10.1234/test?email=test%40example.com"
        respx_mock.get(url).respond(
            200,
            json={
                "doi": "10.1234/test",
                "is_oa": True,
                "oa_status": "gold",
                "title": "Test Paper",
                "publisher": "Test Publisher",
                "z_authors": [
                    {"given": "Alice", "family": "Smith"},
                    {"given": "Bob", "family": "Jones"},
                ],
                "best_oa_location": {
                    "url_for_pdf": "https://example.com/paper.pdf",
                    "url": "https://example.com/paper",
                },
            },
        )
        data = await resolver.query_unpaywall("10.1234/test")
        assert data is not None
        assert data["is_oa"] is True
        assert data["oa_status"] == "gold"
        assert data["best_oa_location"]["url_for_pdf"] == "https://example.com/paper.pdf"

    async def test_unpaywall_404(self, respx_mock, resolver: DOIResolver) -> None:
        url = "https://api.unpaywall.org/v2/10.9999/notfound?email=test%40example.com"
        respx_mock.get(url).respond(404)
        data = await resolver.query_unpaywall("10.9999/notfound")
        assert data is None


@pytest.mark.asyncio
class TestQueryCrossref:
    async def test_crossref_success(self, respx_mock, resolver: DOIResolver) -> None:
        url = "https://api.crossref.org/works/10.1234/crtest"
        respx_mock.get(url).respond(
            200,
            json={
                "message": {
                    "title": ["Crossref Paper"],
                    "author": [{"given": "Carol", "family": "Davis"}],
                    "publisher": "Crossref Publishing",
                    "link": [{"content-type": "application/pdf", "url": "https://crossref.org/paper.pdf"}],
                }
            },
        )
        data = await resolver.query_crossref("10.1234/crtest")
        assert data is not None
        assert data["message"]["title"][0] == "Crossref Paper"

    async def test_crossref_404(self, respx_mock, resolver: DOIResolver) -> None:
        url = "https://api.crossref.org/works/10.9999/notfound"
        respx_mock.get(url).respond(404)
        data = await resolver.query_crossref("10.9999/notfound")
        assert data is None


@pytest.mark.asyncio
class TestResolve:
    async def test_resolve_via_unpaywall(self, respx_mock, resolver: DOIResolver) -> None:
        up_url = "https://api.unpaywall.org/v2/10.1234/resolve?email=test%40example.com"
        respx_mock.get(up_url).respond(
            200,
            json={
                "doi": "10.1234/resolve",
                "is_oa": True,
                "oa_status": "gold",
                "title": "Resolved Paper",
                "publisher": "Some Publisher",
                "z_authors": [{"given": "Alice", "family": "Smith"}],
                "best_oa_location": {"url_for_pdf": "https://example.com/paper.pdf"},
            },
        )
        result = await resolver.resolve("10.1234/resolve")
        assert result is not None
        assert result.doi == "10.1234/resolve"
        assert result.is_oa is True
        assert result.pdf_url == "https://example.com/paper.pdf"
        assert result.title == "Resolved Paper"
        assert result.authors == ["Alice Smith"]

    async def test_resolve_invalid_doi(self, resolver: DOIResolver) -> None:
        result = await resolver.resolve("not a doi")
        assert result is None

    async def test_resolve_no_oa(self, respx_mock, resolver: DOIResolver) -> None:
        up_url = "https://api.unpaywall.org/v2/10.9999/closed?email=test%40example.com"
        respx_mock.get(up_url).respond(
            200,
            json={
                "doi": "10.9999/closed",
                "is_oa": False,
                "oa_status": "closed",
                "title": "Closed Paper",
                "publisher": "Paywall Publisher",
                "z_authors": [],
            },
        )
        result = await resolver.resolve("10.9999/closed")
        assert result is not None
        assert result.is_oa is False
        assert result.pdf_url is None
