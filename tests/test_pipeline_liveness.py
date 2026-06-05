"""Tests for pipeline_liveness_service.py."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_stale_digest_alerts(tmp_path, monkeypatch):
    monkeypatch.setenv("ARXIV_MCP_DATA_DIR", str(tmp_path))
    from arxiv_mcp.config import load_settings
    from arxiv_mcp.pipeline_liveness_service import check_pipeline_liveness

    hunt = tmp_path / "codehunt"
    hunt.mkdir(parents=True)
    old = hunt / "digest_codehunt_old.json"
    old.write_text(json.dumps({"ok": True}), encoding="utf-8")
    # Set mtime to 3 days ago
    old_mtime = time.time() - (72 * 3600)
    import os

    os.utime(old, (old_mtime, old_mtime))

    settings = load_settings()
    result = await check_pipeline_liveness(stale_hours=48, settings=settings)
    codes = {a["code"] for a in result["alerts"]}
    assert "CODEHUNT_DIGEST_STALE" in codes
    assert result["healthy"] is False
