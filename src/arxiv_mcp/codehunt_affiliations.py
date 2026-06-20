"""Tiered university / lab affiliation signals for code-hunt."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from arxiv_mcp.config import Settings, load_settings

AffKind = Literal["university", "company"]
AffTier = Literal["a", "b"]

_BUILTIN: dict[str, list[str]] = {
    "tier_a_universities": ["tsinghua", "university of tokyo", "mit", "stanford"],
    "tier_a_companies": ["anthropic", "deepmind", "openai", "google research"],
    "tier_b_universities": [],
}


def _repo_config_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "config" / "codehunt_affiliations.json"
        if candidate.is_file():
            return candidate
    return here.parents[2] / "config" / "codehunt_affiliations.json"


def _load_json_affiliations(path: Path) -> dict[str, list[str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, list[str]] = {}
    for key in ("tier_a_universities", "tier_a_companies", "tier_b_universities"):
        raw = data.get(key)
        if isinstance(raw, list):
            out[key] = [str(x).strip() for x in raw if str(x).strip()]
    return out


@lru_cache(maxsize=8)
def _cached_affiliation_tables(settings_file: str, data_file: str, repo_file: str) -> tuple[
    tuple[tuple[str, AffTier, AffKind], ...],
    tuple[tuple[str, AffTier, AffKind], ...],
]:
    tables: dict[str, list[str]] = {}
    for path_str in (repo_file, data_file, settings_file):
        if not path_str:
            continue
        merged = _load_json_affiliations(Path(path_str))
        for key, values in merged.items():
            tables[key] = values
    if not tables:
        tables = dict(_BUILTIN)

    def build(key: str, tier: AffTier, kind: AffKind) -> list[tuple[str, AffTier, AffKind]]:
        rows: list[tuple[str, AffTier, AffKind]] = []
        for term in tables.get(key, []):
            low = term.lower().strip()
            if low:
                rows.append((low, tier, kind))
        rows.sort(key=lambda r: len(r[0]), reverse=True)
        return rows

    tier_a = build("tier_a_universities", "a", "university") + build(
        "tier_a_companies", "a", "company"
    )
    tier_b = build("tier_b_universities", "b", "university")
    return tuple(tier_a), tuple(tier_b)


def load_affiliation_tables(settings: Settings | None = None) -> tuple[
    tuple[tuple[str, AffTier, AffKind], ...],
    tuple[tuple[str, AffTier, AffKind], ...],
]:
    settings = settings or load_settings()
    data_path = settings.resolved_data_dir() / "codehunt" / "affiliations.json"
    repo_path = _repo_config_path()
    file_setting = (settings.codehunt_affiliations_file or "").strip()
    return _cached_affiliation_tables(
        file_setting,
        str(data_path) if data_path.is_file() else "",
        str(repo_path) if repo_path.is_file() else "",
    )


_SHORT_BOUNDARY_TERMS = frozenset(
    {"mit", "cmu", "ucl", "nus", "anu", "uw", "snu", "tum", "msr", "fair", "iit", "mila"}
)


def _term_in_text(term: str, low: str) -> bool:
    # Avoid false positives like "commit" matching "mit".
    if len(term) <= 4 or term in _SHORT_BOUNDARY_TERMS:
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", low))
    return term in low


def _match_terms(text: str, table: tuple[tuple[str, AffTier, AffKind], ...]) -> list[dict[str, str]]:
    low = text.lower()
    hits: list[dict[str, str]] = []
    seen: set[str] = set()
    for term, tier, kind in table:
        if not _term_in_text(term, low):
            continue
        if term in seen:
            continue
        seen.add(term)
        hits.append({"term": term, "tier": tier, "kind": kind})
    return hits


def classify_affiliations(
    text: str,
    *,
    settings: Settings | None = None,
    min_tier: AffTier = "a",
) -> list[dict[str, str]]:
    """Return affiliation hits in abstract/title/fulltext blob (tier a/b, university/company)."""
    tier_a, tier_b = load_affiliation_tables(settings)
    hits = _match_terms(text, tier_a)
    if min_tier == "b":
        hits.extend(_match_terms(text, tier_b))
    return hits


def affiliation_signal(hits: list[dict[str, str]], *, min_tier: AffTier = "a") -> bool:
    if not hits:
        return False
    if min_tier == "a":
        return any(h.get("tier") == "a" for h in hits)
    return True


def best_affiliation_tier(hits: list[dict[str, str]]) -> AffTier | None:
    if not hits:
        return None
    if any(h.get("tier") == "a" for h in hits):
        return "a"
    if any(h.get("tier") == "b" for h in hits):
        return "b"
    return None


def affiliation_summary(hits: list[dict[str, str]], limit: int = 6) -> str:
    if not hits:
        return "none"
    parts = []
    for h in hits[:limit]:
        parts.append(f"{h['term']} ({h['tier']}/{h['kind']})")
    return ", ".join(parts)


def clear_affiliation_cache() -> None:
    _cached_affiliation_tables.cache_clear()
