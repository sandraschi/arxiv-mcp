"""FastMCP 3.1 server: arXiv discovery, experimental HTML extraction, corpus hooks."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastmcp import FastMCP
from fastmcp.server.providers.skills import SkillsDirectoryProvider

from arxiv_mcp.arxiv_html import (
    arxiv_abs_metadata_from_html,
    arxiv_category_recent_html,
    arxiv_org_search_advanced_html,
    arxiv_org_search_html,
    jina_reader_fetch,
    list_categories_response,
)
from arxiv_mcp.config import load_settings
from arxiv_mcp.html_extract import fetch_html_markdown, html_url_for_paper
from arxiv_mcp.output_schemas import (
    GET_CONTENT_OUTPUT_SCHEMA,
    GET_PAPER_HTML_OUTPUT_SCHEMA,
    GET_RECENT_OUTPUT_SCHEMA,
    HTML_SEARCH_OUTPUT_SCHEMA,
    LIST_CATEGORIES_OUTPUT_SCHEMA,
)
from arxiv_mcp.services import corpus, papers

mcp = FastMCP(
    "arxiv-mcp",
    instructions=(
        "High-density arXiv research tools: search, metadata, experimental HTML→Markdown, "
        "Semantic Scholar lineage, local corpus ingest, and structured synthesis prompts. "
        "Also: arxiv.org HTML search (search, searchAdvanced), abs-page metadata (getPaper), "
        "Jina Reader full text (getContent), category recents (getRecent), listCategories."
    ),
)

_skills_dir = Path(__file__).resolve().parent / "skills"
if _skills_dir.is_dir():
    mcp.add_provider(SkillsDirectoryProvider(roots=[_skills_dir]))


@mcp.tool()
async def search_papers(
    query: str,
    categories: list[str] | None = None,
    limit: int = 10,
    sort_by: Literal["relevance", "submitted", "updated"] = "submitted",
) -> dict[str, Any]:
    """SEARCH_PAPERS — Query arXiv with optional category filters and sorting.

    PORTMANTEAU RATIONALE: Primary discovery surface for “firefront” scanning.

    Args:
        query: arXiv query text (keywords; combined with categories when provided).
        categories: arXiv categories such as cs.AI, cs.LG, cs.RO.
        limit: Max results (capped at 100).
        sort_by: relevance | submitted | updated.

    Returns:
        success, papers (metadata list), message.
    """
    try:
        rows = await papers.search_papers(
            query, categories=categories, limit=limit, sort_by=sort_by
        )
        return {
            "success": True,
            "message": f"Found {len(rows)} paper(s).",
            "papers": [papers.paper_summary_to_dict(p) for p in rows],
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "papers": [],
        }


@mcp.tool()
async def get_paper_details(paper_id: str) -> dict[str, Any]:
    """GET_PAPER_DETAILS — Full metadata: title, abstract, authors, links.

    Args:
        paper_id: arXiv id, URL, or arxiv: prefix form.

    Returns:
        success, paper dict including html_url for experimental HTML.
    """
    try:
        p = await papers.get_paper_details(paper_id)
        return {
            "success": True,
            "message": "Metadata loaded.",
            "paper": papers.paper_summary_to_dict(p),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }


@mcp.tool()
async def fetch_full_text(
    paper_id: str,
    format: Literal["markdown"] = "markdown",
    prefer_html: bool = True,
) -> dict[str, Any]:
    """FETCH_FULL_TEXT — Prefer arXiv experimental HTML converted to Markdown.

    When ``prefer_html`` is true, downloads ``https://arxiv.org/html/{id}`` and converts
    to Markdown. Not every paper has HTML; check ``html_available`` and use PDF tooling
    externally if false.

    Args:
        paper_id: arXiv id or URL.
        format: Currently only ``markdown`` is supported server-side.
        prefer_html: If false, returns guidance (PDF/source not extracted here yet).

    Returns:
        success, markdown (when available), html_url, http_status, notes.
    """
    try:
        meta = await papers.get_paper_details(paper_id)
        aid = meta.paper_id
        url = html_url_for_paper(aid)
        if not prefer_html:
            return {
                "success": True,
                "message": "HTML path disabled by flag; no PDF extraction in-server.",
                "paper_id": aid,
                "html_url": url,
                "markdown": None,
                "html_available": None,
            }
        ok, payload, status, ctype = await fetch_html_markdown(aid)
        if not ok:
            return {
                "success": False,
                "message": payload,
                "paper_id": aid,
                "html_url": url,
                "markdown": None,
                "html_available": False,
                "http_status": status,
                "content_type": ctype,
                "recommendations": [
                    "Try another version suffix (v1 vs v2).",
                    "Open pdf_url from get_paper_details and use an external PDF→MD pipeline.",
                ],
            }
        return {
            "success": True,
            "message": "Experimental HTML fetched and converted to Markdown.",
            "paper_id": aid,
            "title": meta.title,
            "html_url": url,
            "markdown": payload,
            "html_available": True,
            "http_status": status,
            "content_type": ctype,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }


@mcp.tool()
async def list_category_latest(
    category: str,
    limit: int = 25,
    hours: int = 24,
) -> dict[str, Any]:
    """LIST_CATEGORY_LATEST — Recent submissions in a category (~last ``hours``).

    Args:
        category: arXiv category (e.g. cs.LG).
        limit: Max papers after time filter.
        hours: Rolling window in hours (client-side filter on published time).

    Returns:
        success, papers.
    """
    try:
        rows = await papers.list_category_latest(category, limit=limit, hours=hours)
        return {
            "success": True,
            "message": f"{len(rows)} paper(s) in ~{hours}h window (best-effort).",
            "papers": [papers.paper_summary_to_dict(p) for p in rows],
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "papers": [],
        }


@mcp.tool()
async def find_connected_papers(paper_id: str, limit: int = 12) -> dict[str, Any]:
    """FIND_CONNECTED_PAPERS — Citation/reference lineage via Semantic Scholar.

    Args:
        paper_id: arXiv id or URL.
        limit: Max items per side (citations and references).

    Returns:
        Graph slice with citations/references (arXiv ids when known).
    """
    settings = load_settings()
    try:
        graph = await papers.find_connected_papers(
            paper_id, limit=limit, api_key=settings.semantic_scholar_api_key
        )
        return {"success": True, "message": "Semantic Scholar graph slice.", **graph}
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }


@mcp.tool()
async def ingest_paper_to_corpus(
    paper_id: str,
    markdown: str | None = None,
    source: Literal["html", "external"] = "html",
) -> dict[str, Any]:
    """INGEST_PAPER_TO_CORPUS — Persist Markdown + metadata for local RAG/memory.

    If ``markdown`` is omitted, fetches experimental HTML and converts it.
    """
    settings = load_settings()
    try:
        meta = await papers.get_paper_details(paper_id)
        aid = meta.paper_id
        md = markdown
        if md is None:
            ok, payload, _, _ = await fetch_html_markdown(aid)
            if not ok:
                return {
                    "success": False,
                    "message": payload,
                    "paper_id": aid,
                    "recommendations": [
                        "Provide markdown explicitly from an external PDF pipeline.",
                    ],
                }
            md = payload
        rec = corpus.ingest_markdown(
            aid,
            meta.title,
            md,
            source=source,
            meta={"authors": meta.authors, "categories": meta.categories},
            settings=settings,
        )
        return {
            "success": True,
            "message": "Paper ingested into local corpus.",
            "record": rec,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }


@mcp.tool()
async def compare_papers_convergence(paper_ids: list[str]) -> dict[str, Any]:
    """COMPARE_PAPERS_CONVERGENCE — Bundle abstracts for cross-paper synthesis.

    Server-side statistical testing is not performed; output is structured evidence
    for an LLM or analyst to judge convergence vs contradiction.
    """
    if len(paper_ids) < 2:
        return {
            "success": False,
            "error": "Provide at least two paper_ids.",
            "error_type": "ValueError",
        }
    bundle: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for raw in paper_ids[:12]:
        try:
            p = await papers.get_paper_details(raw)
            bundle.append(papers.paper_summary_to_dict(p))
        except Exception as e:
            errors.append({"paper_id": raw, "error": str(e)})
    prompt = (
        "You are reviewing multiple arXiv abstracts. "
        "For each claim family, mark: supported / contradicted / unclear across papers. "
        "Cite paper_id for every bullet. Flag speculative language."
    )
    return {
        "success": True,
        "message": f"Prepared {len(bundle)} papers for adjudication.",
        "papers": bundle,
        "errors": errors,
        "analysis_prompt": prompt,
    }


# --- arxiv.org HTML UI + Jina Reader ---


@mcp.tool(output_schema=HTML_SEARCH_OUTPUT_SCHEMA)
async def search(
    query: str = "",
    category: str | None = None,
    author: str | None = None,
    sort_by: str = "relevance",
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    """SEARCH — arxiv.org HTML search (abstracts + authors per hit).

    Use for broad keyword discovery with optional author/category filters. Prefer
    ``searchAdvanced`` when you need title/abstract/id/date field filters.

    Args:
        query: Free-text query (optional if author or category is set).
        category: arXiv category (e.g. cs.LG).
        author: Author filter (``au:``-style name fragment on the server side).
        sort_by: relevance | date_desc | date_asc | submissions_desc | submissions_asc.
        page: 1-based page index.
        page_size: Page size (capped at 50).

    Returns:
        On success, dict with:
        ``query`` (str), ``total_results`` (int, may be 0 if unknown), ``papers`` (list),
        ``page``, ``page_size``. Each paper has ``id_arxiv``, ``title``, ``abstract``,
        ``authors``, ``categories``, ``url_abstract``, ``url_pdf``, optional date strings.
        On invalid input: ``{"error": "..."}`` (e.g. empty query/author/category).
        Network or HTTP failures propagate as tool errors.

    Notes:
        Parsed rows that fail HTML extraction are skipped silently; ``len(papers)``
        can be lower than ``page_size`` even when more hits exist.
    """
    return await arxiv_org_search_html(
        query,
        category=category,
        author=author,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )


@mcp.tool(name="searchAdvanced", output_schema=HTML_SEARCH_OUTPUT_SCHEMA)
async def search_advanced(
    title: str | None = None,
    abstract: str | None = None,
    author: str | None = None,
    category: str | None = None,
    id_arxiv: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_by: str = "relevance",
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    """SEARCH_ADVANCED — Field-scoped HTML search (finer than ``search``).

    Args:
        title: Search within titles (ti:).
        abstract: Search within abstracts (abs:).
        author: Author filter.
        category: Category filter.
        id_arxiv: arXiv id pattern (id:).
        date_from / date_to: YYYY-MM-DD when the arXiv advanced UI accepts them.
        sort_by / page / page_size: Same semantics as ``search``.

    Returns:
        Same shape as ``search`` on success. If no field is provided:
        ``{"error": "At least one search field is required"}``.
        HTTP/network errors propagate as tool errors.
    """
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
        page_size=page_size,
    )


@mcp.tool(name="getPaper", output_schema=GET_PAPER_HTML_OUTPUT_SCHEMA)
async def get_paper(id_or_url: str) -> dict[str, Any]:
    """GET_PAPER — Metadata from the arxiv.org abstract HTML page.

    Args:
        id_or_url: New-style id (``2401.00001`` / ``2401.00001v2``), ``arxiv:…``, or
            a full ``https://arxiv.org/abs/…`` or ``…/pdf/…`` URL.

    Returns:
        ``success`` true with ``paper`` (metadata dict), or false with ``error``,
        ``error_type``, ``recovery_options`` (no exceptions for HTTP).
    """
    return await arxiv_abs_metadata_from_html(id_or_url)


@mcp.tool(name="getContent", output_schema=GET_CONTENT_OUTPUT_SCHEMA)
async def get_content(id_or_url: str) -> dict[str, Any]:
    """GET_CONTENT — Full text via **Jina Reader** (third-party), not arXiv.

    Fetches ``{ARXIV_MCP_JINA_READER_BASE_URL}/{abs_url}``. Default base is
    ``https://r.jina.ai``. Uses a longer HTTP timeout than HTML scraping.

    Args:
        id_or_url: Same accepted forms as ``getPaper``; non-HTTP strings are treated as ids.

    Returns:
        ``success`` true with ``content``, ``abs_url``, ``jina_url``, or false with
        structured error. Prefer ``fetch_full_text`` for local experimental HTML without Jina.
    """
    return await jina_reader_fetch(id_or_url)


@mcp.tool(name="getRecent", output_schema=GET_RECENT_OUTPUT_SCHEMA)
async def get_recent(category: str = "cs.AI", count: int = 10) -> dict[str, Any]:
    """GET_RECENT — Recent listing for one category (list page HTML).

    Args:
        category: arXiv category code (e.g. cs.AI).
        count: Max papers (capped at 50).

    Returns:
        Success with ``category``, ``category_name``, ``count``, ``papers``, ``parse_stats``,
        or structured error. List rows often omit abstracts.
    """
    return await arxiv_category_recent_html(category=category, count=count)


@mcp.tool(name="listCategories", output_schema=LIST_CATEGORIES_OUTPUT_SCHEMA)
async def list_categories() -> dict[str, Any]:
    """LIST_CATEGORIES — Curated list of common categories (code, name, group).

    Returns:
        ``success`` true with ``categories`` (sorted list of dicts). Static catalog.
    """
    return list_categories_response()


@mcp.prompt(
    name="generate_summary_prompt",
    description="Structured analyst brief for deep paper reading (instrumental convergence, qualia, etc.).",
    tags={"arxiv", "analysis"},
)
def generate_summary_prompt(
    lens: Literal["instrumental_convergence", "qualia", "methods_audit", "general"] = "general",
    paper_id: str | None = None,
) -> str:
    """Return a reusable prompt skeleton the client can inject before tool use."""
    header = (
        "You are an adversarial research analyst. Use arxiv-mcp tools to pull metadata "
        "and (when available) experimental HTML Markdown via fetch_full_text."
    )
    if paper_id:
        header += f"\nFocus paper: {paper_id} (normalize id, then fetch metadata first)."
    lenses = {
        "instrumental_convergence": (
            "\nLens: instrumental convergence / power-seeking memes.\n"
            "- Extract stated assumptions and optimization targets.\n"
            "- Separate empirical results from speculative extrapolation.\n"
            "- List failure modes the authors dismiss or omit."
        ),
        "qualia": (
            "\nLens: phenomenology / qualia claims.\n"
            "- Map definitions of terms.\n"
            "- Identify where introspection, third-person evidence, or analogy is doing work.\n"
            "- Propose falsifiable predictions implied by the text."
        ),
        "methods_audit": (
            "\nLens: methods audit.\n"
            "- Dataset, splits, baselines, metrics.\n"
            "- Compute and reproducibility signals.\n"
            "- Threats to validity checklist."
        ),
        "general": (
            "\nLens: general deep read.\n"
            "- Problem, approach, key results, limitations, related work hooks."
        ),
    }
    return header + lenses[lens]
