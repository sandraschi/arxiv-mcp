"""Firefront scan: discover recent papers and optional depot ingest + digest file."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from arxiv_mcp.config import Settings, load_settings
from arxiv_mcp.depot_service import ingest_paper_with_fallback
from arxiv_mcp.services import papers


async def run_firefront_scan(
    topic: str,
    *,
    categories: list[str] | None = None,
    days: int = 7,
    limit_per_category: int = 25,
    ingest_top_n: int = 0,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Collect recent arXiv papers per category, dedupe, optionally ingest, write digest JSON."""
    settings = settings or load_settings()
    cats = [c.strip() for c in (categories or ["cs.AI", "cs.LG", "q-bio.NC"]) if c.strip()]
    hours = max(1, int(days)) * 24
    limit_per_category = min(max(limit_per_category, 1), 100)

    seen: set[str] = set()
    collected: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for cat in cats:
        try:
            rows = await papers.list_category_latest(
                cat, limit=limit_per_category, hours=hours, settings=settings
            )
        except Exception as exc:
            errors.append({"category": cat, "error": str(exc), "error_type": type(exc).__name__})
            continue
        for p in rows:
            d = papers.paper_summary_to_dict(p)
            pid = d["paper_id"]
            if pid in seen:
                continue
            seen.add(pid)
            collected.append(
                {
                    "paper_id": pid,
                    "title": d["title"],
                    "categories": d["categories"],
                    "published": d["published"],
                    "abs_url": d["abs_url"],
                    "source_category_scan": cat,
                }
            )

    collected.sort(key=lambda x: x.get("published") or "", reverse=True)

    ingested: list[dict[str, Any]] = []
    if ingest_top_n > 0:
        for item in collected[: ingest_top_n]:
            try:
                rec = await ingest_paper_with_fallback(item["paper_id"], settings=settings)
                ingested.append(
                    {
                        "paper_id": item["paper_id"],
                        "success": rec.get("success", False),
                        "chunks": rec.get("chunks"),
                        "source": rec.get("source"),
                        "error": rec.get("error"),
                    }
                )
            except Exception as exc:
                ingested.append(
                    {
                        "paper_id": item["paper_id"],
                        "success": False,
                        "error": str(exc),
                    }
                )

    digest = {
        "topic": topic,
        "days": days,
        "categories": cats,
        "scanned_at": time.time(),
        "paper_count": len(collected),
        "papers": collected,
        "ingested": ingested,
        "errors": errors,
    }

    digest_dir = settings.resolved_data_dir() / "firefront"
    digest_dir.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time())
    safe_topic = re.sub(r"[^\w.-]+", "_", topic)[:40]
    path = digest_dir / f"digest_{safe_topic}_{stamp}.json"
    path.write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "success": True,
        "message": f"Firefront scan: {len(collected)} unique papers across {len(cats)} categories.",
        "topic": topic,
        "days": days,
        "paper_count": len(collected),
        "digest_path": str(path),
        "papers": collected[:50],
        "ingested": ingested,
        "errors": errors,
        "hint": "Use firefront_scan_prompt for LLM triage briefing on these ids.",
    }
