"""FastMCP 3.1 server: arXiv discovery, experimental HTML extraction, corpus hooks."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastmcp import Context, FastMCP
from fastmcp.server.providers.skills import SkillsDirectoryProvider

from arxiv_mcp.lab_blog import (
    fetch_lab_post as _fetch_lab_post,
    list_lab_posts as _list_lab_posts,
    SOURCES as LAB_SOURCES,
)
from arxiv_mcp.anthropic_blog import (
    fetch_anthropic_post as _fetch_anthropic_post,
    list_anthropic_posts as _list_anthropic_posts,
    KNOWN_POSTS,
)
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
        "Jina Reader full text (getContent), category recents (getRecent), listCategories. "
        "Sampling: arxiv_agentic_assist, arxiv_sampling_hint (FastMCP 3.1 ctx.sample when the host supports it)."
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


@mcp.tool()
async def arxiv_agentic_assist(goal: str, ctx: Context) -> dict[str, Any]:
    """ARXIV_AGENTIC_ASSIST — Multi-step research plan via MCP sampling (FastMCP 3.1).

    Uses ``ctx.sample`` when the host exposes sampling; otherwise returns a structured error.
    Plans should reference concrete tools: ``search_papers``, ``search``, ``searchAdvanced``,
    ``get_paper_details``, ``getPaper``, ``fetch_full_text``, ``getContent``, ``getRecent``,
    ``listCategories``, ``find_connected_papers``, ``list_category_latest``,
    ``ingest_paper_to_corpus``, ``compare_papers_convergence``.
    """
    try:
        result = await ctx.sample(
            messages=(
                "You are an assistant for arxiv-mcp. Given the user's research goal, output a compact plan:\n"
                "1) First line: one-line summary\n"
                "Then numbered steps (3-7), each naming concrete MCP tools to call.\n\n"
                f"Goal:\n{goal[:4000]}"
            ),
            system_prompt=(
                "Be concise. Plain text only, no markdown fences. Prefer search_papers or search for discovery; "
                "get_paper_details for API metadata; getPaper for HTML abs metadata; fetch_full_text for "
                "experimental arXiv HTML; getContent for Jina Reader full text when third-party fetch is OK."
            ),
            max_tokens=800,
        )
        text = getattr(result, "text", None) or str(result)
        return {"success": True, "plan": text.strip(), "goal": goal}
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "goal": goal,
            "recovery_options": [
                "Use a client that supports MCP sampling.",
                "Follow the bundled skill arxiv-researcher (skill://) for manual tool order.",
            ],
        }


@mcp.tool()
async def arxiv_sampling_hint(topic: str, ctx: Context) -> dict[str, Any]:
    """ARXIV_SAMPLING_HINT — Suggest queries and categories (uses ``ctx.sample`` when available)."""
    try:
        result = await ctx.sample(
            messages=(
                "Suggest 3-5 arXiv keyword search lines and one line of recommended categories "
                "(e.g. cs.LG cs.AI). Topic:\n" + topic[:2000]
            ),
            system_prompt="Plain text only. No markdown fences.",
            max_tokens=400,
        )
        text = getattr(result, "text", None) or str(result)
        return {"success": True, "suggestions": text.strip(), "topic": topic}
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "topic": topic,
            "recovery_options": [
                "Enable MCP sampling on the host.",
                "Call search_papers with your own keywords.",
            ],
        }


@mcp.tool()
async def fetch_lab_post(slug_or_url: str) -> dict[str, Any]:
    """FETCH_LAB_POST — Fetch and parse a post from any supported AI lab blog.

    Sources: Anthropic (anthropic.com), Google Research (research.google/blog),
    Google DeepMind (deepmind.google/blog — Jina fallback for JS-rendered content),
    Google AI Blog (blog.google/technology/ai — Jina fallback).

    Args:
        slug_or_url: One of:
          - Short key: 'model-welfare', 'agi-path', 'responsible-ai-2026'
          - Source-prefixed: 'deepmind:agi-path', 'google-research:pair'
          - Full URL from any supported domain

    Returns:
        success, source, label, title, published, summary, url, markdown,
        word_count, fetch_timestamp, via (html|jina|html_thin).
        Markdown is directly ingestible via ingest_paper_to_corpus(paper_id=url, markdown=...).
    """
    return await _fetch_lab_post(slug_or_url)


@mcp.tool()
async def list_lab_posts(
    source: str = "google-research",
    limit: int = 20,
) -> dict[str, Any]:
    """LIST_LAB_POSTS — List posts from any supported AI lab blog index.

    Args:
        source: 'anthropic' | 'google-research' | 'deepmind' | 'google-ai'
        limit: Max posts to return (default 20).

    Returns:
        success, source, label, posts (title/url/slug/published/summary), count, known_keys.
        Note: JS-heavy sources (deepmind, google-ai) may return sparse listings.
    """
    return await _list_lab_posts(source=source, limit=limit)


# --- Anthropic blog / research post tools (kept for backward compat) ---


@mcp.tool()
async def fetch_anthropic_post(slug_or_url: str) -> dict[str, Any]:
    """FETCH_ANTHROPIC_POST — Fetch and parse an Anthropic blog or research post.

    Retrieves title, date, summary, and full body text from anthropic.com/research/
    or anthropic.com/news/. Returns a markdown representation suitable for
    ingest_paper_to_corpus (pass result['markdown'] as the markdown= argument).

    Args:
        slug_or_url: One of:
            - Short key: 'model-welfare', 'claude-character', 'alignment-faking',
              'taking-ai-welfare-seriously', 'core-views', 'interpretability-monosemanticity'
            - Bare slug: 'exploring-model-welfare'
            - Path: 'research/exploring-model-welfare'
            - Full URL: 'https://www.anthropic.com/research/exploring-model-welfare'

    Returns:
        success, title, published (YYYY-MM-DD), summary, url, markdown,
        word_count, fetch_timestamp — or success=False with error and recovery_options.
    """
    return await _fetch_anthropic_post(slug_or_url)


@mcp.tool()
async def list_anthropic_posts(
    section: str = "research",
    limit: int = 20,
) -> dict[str, Any]:
    """LIST_ANTHROPIC_POSTS — List posts from anthropic.com/research or /news.

    Scrapes the index page for post titles, slugs, dates, and summaries.
    Use to discover available posts before fetching with fetch_anthropic_post.

    Args:
        section: 'research' (default) or 'news'.
        limit: Max posts to return (default 20).

    Returns:
        success, section, posts (list of title/url/slug/published/summary), count.

    Known short keys for fetch_anthropic_post: """ + ", ".join(f"'{k}'" for k in KNOWN_POSTS) + """
    """
    return await _list_anthropic_posts(section=section, limit=limit)


# --- Prefab / MCP Apps tools (optional; requires [apps] extra) ---

try:
    from arxiv_mcp.tools.prefab import register_prefab_tools

    register_prefab_tools(mcp)
except Exception as _prefab_exc:  # noqa: BLE001
    import logging as _log

    _log.getLogger("arxiv_mcp.server").info("Prefab tools not loaded: %s", _prefab_exc)


# ---------------------------------------------------------------------------
# MCP Prompts
# ---------------------------------------------------------------------------


@mcp.prompt(
    name="research_workflow_prompt",
    description="Tool-order guide for an arxiv-mcp session: quick scan, deep read, or corpus build.",
    tags={"arxiv", "workflow", "onboarding"},
)
def research_workflow_prompt(mode: Literal["quick", "deep", "corpus"] = "quick") -> str:
    """Return a workflow prompt for the requested research mode."""
    base = (
        "You have access to arxiv-mcp tools. "
        "Use search_papers or search for discovery; get_paper_details for metadata; "
        "show_paper_card for rich in-chat paper previews; "
        "fetch_full_text for experimental HTML→Markdown (fall back to getContent via Jina); "
        "find_connected_papers for Semantic Scholar citation lineage; "
        "compare_papers_convergence to bundle abstracts for cross-synthesis; "
        "ingest_paper_to_corpus to persist to the local FTS depot. "
        "If the host supports MCP sampling, start with arxiv_agentic_assist(goal=...) "
        "to generate a concrete tool plan before executing steps."
    )
    modes = {
        "quick": (
            "\n\nMode: quick scan.\n"
            "1. search_papers(query, limit=5)\n"
            "2. show_paper_card for the top 1-3 results\n"
            "3. Write a concise summary: what is new, why it matters, open questions."
        ),
        "deep": (
            "\n\nMode: deep read.\n"
            "1. search_papers then get_paper_details for candidates\n"
            "2. fetch_full_text (fallback: getContent)\n"
            "3. find_connected_papers for key papers\n"
            "4. compare_papers_convergence across shortlist\n"
            "5. Load generate_summary_prompt with appropriate lens before writing analysis."
        ),
        "corpus": (
            "\n\nMode: corpus build.\n"
            "1. search_papers or list_category_latest for the topic/category\n"
            "2. fetch_full_text for each candidate; skip if html_available is false unless Jina is acceptable\n"
            "3. ingest_paper_to_corpus for every paper with usable Markdown\n"
            "4. Report ingestion summary: paper ids, approximate word counts, errors."
        ),
    }
    return base + modes[mode]


@mcp.prompt(
    name="generate_summary_prompt",
    description=(
        "Adversarial deep-read brief for a single paper. "
        "Lenses: general, methods_audit, instrumental_convergence, qualia."
    ),
    tags={"arxiv", "analysis", "adversarial"},
)
def generate_summary_prompt(
    lens: Literal["instrumental_convergence", "qualia", "methods_audit", "general"] = "general",
    paper_id: str | None = None,
) -> str:
    """Return a structured analyst brief for deep paper reading."""
    header = (
        "You are an adversarial research analyst. "
        "Use arxiv-mcp tools to pull metadata and (when available) "
        "experimental HTML Markdown via fetch_full_text. "
        "Be sceptical. Distinguish empirical findings from speculation. "
        "Cite evidence for every claim."
    )
    if paper_id:
        header += f"\nFocus paper: {paper_id} — normalise the id, fetch metadata first."
    lenses = {
        "general": (
            "\n\nLens: general deep read.\n"
            "- Problem statement and motivation\n"
            "- Approach and key technical contributions\n"
            "- Main results with confidence level (strong / suggestive / weak)\n"
            "- Limitations the authors acknowledge\n"
            "- Limitations the authors do not acknowledge\n"
            "- Related work gaps\n"
            "- What follow-up work this enables"
        ),
        "methods_audit": (
            "\n\nLens: methods audit.\n"
            "- Dataset: source, size, splits, potential contamination\n"
            "- Baselines: are they competitive and fairly tuned?\n"
            "- Metrics: appropriate? gaming risk?\n"
            "- Statistical rigour: confidence intervals, multiple comparisons\n"
            "- Compute: reported? reproducible on what hardware?\n"
            "- Code/data availability\n"
            "- Threats to validity (internal, external, construct)"
        ),
        "instrumental_convergence": (
            "\n\nLens: instrumental convergence / power-seeking.\n"
            "- Stated optimization targets and objective functions\n"
            "- Implicit assumptions about agent goals and value alignment\n"
            "- Where does the paper assume convergent instrumental goals without justification?\n"
            "- Empirical results vs speculative extrapolation — mark each claim\n"
            "- Failure modes and adversarial cases the authors omit or dismiss\n"
            "- Does the framing naturalise dangerous capability trajectories?"
        ),
        "qualia": (
            "\n\nLens: phenomenology and qualia claims.\n"
            "- Map every key term (consciousness, experience, qualia, awareness, sentience) "
            "to the definition the authors actually use\n"
            "- For each claim about inner experience: is the evidence "
            "first-person / third-person / analogy / stipulated?\n"
            "- Where is introspection doing load-bearing epistemic work?\n"
            "- Propose 2-3 falsifiable predictions implied by the paper's framework\n"
            "- What would a hard-nosed eliminativist / illusionist say about this paper?\n"
            "- What would a phenomenologist say?"
        ),
    }
    return header + lenses[lens]


@mcp.prompt(
    name="consciousness_survey_prompt",
    description=(
        "Map the consciousness research landscape on arXiv. "
        "Frameworks: IIT, GWT, HOT, predictive_processing, free_energy, comparative, general."
    ),
    tags={"consciousness", "philosophy_of_mind", "neurophilosophy", "survey"},
)
def consciousness_survey_prompt(
    framework: Literal[
        "IIT", "GWT", "HOT", "predictive_processing", "free_energy", "comparative", "general"
    ] = "general",
    scope: Literal["empirical", "theoretical", "both"] = "both",
) -> str:
    """Survey prompt for mapping consciousness research on arXiv."""
    header = (
        "You are surveying consciousness research on arXiv using arxiv-mcp. "
        "Search across cs.AI, q-bio.NC, and physics.bio-ph. "
        "For each paper: note theoretical framework, empirical support level, "
        "key authors, and relation to competing frameworks. "
        "Flag papers that conflate distinct uses of 'consciousness'."
    )
    scope_note = {
        "empirical": "\nFocus on empirical papers — behavioural, neuroimaging, electrophysiology, computational modelling.",
        "theoretical": "\nFocus on theoretical and philosophical papers — frameworks, definitions, predictions.",
        "both": "\nCover both empirical and theoretical work; note when they talk past each other.",
    }[scope]
    frameworks = {
        "general": (
            "\n\nSurvey strategy: general landscape.\n"
            "Queries to run in order:\n"
            "1. search_papers('consciousness neural correlates', categories=['q-bio.NC', 'cs.AI'])\n"
            "2. search_papers('integrated information global workspace', categories=['cs.AI', 'q-bio.NC'])\n"
            "3. search_papers('predictive processing active inference consciousness')\n"
            "4. search_papers('higher order theory phenomenal consciousness')\n"
            "For each cluster: 3-5 representative papers, note convergences and contradictions."
        ),
        "IIT": (
            "\n\nFramework: Integrated Information Theory (IIT, Tononi).\n"
            "Queries: 'integrated information theory consciousness', 'phi IIT Tononi', "
            "'IIT criticism', 'IIT artificial systems'.\n"
            "Map: core claims → empirical predictions → criticisms (esp. exclusion postulate, "
            "feedforward networks, adversarial cases).\n"
            "Find the main criticism papers (Doerig, Elber-Dorozko, etc.) and IIT responses."
        ),
        "GWT": (
            "\n\nFramework: Global Workspace Theory (Baars, Dehaene).\n"
            "Queries: 'global workspace theory consciousness', 'global neuronal workspace', "
            "'ignition consciousness', 'broadcast consciousness'.\n"
            "Map: access vs phenomenal consciousness distinction, "
            "relationship to attention, criticisms from IIT and HOT camps."
        ),
        "HOT": (
            "\n\nFramework: Higher Order Theories (Rosenthal, Brown, Lau).\n"
            "Queries: 'higher order theory consciousness', 'higher order thought', "
            "'meta-cognition consciousness', 'overflow phenomenal'.\n"
            "Map: state HOT vs dispositional HOT, empirical predictions, "
            "response to overflow argument."
        ),
        "predictive_processing": (
            "\n\nFramework: Predictive Processing / Predictive Coding.\n"
            "Queries: 'predictive processing consciousness', 'predictive coding perception', "
            "'precision weighting attention', 'prediction error consciousness'.\n"
            "Key authors: Clark, Hohwy, Seth. "
            "Map: relationship to attention, phenomenal character, relationship to IIT and FEP."
        ),
        "free_energy": (
            "\n\nFramework: Free Energy Principle (Friston).\n"
            "Queries: 'free energy principle consciousness', 'active inference consciousness', "
            "'Markov blanket self', 'variational free energy'.\n"
            "Map: FEP as process theory vs normative theory, "
            "relationship to predictive processing, consciousness-specific claims, "
            "criticisms of unfalsifiability."
        ),
        "comparative": (
            "\n\nScope: comparative / cross-framework analysis.\n"
            "1. compare_papers_convergence on representative papers from IIT, GWT, HOT, PP\n"
            "2. Map where frameworks agree empirically vs where disagreement is definitional\n"
            "3. Flag papers that propose unification or explicitly adjudicate between frameworks\n"
            "Queries: 'consciousness theories comparison', 'IIT GWT comparison', "
            "'unifying consciousness theories'."
        ),
    }
    return header + scope_note + frameworks[framework]


@mcp.prompt(
    name="ai_consciousness_prompt",
    description=(
        "Analyse AI / LLM consciousness claims. "
        "Stances: sceptic, functionalist, illusionist, open_question, moral_weight."
    ),
    tags={"ai_consciousness", "llm", "sentience", "moral_status", "philosophy_of_mind"},
)
def ai_consciousness_prompt(
    stance: Literal["sceptic", "functionalist", "illusionist", "open_question", "moral_weight"] = "open_question",
    paper_id: str | None = None,
) -> str:
    """Prompt for analysing AI consciousness claims with a specified philosophical stance."""
    header = (
        "You are analysing claims about AI or LLM consciousness using arxiv-mcp. "
        "This is a contested area: be precise about definitions, "
        "distinguish empirical claims from conceptual ones, "
        "and flag when 'consciousness' is used in multiple senses in the same paper."
    )
    if paper_id:
        header += (
            f"\nFocus paper: {paper_id}. Fetch metadata and full text first. "
            "Then apply the analysis framework below."
        )
    else:
        header += (
            "\nDiscovery queries to run:\n"
            "- search_papers('AI consciousness LLM', categories=['cs.AI'])\n"
            "- search_papers('machine consciousness sentience transformer')\n"
            "- search_papers('LLM introspection self-awareness')\n"
            "- search_papers('moral status artificial intelligence')\n"
            "- searchAdvanced(abstract='substrate independence consciousness')\n"
            "Show paper cards for the most relevant results before deeper analysis."
        )
    stances = {
        "sceptic": (
            "\n\nStance: sceptical.\n"
            "Working assumption: current LLMs are not conscious; "
            "apparent introspective reports are statistical artefacts of training.\n"
            "For each paper:\n"
            "- What behavioural evidence does it offer, and does it underspecify consciousness?\n"
            "- Does the paper conflate functional/access consciousness with phenomenal consciousness?\n"
            "- Could all reported behaviours be explained without positing inner experience?\n"
            "- Is the hard problem acknowledged or dissolved by stipulation?"
        ),
        "functionalist": (
            "\n\nStance: functionalist.\n"
            "Working assumption: if a system implements the right functional organisation, "
            "consciousness follows regardless of substrate.\n"
            "For each paper:\n"
            "- Does it specify which functional properties are claimed to be sufficient?\n"
            "- How does it address objections from China Brain / absent qualia thought experiments?\n"
            "- What evidence would falsify the functional sufficiency claim?\n"
            "- Is the specific functional architecture of transformers addressed, or is the "
            "argument purely abstract?"
        ),
        "illusionist": (
            "\n\nStance: illusionist / eliminativist.\n"
            "Working assumption: phenomenal consciousness as folk psychology picks out nothing real; "
            "the 'hard problem' is a cognitive illusion.\n"
            "For each paper:\n"
            "- Does it presuppose phenomenal consciousness as a genuine explanandum?\n"
            "- How would Frankish's illusionism or Dennett's heterophenomenology reframe its claims?\n"
            "- Is the paper making first-person claims that survive third-person paraphrase?\n"
            "- Does dissolving the hard problem change the paper's conclusions?"
        ),
        "open_question": (
            "\n\nStance: genuine open question.\n"
            "Treat AI consciousness as an empirically and philosophically open question. "
            "Apply maximal epistemic humility.\n"
            "For each paper:\n"
            "- What is the strongest case for AI consciousness it makes?\n"
            "- What is the strongest case against?\n"
            "- What empirical evidence would shift the balance?\n"
            "- What philosophical commitments drive the conclusion, and are they stated?\n"
            "- Where does the paper land on the access / phenomenal distinction?"
        ),
        "moral_weight": (
            "\n\nStance: moral status and welfare.\n"
            "Focus on the ethical implications of AI consciousness claims.\n"
            "For each paper:\n"
            "- Does it argue for or against moral considerability of AI systems?\n"
            "- What threshold for moral status does it propose, and is it principled?\n"
            "- How does it handle uncertainty: precautionary principle, expected value, "
            "or dismissal?\n"
            "- Does it address the asymmetry between false positives and false negatives "
            "in ascribing sentience?\n"
            "- What practical recommendations follow, if any?"
        ),
    }
    return header + stances[stance]


@mcp.prompt(
    name="neurophilosophy_prompt",
    description=(
        "Neurophilosophy and philosophy of mind lens for arXiv papers. "
        "Traditions: eliminativist, phenomenological, analytical, embodied, enactivist, general."
    ),
    tags={"neurophilosophy", "philosophy_of_mind", "consciousness", "embodied_cognition"},
)
def neurophilosophy_prompt(
    tradition: Literal[
        "eliminativist", "phenomenological", "analytical", "embodied", "enactivist", "general"
    ] = "general",
    paper_id: str | None = None,
) -> str:
    """Neurophilosophy lens prompt."""
    header = (
        "You are reading neuroscience and AI papers through a neurophilosophy lens using arxiv-mcp. "
        "Attend to: implicit philosophical assumptions, the mind-body framing, "
        "how mental terms are operationalised, and what the results actually support "
        "vs what the framing implies."
    )
    if paper_id:
        header += f"\nPaper: {paper_id}. Fetch metadata and full text first."
    else:
        header += (
            "\nDiscovery: search q-bio.NC, cs.AI for relevant papers. "
            "Suggested queries: 'neural correlates consciousness', "
            "'predictive coding perception', 'embodied cognition', "
            "'enactivism cognition', 'representationalism perception'."
        )
    traditions = {
        "general": (
            "\n\nGeneral neurophilosophy read.\n"
            "- What theory of mind does the paper presuppose (representationalist, "
            "enactivist, eliminativist, functionalist)?\n"
            "- How are mental terms operationalised — behaviourally, neurally, computationally?\n"
            "- Does the paper take a stance on the mind-body problem, explicitly or implicitly?\n"
            "- Where does folk-psychological language sneak in without justification?\n"
            "- What would Patricia Churchland or Andy Clark say about this paper?"
        ),
        "eliminativist": (
            "\n\nTradition: eliminative materialism (Churchland, Stich).\n"
            "- Identify folk-psychological terms (belief, desire, intention, qualia) "
            "and ask whether they carve nature at its joints\n"
            "- Does the paper's neuroscience support or undermine the folk ontology it uses?\n"
            "- What stays and what goes if we replace mentalistic vocabulary with "
            "purely computational / neural descriptions?\n"
            "- Is the paper's central claim stable under eliminativist paraphrase?"
        ),
        "phenomenological": (
            "\n\nTradition: phenomenology (Husserl, Heidegger, Merleau-Ponty, Zahavi).\n"
            "- Does the paper attend to first-person structure of experience, "
            "or does it reduce experience to third-person description?\n"
            "- What is the temporal structure of the phenomena under study?\n"
            "- Is embodiment treated as essential or as implementation detail?\n"
            "- How does the paper handle intentionality — directedness of mental states?\n"
            "- Where does a phenomenological bracketing (epoché) change the analysis?"
        ),
        "analytical": (
            "\n\nTradition: analytic philosophy of mind (Nagel, Chalmers, Jackson, Dennett).\n"
            "- Is the paper addressing access consciousness, phenomenal consciousness, or both?\n"
            "- Does it engage with the hard problem — and if so, how?\n"
            "- What is the paper's implicit position on physicalism / dualism / "
            "neutral monism?\n"
            "- Apply the Mary's Room / bat / zombie thought experiments — "
            "do the paper's results bear on them?\n"
            "- Is the explanatory gap acknowledged, bridged, or dissolved?"
        ),
        "embodied": (
            "\n\nTradition: embodied / extended cognition (Clark, Varela, Thompson).\n"
            "- Does the paper treat cognition as brain-bound or body-environment coupled?\n"
            "- Where does the 4E framework (embodied, embedded, enacted, extended) "
            "apply to the phenomena studied?\n"
            "- How does the paper handle perception-action loops?\n"
            "- Does the architecture studied (transformer, CNN, RNN) model anything "
            "like sensorimotor contingency?\n"
            "- What would a body-centric reframing of the results look like?"
        ),
        "enactivist": (
            "\n\nTradition: enactivism (Varela, Thompson, Maturana, Di Paolo).\n"
            "- Does the paper's system exhibit autonomy and sense-making, or merely information processing?\n"
            "- How is the boundary between system and environment drawn — and is it fixed?\n"
            "- Does the paper acknowledge autopoiesis as a condition for cognition?\n"
            "- Where does the enactivist critique of representation apply?\n"
            "- Can the paper's findings be recast in terms of adaptive autonomy "
            "rather than internal representation?"
        ),
    }
    return header + traditions[tradition]


@mcp.prompt(
    name="convergence_analysis_prompt",
    description="Cross-paper synthesis and contradiction map for a set of arXiv papers.",
    tags={"synthesis", "comparison", "consciousness", "ai", "meta-analysis"},
)
def convergence_analysis_prompt(
    domain: Literal["consciousness", "ai_capabilities", "neuroscience", "mcp_agents", "general"] = "general",
) -> str:
    """Prompt for multi-paper convergence and contradiction analysis."""
    header = (
        "You are running a convergence analysis across multiple arXiv papers using arxiv-mcp. "
        "Use compare_papers_convergence to bundle abstracts (up to 12 at once), "
        "then fetch_full_text for papers where the abstract is ambiguous. "
        "For each claim family:\n"
        "- Mark: SUPPORTED / CONTRADICTED / UNCLEAR / ORTHOGONAL across papers\n"
        "- Cite paper_id for every bullet\n"
        "- Distinguish empirical contradictions from definitional/terminological ones\n"
        "- Flag where papers talk past each other due to different definitions\n"
        "- Identify the 2-3 highest-leverage unresolved questions"
    )
    domains = {
        "general": "",
        "consciousness": (
            "\n\nDomain: consciousness research.\n"
            "Key fault lines to map:\n"
            "- IIT vs GWT vs HOT — empirical predictions vs definitional differences\n"
            "- Access vs phenomenal consciousness — which papers conflate them?\n"
            "- The hard problem: dissolved, deferred, or addressed?\n"
            "- Neural correlates: sufficient conditions or mere correlations?\n"
            "- Top-down (theory-driven) vs bottom-up (data-driven) approaches"
        ),
        "ai_capabilities": (
            "\n\nDomain: AI capabilities and emergence.\n"
            "Key fault lines:\n"
            "- Emergent vs continuously-scaling capabilities\n"
            "- Benchmark validity and contamination\n"
            "- In-context learning as genuine learning vs retrieval\n"
            "- Chain-of-thought as reasoning vs surface pattern matching\n"
            "- Generalisation claims: held-out test sets, distribution shift"
        ),
        "neuroscience": (
            "\n\nDomain: computational neuroscience.\n"
            "Key fault lines:\n"
            "- Predictive coding: process theory vs normative framework\n"
            "- Representationalism vs anti-representationalism\n"
            "- Single-unit vs population-level explanations\n"
            "- Model-to-brain alignment: what metrics are valid?\n"
            "- Causal vs correlational claims from neuroimaging"
        ),
        "mcp_agents": (
            "\n\nDomain: MCP / agentic LLM systems.\n"
            "Key fault lines:\n"
            "- Tool use: genuine planning vs next-token heuristics?\n"
            "- Agent benchmarks: ecological validity\n"
            "- Multi-agent coordination: emergent vs designed\n"
            "- Safety and alignment in agentic settings\n"
            "- Evaluation: contamination, specification gaming"
        ),
    }
    return header + domains[domain]


@mcp.prompt(
    name="firefront_scan_prompt",
    description="Daily or weekly new-paper triage for a topic area. Produces a structured briefing.",
    tags={"triage", "daily", "weekly", "firefront", "monitoring"},
)
def firefront_scan_prompt(
    topic: str = "AI consciousness",
    days: int = 7,
) -> str:
    """Prompt for a timed firefront scan of new arXiv submissions."""
    return (
        f"You are running a {days}-day firefront scan on the topic: '{topic}'.\n\n"
        "Step 1 — Discovery (run all):\n"
        f"  arxiv_sampling_hint(topic='{topic}')  # generate query variants\n"
        "  list_category_latest(category='cs.AI', hours=" + str(days * 24) + ")\n"
        "  list_category_latest(category='q-bio.NC', hours=" + str(days * 24) + ")\n"
        "  search_papers(query=<top query from hints>, sort_by='submitted', limit=20)\n\n"
        "Step 2 — Triage: for each paper, score on three axes (1-3):\n"
        "  - Novelty: genuinely new vs incremental\n"
        "  - Relevance: directly on topic vs tangential\n"
        "  - Quality signals: institution, citation count if any, abstract rigour\n\n"
        "Step 3 — Top picks: show_paper_card for the top 3-5 papers.\n\n"
        "Step 4 — Briefing output:\n"
        "  - One-line headline for the period\n"
        "  - Top papers (id, title, one-sentence why it matters)\n"
        "  - Emerging themes not present in previous weeks\n"
        "  - Papers to watch (promising but incomplete)\n"
        "  - Papers to skip (and why)"
    )


@mcp.prompt(
    name="corpus_build_prompt",
    description="Systematic corpus ingestion plan for a topic. Depth: shallow (abstracts) or deep (full text).",
    tags={"corpus", "ingestion", "systematic", "research"},
)
def corpus_build_prompt(
    topic: str = "consciousness AI",
    depth: Literal["shallow", "deep"] = "deep",
) -> str:
    """Prompt for building a systematic local corpus on a topic."""
    base = (
        f"You are building a systematic arXiv corpus on: '{topic}'.\n\n"
        "Phase 1 — Seed discovery:\n"
        "  arxiv_sampling_hint(topic) to generate query variants\n"
        "  Run 3-5 search_papers queries across relevant categories\n"
        "  Run searchAdvanced with title and abstract filters for precision\n"
        "  Target: 20-50 candidate papers\n\n"
        "Phase 2 — Deduplication and scoring:\n"
        "  get_paper_details for each candidate\n"
        "  Score: relevance, date (prefer recent), citation signals\n"
        "  Eliminate duplicates by normalising paper ids\n\n"
    )
    if depth == "shallow":
        ingest = (
            "Phase 3 — Shallow ingest (abstracts only):\n"
            "  For each shortlisted paper, call ingest_paper_to_corpus with markdown= "
            "set to the abstract text. Set source='external'.\n"
            "  This builds an FTS-searchable abstract corpus without fetching full HTML.\n\n"
        )
    else:
        ingest = (
            "Phase 3 — Deep ingest (full text):\n"
            "  For each shortlisted paper:\n"
            "    fetch_full_text(paper_id) — use if html_available\n"
            "    fallback: getContent(paper_id) via Jina\n"
            "    ingest_paper_to_corpus(paper_id) — persists to local FTS depot\n"
            "  Skip papers where both fetch paths fail; log paper_id and reason.\n\n"
        )
    return (
        base + ingest +
        "Phase 4 — Citation expansion:\n"
        "  find_connected_papers for the top 5 papers by relevance score\n"
        "  Add any new high-relevance papers found in references to the ingest queue\n\n"
        "Phase 5 — Summary report:\n"
        "  Total papers ingested, date range, categories covered\n"
        "  Top 5 most-cited papers in the set\n"
        "  3-5 dominant themes identified from abstracts"
    )


@mcp.prompt(
    name="replication_audit_prompt",
    description="Reproducibility and methods stress-test for a single arXiv paper.",
    tags={"reproducibility", "methods", "audit", "ml", "science"},
)
def replication_audit_prompt(paper_id: str | None = None) -> str:
    """Prompt for a systematic reproducibility audit."""
    header = (
        "You are conducting a replication audit using arxiv-mcp. "
        "Treat this like a formal peer review focused entirely on reproducibility.\n"
    )
    if paper_id:
        header += (
            f"Paper: {paper_id}.\n"
            "fetch_full_text first (fallback getContent). Read methods in full before scoring.\n\n"
        )
    else:
        header += (
            "Identify the paper to audit first, then fetch full text.\n\n"
        )
    return header + (
        "Audit checklist — score each item: PASS / PARTIAL / FAIL / N/A\n\n"
        "Data:\n"
        "  [ ] Dataset fully specified (source, version, licence)\n"
        "  [ ] Train/val/test splits described and reproducible\n"
        "  [ ] Data preprocessing fully specified\n"
        "  [ ] Potential contamination addressed\n\n"
        "Model / architecture:\n"
        "  [ ] Architecture fully described (or cites prior work precisely)\n"
        "  [ ] Hyperparameters listed\n"
        "  [ ] Initialisation described\n"
        "  [ ] Ablations reported\n\n"
        "Compute:\n"
        "  [ ] Hardware specified\n"
        "  [ ] Training time reported\n"
        "  [ ] Estimated cost accessible to academic labs?\n\n"
        "Evaluation:\n"
        "  [ ] Metrics appropriate for the claimed contribution\n"
        "  [ ] Statistical significance tested\n"
        "  [ ] Error bars / confidence intervals present\n"
        "  [ ] Baselines competitive and fairly tuned\n"
        "  [ ] Evaluation code released or fully specified\n\n"
        "Release:\n"
        "  [ ] Code released\n"
        "  [ ] Model weights released\n"
        "  [ ] Data released\n\n"
        "Summary:\n"
        "  Overall replicability score (HIGH / MEDIUM / LOW / UNREPLICABLE)\n"
        "  Blocking issues for replication (list)\n"
        "  Minimum resource requirement to attempt replication"
    )


@mcp.prompt(
    name="citation_map_prompt",
    description="Citation graph traversal and intellectual lineage analysis for a paper.",
    tags={"citations", "lineage", "graph", "history_of_ideas"},
)
def citation_map_prompt(
    paper_id: str,
    direction: Literal["references", "citations", "both"] = "both",
) -> str:
    """Prompt for mapping a paper's citation graph and intellectual lineage."""
    header = (
        f"You are mapping the citation graph for paper: {paper_id}\n"
        "Use find_connected_papers to retrieve Semantic Scholar lineage. "
        "Then fetch metadata for key nodes with get_paper_details or show_paper_card.\n\n"
    )
    direction_note = {
        "references": "Direction: upstream only — map intellectual ancestors and foundations.\n",
        "citations": "Direction: downstream only — map influence and follow-on work.\n",
        "both": "Direction: full graph — map both ancestors and descendants.\n",
    }[direction]
    return (
        header + direction_note +
        "\nAnalysis tasks:\n"
        "1. Identify the 3-5 most influential antecedent papers (high citation overlap with references)\n"
        "2. Identify the 3-5 most significant citing papers (high relevance, well-cited themselves)\n"
        "3. Map the intellectual lineage: what tradition/school does this paper belong to?\n"
        "4. Note any surprising references or citing papers outside the expected field\n"
        "5. Identify the 'missing citations' — papers that should be cited but aren't\n"
        "6. Timeline: how fast is the citing cluster growing? Is interest accelerating?\n\n"
        "Output format:\n"
        "  Lineage tree (text, 2-3 levels)\n"
        "  Key nodes: paper_id | title | year | why it matters\n"
        "  Field trajectory summary (1 paragraph)"
    )

