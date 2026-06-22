"""Tests for the job-based deep epistemic analysis (services.epistemic_jobs).

All tests stub depot_service.deep_analyze_paper_epistemics — no network, no LLM.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

import arxiv_mcp.depot_service as depot
from arxiv_mcp.services.epistemic_jobs import EpistemicJobManager


@pytest.fixture
def mgr(tmp_path: Path) -> EpistemicJobManager:
    return EpistemicJobManager(tmp_path / "jobs.sqlite3")


@pytest.fixture
def patch_deep(monkeypatch):
    """Return a setter that swaps the deep-analysis coroutine."""

    def _set(fn):
        monkeypatch.setattr(depot, "deep_analyze_paper_epistemics", fn)

    return _set


@pytest.fixture
def sampling_env(monkeypatch):
    monkeypatch.setenv("ARXIV_MCP_SAMPLING_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("ARXIV_MCP_EPISTEMIC_DEEP_ENABLED", "true")


async def _wait_for(mgr: EpistemicJobManager, job_id: str, target: set[str], timeout: float = 5.0) -> dict:
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        st = await mgr.status(job_id)
        if st.get("status") in target:
            return st
        if asyncio.get_event_loop().time() > deadline:
            raise AssertionError(f"job never reached {target}: {st}")
        await asyncio.sleep(0.05)


async def test_submit_completes_and_returns_result(mgr, patch_deep, sampling_env):
    async def fake(paper_id, *, ingest_if_missing, force_refresh, sample_fn):
        assert sample_fn is None  # background = HTTP path only
        await asyncio.sleep(0.1)
        return {"success": True, "arxiv_id": paper_id, "epistemic_profile": {"analyzer": "stub", "claims": []}}

    patch_deep(fake)
    sub = await mgr.submit("9999.00001")
    assert sub["success"] and sub["status"] == "queued"
    st = await _wait_for(mgr, sub["job_id"], {"complete", "failed"})
    assert st["status"] == "complete"
    assert st["result"]["epistemic_profile"]["analyzer"] == "stub"


async def test_failed_job_persists_error(mgr, patch_deep, sampling_env):
    async def fake(paper_id, **kw):
        return {"success": False, "error": "boom"}

    patch_deep(fake)
    sub = await mgr.submit("9999.00002")
    st = await _wait_for(mgr, sub["job_id"], {"failed"})
    assert st["error"] == "boom"


async def test_exception_in_job_marks_failed(mgr, patch_deep, sampling_env):
    async def fake(paper_id, **kw):
        raise RuntimeError("kaput")

    patch_deep(fake)
    sub = await mgr.submit("9999.00003")
    st = await _wait_for(mgr, sub["job_id"], {"failed"})
    assert "kaput" in st["error"]


async def test_cancel_running_job(mgr, patch_deep, sampling_env):
    async def fake(paper_id, **kw):
        await asyncio.sleep(30)
        return {"success": True}

    patch_deep(fake)
    sub = await mgr.submit("9999.00004")
    await asyncio.sleep(0.2)
    res = await mgr.cancel(sub["job_id"])
    assert res["success"]
    st = await _wait_for(mgr, sub["job_id"], {"cancelled"})
    assert st["status"] == "cancelled"


async def test_cancel_finished_job_rejected(mgr, patch_deep, sampling_env):
    async def fake(paper_id, **kw):
        return {"success": True, "arxiv_id": paper_id, "epistemic_profile": {}}

    patch_deep(fake)
    sub = await mgr.submit("9999.00005")
    await _wait_for(mgr, sub["job_id"], {"complete"})
    res = await mgr.cancel(sub["job_id"])
    assert not res["success"] and res["error"] == "not_cancellable"


async def test_submit_without_sampling_endpoint_fails_fast(mgr, monkeypatch):
    monkeypatch.setenv("ARXIV_MCP_SAMPLING_BASE_URL", "")
    monkeypatch.setenv("ARXIV_MCP_EPISTEMIC_DEEP_ENABLED", "true")
    sub = await mgr.submit("9999.00006")
    assert not sub["success"] and sub["error"] == "no_sampling_endpoint"
    assert "recovery_options" in sub


async def test_list_filter_and_invalid_filter(mgr, patch_deep, sampling_env):
    async def fake(paper_id, **kw):
        return {"success": True, "arxiv_id": paper_id, "epistemic_profile": {}}

    patch_deep(fake)
    sub = await mgr.submit("9999.00007")
    await _wait_for(mgr, sub["job_id"], {"complete"})
    ls = await mgr.list_jobs(status="complete")
    assert ls["success"] and ls["count"] == 1
    bad = await mgr.list_jobs(status="bogus")
    assert not bad["success"] and bad["error"] == "invalid_status_filter"


async def test_running_jobs_marked_interrupted_on_restart(mgr, tmp_path):
    await mgr.init()
    await asyncio.to_thread(mgr._insert_sync, "stranded", "9999.00008", True, False)
    await asyncio.to_thread(mgr._set_status_sync, "stranded", "running")
    fresh = EpistemicJobManager(tmp_path / "jobs.sqlite3")
    st = await fresh.status("stranded")
    assert st["status"] == "interrupted"
    assert st.get("recommendations")


async def test_status_unknown_job(mgr):
    st = await mgr.status("nope")
    assert not st["success"] and st["error"] == "job_not_found"
