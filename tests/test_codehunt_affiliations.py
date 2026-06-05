"""Affiliation tier and media traction helpers."""

from __future__ import annotations

import pytest

from arxiv_mcp.codehunt_affiliations import (
    affiliation_signal,
    classify_affiliations,
    clear_affiliation_cache,
)
from arxiv_mcp.codehunt_media import _parse_google_news_rss, probe_media_traction


def test_tier_a_tsinghua_not_lyons_agricultural():
    clear_affiliation_cache()
    hits = classify_affiliations(
        "We present results from Tsinghua University on efficient transformers.",
        min_tier="a",
    )
    assert affiliation_signal(hits, min_tier="a")
    assert any("tsinghua" in h["term"] for h in hits)

    rural = classify_affiliations(
        "A study from Lyons Agricultural College on crop yield forecasting.",
        min_tier="a",
    )
    assert not affiliation_signal(rural, min_tier="a")


def test_company_anthropic_deepmind():
    clear_affiliation_cache()
    blob = "Authors from Anthropic and Google DeepMind propose a new alignment method."
    hits = classify_affiliations(blob, min_tier="a")
    terms = {h["term"] for h in hits}
    assert "anthropic" in terms or "google deepmind" in terms or "deepmind" in terms


def test_mit_word_boundary():
    clear_affiliation_cache()
    assert not affiliation_signal(classify_affiliations("We commit to open science.", min_tier="a"))
    assert affiliation_signal(
        classify_affiliations("Massachusetts Institute of Technology (MIT) authors.", min_tier="a")
    )


def test_parse_google_news_rss():
    xml = (
        "<rss><channel><item>"
        "<title>New arXiv paper on AI safety - TechCrunch</title>"
        "<link>https://arxiv.org/abs/2401.12345</link>"
        "<source>TechCrunch</source>"
        "</item></channel></rss>"
    )
    hits = _parse_google_news_rss(
        xml,
        paper_id="2401.12345",
        title="AI safety foundations",
    )
    assert len(hits) >= 1
    assert hits[0]["source"] == "google_news"


@pytest.mark.asyncio
async def test_media_probe_skips_young_paper():
    from arxiv_mcp.config import Settings

    settings = Settings(codehunt_media_min_age_days=7, codehunt_media_max_age_days=45)
    out = await probe_media_traction(
        paper_id="2401.12345",
        title="Test",
        published="2099-01-01T00:00:00Z",
        settings=settings,
    )
    assert out.get("skipped") is True
