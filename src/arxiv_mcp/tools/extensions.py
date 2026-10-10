"""Optional MCP tools registered after core server module loads."""

from __future__ import annotations

from typing import Annotated

from pydantic import Any, Field


def register_extension_tools(mcp) -> None:
    from arxiv_mcp.firefront_service import run_firefront_scan

    @mcp.tool(annotations={"readOnlyHint": False, "idempotentHint": True, "openWorldHint": True})
    async def run_firefront_scan_tool(
        topic: Annotated[str, Field(description="Topic label stored in the digest (for your triage workflow).")],
        categories: Annotated[
            list[str] | None, Field(description="arXiv categories to scan; defaults to cs.AI, cs.LG, q-bio.NC.")
        ] = None,
        days: Annotated[
            int, Field(description="Rolling window in days (converted to hours for list_category_latest).")
        ] = 7,
        limit_per_category: Annotated[int, Field(description="Max papers per category before dedupe.")] = 25,
        ingest_top_n: Annotated[
            int, Field(description="If > 0, ingest this many newest papers into the depot (HTML/PDF).")
        ] = 0,
    ) -> dict[str, Any]:
        """RUN_FIREFRONT_SCAN - Collect recent arXiv papers and write a digest JSON.

            Scans ``list_category_latest`` across categories (default cs.AI, cs.LG, q-bio.NC),
            deduplicates by paper id, optionally ingests the top N into the depot, and saves
            ``data/arxiv_mcp/firefront/digest_{topic}_{timestamp}.json``. Pair with
            ``firefront_scan_prompt`` for LLM triage of the digest.

            Rate limits on the arXiv API are retried automatically; transient failures return
            structured recovery hints.

        ## Return Format
        `{"success": bool, "message": str, "data": {...}}` - success flag with
        a human-readable message plus the payload keys described above.
        Failures carry `success: False` with `error` + `error_type`.

        ## Examples
        `run_firefront_scan_tool(paper_id="2501.00001")` -> `{"success": True, "message": ...}`
        """
        return await run_firefront_scan(
            topic,
            categories=categories,
            days=days,
            limit_per_category=limit_per_category,
            ingest_top_n=ingest_top_n,
        )

    from arxiv_mcp.codehunt_service import (
        check_media_traction,
        codehunt_stats,
        repoll_pending,
        run_codehunt_scan,
    )

    @mcp.tool(annotations={"readOnlyHint": False, "idempotentHint": True, "openWorldHint": True})
    async def run_codehunt_scan_tool(
        categories: Annotated[
            list[str] | None, Field(description="arXiv categories to scan; defaults to ARXIV_MCP_CODEHUNT_CATEGORIES.")
        ] = None,
        days: Annotated[int, Field(description="rolling lookback window in days.")] = 3,
        limit_per_category: Annotated[int, Field(description="max papers per category before dedupe.")] = 50,
        fulltext_max_papers: Annotated[
            int | None, Field(description="cap on full-text fetches for promise-without-link papers.")
        ] = None,
        push: Annotated[bool, Field(description="push newly-live drops to aiwatcher (POST /api/fleet/ingest).")] = True,
    ) -> dict[str, Any]:
        """RUN_CODEHUNT_SCAN - Mine recent arXiv papers for open-weight code/repo drops.

            Scans recent submissions (default cs.AI, cs.RO, cs.SD) and extracts GitHub /
            Gitee / *.github.io / HuggingFace / ModelScope links and "code coming soon"
            promises from abstracts. For abstracts that promise code but show no link, a
            bounded number of papers have their full text fetched to confirm. Each hit is
            tagged with Chinese-lab affiliation, VLA title signals, and watch-list authors
            (``config/codehunt_watch_authors.json``) and persisted to SQLite
            (``data/arxiv_mcp/codehunt/tracking.sqlite3``). New findings get an immediate
            liveness pass; live drops matching push policy are sent to aiwatcher.
            Call ``arxiv_help(topic='codehunt')`` for full documentation.

        ## Return Format
        `{"success": bool, "message": str, "data": {...}}` - success flag with
        a human-readable message plus the payload keys described above.
        Failures carry `success: False` with `error` + `error_type`.

        ## Examples
        `run_codehunt_scan_tool(paper_id="2501.00001")` -> `{"success": True, "message": ...}`
        """
        return await run_codehunt_scan(
            categories=categories,
            days=days,
            limit_per_category=limit_per_category,
            fulltext_max_papers=fulltext_max_papers,
            push=push,
        )

    @mcp.tool(annotations={"readOnlyHint": False, "idempotentHint": True, "openWorldHint": True})
    async def repoll_codehunt_tool(
        limit: Annotated[int, Field(description="max promised findings to re-check this pass.")] = 200,
        push: Annotated[bool, Field(description="push newly-live drops to aiwatcher.")] = True,
    ) -> dict[str, Any]:
        """REPOLL_CODEHUNT - Re-check promised repos for liveness and push live drops.

            Iterates findings with status 'promised' that carry candidate repo URLs and
            re-checks each for liveness. When a repo resolves, the finding flips to
            'code_live' and (respecting the china-only-push setting) is pushed to
            aiwatcher as a high-urgency fleet event. Run on a 12h cadence to catch drops
            the hour weights go public.

        ## Return Format
        `{"success": bool, "message": str, "data": {...}}` - success flag with
        a human-readable message plus the payload keys described above.
        Failures carry `success: False` with `error` + `error_type`.

        ## Examples
        `repoll_codehunt_tool(paper_id="2501.00001")` -> `{"success": True, "message": ...}`
        """
        return await repoll_pending(limit=limit, push=push)

    @mcp.tool(annotations={"readOnlyHint": False, "idempotentHint": True, "openWorldHint": True})
    async def codehunt_stats_tool() -> dict[str, Any]:
        """CODEHUNT_STATS - Tracking DB summary: totals by status, China count, recent live drops.

        ## Return Format
        `{"success": bool, "message": str, "data": {...}}` - success flag with
        a human-readable message plus the payload keys described above.
        Failures carry `success: False` with `error` + `error_type`.

        ## Examples
        `codehunt_stats_tool(paper_id="2501.00001")` -> `{"success": True, "message": ...}`
        """
        return codehunt_stats()

    @mcp.tool(annotations={"readOnlyHint": False, "idempotentHint": True, "openWorldHint": True})
    async def check_codehunt_media_tool(
        limit: Annotated[int, Field(description="max findings to probe per pass.")] = 40,
        push: Annotated[bool, Field(description="POST new media traction to aiwatcher fleet ingest.")] = True,
    ) -> dict[str, Any]:
        """CHECK_CODEHUNT_MEDIA - Probe HN + Google News + tech RSS ~1 week after arXiv pub.

            Checks tracked papers (tier affiliations, watch authors, China signal, or live code)
            for tech/MSM coverage. Pushes ``[media-traction]`` fleet events to aiwatcher when hits
            are found. Run daily (see install_codehunt_tasks.ps1).

        ## Return Format
        `{"success": bool, "message": str, "data": {...}}` - success flag with
        a human-readable message plus the payload keys described above.
        Failures carry `success: False` with `error` + `error_type`.

        ## Examples
        `check_codehunt_media_tool(paper_id="2501.00001")` -> `{"success": True, "message": ...}`
        """
        return await check_media_traction(limit=limit, push=push)

    from arxiv_mcp.pipeline_liveness_service import check_pipeline_liveness

    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
    async def pipeline_liveness_tool(
        stale_hours: Annotated[int, Field(description="stale_hours parameter.")] = 48,
    ) -> dict[str, Any]:
        """PIPELINE_LIVENESS - Alert when code-hunt digests are stale or aiwatcher push target is down.

        ## Return Format
        `{"success": bool, "message": str, "data": {...}}` - success flag with
        a human-readable message plus the payload keys described above.
        Failures carry `success: False` with `error` + `error_type`.

        ## Examples
        `pipeline_liveness_tool(paper_id="2501.00001")` -> `{"success": True, "message": ...}`
        """
        return await check_pipeline_liveness(stale_hours=stale_hours)

    from arxiv_mcp.app import _log_buffer

    @mcp.tool(annotations={"readOnly": True}, version="0.1.0")
    async def query_logs(
        source: Annotated[str | None, Field(description="source parameter.")] = None,
        level: Annotated[str | None, Field(description="level parameter.")] = None,
        search: Annotated[str | None, Field(description="search parameter.")] = None,
        limit: Annotated[int, Field(description="limit parameter.")] = 50,
    ) -> dict[str, Any]:
        """Query the in-memory log ring buffer for recent log entries.

            Filter by source (logger name), level (info, warn, error, debug),
            or free-text search in the message body.

            Returns: dict with filtered log entries, count, total_matching.

        ## Return Format
        `{"success": bool, "message": str, "data": {...}}` - success flag with
        a human-readable message plus the payload keys described above.
        Failures carry `success: False` with `error` + `error_type`.

        ## Examples
        `query_logs(paper_id="2501.00001")` -> `{"success": True, "message": ...}`
        """
        import copy

        items: list[dict] = list(copy.deepcopy(_log_buffer))
        if source:
            src = source.lower()
            items = [i for i in items if src in i.get("source", "").lower() or src in i.get("logger", "").lower()]
        if level:
            items = [i for i in items if i.get("level", "").lower() == level.lower()]
        if search:
            q = search.lower()
            items = [i for i in items if q in i.get("message", "").lower()]

        items.reverse()
        total = len(items)
        page = items[:limit]
        return {"success": True, "logs": page, "count": len(page), "total_matching": total}

    from arxiv_mcp.help_content import get_help

    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
    async def arxiv_help(
        topic: Annotated[str | None, Field(description="Help section id, or omit for topic list + overview.")] = None,
    ) -> dict[str, Any]:
        """ARXIV_HELP - Documentation for code-hunt, watch authors, fleet/API keys, and tools.

            Call with no topic for the index. Use topic=codehunt, watch_authors, fleet, api_keys,
            pipeline_liveness, mcp, or install. Returns markdown agents can read in-chat.

        ## Return Format
        `{"success": bool, "message": str, "data": {...}}` - success flag with
        a human-readable message plus the payload keys described above.
        Failures carry `success: False` with `error` + `error_type`.

        ## Examples
        `arxiv_help(paper_id="2501.00001")` -> `{"success": True, "message": ...}`
        """
        return get_help(topic)
