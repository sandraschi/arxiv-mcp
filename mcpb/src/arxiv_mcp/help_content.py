"""Structured help for arxiv-mcp MCP tool and REST /api/help."""

from __future__ import annotations

from pathlib import Path
from typing import Any

_TOPICS: dict[str, str] = {
    "overview": "overview",
    "codehunt": "CODEHUNT.md",
    "watch_authors": "CODEHUNT.md#watch-list-authors",
    "affiliations": "CODEHUNT.md#tiered-affiliations-universities--labs",
    "media_traction": "CODEHUNT.md#media-traction-1-week-after-arxiv",
    "botblocks": "BOTBLOCK_ANTIPATTERN.md",
    "ignore_botblocks": "BOTBLOCK_ANTIPATTERN.md",
    "publication_auth": "PUBLICATION_AUTH.md",
    "publications": "PUBLICATION_AUTH.md",
    "readly": "READLY_INTEGRATION.md",
    "fleet": "FLEET_INTEGRATION.md",
    "fleet_integration": "FLEET_INTEGRATION.md",
    "api_keys": "FLEET_INTEGRATION.md#api-keys-read-this-carefully",
    "pipeline_liveness": "CODEHUNT.md",
    "install": "INSTALL.md",
    "mcp": "TOOLS.md",
}


def _repo_docs() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "docs"
        if candidate.is_dir() and (candidate / "CODEHUNT.md").is_file():
            return candidate
    return here.parents[2] / "docs"


def _read_doc_file(name: str) -> str:
    path = _repo_docs() / name
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return f"(missing doc: {name})"


def _overview_markdown() -> str:
    return """# arxiv-mcp help

High-density arXiv research server (FastMCP 3.2). Use **topic** to load a section.

## Topics (call `arxiv_help(topic="...")`)

| topic | Content |
|-------|---------|
| `codehunt` | Open-weight repo tracking, scan/repoll, scheduler |
| `watch_authors` | Curated author watchlist (LeCun, Fei-Fei Li, …) |
| `affiliations` | Tier-A universities & labs (Tsinghua, Anthropic, DeepMind, …) |
| `media_traction` | HN + news + tech RSS (~7d); no publisher HTML scrape |
| `botblocks` | Ignore bot blocks — legal context & scaffolding antipattern |
| `publication_auth` | NYT/WSJ subscriber credentials, valid_till, cookie |
| `readly` | readly-mcp cross-connect, New Scientist, watch magazines |
| `fleet` / `fleet_integration` | aiwatcher ingest, vla-mcp, supervisor probes |
| `api_keys` | AIWATCHER_API_KEY chain (not Semantic Scholar) |
| `pipeline_liveness` | Stale digest + downstream health |
| `mcp` | Core tool manifest |
| `install` | Setup and ports |

## Code-hunt MCP tools

- `run_codehunt_scan_tool` — scan categories for repo links
- `repoll_codehunt_tool` — re-check promised URLs
- `codehunt_stats_tool` — SQLite summary
- `pipeline_liveness_tool` — fleet pipeline health
- `check_codehunt_media_tool` — HN/news traction pass
- `arxiv_help` — this help system

## Ports

- Backend / MCP HTTP: **10770**
- Webapp (Vite): **10771**

## REST help

- `GET /api/help` — topic list
- `GET /api/help/{topic}` — markdown body

## Quick start for agents

1. `arxiv_help(topic="api_keys")` if fleet push returns 401
2. `run_codehunt_scan_tool(days=3)` then `codehunt_stats_tool`
3. `pipeline_liveness_tool` before blaming "broken" ingest
"""


def get_help(topic: str | None = None) -> dict[str, Any]:
    """Return help markdown and metadata for MCP/REST."""
    topics = sorted({k for k in _TOPICS if not k.endswith("_integration") or k == "fleet_integration"})
    if not topic or topic.strip().lower() in ("list", "topics", "index"):
        return {
            "success": True,
            "server": "arxiv-mcp",
            "topics": topics,
            "markdown": _overview_markdown(),
            "message": "Call arxiv_help(topic='codehunt') for full section markdown.",
        }

    key = topic.strip().lower().replace("-", "_")
    if key == "watch_authors":
        body = _read_doc_file("CODEHUNT.md")
        # Anchor section is in the doc; include full CODEHUNT for searchability.
        return {
            "success": True,
            "topic": key,
            "markdown": body,
            "message": "Watch-list authors: config/codehunt_watch_authors.json",
        }

    mapped = _TOPICS.get(key)
    if not mapped:
        return {
            "success": False,
            "error": f"Unknown topic: {topic}",
            "topics": topics,
            "message": f"Valid topics: {', '.join(topics)}",
        }

    if mapped == "overview":
        md = _overview_markdown()
    else:
        file_name = mapped.split("#")[0]
        md = _read_doc_file(file_name)

    return {
        "success": True,
        "topic": key,
        "doc_file": mapped,
        "markdown": md,
        "message": f"Loaded {mapped}",
    }
