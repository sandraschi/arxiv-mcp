"""REST tests for code-hunt and pipeline liveness endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture()
def client():
    from arxiv_mcp.app import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


@pytest.mark.asyncio
async def test_pipeline_liveness_route(client: AsyncClient, tmp_path, monkeypatch):
    monkeypatch.setenv("ARXIV_MCP_DATA_DIR", str(tmp_path))
    async with client as c:
        resp = await c.get("/api/pipeline/liveness?stale_hours=48")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "alerts" in data
    assert any(a.get("code") == "CODEHUNT_NEVER_RUN" for a in data["alerts"])


@pytest.mark.asyncio
async def test_codehunt_stats_route(client: AsyncClient, tmp_path, monkeypatch):
    monkeypatch.setenv("ARXIV_MCP_DATA_DIR", str(tmp_path))
    async with client as c:
        resp = await c.get("/api/codehunt/stats")
    assert resp.status_code == 200
    assert "total_findings" in resp.json()
