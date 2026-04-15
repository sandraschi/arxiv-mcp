"""FastAPI: REST dashboard API + mounted FastMCP HTTP (streamable)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from arxiv_mcp.anthropic_blog import (
    fetch_anthropic_post as _fetch_anthropic_post,
    list_anthropic_posts as _list_anthropic_posts,
    KNOWN_POSTS,
)
from arxiv_mcp.lab_blog import (
    fetch_lab_post as _fetch_lab_post,
    list_lab_posts as _list_lab_posts,
    SOURCES as LAB_SOURCES,
)
from arxiv_mcp.arxiv_html import list_categories_payload
from arxiv_mcp.config import load_settings
from arxiv_mcp.depot_service import ingest_paper_html
from arxiv_mcp.server import mcp
from arxiv_mcp.services import corpus, papers
from arxiv_mcp.tools_manifest import MCP_TOOLS

mcp_http = mcp.http_app(path="/mcp")
router = APIRouter(prefix="/api")

_FLEET_PATH = Path(__file__).resolve().parent / "data" / "fleet_default.json"


class FavoriteIn(BaseModel):
    arxiv_id: str = Field(..., min_length=4)
    title: str | None = None
    note: str | None = None


class IngestIn(BaseModel):
    paper_id: str = Field(..., min_length=4)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "arxiv-mcp"}


@router.get("/stats")
async def api_stats() -> dict[str, Any]:
    return corpus.depot_stats()


@router.get("/categories")
async def api_categories() -> dict[str, Any]:
    """Static arXiv subject codes (same catalog as MCP `listCategories`)."""
    return {"categories": list_categories_payload()}


@router.get("/search")
async def api_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("submitted"),
    categories: str | None = Query(None, description="Comma-separated arXiv categories"),
) -> dict[str, Any]:
    cats = [c.strip() for c in categories.split(",") if c.strip()] if categories else None
    rows = await papers.search_papers(q, categories=cats, limit=limit, sort_by=sort_by)
    return {"papers": [papers.paper_summary_to_dict(p) for p in rows]}


@router.get("/category/latest")
async def api_category_latest(
    category: str = Query(..., min_length=2),
    limit: int = Query(25, ge=1, le=100),
    hours: int = Query(24, ge=1, le=168),
) -> dict[str, Any]:
    rows = await papers.list_category_latest(category, limit=limit, hours=hours)
    return {"papers": [papers.paper_summary_to_dict(p) for p in rows]}


@router.get("/paper")
async def api_paper(paper_id: str = Query(..., min_length=5)) -> dict[str, Any]:
    p = await papers.get_paper_details(paper_id)
    return {"paper": papers.paper_summary_to_dict(p)}


@router.get("/corpus")
async def api_corpus(limit: int = Query(50, ge=1, le=500)) -> dict[str, Any]:
    rows = corpus.list_ingested(limit=limit)
    return {"ingested": rows}


@router.get("/corpus/item")
async def api_corpus_item(arxiv_id: str = Query(..., min_length=4)) -> dict[str, Any]:
    row = corpus.get_paper_markdown(arxiv_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not in depot")
    return row


@router.get("/depot/search")
async def api_depot_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    max_age_days: int | None = Query(
        None,
        ge=1,
        le=3650,
        description=(
            "Exclude papers published more than N days ago. "
            "Recommended for AI/ML topics: 180 (six months). "
            "No filtering if omitted."
        ),
    ),
) -> dict[str, Any]:
    hits = corpus.search_depot_fts(q, limit=limit, max_age_days=max_age_days)
    return {
        "query": q,
        "max_age_days": max_age_days,
        "hits": hits,
        "engine": "sqlite_fts5",
    }


@router.post("/depot/ingest")
async def api_depot_ingest(body: IngestIn) -> dict[str, Any]:
    result = await ingest_paper_html(body.paper_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "ingest failed"))
    return result


@router.get("/favorites")
async def api_favorites_list(limit: int = Query(200, ge=1, le=500)) -> dict[str, Any]:
    return {"favorites": corpus.list_favorites(limit=limit)}


@router.post("/favorites")
async def api_favorites_add(body: FavoriteIn) -> dict[str, Any]:
    corpus.add_favorite(body.arxiv_id, title=body.title, note=body.note)
    return {"ok": True, "arxiv_id": body.arxiv_id}


@router.delete("/favorites/{arxiv_id:path}")
async def api_favorites_remove(arxiv_id: str) -> dict[str, Any]:
    ok = corpus.remove_favorite(arxiv_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"ok": True}


@router.get("/tools")
async def api_tools() -> dict[str, Any]:
    return {"tools": MCP_TOOLS, "mcp_http_path": "/mcp"}


class AnthropicFetchIn(BaseModel):
    slug_or_url: str = Field(..., min_length=3)
    ingest: bool = Field(False, description="If true, also ingest into local corpus after fetch")


class LabFetchIn(BaseModel):
    slug_or_url: str = Field(..., min_length=3)
    ingest: bool = Field(False)


@router.get("/lab/sources")
async def api_lab_sources() -> dict[str, Any]:
    """List supported lab blog sources."""
    return {
        "sources": [
            {"id": k, "label": v["label"], "js_heavy": v["js_heavy"],
             "sections": list(v["sections"].keys()),
             "known_keys": list(v["known_posts"].keys())}
            for k, v in LAB_SOURCES.items()
        ]
    }


@router.get("/lab/posts")
async def api_lab_posts(
    source: str = Query("google-research"),
    limit: int = Query(20, ge=1, le=50),
) -> dict[str, Any]:
    """List posts from any supported AI lab blog."""
    return await _list_lab_posts(source=source, limit=limit)


@router.post("/lab/fetch")
async def api_lab_fetch(body: LabFetchIn) -> dict[str, Any]:
    """Fetch a post from any supported AI lab blog, optionally ingest to corpus."""
    result = await _fetch_lab_post(body.slug_or_url)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "fetch failed"))
    if body.ingest and result.get("markdown"):
        try:
            settings = load_settings()
            rec = corpus.ingest_markdown(
                result["url"], result["title"], result["markdown"],
                source="external",
                meta={"published": result.get("published", ""),
                      "source_type": f"lab_blog_{result.get('source', 'unknown')}"},
                settings=settings,
            )
            result["ingested"] = True
            result["corpus_record"] = rec
        except Exception as e:
            result["ingested"] = False
            result["ingest_error"] = str(e)
    else:
        result["ingested"] = False
    return result


@router.get("/anthropic/posts")
async def api_anthropic_posts(
    section: str = Query("research", pattern="^(research|news)$"),
    limit: int = Query(20, ge=1, le=50),
) -> dict[str, Any]:
    """List posts from anthropic.com/research or /news."""
    result = await _list_anthropic_posts(section=section, limit=limit)
    result["known_keys"] = list(KNOWN_POSTS.keys())
    return result


@router.post("/anthropic/fetch")
async def api_anthropic_fetch(body: AnthropicFetchIn) -> dict[str, Any]:
    """Fetch an Anthropic post and optionally ingest it into the local corpus."""
    result = await _fetch_anthropic_post(body.slug_or_url)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "fetch failed"))
    if body.ingest and result.get("markdown"):
        try:
            settings = load_settings()
            rec = corpus.ingest_markdown(
                result["url"],
                result["title"],
                result["markdown"],
                source="external",
                meta={"published": result.get("published", ""), "source_type": "anthropic_blog"},
                settings=settings,
            )
            result["ingested"] = True
            result["corpus_record"] = rec
        except Exception as e:
            result["ingested"] = False
            result["ingest_error"] = str(e)
    else:
        result["ingested"] = False
    return result


@router.get("/prompts")
async def api_prompts() -> dict[str, Any]:
    """Return the MCP prompt manifest for display in the webapp."""
    from arxiv_mcp.tools_manifest import MCP_PROMPTS  # lazy import — may not exist yet
    return {"prompts": MCP_PROMPTS}


@router.get("/fleet")
async def api_fleet() -> dict[str, Any]:
    if _FLEET_PATH.is_file():
        hubs = json.loads(_FLEET_PATH.read_text(encoding="utf-8"))
    else:
        hubs = []
    return {"hubs": hubs}


def build_app() -> FastAPI:
    settings = load_settings()
    app = FastAPI(
        title="arxiv-mcp",
        version="0.4.0",
        lifespan=mcp_http.lifespan,
    )
    app.include_router(router)
    app.mount("/mcp", mcp_http)

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {
            "service": "arxiv-mcp",
            "version": "0.3.1",
            "transports": {
                "stdio": {
                    "command": "uv",
                    "args": ["run", "python", "-m", "arxiv_mcp", "--stdio"],
                },
                "streamable_http": {
                    "mcp_url": f"http://{settings.host}:{settings.port}/mcp",
                },
            },
            "mcp_http": f"http://{settings.host}:{settings.port}/mcp",
            "api": f"http://{settings.host}:{settings.port}/api",
            "webapp": "http://127.0.0.1:10771",
        }

    @app.get("/.well-known/mcp/manifest.json")
    async def well_known_mcp_manifest() -> dict[str, Any]:
        """Machine-readable dual-transport discovery (LobeHub / indexer friendly)."""
        s = load_settings()
        base = f"http://{s.host}:{s.port}"
        return {
            "name": "arxiv-mcp",
            "version": "0.3.1",
            "repository": "https://github.com/sandraschi/arxiv-mcp",
            "transports": {
                "stdio": {
                    "command": "uv",
                    "args": ["run", "python", "-m", "arxiv_mcp", "--stdio"],
                },
                "streamable_http": {
                    "url": f"{base}/mcp",
                    "note": "FastMCP 3.1 http_app; start with: uv run python -m arxiv_mcp --serve",
                },
            },
        }

    return app


app = build_app()
