"""Bright Hand (Bright Data) unlocker helpers."""

from __future__ import annotations

import pytest

from arxiv_mcp.brighthand_fetch import brighthand_configured
from arxiv_mcp.config import Settings
from arxiv_mcp.runtime_settings import media_use_brighthand, write_overrides


def test_brighthand_configured_requires_token_and_zone():
    assert brighthand_configured(Settings()) is False
    assert brighthand_configured(Settings(brightdata_api_token="tok", brightdata_zone="web_unlocker1")) is True


def test_media_use_brighthand_requires_ignore_botblocks(tmp_path):
    settings = Settings(
        data_dir=tmp_path / "data",
        codehunt_media_ignore_botblocks=False,
        codehunt_media_use_brighthand=True,
    )
    assert media_use_brighthand(settings) is False
    write_overrides({"media_ignore_botblocks": True, "media_use_brighthand": True}, settings=settings)
    assert media_use_brighthand(settings) is True


@pytest.mark.asyncio
async def test_brighthand_fetch_missing_config():
    from arxiv_mcp.brighthand_fetch import brighthand_fetch_markdown

    out = await brighthand_fetch_markdown("https://example.com", settings=Settings())
    assert out.get("success") is False
    assert "brightdata" in str(out.get("error"))
