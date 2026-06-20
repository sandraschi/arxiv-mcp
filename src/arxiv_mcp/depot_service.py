"""Orchestrate HTML fetch + corpus ingest + epistemic analysis for REST/MCP."""

from __future__ import annotations

import logging
from typing import Any

from arxiv_mcp.config import Settings, load_settings
from arxiv_mcp.html_sections import prepare_ingest_from_html, prepare_ingest_from_plaintext
from arxiv_mcp.http import get_text
from arxiv_mcp.pdf_text import fetch_pdf_plaintext
from arxiv_mcp.services import corpus, papers
from arxiv_mcp.services.epistemic_deep import SampleFn, run_deep_epistemic_analysis
from arxiv_mcp.services.epistemic_profile import build_epistemic_profile

log = logging.getLogger(__name__)


async def _fetch_raw_html(aid: str, settings: Settings) -> tuple[bool, str, dict[str, Any]]:
    from arxiv_mcp.html_extract import html_url_for_paper

    url = html_url_for_paper(aid)
    payload = await get_text(
        url,
        settings=settings,
        cache_endpoint="arxiv_html_ingest",
    )
    if not payload.ok or not payload.text:
        return False, payload.error.get("error", "HTML fetch failed") if payload.error else "HTML fetch failed", {
            "http_status": payload.status_code,
        }
    return True, payload.text, {"http_status": payload.status_code, "from_cache": payload.from_cache}


