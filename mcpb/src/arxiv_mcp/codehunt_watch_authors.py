"""Curated author watchlist for code-hunt priority (high-signal researchers)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from arxiv_mcp.config import Settings, load_settings

_BUILTIN_DEFAULTS: tuple[str, ...] = (
    "Yann LeCun",
    "Fei-Fei Li",
    "Geoffrey Hinton",
    "Yoshua Bengio",
    "Andrew Ng",
    "Demis Hassabis",
    "Andrej Karpathy",
    "Sergey Levine",
    "Pieter Abbeel",
    "Chelsea Finn",
)


def _normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower().strip())


def _repo_config_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "config" / "codehunt_watch_authors.json"
        if candidate.is_file():
            return candidate
    return here.parents[2] / "config" / "codehunt_watch_authors.json"


def _parse_name_list(raw: str) -> list[str]:
    names: list[str] = []
    for part in raw.split(","):
        name = part.strip()
        if name and name not in names:
            names.append(name)
    return names


def _load_json_names(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    names: list[str] = []
    for item in data:
        if isinstance(item, str):
            name = item.strip()
            if name and name not in names:
                names.append(name)
    return names


@lru_cache(maxsize=8)
def _cached_watch_names(
    settings_file: str | None,
    settings_extra: str,
    data_file: str,
    repo_file: str,
) -> tuple[str, ...]:
    names: list[str] = []
    if settings_file:
        names.extend(_load_json_names(Path(settings_file)))
    if not names and data_file:
        names.extend(_load_json_names(Path(data_file)))
    if not names and repo_file:
        names.extend(_load_json_names(Path(repo_file)))
    if not names:
        names.extend(_BUILTIN_DEFAULTS)
    names.extend(_parse_name_list(settings_extra))
    # Dedupe preserving order (case-insensitive).
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        key = _normalize_name(name)
        if key in seen:
            continue
        seen.add(key)
        out.append(name)
    return tuple(out)


def load_watch_authors(settings: Settings | None = None) -> tuple[str, ...]:
    """Resolve watchlist: env file > data dir JSON > repo config > builtins + extras."""
    settings = settings or load_settings()
    data_path = settings.resolved_data_dir() / "codehunt" / "watch_authors.json"
    repo_path = _repo_config_path()
    file_setting = (settings.codehunt_watch_authors_file or "").strip() or None
    extra = settings.codehunt_watch_authors_extra or ""
    return _cached_watch_names(
        file_setting,
        extra,
        str(data_path) if data_path.is_file() else "",
        str(repo_path) if repo_path.is_file() else "",
    )


def classify_watch_authors(
    authors: list[str] | None,
    *,
    settings: Settings | None = None,
) -> list[str]:
    """Return matched watchlist names for paper author strings."""
    if not authors:
        return []
    watch = load_watch_authors(settings)
    hits: list[str] = []
    normalized_authors = [_normalize_name(a) for a in authors if a and a.strip()]
    for watch_name in watch:
        wn = _normalize_name(watch_name)
        if not wn:
            continue
        for author in normalized_authors:
            if wn in author or author in wn:
                if watch_name not in hits:
                    hits.append(watch_name)
                break
    return hits


def clear_watch_author_cache() -> None:
    _cached_watch_names.cache_clear()
