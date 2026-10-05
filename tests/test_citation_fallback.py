"""Citation graph fallback: S2 429 -> OpenAlex, transparent for agents."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from arxiv_mcp.config import Settings
from arxiv_mcp.services import papers


def _settings() -> Settings:
    return Settings(
        citation_fallback_enabled=True,
        openalex_base_url="https://api.openalex.org",
        openalex_mailto="",
        arxiv_max_retries=0,
    )


def _payload(*, ok: bool, status: int | None, text: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        ok=ok,
        status_code=status,
        text=text,
        content=None,
        headers={},
        content_type="application/json",
        error={"success": False, "error": f"HTTP {status}"} if not ok else None,
        from_cache=False,
    )


def _oa_work() -> dict[str, Any]:
    return {
        "id": "https://openalex.org/W123",
        "title": "Self-Harness",
        "display_name": "Self-Harness",
        "publication_year": 2026,
        "doi": "https://doi.org/10.1234/x",
        "primary_location": {"landing_page_url": "https://arxiv.org/abs/2606.09498", "pdf_url": None},
        "best_oa_location": {"landing_page_url": None},
        "locations": [],
        "ids": {"arxiv": "2606.09498"},
        "cited_by_count": 7,
        "referenced_works": ["https://openalex.org/W9"],
    }


@pytest.mark.asyncio
async def test_s2_success_has_source_no_fallback() -> None:
    s2 = {"title": "Self-Harness", "year": 2026, "citations": [], "references": []}

    async def fake_get_text(url: str, **kwargs: Any) -> SimpleNamespace:
        assert "api.semanticscholar.org" in url
        return _payload(ok=True, status=200, text=json.dumps(s2))

    with patch("arxiv_mcp.services.papers.get_text", fake_get_text):
        out = await papers.find_connected_papers("2606.09498", limit=5, settings=_settings())
    assert out["found"] is True
    assert out["source"] == "semantic_scholar"
    assert out["fallback_used"] is False


@pytest.mark.asyncio
async def test_s2_429_falls_back_to_openalex_transparently() -> None:
    calls: list[str] = []

    async def fake_get_text(url: str, **kwargs: Any) -> SimpleNamespace:
        calls.append(url)
        if "api.semanticscholar.org" in url:
            return _payload(ok=False, status=429)
        if "/works/https://arxiv.org/abs/" in url:
            return _payload(ok=True, status=200, text=json.dumps(_oa_work()))
        if ("/works?" in url and "cites%3A" in url) or ("cites:" in url):
            return _payload(ok=True, status=200, text=json.dumps({"results": []}))
        if ("/works?" in url and "openalex%3A" in url) or ("openalex:" in url):
            return _payload(ok=True, status=200, text=json.dumps({"results": []}))
        return _payload(ok=False, status=404)

    with patch("arxiv_mcp.services.papers.get_text", fake_get_text):
        out = await papers.find_connected_papers("2606.09498", limit=3, settings=_settings())
    assert out["found"] is True
    assert out["source"] == "openalex"
    assert out["fallback_used"] is True
    assert out["semantic_scholar_status"] == 429
    assert "notice" in out
    assert any("api.semanticscholar.org" in u for u in calls)
    assert any("api.openalex.org" in u for u in calls)


@pytest.mark.asyncio
async def test_both_providers_down_returns_combined_envelope() -> None:
    async def fake_get_text(url: str, **kwargs: Any) -> SimpleNamespace:
        return _payload(ok=False, status=429 if "semanticscholar" in url else 500)

    with patch("arxiv_mcp.services.papers.get_text", fake_get_text):
        out = await papers.find_connected_papers("2606.09498", limit=3, settings=_settings())
    assert out["found"] is False
    assert out["success"] is False
    assert out["error_type"] == "CitationGraphUnavailable"
    assert out["semantic_scholar_status"] == 429
    assert out.get("recovery_options")


@pytest.mark.asyncio
async def test_fallback_can_be_disabled() -> None:
    async def fake_get_text(url: str, **kwargs: Any) -> SimpleNamespace:
        raise AssertionError("OpenAlex must not be called when fallback is disabled")

    s = _settings()
    s.citation_fallback_enabled = False
    s2 = {"title": "T", "year": 2026, "citations": [], "references": []}

    async def fake_s2(url: str, **kwargs: Any) -> SimpleNamespace:
        return _payload(ok=True, status=200, text=json.dumps(s2))

    with patch("arxiv_mcp.services.papers.get_text", fake_s2):
        out = await papers.find_connected_papers("2606.09498", limit=2, settings=s)
    assert out["source"] == "semantic_scholar"
    _ = fake_get_text  # silence unused warning for the guard above


def test_extract_arxiv_id_from_openalex_urls() -> None:
    assert papers._extract_arxiv_id("https://arxiv.org/abs/2606.09498v3") == "2606.09498"
    assert papers._extract_arxiv_id("https://arxiv.org/pdf/2603.03329") == "2603.03329"
    assert papers._extract_arxiv_id(None, "", "not-an-id") is None


def test_openalex_work_to_item_prefers_arxiv() -> None:
    item = papers._openalex_work_to_item(_oa_work())
    assert item["arxiv"] == "2606.09498"
    assert item["title"] == "Self-Harness"
    assert item["year"] == 2026
