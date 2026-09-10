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


@pytest.mark.asyncio
async def test_llm_gpus_parses_nvidia_smi(client: AsyncClient, monkeypatch):
    import subprocess

    class _Proc:
        returncode = 0
        stdout = "0, NVIDIA GeForce RTX 4090, 24564, 2108, 22456\n"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Proc())
    async with client as c:
        resp = await c.get("/api/llm/gpus")
    assert resp.status_code == 200
    (gpu,) = resp.json()["gpus"]
    assert (gpu["index"], gpu["name"]) == (0, "NVIDIA GeForce RTX 4090")
    assert (gpu["total_mb"], gpu["used_mb"], gpu["free_mb"]) == (24564, 2108, 22456)


@pytest.mark.asyncio
async def test_llm_gpus_empty_without_nvidia_smi(client: AsyncClient, monkeypatch):
    import subprocess

    def _missing(*a, **k):
        raise FileNotFoundError("nvidia-smi")

    monkeypatch.setattr(subprocess, "run", _missing)
    async with client as c:
        resp = await c.get("/api/llm/gpus")
    assert resp.status_code == 200
    assert resp.json() == {"gpus": []}


@pytest.mark.asyncio
async def test_llm_unload_evicts_all(client: AsyncClient, monkeypatch):
    from arxiv_mcp import llm_providers

    async def _fake_switch(keep, base_url):
        assert keep == ""
        return {"evicted": ["qwen3.8:27b"], "warmed": False, "engine": True}

    monkeypatch.setattr(llm_providers, "switch_ollama_model", _fake_switch)
    async with client as c:
        resp = await c.post("/api/llm/unload", json={"provider": "ollama"})
    assert resp.status_code == 200
    assert resp.json()["evicted"] == ["qwen3.8:27b"]


@pytest.mark.asyncio
async def test_llm_unload_rejects_non_ollama(client: AsyncClient):
    async with client as c:
        resp = await c.post("/api/llm/unload", json={"provider": "openai"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_llm_unload_engine_down_is_502(client: AsyncClient, monkeypatch):
    from arxiv_mcp import llm_providers

    async def _fake_switch(keep, base_url):
        return {"evicted": [], "warmed": False, "engine": False}

    monkeypatch.setattr(llm_providers, "switch_ollama_model", _fake_switch)
    async with client as c:
        resp = await c.post("/api/llm/unload", json={"provider": "ollama"})
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_llm_loaded_lists_residents(client: AsyncClient, monkeypatch):
    from arxiv_mcp import llm_providers

    async def _fake_loaded(base_url):
        return {
            "engine": True,
            "models": [{"name": "llama3.2:3b", "size_vram_mb": 10138, "expires_at": ""}],
        }

    monkeypatch.setattr(llm_providers, "ollama_loaded", _fake_loaded)
    async with client as c:
        resp = await c.get("/api/llm/loaded?provider=ollama")
    assert resp.status_code == 200
    assert resp.json()["models"][0]["name"] == "llama3.2:3b"


@pytest.mark.asyncio
async def test_llm_loaded_rejects_non_ollama(client: AsyncClient):
    async with client as c:
        resp = await c.get("/api/llm/loaded?provider=openai")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_apps_hub_lists_registry(client: AsyncClient):
    async with client as c:
        resp = await c.get("/api/apps")
    assert resp.status_code == 200
    data = resp.json()
    assert data["fleet_total"] > 100
    assert data["apps"], "registry has webapp ports, hub must not be empty"
    first = data["apps"][0]
    assert {"id", "port", "url", "gh_url"} <= set(first)


@pytest.mark.asyncio
async def test_apps_health_closed_port(client: AsyncClient):
    async with client as c:
        resp = await c.get("/api/apps/health?port=9")
    assert resp.status_code == 200
    assert resp.json()["alive"] is False


@pytest.mark.asyncio
async def test_apps_ensure_unknown_id(client: AsyncClient):
    async with client as c:
        resp = await c.post("/api/apps/ensure", json={"id": "no-such-app-xyz", "port": 9})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body.get("alive", False) is False
