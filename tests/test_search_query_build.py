"""Regression tests: free-text arXiv queries must AND their terms and sort by relevance.

Bug 2026-10-11: bare multi-word queries ("sitagliptin first clinical trial") were sent
to the arXiv API as-is and sorted newest-first, returning brand-new papers that
matched any single common word.
"""

from __future__ import annotations

import arxiv
import pytest
from httpx import ASGITransport, AsyncClient

from arxiv_mcp.services import papers
from arxiv_mcp.services.papers import build_query


def test_single_word():
    assert build_query("sitagliptin", None) == "all:sitagliptin"


def test_multi_word_is_anded():
    assert build_query("sitagliptin first clinical trial", None) == (
        "all:sitagliptin AND all:first AND all:clinical AND all:trial"
    )


def test_quoted_phrase_kept():
    assert build_query('"clinical trial" sitagliptin', None) == 'all:"clinical trial" AND all:sitagliptin'


@pytest.mark.parametrize(
    "q",
    [
        "ti:transformer",
        "au:hinton AND ti:capsule",
        "all:llm ANDNOT cat:cs.CV",
        "diffusion OR flow",
        "(ti:a OR ti:b)",
        "cat:cs.RO",
    ],
)
def test_advanced_syntax_untouched(q: str):
    assert build_query(q, None) == q


def test_empty_and_categories():
    assert build_query("  ", None) == "all:*"
    assert build_query("robot world model", ["cs.RO", "cs.AI"]) == (
        "(all:robot AND all:world AND all:model) AND (cat:cs.RO OR cat:cs.AI)"
    )


class _FakeClient:
    def __init__(self) -> None:
        self.searches: list[arxiv.Search] = []

    def results(self, search: arxiv.Search):
        self.searches.append(search)
        return iter(())


@pytest.fixture()
def fake_client(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(papers, "_client", lambda settings: fake)
    return fake


@pytest.fixture()
def client():
    from arxiv_mcp.app import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


@pytest.mark.asyncio
async def test_preprints_search_defaults_to_relevance(client: AsyncClient, fake_client: _FakeClient):
    async with client as c:
        resp = await c.get("/api/preprints/search", params={"q": "first clinical", "servers": "arxiv"})
    assert resp.status_code == 200
    (search,) = fake_client.searches
    assert search.sort_by == arxiv.SortCriterion.Relevance
    assert search.query == "all:first AND all:clinical"


@pytest.mark.asyncio
async def test_preprints_search_newest_first_on_request(client: AsyncClient, fake_client: _FakeClient):
    async with client as c:
        resp = await c.get(
            "/api/preprints/search",
            params={"q": "first clinical", "servers": "arxiv", "sort_by": "submitted"},
        )
    assert resp.status_code == 200
    (search,) = fake_client.searches
    assert search.sort_by == arxiv.SortCriterion.SubmittedDate
