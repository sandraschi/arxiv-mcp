"""Runtime settings overrides for UI toggles."""

from __future__ import annotations

from arxiv_mcp.config import Settings
from arxiv_mcp.runtime_settings import (
    media_ignore_botblocks,
    media_settings_payload,
    write_overrides,
)


def test_media_ignore_botblocks_env_default(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", codehunt_media_ignore_botblocks=False)
    assert media_ignore_botblocks(settings) is False


def test_media_ignore_botblocks_runtime_override(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", codehunt_media_ignore_botblocks=False)
    write_overrides({"media_ignore_botblocks": True}, settings=settings)
    assert media_ignore_botblocks(settings) is True
    write_overrides({"media_use_brighthand": True}, settings=settings)
    payload = media_settings_payload(settings)
    assert payload["media_ignore_botblocks"] is True
    assert payload["media_use_brighthand"] is True
    assert payload["source"] == "runtime_override"


def test_help_topic_botblocks():
    from arxiv_mcp.help_content import get_help

    out = get_help("botblocks")
    assert out.get("success") is True
    assert "antipattern" in (out.get("markdown") or "").lower()
