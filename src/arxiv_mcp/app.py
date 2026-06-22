"""FastAPI: REST dashboard API + mounted FastMCP HTTP (streamable)."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from arxiv_mcp import __version__
from arxiv_mcp.anthropic_blog import (
    KNOWN_POSTS,
)
from arxiv_mcp.anthropic_blog import (
    fetch_anthropic_post as _fetch_anthropic_post,
)
from arxiv_mcp.anthropic_blog import (
    list_anthropic_posts as _list_anthropic_posts,
)
from arxiv_mcp.arxiv_html import arxiv_org_search_advanced_html, list_categories_payload
from arxiv_mcp.capabilities import build_capabilities
from arxiv_mcp.config import load_settings
from arxiv_mcp.depot_service import (
    analyze_paper_epistemics,
    deep_analyze_paper_epistemics,
    ingest_and_analyze_paper,
    ingest_paper_html,
    list_depot_by_epistemics,
)
from arxiv_mcp.firefront_service import run_firefront_scan
from arxiv_mcp.lab_blog import (
    SOURCES as LAB_SOURCES,
)
from arxiv_mcp.lab_blog import (
    fetch_lab_post as _fetch_lab_post,
)
from arxiv_mcp.lab_blog import (
    list_lab_posts as _list_lab_posts,
)
from arxiv_mcp.server import mcp
from arxiv_mcp.services import corpus, papers
from arxiv_mcp.startup_probe import run_startup_probes
from arxiv_mcp.tools_manifest import MCP_PROMPTS

mcp_http = mcp.http_app(path="/mcp")
router = APIRouter(prefix="/api")

_FLEET_PATH = Path(__file__).resolve().parent / "data" / "fleet_default.json"


class FavoriteIn(BaseModel):
    arxiv_id: str = Field(..., min_length=4)
    title: str | None = None
    note: str | None = None


class IngestIn(BaseModel):
    paper_id: str = Field(..., min_length=4)


class MediaSettingsIn(BaseModel):
    media_ignore_botblocks: bool | None = None
    media_use_brighthand: bool | None = None


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


@router.get("/preprints/search")
async def api_preprints_search(
    q: str = Query(..., min_length=1),
    servers: str = Query("arxiv,biorxiv,medrxiv,chemrxiv,researchsquare"),
    limit: int = Query(20, ge=1, le=50),
    hours: int = Query(720, ge=1, le=8760),
) -> dict:
    """Search multiple preprint servers in parallel.

    Servers: arxiv, biorxiv, medrxiv, chemrxiv, researchsquare
    """
    import logging
    logger = logging.getLogger(__name__)
    from arxiv_mcp.services.preprint_servers import (
        SERVER_LABELS,
        merge_results,
        search_all,
    )

    srv_list = [s.strip() for s in servers.split(",") if s.strip()]
    results_by_server = search_all(q, servers=[s for s in srv_list if s != "arxiv"], limit=limit, hours=hours)

    # Add arXiv results
    if "arxiv" in srv_list:
        try:
            arxiv_results = await papers.search_papers(q, limit=limit)
            from arxiv_mcp.services.preprint_servers import Paper

            results_by_server["arxiv"] = [
                Paper(
                    paper_id=p.get("entry_id", ""),
                    title=p.get("title", ""),
                    summary=p.get("summary", ""),
                    authors=[a.get("name", "") for a in p.get("authors", [])],
                    categories=p.get("categories", []),
                    published=str(p.get("published", "")),
                    server="arxiv",
                    html_url=p.get("link", ""),
                    pdf_url=p.get("pdf_url", ""),
                )
                for p in (papers.paper_summary_to_dict(r) for r in arxiv_results)
            ]
        except Exception as e:
            logger.warning("arXiv search in preprints endpoint failed: %s", e)
            results_by_server["arxiv"] = []

    merged = merge_results(results_by_server, total_limit=limit * len(results_by_server))

    # Return per-server breakdown + merged
    per_server = {}
    for srv, pp in results_by_server.items():
        label = SERVER_LABELS.get(srv, srv)
        per_server[srv] = {"label": label, "count": len(pp), "papers": [p.__dict__ for p in pp]}

    return {"merged": [p.__dict__ for p in merged], "per_server": per_server, "total": len(merged)}


@router.get("/category/latest")
async def api_category_latest(
    category: str = Query(..., min_length=2),
    limit: int = Query(25, ge=1, le=100),
    hours: int = Query(24, ge=1, le=168),
) -> dict[str, Any]:
    rows = await papers.list_category_latest(category, limit=limit, hours=hours)
    return {"papers": [papers.paper_summary_to_dict(p) for p in rows]}


@router.get("/searchAdvanced")
async def api_search_advanced(
    title: str | None = Query(None, description="Search within paper titles (ti:)"),
    abstract: str | None = Query(None, description="Search within abstracts (abs:)"),
    author: str | None = Query(None, description="Author filter (au:)"),
    category: str | None = Query(None, description="Category filter (cat:)"),
    id_arxiv: str | None = Query(None, description="arXiv ID pattern (id:)"),
    date_from: str | None = Query(None, description="YYYY-MM-DD start date"),
    date_to: str | None = Query(None, description="YYYY-MM-DD end date"),
    sort_by: str = Query("relevance"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=50),
    limit: int | None = Query(None, description="Alias for page_size (convenience)"),
) -> dict[str, Any]:
    """Field-scoped search on arxiv.org HTML (same as MCP searchAdvanced tool)."""
    return await arxiv_org_search_advanced_html(
        title=title,
        abstract=abstract,
        author=author,
        category=category,
        id_arxiv=id_arxiv,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        page=page,
        page_size=limit or page_size,
    )


@router.get("/paper")
async def api_paper(paper_id: str = Query(..., min_length=5)) -> dict[str, Any]:
    p = await papers.get_paper_details(paper_id)
    return {"paper": papers.paper_summary_to_dict(p)}


@router.get("/corpus")
async def api_corpus(
    limit: int = Query(50, ge=1, le=500),
    primary_mode: str | None = Query(None, description="Filter by epistemic primary_mode"),
    needs_bench: bool | None = Query(None),
    needs_telescope_or_instrument: bool | None = Query(None),
    needs_formal_verification: bool | None = Query(None),
    has_deep_claims: bool | None = Query(None, description="True = only papers with LLM claim tables"),
) -> dict[str, Any]:
    if any(
        x is not None
        for x in (primary_mode, needs_bench, needs_telescope_or_instrument, needs_formal_verification, has_deep_claims)
    ):
        rows = corpus.list_ingested_filtered(
            limit=limit,
            primary_mode=primary_mode,
            needs_bench=needs_bench,
            needs_telescope_or_instrument=needs_telescope_or_instrument,
            needs_formal_verification=needs_formal_verification,
            has_deep_claims=has_deep_claims,
        )
        return {"ingested": rows, "filtered": True}
    rows = corpus.list_ingested(limit=limit)
    return {"ingested": rows, "filtered": False}


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
    mode: str = Query(
        "hybrid",
        pattern="^(fts|semantic|hybrid)$",
        description="Search engine: fts (BM25), semantic (LanceDB), hybrid (RRF merge)",
    ),
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
    if mode == "fts":
        hits = corpus.search_depot_fts(q, limit=limit, max_age_days=max_age_days)
        engine = "sqlite_fts5"
    elif mode == "semantic":
        try:
            hits = corpus.search_depot_semantic(q, limit=limit)
            engine = "lancedb"
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    else:
        hits, engine = corpus.search_depot_hybrid(q, limit=limit, max_age_days=max_age_days)
    return {
        "query": q,
        "mode": mode,
        "max_age_days": max_age_days,
        "hits": hits,
        "engine": engine,
    }


@router.get("/depot/rag/status")
async def api_depot_rag_status() -> dict[str, Any]:
    from arxiv_mcp.services.vector_rag import vector_rag_status

    return vector_rag_status()


@router.post("/depot/rag/reindex")
async def api_depot_rag_reindex() -> dict[str, Any]:
    from arxiv_mcp.services.vector_rag import reindex_all_vectors

    result = reindex_all_vectors()
    if not result.get("success"):
        raise HTTPException(status_code=503, detail=result.get("error", "reindex failed"))
    return result


class FirefrontIn(BaseModel):
    topic: str = Field(..., min_length=1)
    categories: list[str] | None = None
    days: int = Field(7, ge=1, le=90)
    limit_per_category: int = Field(25, ge=1, le=100)
    ingest_top_n: int = Field(0, ge=0, le=20)


@router.post("/firefront/scan")
async def api_firefront_scan(body: FirefrontIn) -> dict[str, Any]:
    result = await run_firefront_scan(
        body.topic,
        categories=body.categories,
        days=body.days,
        limit_per_category=body.limit_per_category,
        ingest_top_n=body.ingest_top_n,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)
    return result


class CodehuntScanIn(BaseModel):
    categories: list[str] | None = None
    days: int = Field(3, ge=1, le=30)
    limit_per_category: int = Field(50, ge=1, le=100)
    fulltext_max_papers: int | None = Field(None, ge=0, le=50)
    push: bool = True


@router.post("/codehunt/scan")
async def api_codehunt_scan(body: CodehuntScanIn) -> dict[str, Any]:
    from arxiv_mcp.codehunt_service import run_codehunt_scan

    result = await run_codehunt_scan(
        categories=body.categories,
        days=body.days,
        limit_per_category=body.limit_per_category,
        fulltext_max_papers=body.fulltext_max_papers,
        push=body.push,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/codehunt/repoll")
async def api_codehunt_repoll(
    limit: int = Query(200, ge=1, le=1000),
    push: bool = Query(True),
) -> dict[str, Any]:
    from arxiv_mcp.codehunt_service import repoll_pending

    return await repoll_pending(limit=limit, push=push)


@router.get("/codehunt/stats")
async def api_codehunt_stats() -> dict[str, Any]:
    from arxiv_mcp.codehunt_service import codehunt_stats

    return codehunt_stats()


@router.post("/codehunt/media-check")
async def api_codehunt_media_check(
    limit: int = Query(40, ge=1, le=200),
    push: bool = Query(True),
) -> dict[str, Any]:
    from arxiv_mcp.codehunt_service import check_media_traction

    return await check_media_traction(limit=limit, push=push)


@router.get("/pipeline/liveness")
async def api_pipeline_liveness(
    stale_hours: int = Query(48, ge=1, le=168),
) -> dict[str, Any]:
    from arxiv_mcp.pipeline_liveness_service import check_pipeline_liveness

    return await check_pipeline_liveness(stale_hours=stale_hours)


@router.get("/settings/readly")
async def api_readly_settings() -> dict[str, Any]:
    from arxiv_mcp.readly_client import (
        load_readly_watch_magazines,
        readly_health,
        readly_subscription_status,
    )

    settings = load_settings()
    status = readly_subscription_status(settings)
    health = await readly_health(settings) if status.get("enabled") else {"ok": False, "skipped": True}
    return {
        "success": True,
        **status,
        "health": health,
        "watch_magazines": load_readly_watch_magazines(settings),
        "ingest_on_depot": settings.readly_ingest_on_depot,
        "ingest_magazines": settings.parsed_readly_ingest_magazines()
        or [m["readly_query"] for m in load_readly_watch_magazines(settings)],
        "docs": "/api/help/readly",
    }


@router.get("/settings/publications")
async def api_publication_subscriptions() -> dict[str, Any]:
    from arxiv_mcp.publication_subscriptions import (
        expired_subscription_alerts,
        list_subscription_statuses,
    )
    from arxiv_mcp.readly_client import readly_subscription_status

    rows = list_subscription_statuses()
    readly_row = readly_subscription_status()
    if readly_row.get("enabled") or readly_row.get("readly_mcp_url"):
        rows.append(
            {
                "id": "readly",
                "name": "Readly (magazine library)",
                "domains": ["readly.co", "readly.com"],
                "status": readly_row.get("status"),
                "valid_till": readly_row.get("valid_till"),
                "has_user": False,
                "has_password": False,
                "has_cookie": False,
                "configured": readly_row.get("enabled"),
                "usable": readly_row.get("status") == "valid",
                "expiring_soon": readly_row.get("status") == "expiring_soon",
                "expired": readly_row.get("status") == "expired",
                "env_keys": {
                    "url": "ARXIV_MCP_READLY_MCP_URL",
                    "valid_till": "ARXIV_MCP_READLY_VALID_TILL",
                    "token_on_readly": "READLY_AUTH_TOKEN",
                },
            }
        )
    alerts = expired_subscription_alerts()
    return {
        "success": True,
        "publications": rows,
        "alerts": alerts,
        "healthy": not any(a.get("severity") == "critical" for a in alerts),
        "message": "Secrets live in .env only — this endpoint never returns passwords or cookies.",
    }


@router.get("/settings/media")
async def api_media_settings_get() -> dict[str, Any]:
    from arxiv_mcp.runtime_settings import media_settings_payload

    return {"success": True, **media_settings_payload()}


@router.patch("/settings/media")
async def api_media_settings_patch(body: MediaSettingsIn) -> dict[str, Any]:
    from arxiv_mcp.runtime_settings import media_settings_payload, write_overrides

    updates: dict[str, bool] = {}
    if body.media_ignore_botblocks is not None:
        updates["media_ignore_botblocks"] = body.media_ignore_botblocks
    if body.media_use_brighthand is not None:
        updates["media_use_brighthand"] = body.media_use_brighthand
    if not updates:
        raise HTTPException(status_code=400, detail="No settings fields provided")
    write_overrides(updates)
    return {
        "success": True,
        "message": "Media settings updated",
        **media_settings_payload(),
    }


@router.get("/help")
async def api_help_index() -> dict[str, Any]:
    from arxiv_mcp.help_content import get_help

    return get_help(None)


@router.get("/help/{topic}")
async def api_help_topic(topic: str) -> dict[str, Any]:
    from arxiv_mcp.help_content import get_help

    result = get_help(topic)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result)
    return result


@router.post("/depot/ingest")
async def api_depot_ingest(body: IngestIn) -> dict[str, Any]:
    result = await ingest_paper_html(body.paper_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "ingest failed"))
    return result


@router.post("/depot/ingest-analyze")
async def api_depot_ingest_analyze(body: IngestIn, deep: bool = Query(True)) -> dict[str, Any]:
    """Ingest HTML-first; rule + deep LLM epistemic profile when LLM endpoint available."""
    result = await ingest_and_analyze_paper(body.paper_id, deep=deep)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "ingest-analyze failed"))
    return result


@router.post("/depot/analyze")
async def api_depot_analyze(
    body: IngestIn,
    ingest_if_missing: bool = Query(True, description="Ingest from HTML if not already in depot"),
) -> dict[str, Any]:
    result = await analyze_paper_epistemics(body.paper_id, ingest_if_missing=ingest_if_missing)
    if not result.get("success"):
        raise HTTPException(status_code=404 if result.get("error") == "not_in_depot" else 400, detail=result)
    return result


@router.post("/depot/deep-analyze")
async def api_depot_deep_analyze(
    body: IngestIn,
    ingest_if_missing: bool = Query(True),
    force_refresh: bool = Query(False),
) -> dict[str, Any]:
    """LLM claim-level epistemic profile (requires SAMPLING_BASE_URL or MCP sampling client)."""
    result = await deep_analyze_paper_epistemics(
        body.paper_id,
        ingest_if_missing=ingest_if_missing,
        force_refresh=force_refresh,
    )
    if not result.get("success"):
        status = 503 if "SAMPLING" in str(result.get("error", "")).upper() else 400
        raise HTTPException(status_code=status, detail=result)
    return result


@router.get("/depot/epistemics")
async def api_depot_epistemics_filter(
    primary_mode: str | None = Query(None),
    needs_bench: bool | None = Query(None),
    needs_telescope_or_instrument: bool | None = Query(None),
    needs_formal_verification: bool | None = Query(None),
    has_deep_claims: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    return list_depot_by_epistemics(
        primary_mode=primary_mode,
        needs_bench=needs_bench,
        needs_telescope_or_instrument=needs_telescope_or_instrument,
        needs_formal_verification=needs_formal_verification,
        has_deep_claims=has_deep_claims,
        limit=limit,
    )


@router.post("/calibre/ingest")
async def api_calibre_ingest(body: IngestIn) -> dict[str, Any]:
    from arxiv_mcp.server import store_paper_to_calibre
    result = await store_paper_to_calibre(body.paper_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "calibre ingest failed"))
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
    caps = await build_capabilities()
    return {
        "tools": caps["tools"],
        "tool_count": caps["tool_count"],
        "mcp_http_path": "/mcp",
        "source": "capabilities",
    }


@router.get("/capabilities")
async def api_capabilities() -> dict[str, Any]:
    """Runtime introspection: tools, prompts, skills, depot stats, feature flags."""
    return await build_capabilities()


@router.get("/skills")
async def api_skills() -> dict[str, Any]:
    caps = await build_capabilities()
    return {"skills": caps["skills"], "count": len(caps["skills"])}


@router.get("/llm/discover")
async def api_llm_discover() -> dict[str, Any]:
    """Scan common local LLM endpoints (Ollama, LM Studio)."""
    import httpx

    settings = load_settings()
    probes = [
        ("ollama", "http://localhost:11434/api/tags"),
        ("lmstudio", "http://localhost:1234/v1/models"),
    ]
    found: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=3.0) as client:
        for kind, url in probes:
            try:
                resp = await client.get(url)
                if resp.status_code < 500:
                    base_url = url.split("/api")[0].split("/v1")[0]
                    found.append({"kind": kind, "url": base_url, "status": resp.status_code})
            except Exception as exc:
                found.append({"kind": kind, "url": url, "error": str(exc)})

    ollama_up = any(f.get("kind") == "ollama" and f.get("status", 500) < 500 for f in found)
    return {
        "configured_sampling_url": settings.sampling_base_url,
        "configured_model": settings.sampling_model,
        "probes": found,
        "ollama_detected": ollama_up,
        "recommendation": (
            "Set ARXIV_MCP_SAMPLING_BASE_URL=http://localhost:11434/v1 for deep epistemic analysis."
            if ollama_up and not settings.sampling_base_url
            else None
        ),
    }


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
    from fastapi.middleware.cors import CORSMiddleware

    _tauri_desktop = os.environ.get("ARXIV_TAURI", "").lower() in ("1", "true", "yes")

    @asynccontextmanager
    async def app_lifespan(app: FastAPI):
        await run_startup_probes(settings)
        async with mcp_http.lifespan(app):
            yield

    app = FastAPI(
        title="arxiv-mcp",
        version=__version__,
        lifespan=app_lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:10770",
            "http://localhost:10770",
            "http://127.0.0.1:10771",
            "http://localhost:10771",
            "http://goliath:10770",
            "http://goliath:10771",
            "http://tauri.localhost",
            "https://tauri.localhost",
            "tauri://localhost",
        ],
        allow_origin_regex=r"https?://tauri\.localhost(:\d+)?" if _tauri_desktop else None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    app.mount("/mcp", mcp_http)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {
            "service": "arxiv-mcp",
            "version": __version__,
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
            "version": __version__,
            "repository": "https://github.com/sandraschi/arxiv-mcp",
            "transports": {
                "stdio": {
                    "command": "uv",
                    "args": ["run", "python", "-m", "arxiv_mcp", "--stdio"],
                },
                "streamable_http": {
                    "url": f"{base}/mcp",
                    "note": "FastMCP 3.2 http_app; start with: uv run python -m arxiv_mcp --serve",
                },
            },
        }

    return app


app = build_app()
