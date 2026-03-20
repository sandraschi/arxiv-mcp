"""FastAPI application: REST dashboard API + mounted FastMCP HTTP (streamable)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, FastAPI, Query

from arxiv_mcp.config import load_settings
from arxiv_mcp.server import mcp
from arxiv_mcp.services import corpus, papers

mcp_http = mcp.http_app(path="/mcp")
router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "arxiv-mcp"}


@router.get("/search")
async def api_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("submitted"),
) -> dict[str, Any]:
    rows = await papers.search_papers(q, limit=limit, sort_by=sort_by)
    return {"papers": [papers.paper_summary_to_dict(p) for p in rows]}


@router.get("/paper")
async def api_paper(paper_id: str = Query(..., min_length=5)) -> dict[str, Any]:
    p = await papers.get_paper_details(paper_id)
    return {"paper": papers.paper_summary_to_dict(p)}


@router.get("/corpus")
async def api_corpus(limit: int = Query(50, ge=1, le=200)) -> dict[str, Any]:
    rows = corpus.list_ingested(limit=limit)
    return {"ingested": rows}


def build_app() -> FastAPI:
    settings = load_settings()
    app = FastAPI(
        title="arxiv-mcp",
        version="0.1.0",
        lifespan=mcp_http.lifespan,
    )
    app.include_router(router)
    app.mount("/mcp", mcp_http)

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {
            "service": "arxiv-mcp",
            "mcp_http": f"http://{settings.host}:{settings.port}/mcp",
            "api": f"http://{settings.host}:{settings.port}/api",
        }

    return app


app = build_app()
