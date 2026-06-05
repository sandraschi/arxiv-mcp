"""Readly cross-connect client."""

from __future__ import annotations

import pytest

from arxiv_mcp.config import Settings
from arxiv_mcp.readly_client import (
    assert_readly_usable,
    fetch_readly_depot_coverage,
    load_readly_watch_magazines,
    readly_coverage_for_depot,
    readly_enabled,
    readly_hits_for_media,
    readly_subscription_status,
)


def test_load_readly_watch_includes_new_scientist():
    mags = load_readly_watch_magazines()
    names = {m["name"] for m in mags}
    assert "New Scientist" in names


def test_readly_disabled_by_default():
    settings = Settings(readly_enabled=False)
    assert readly_enabled(settings) is False


def test_readly_expired_loud_failure(monkeypatch):
    settings = Settings(
        readly_enabled=True,
        readly_mcp_url="http://127.0.0.1:10863",
        readly_valid_till="2020-01-01",
    )
    status = readly_subscription_status(settings)
    assert status["status"] == "expired"
    block = assert_readly_usable(settings)
    assert block is not None
    assert block["subscription_error"] == "readly_subscription_expired"
    assert block["silent_failure"] is False


def test_readly_coverage_for_depot():
    coverage = readly_coverage_for_depot(
        {
            "success": True,
            "hits": [
                {
                    "magazine": "Nature",
                    "title": "Quantum chips",
                    "url": "https://readly.example/n",
                    "match_score": 4,
                    "issue_title": "Feb 2026",
                }
            ],
        }
    )
    assert len(coverage) == 1
    assert coverage[0]["source"] == "readly_mcp"
    assert coverage[0]["magazine"] == "Nature"


@pytest.mark.asyncio
async def test_fetch_readly_depot_coverage_skipped_when_disabled():
    out = await fetch_readly_depot_coverage(
        "Robot foundation models",
        settings=Settings(readly_enabled=False),
    )
    assert out == []


@pytest.mark.asyncio
async def test_fetch_readly_depot_coverage_respects_ingest_flag(monkeypatch):
    import respx
    from httpx import Response

    settings = Settings(
        readly_enabled=True,
        readly_mcp_url="http://127.0.0.1:10863",
        readly_valid_till="2099-01-01",
        readly_ingest_on_depot=False,
    )
    out = await fetch_readly_depot_coverage("Test paper", settings=settings)
    assert out == []

    settings_on = settings.model_copy(update={"readly_ingest_on_depot": True})
    with respx.mock:
        respx.post("http://127.0.0.1:10863/api/content/match").mock(
            return_value=Response(
                200,
                json={
                    "success": True,
                    "hits": [{"magazine": "Wired", "title": "AI", "url": "https://x", "match_score": 2}],
                },
            )
        )
        hits = await fetch_readly_depot_coverage("Test paper", settings=settings_on)
    assert len(hits) == 1
    assert hits[0]["magazine"] == "Wired"


def test_readly_hits_normalization():
    hits = readly_hits_for_media(
        "robotics",
        {
            "success": True,
            "hits": [
                {
                    "magazine": "New Scientist",
                    "title": "Robot foundation models",
                    "url": "https://readly.example/a",
                    "match_score": 3,
                }
            ],
        },
    )
    assert len(hits) == 1
    assert hits[0]["source"] == "readly"
    assert hits[0]["outlet"] == "New Scientist"


@pytest.mark.asyncio
async def test_probe_readly_skipped_when_disabled():
    from arxiv_mcp.codehunt_readly import probe_readly_for_paper

    out = await probe_readly_for_paper(
        paper_id="2401.12345",
        title="Test paper",
        settings=Settings(readly_enabled=False),
    )
    assert out.get("skipped") is True
