"""Tests for tech RSS feed cache (bot-safe media traction)."""

from __future__ import annotations

import json
import time

import pytest

from arxiv_mcp.codehunt_media_feeds import (
    _parse_rss_items,
    load_media_feeds,
    search_feed_cache,
)
from arxiv_mcp.config import Settings


SAMPLE_RSS = """<?xml version="1.0"?>
<rss><channel>
<item>
  <title>New arXiv paper 2401.99999 changes robotics</title>
  <link>https://arstechnica.com/ai/2024/01/test-story/</link>
  <description>Researchers cite arxiv.org/abs/2401.99999</description>
  <pubDate>Mon, 15 Jan 2024 12:00:00 GMT</pubDate>
</item>
<item>
  <title>Unrelated gadget review</title>
  <link>https://arstechnica.com/gadgets/phone/</link>
</item>
</channel></rss>"""


def test_parse_rss_items_extracts_arxiv_id():
    entries = _parse_rss_items(SAMPLE_RSS, feed_id="ars", outlet="Ars Technica")
    assert len(entries) == 2
    assert "2401.99999" in entries[0]["arxiv_ids"]


def test_load_media_feeds_from_repo_config():
    feeds = load_media_feeds()
    ids = {f["id"] for f in feeds}
    assert "ars-technica" in ids
    assert any("feeds.arstechnica.com" in f["url"] for f in feeds)


def test_search_feed_cache_matches_arxiv_id(tmp_path):
    settings = Settings(data_dir=tmp_path / "data")
    cache_dir = settings.resolved_data_dir() / "codehunt"
    cache_dir.mkdir(parents=True)
    cache_file = cache_dir / "media_feed_cache.json"
    cache_file.write_text(
        json.dumps(
            {
                "fetched_at": time.time(),
                "entries": [
                    {
                        "feed_id": "ars",
                        "outlet": "Ars Technica",
                        "title": "Paper 2401.99999 on robots",
                        "url": "https://arstechnica.com/ai/story/",
                        "blob": "paper 2401.99999 on robots https://arstechnica.com/ai/story/",
                        "arxiv_ids": ["2401.99999"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    hits = search_feed_cache(
        paper_id="2401.99999",
        title="Robot foundation model",
        settings=settings,
    )
    assert len(hits) == 1
    assert hits[0]["source"] == "tech_rss"
    assert hits[0]["snippet_only"] is True
    assert hits[0]["fetch_policy"] == "rss_metadata_only"
    assert hits[0]["publisher_blocks_scrape"] is True
