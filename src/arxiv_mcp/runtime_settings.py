"""UI-persisted settings overrides (merged over env-based Settings)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from arxiv_mcp.config import Settings, load_settings

_FILENAME = "runtime_settings.json"


def _path(settings: Settings) -> Path:
    return settings.resolved_data_dir() / _FILENAME


def read_overrides(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or load_settings()
    path = _path(settings)
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def write_overrides(updates: dict[str, Any], settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or load_settings()
    current = read_overrides(settings)
    current.update(updates)
    current["updated_at"] = time.time()
    path = _path(settings)
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current


def _override_bool(overrides: dict[str, Any], key: str, env_value: bool) -> bool:
    if key in overrides:
        return bool(overrides[key])
    return bool(env_value)


def media_ignore_botblocks(settings: Settings | None = None) -> bool:
    """True when UI or env enables enrichment for bot-blocked publisher URLs."""
    settings = settings or load_settings()
    overrides = read_overrides(settings)
    return _override_bool(overrides, "media_ignore_botblocks", settings.codehunt_media_ignore_botblocks)


def media_use_brighthand(settings: Settings | None = None) -> bool:
    """True when Bright Hand (Bright Data) may run after Jina fails."""
    settings = settings or load_settings()
    if not media_ignore_botblocks(settings):
        return False
    overrides = read_overrides(settings)
    return _override_bool(overrides, "media_use_brighthand", settings.codehunt_media_use_brighthand)


def media_settings_payload(settings: Settings | None = None) -> dict[str, Any]:
    from arxiv_mcp.brighthand_fetch import brighthand_configured

    settings = settings or load_settings()
    overrides = read_overrides(settings)
    ignore = media_ignore_botblocks(settings)
    brighthand = media_use_brighthand(settings)
    bd_ready = brighthand_configured(settings)
    strategy_enabled = "rss_metadata_plus_optional_jina_reader"
    if ignore and brighthand and bd_ready:
        strategy_enabled = "rss_metadata_jina_then_brighthand_unlocker"
    elif ignore:
        strategy_enabled = "rss_metadata_plus_optional_jina_reader"
    return {
        "media_ignore_botblocks": ignore,
        "media_use_brighthand": brighthand,
        "brighthand_configured": bd_ready,
        "brighthand_zone": settings.brightdata_zone,
        "source": (
            "runtime_override"
            if "media_ignore_botblocks" in overrides or "media_use_brighthand" in overrides
            else "env_default"
        ),
        "env_default_ignore": bool(settings.codehunt_media_ignore_botblocks),
        "env_default_brighthand": bool(settings.codehunt_media_use_brighthand),
        "updated_at": overrides.get("updated_at"),
        "legal_doc": "/api/help/botblocks",
        "strategy_default": "aggregators_and_rss_metadata_only",
        "strategy_when_enabled": strategy_enabled,
    }