async def resolve_fulltext_for_ingest(
    paper_id: str,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """HTML-first full text with section chunks; PDF fallback when HTML unavailable."""
    settings = settings or load_settings()
    meta = await papers.get_paper_details(paper_id)
    aid = meta.paper_id

    ok_html, raw_or_msg, fetch_meta = await _fetch_raw_html(aid, settings)
    if ok_html:
        md, chunks, quality = prepare_ingest_from_html(raw_or_msg)
        return {
            "success": True,
            "arxiv_id": aid,
            "markdown": md,
            "chunks": chunks,
            "source": "html",
            "ingest_meta": {**fetch_meta, **quality},
        }

    if meta.pdf_url:
        ok_pdf, text, err_type = await fetch_pdf_plaintext(
            meta.pdf_url,
            max_chars=settings.fetch_full_text_pdf_max_chars,
            settings=settings,
        )
        if ok_pdf:
            md, chunks, quality = prepare_ingest_from_plaintext(text, source="pdf")
            return {
                "success": True,
                "arxiv_id": aid,
                "markdown": md,
                "chunks": chunks,
                "source": "pdf",
                "ingest_meta": {
                    **fetch_meta,
                    **quality,
                    "html_error": raw_or_msg,
                },
            }
        return {
            "success": False,
            "error": f"{raw_or_msg}; PDF fallback failed: {text}",
            "arxiv_id": aid,
            "error_type": err_type,
            **fetch_meta,
        }

    return {
        "success": False,
        "error": raw_or_msg,
        "arxiv_id": aid,
        **fetch_meta,
        "recommendations": [
            "Try another version suffix (v1 vs v2).",
            "Provide markdown= explicitly from an external pipeline.",
        ],
    }


async def ingest_paper_with_fallback(
    paper_id: str,
    *,
    markdown: str | None = None,
    source: str = "html",
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Ingest with optional pre-supplied markdown or HTML/PDF resolution."""
    settings = settings or load_settings()
    meta = await papers.get_paper_details(paper_id)
    aid = meta.paper_id

    precomputed: list[str] | None = None
    ingest_meta: dict[str, Any] = {}
    if markdown is None:
        resolved = await resolve_fulltext_for_ingest(aid, settings=settings)
        if not resolved.get("success"):
            return resolved
        markdown = resolved["markdown"]
        source = resolved.get("source", source)
        precomputed = resolved.get("chunks")
        ingest_meta = resolved.get("ingest_meta") or {}
    else:
        _, precomputed, ingest_meta = prepare_ingest_from_plaintext(markdown, source=source)

    meta_payload = {
        "authors": meta.authors,
        "categories": meta.categories,
        "published": meta.published,
        "ingest_meta": ingest_meta,
    }
    rec = corpus.ingest_markdown(
        aid,
        meta.title,
        markdown,
        source=source,
        meta=meta_payload,
        settings=settings,
        precomputed_chunks=precomputed,
    )
    return {
        "success": True,
        "arxiv_id": aid,
        "title": meta.title,
        **rec,
    }


async def ingest_paper_html(paper_id: str) -> dict[str, Any]:
    """Fetch experimental HTML (or PDF) and ingest into depot."""
    result = await ingest_paper_with_fallback(paper_id)
    if result.get("success"):
        result["html_preferred"] = result.get("source") == "html"
        result.setdefault(
            "message",
            "Paper ingested with section-aware chunks when HTML structure allows.",
        )
    return result


async def _ensure_depot_paper(paper_id: str, *, ingest_if_missing: bool) -> dict[str, Any]:
    meta = await papers.get_paper_details(paper_id)
    aid = meta.paper_id
    row = corpus.get_paper_markdown(aid)
    if row:
        return {"success": True, "arxiv_id": aid, "title": row["title"], "row": row, "meta": meta}
    if not ingest_if_missing:
        return {
            "success": False,
            "error": "not_in_depot",
            "arxiv_id": aid,
            "recommendations": ["Ingest first or set ingest_if_missing=true."],
        }
    ingested = await ingest_paper_html(aid)
    if not ingested.get("success"):
        return ingested
    row = corpus.get_paper_markdown(aid)
    return {"success": True, "arxiv_id": aid, "title": ingested.get("title", meta.title), "row": row, "meta": meta}


async def deep_analyze_paper_epistemics(
    paper_id: str,
    *,
    ingest_if_missing: bool = True,
    force_refresh: bool = False,
    sample_fn: SampleFn | None = None,
) -> dict[str, Any]:
    """Full v2 analysis: rule profile + LLM claim table persisted to depot."""
    ensured = await _ensure_depot_paper(paper_id, ingest_if_missing=ingest_if_missing)
    if not ensured.get("success"):
        return ensured
    row = ensured.get("row")
    if not row:
        return {"success": False, "error": "depot_row_missing", "arxiv_id": ensured["arxiv_id"]}
    aid = ensured["arxiv_id"]
    meta = ensured.get("meta")
    categories = (row.get("meta") or {}).get("categories")
    if not isinstance(categories, list) and meta:
        categories = meta.categories

    existing_profile = (row.get("meta") or {}).get("epistemic_profile")
    if (
        not force_refresh
        and existing_profile
        and existing_profile.get("claims")
        and "+" in str(existing_profile.get("analyzer", ""))
    ):
        return {
            "success": True,
            "arxiv_id": aid,
            "title": row["title"],
            "ingested": True,
            "epistemic_profile": existing_profile,
            "cached": True,
        }

    try:
        profile = await run_deep_epistemic_analysis(
            row["markdown"],
            title=row["title"],
            categories=categories if isinstance(categories, list) else None,
            sample_fn=sample_fn,
        )
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "arxiv_id": aid,
            "recovery_options": [
                "Set ARXIV_MCP_SAMPLING_BASE_URL to an OpenAI-compatible endpoint (e.g. Ollama http://localhost:11434/v1).",
                "Use a Cursor client with MCP sampling and call deep_analyze_paper_epistemics from the agent.",
                "Rule-only profile remains available via analyze_paper_epistemics.",
            ],
        }

    saved = corpus.persist_epistemic_profile(aid, profile)
    if not saved.get("success"):
        return saved
    return {
        "success": True,
        "arxiv_id": aid,
        "title": row["title"],
        "ingested": True,
        "epistemic_profile": profile,
        "message": "Deep epistemic profile with claim table saved.",
    }


async def _attach_readly_coverage(aid: str, title: str) -> list[dict[str, Any]]:
    from arxiv_mcp.readly_client import fetch_readly_depot_coverage

    try:
        coverage = await fetch_readly_depot_coverage(title)
        if coverage:
            corpus.persist_readly_coverage(aid, coverage)
        return coverage
    except Exception as exc:
        log.warning("readly depot coverage failed for %s: %s", aid, exc)
        return []


async def _finalize_ingest_with_readly(result: dict[str, Any]) -> dict[str, Any]:
    if not result.get("success"):
        return result
    aid = str(result.get("arxiv_id") or "")
    title = str(result.get("title") or "")
    result["readly_coverage"] = await _attach_readly_coverage(aid, title)
    return result


async def ingest_and_analyze_paper(
    paper_id: str,
    *,
    deep: bool = True,
    sample_fn: SampleFn | None = None,
) -> dict[str, Any]:
    """Ingest (HTML-first) then rule + optional deep LLM epistemic analysis."""
    result = await ingest_paper_html(paper_id)
    if not result.get("success"):
        return result
    if deep:
        deep_result = await deep_analyze_paper_epistemics(
            result["arxiv_id"],
            ingest_if_missing=False,
            force_refresh=True,
            sample_fn=sample_fn,
        )
        if deep_result.get("success"):
            return await _finalize_ingest_with_readly(
                {
                    **result,
                    "epistemic_profile": deep_result.get("epistemic_profile"),
                    "message": "Paper ingested (HTML-first) with deep epistemic profile.",
                }
            )
        result["deep_analysis_error"] = deep_result.get("error")
        result["recovery_options"] = deep_result.get("recovery_options")
    profile = result.get("epistemic_profile") or build_epistemic_profile(
        "",
        categories=(await papers.get_paper_details(paper_id)).categories,
        title=result.get("title", ""),
    )
    return await _finalize_ingest_with_readly(
        {
            **result,
            "epistemic_profile": profile,
            "message": "Paper ingested with rule epistemic profile (deep analysis unavailable).",
        }
    )


async def analyze_paper_epistemics(
    paper_id: str,
    *,
    ingest_if_missing: bool = True,
) -> dict[str, Any]:
    """Return rule-based epistemic profile for a depot paper; optionally ingest first."""
    ensured = await _ensure_depot_paper(paper_id, ingest_if_missing=ingest_if_missing)
    if not ensured.get("success"):
        return ensured
    row = ensured.get("row")
    if not row:
        return {"success": False, "error": "depot_row_missing", "arxiv_id": ensured["arxiv_id"]}
    aid = ensured["arxiv_id"]
    profile = (row.get("meta") or {}).get("epistemic_profile")
    if profile and not profile.get("claims"):
        return {
            "success": True,
            "arxiv_id": aid,
            "title": row["title"],
            "ingested": True,
            "epistemic_profile": profile,
            "source": row.get("source"),
            "hint": "Use deep_analyze_paper_epistemics for claim-level LLM analysis.",
        }
    if profile:
        return {
            "success": True,
            "arxiv_id": aid,
            "title": row["title"],
            "ingested": True,
            "epistemic_profile": profile,
            "source": row.get("source"),
        }
    analyzed = corpus.analyze_ingested_paper(aid)
    if analyzed.get("success"):
        return {
            "success": True,
            "arxiv_id": aid,
            "title": row["title"],
            "ingested": True,
            "epistemic_profile": analyzed["epistemic_profile"],
            "source": row.get("source"),
        }
    return analyzed


def list_depot_by_epistemics(
    *,
    primary_mode: str | None = None,
    needs_bench: bool | None = None,
    needs_telescope_or_instrument: bool | None = None,
    needs_formal_verification: bool | None = None,
    has_deep_claims: bool | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    rows = corpus.list_ingested_filtered(
        limit=limit,
        primary_mode=primary_mode,
        needs_bench=needs_bench,
        needs_telescope_or_instrument=needs_telescope_or_instrument,
        needs_formal_verification=needs_formal_verification,
        has_deep_claims=has_deep_claims,
    )
    return {"papers": rows, "count": len(rows)}
