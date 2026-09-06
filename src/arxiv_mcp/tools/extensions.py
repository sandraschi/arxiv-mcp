"""Optional MCP tools registered after core server module loads."""

from __future__ import annotations

from typing import Any


def register_extension_tools(mcp) -> None:
    from arxiv_mcp.firefront_service import run_firefront_scan

    @mcp.tool()
    async def run_firefront_scan_tool(
        topic: str,
        categories: list[str] | None = None,
        days: int = 7,
        limit_per_category: int = 25,
        ingest_top_n: int = 0,
    ) -> dict[str, Any]:
        """RUN_FIREFRONT_SCAN - Collect recent arXiv papers and write a digest JSON.

        Scans ``list_category_latest`` across categories (default cs.AI, cs.LG, q-bio.NC),
        deduplicates by paper id, optionally ingests the top N into the depot, and saves
        ``data/arxiv_mcp/firefront/digest_{topic}_{timestamp}.json``. Pair with
        ``firefront_scan_prompt`` for LLM triage of the digest.

        Rate limits on the arXiv API are retried automatically; transient failures return
        structured recovery hints.

        Args:
            topic: Topic label stored in the digest (for your triage workflow).
            categories: arXiv categories to scan; defaults to cs.AI, cs.LG, q-bio.NC.
            days: Rolling window in days (converted to hours for list_category_latest).
            limit_per_category: Max papers per category before dedupe.
            ingest_top_n: If > 0, ingest this many newest papers into the depot (HTML/PDF).
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

    @mcp.tool()
    async def run_codehunt_scan_tool(
        categories: list[str] | None = None,
        days: int = 3,
        limit_per_category: int = 50,
        fulltext_max_papers: int | None = None,
        push: bool = True,
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

        Args:
            categories: arXiv categories to scan; defaults to ARXIV_MCP_CODEHUNT_CATEGORIES.
            days: rolling lookback window in days.
            limit_per_category: max papers per category before dedupe.
            fulltext_max_papers: cap on full-text fetches for promise-without-link papers.
            push: push newly-live drops to aiwatcher (POST /api/fleet/ingest).
        """
        return await run_codehunt_scan(
            categories=categories,
            days=days,
            limit_per_category=limit_per_category,
            fulltext_max_papers=fulltext_max_papers,
            push=push,
        )

    @mcp.tool()
    async def repoll_codehunt_tool(limit: int = 200, push: bool = True) -> dict[str, Any]:
        """REPOLL_CODEHUNT - Re-check promised repos for liveness and push live drops.

        Iterates findings with status 'promised' that carry candidate repo URLs and
        re-checks each for liveness. When a repo resolves, the finding flips to
        'code_live' and (respecting the china-only-push setting) is pushed to
        aiwatcher as a high-urgency fleet event. Run on a 12h cadence to catch drops
        the hour weights go public.

        Args:
            limit: max promised findings to re-check this pass.
            push: push newly-live drops to aiwatcher.
        """
        return await repoll_pending(limit=limit, push=push)

    @mcp.tool()
    async def codehunt_stats_tool() -> dict[str, Any]:
        """CODEHUNT_STATS - Tracking DB summary: totals by status, China count, recent live drops."""
        return codehunt_stats()

    @mcp.tool()
    async def check_codehunt_media_tool(limit: int = 40, push: bool = True) -> dict[str, Any]:
        """CHECK_CODEHUNT_MEDIA - Probe HN + Google News + tech RSS ~1 week after arXiv pub.

        Checks tracked papers (tier affiliations, watch authors, China signal, or live code)
        for tech/MSM coverage. Pushes ``[media-traction]`` fleet events to aiwatcher when hits
        are found. Run daily (see install_codehunt_tasks.ps1).

        Args:
            limit: max findings to probe per pass.
            push: POST new media traction to aiwatcher fleet ingest.
        """
        return await check_media_traction(limit=limit, push=push)

    from arxiv_mcp.pipeline_liveness_service import check_pipeline_liveness

    @mcp.tool()
    async def pipeline_liveness_tool(stale_hours: int = 48) -> dict[str, Any]:
        """PIPELINE_LIVENESS - Alert when code-hunt digests are stale or aiwatcher push target is down."""
        return await check_pipeline_liveness(stale_hours=stale_hours)

    from arxiv_mcp.app import _log_buffer

    @mcp.tool(annotations={"readOnly": True}, version="0.1.0")
    async def query_logs(
        source: str | None = None,
        level: str | None = None,
        search: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Query the in-memory log ring buffer for recent log entries.

        Filter by source (logger name), level (info, warn, error, debug),
        or free-text search in the message body.

        Returns: dict with filtered log entries, count, total_matching.
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

    @mcp.tool()
    async def arxiv_help(topic: str | None = None) -> dict[str, Any]:
        """ARXIV_HELP - Documentation for code-hunt, watch authors, fleet/API keys, and tools.

        Call with no topic for the index. Use topic=codehunt, watch_authors, fleet, api_keys,
        pipeline_liveness, mcp, or install. Returns markdown agents can read in-chat.

        Args:
            topic: Help section id, or omit for topic list + overview.
        """
        return get_help(topic)
