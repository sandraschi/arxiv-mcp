"""Async job runner for deep epistemic analysis.

The synchronous ``deep_analyze_paper_epistemics`` tool blocks for the full LLM
sampling duration, which exceeds the 4-minute client timeout in Claude Desktop
when the sampling backend is slow. This module provides a job-based alternative
(leanforge-mcp JobManager pattern): submit returns a job_id immediately, the
analysis runs as a background asyncio task in the server process, and a poll
tool reports status/result.

HONESTY CONSTRAINT: background jobs CANNOT use MCP ``ctx.sample`` — the request
context dies when the submit tool returns. Job mode therefore requires
``ARXIV_MCP_SAMPLING_BASE_URL`` (OpenAI-compatible HTTP endpoint, e.g. Ollama).
Submission fails fast with recovery options if no endpoint is configured.

Persistence: stdlib sqlite3 (no aiosqlite dependency) wrapped in
``asyncio.to_thread`` — job rows are tiny, so thread-offloaded sync access is
adequate and keeps the dependency surface unchanged. On first manager init in a
fresh process, any jobs still marked ``running`` are flipped to ``interrupted``
(server crashed or was restarted mid-job).
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from arxiv_mcp.config import Settings, load_settings

log = logging.getLogger(__name__)

JobStatus = Literal["queued", "running", "complete", "failed", "cancelled", "interrupted"]

VALID_STATUSES: tuple[str, ...] = ("queued", "running", "complete", "failed", "cancelled", "interrupted")

SCHEMA = """
CREATE TABLE IF NOT EXISTS epistemic_jobs (
    id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status TEXT NOT NULL,
    ingest_if_missing INTEGER NOT NULL DEFAULT 1,
    force_refresh INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    result_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_epistemic_jobs_status ON epistemic_jobs(status);
CREATE INDEX IF NOT EXISTS idx_epistemic_jobs_paper ON epistemic_jobs(paper_id);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


class EpistemicJobManager:
    """SQLite-backed job store + in-process asyncio task launcher."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False
        self._init_lock = asyncio.Lock()
        # Strong references so background tasks are not garbage-collected.
        self._tasks: dict[str, asyncio.Task[None]] = {}

    # ---------------------------------------------------------------- sync DB

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_sync(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            # Fresh process: anything still 'running' died with the old process.
            conn.execute(
                "UPDATE epistemic_jobs SET status='interrupted', updated_at=? WHERE status='running'",
                (_now(),),
            )
            conn.commit()

    def _insert_sync(self, job_id: str, paper_id: str, ingest_if_missing: bool, force_refresh: bool) -> None:
        now = _now()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO epistemic_jobs
                   (id, paper_id, created_at, updated_at, status, ingest_if_missing, force_refresh)
                   VALUES (?, ?, ?, ?, 'queued', ?, ?)""",
                (job_id, paper_id, now, now, int(ingest_if_missing), int(force_refresh)),
            )
            conn.commit()

    def _set_status_sync(
        self,
        job_id: str,
        status: JobStatus,
        *,
        error: str | None = None,
        result_json: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE epistemic_jobs SET status=?, updated_at=?, error=?, "
                "result_json=COALESCE(?, result_json) WHERE id=?",
                (status, _now(), error, result_json, job_id),
            )
            conn.commit()

    def _get_sync(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM epistemic_jobs WHERE id=?", (job_id,)).fetchone()
            return dict(row) if row is not None else None

    def _list_sync(self, status: str | None, limit: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM epistemic_jobs WHERE status=? ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM epistemic_jobs ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]

    # --------------------------------------------------------------- async API

    async def init(self) -> None:
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            await asyncio.to_thread(self._init_sync)
            self._initialized = True
            log.info("EpistemicJobManager initialised at %s", self.db_path)

    async def submit(
        self,
        paper_id: str,
        *,
        ingest_if_missing: bool = True,
        force_refresh: bool = False,
        settings: Settings | None = None,
    ) -> dict[str, Any]:
        """Create a job row and launch the background task. Returns immediately."""
        await self.init()
        settings = settings or load_settings()

        # Fail fast: background jobs cannot use MCP ctx.sample, so an HTTP
        # sampling endpoint is a hard requirement (Implementation Honesty —
        # never accept a job that is guaranteed to fail later).
        if not settings.epistemic_deep_enabled:
            return {
                "success": False,
                "error": "epistemic_deep_disabled",
                "recommendations": ["Set ARXIV_MCP_EPISTEMIC_DEEP_ENABLED=true."],
            }
        if not (settings.sampling_base_url or "").strip():
            return {
                "success": False,
                "error": "no_sampling_endpoint",
                "detail": (
                    "Job mode runs in the background and cannot use MCP ctx.sample "
                    "(the request context ends when submit returns)."
                ),
                "recovery_options": [
                    "Set ARXIV_MCP_SAMPLING_BASE_URL to an OpenAI-compatible endpoint "
                    "(e.g. Ollama: http://localhost:11434/v1).",
                    "For ctx.sample-based analysis, call deep_analyze_paper_epistemics "
                    "synchronously from a client without a short tool timeout (e.g. Cursor agent).",
                ],
            }

        job_id = str(uuid.uuid4())
        await asyncio.to_thread(self._insert_sync, job_id, paper_id, ingest_if_missing, force_refresh)
        task = asyncio.create_task(self._run_job(job_id, paper_id, ingest_if_missing, force_refresh))
        self._tasks[job_id] = task
        task.add_done_callback(lambda _t, jid=job_id: self._tasks.pop(jid, None))
        log.info("Submitted epistemic job %s for paper %s", job_id, paper_id)
        return {
            "success": True,
            "job_id": job_id,
            "paper_id": paper_id,
            "status": "queued",
            "message": (
                "Deep epistemic analysis running in background. "
                "Poll with epistemic_job(operation='status', job_id=...)."
            ),
        }

    async def _run_job(self, job_id: str, paper_id: str, ingest_if_missing: bool, force_refresh: bool) -> None:
        # Import here to avoid a circular import (depot_service imports services.*).
        from arxiv_mcp.depot_service import deep_analyze_paper_epistemics

        await asyncio.to_thread(self._set_status_sync, job_id, "running")
        try:
            result = await deep_analyze_paper_epistemics(
                paper_id,
                ingest_if_missing=ingest_if_missing,
                force_refresh=force_refresh,
                sample_fn=None,  # background = HTTP sampling path only
            )
        except asyncio.CancelledError:
            await asyncio.to_thread(self._set_status_sync, job_id, "cancelled", error="cancelled by user")
            raise
        except Exception as exc:  # job boundary: persist any failure
            log.exception("Epistemic job %s crashed", job_id)
            await asyncio.to_thread(self._set_status_sync, job_id, "failed", error=f"{type(exc).__name__}: {exc}")
            return

        result_json = json.dumps(result, ensure_ascii=False)
        if result.get("success"):
            await asyncio.to_thread(self._set_status_sync, job_id, "complete", result_json=result_json)
            log.info("Epistemic job %s COMPLETE (paper %s)", job_id, paper_id)
        else:
            await asyncio.to_thread(
                self._set_status_sync,
                job_id,
                "failed",
                error=str(result.get("error", "unknown")),
                result_json=result_json,
            )
            log.info("Epistemic job %s FAILED: %s", job_id, result.get("error"))

    async def status(self, job_id: str) -> dict[str, Any]:
        await self.init()
        row = await asyncio.to_thread(self._get_sync, job_id)
        if row is None:
            return {"success": False, "error": "job_not_found", "job_id": job_id}
        out: dict[str, Any] = {
            "success": True,
            "job_id": row["id"],
            "paper_id": row["paper_id"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "error": row["error"],
        }
        if row["status"] == "complete" and row["result_json"]:
            try:
                out["result"] = json.loads(row["result_json"])
            except json.JSONDecodeError:
                out["result"] = None
                out["error"] = "result_json_corrupt"
        elif row["status"] == "interrupted":
            out["recommendations"] = ["Server restarted mid-job. Re-submit the job."]
        return out

    async def list_jobs(self, status: str | None = None, limit: int = 20) -> dict[str, Any]:
        await self.init()
        if status is not None and status not in VALID_STATUSES:
            return {
                "success": False,
                "error": "invalid_status_filter",
                "valid_statuses": list(VALID_STATUSES),
            }
        rows = await asyncio.to_thread(self._list_sync, status, max(1, min(limit, 100)))
        jobs = [
            {
                "job_id": r["id"],
                "paper_id": r["paper_id"],
                "status": r["status"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "error": r["error"],
            }
            for r in rows
        ]
        return {"success": True, "jobs": jobs, "count": len(jobs)}

    async def cancel(self, job_id: str) -> dict[str, Any]:
        await self.init()
        row = await asyncio.to_thread(self._get_sync, job_id)
        if row is None:
            return {"success": False, "error": "job_not_found", "job_id": job_id}
        if row["status"] not in ("queued", "running"):
            return {
                "success": False,
                "error": "not_cancellable",
                "job_id": job_id,
                "status": row["status"],
            }
        task = self._tasks.get(job_id)
        if task is not None and not task.done():
            task.cancel()
        else:
            # Task object gone (shouldn't happen for queued/running in same
            # process) — mark cancelled directly so the row is not stranded.
            await asyncio.to_thread(self._set_status_sync, job_id, "cancelled", error="cancelled by user")
        return {"success": True, "job_id": job_id, "status": "cancelled"}


_manager: EpistemicJobManager | None = None


def get_job_manager(settings: Settings | None = None) -> EpistemicJobManager:
    """Lazy process-wide singleton."""
    global _manager
    if _manager is None:
        settings = settings or load_settings()
        _manager = EpistemicJobManager(settings.resolved_data_dir() / "epistemic_jobs.sqlite3")
    return _manager
