"""FastAPI: REST dashboard API + mounted FastMCP HTTP (streamable)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from collections import deque
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from arxiv_mcp import __version__, llm_providers
from arxiv_mcp.anthropic_blog import (
    KNOWN_POSTS,
)
from arxiv_mcp.anthropic_blog import (
    fetch_anthropic_post as _fetch_anthropic_post,
)
from arxiv_mcp.anthropic_blog import (
    list_anthropic_posts as _list_anthropic_posts,
)
from arxiv_mcp.arxiv_html import arxiv_org_search_advanced_html, list_categories_payload
from arxiv_mcp.capabilities import build_capabilities
from arxiv_mcp.config import load_settings
from arxiv_mcp.depot_service import (
    analyze_paper_epistemics,
    deep_analyze_paper_epistemics,
    ingest_and_analyze_paper,
    ingest_paper_html,
    list_depot_by_epistemics,
)
from arxiv_mcp.firefront_service import run_firefront_scan
from arxiv_mcp.lab_blog import (
    SOURCES as LAB_SOURCES,
)
from arxiv_mcp.lab_blog import (
    fetch_lab_post as _fetch_lab_post,
)
from arxiv_mcp.lab_blog import (
    list_lab_posts as _list_lab_posts,
)
from arxiv_mcp.server import mcp
from arxiv_mcp.services import corpus, papers
from arxiv_mcp.startup_probe import run_startup_probes
from arxiv_mcp.tools_manifest import MCP_PROMPTS

# -- Log ring buffer (in-memory, 1000 entries) --
_log_buffer: deque[dict[str, Any]] = deque(maxlen=5000)


class _RingBufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        _log_buffer.append(
            {
                "id": f"{int(record.created * 1000):x}-{uuid.uuid4().hex[:6]}",
                "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
                "level": "warn" if record.levelname == "WARNING" else record.levelname.lower(),
                "message": record.getMessage(),
                "source": "server",
                "logger": record.name,
            }
        )


_log_handler = _RingBufferHandler()
_log_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(_log_handler)


mcp_http = mcp.http_app(path="/")
router = APIRouter(prefix="/api")

_FLEET_PATH = Path(__file__).resolve().parent / "data" / "fleet_default.json"


class FavoriteIn(BaseModel):
    arxiv_id: str = Field(..., min_length=4)
    title: str | None = None
    note: str | None = None


class IngestIn(BaseModel):
    paper_id: str = Field(..., min_length=4)


class MediaSettingsIn(BaseModel):
    media_ignore_botblocks: bool | None = None
    media_use_brighthand: bool | None = None


@router.get("/logs")
async def api_logs(
    level: str | None = Query(None, description="Filter: info, warn, error, debug"),
    search: str | None = Query(None, description="Substring search in message"),
    source: str | None = Query(None, description="client or server"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Read from the in-memory log ring buffer."""
    import copy

    items: list[dict[str, Any]] = list(copy.deepcopy(_log_buffer))

    if source:
        items = [i for i in items if i.get("source") == source]
    if level:
        items = [i for i in items if i.get("level") == level]
    if search:
        items = [i for i in items if search.lower() in i.get("message", "").lower()]

    items.reverse()
    total = len(items)
    page = items[offset : offset + limit]
    return {"entries": page, "total": total, "offset": offset, "limit": limit}


class LogIn(BaseModel):
    level: str = Field(default="info", pattern="^(info|warn|error|debug)$")
    message: str = Field(..., min_length=1)
    source: str = Field(default="client")


@router.post("/logs")
async def api_logs_push(body: LogIn) -> dict[str, Any]:
    _log_buffer.append(
        {
            "id": f"{int(datetime.now().timestamp() * 1000):x}-{uuid.uuid4().hex[:6]}",
            "ts": datetime.now(tz=UTC).isoformat(),
            "level": body.level,
            "message": body.message,
            "source": body.source,
            "logger": "webapp",
        }
    )
    return {"ok": True}


@router.get("/settings/llm")
async def api_llm_settings_get() -> dict[str, Any]:
    """Read saved LLM provider config from data dir (key bytes never returned)."""
    from arxiv_mcp.config import load_settings

    settings = load_settings()
    path = settings.resolved_data_dir() / "llm_settings.json"
    base = {"provider": "ollama", "endpoint": "http://localhost:11434", "model": ""}
    if path.is_file():
        try:
            base.update(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    base.pop("api_key", None)
    base["keys_configured"] = llm_providers.keys_configured(settings)
    return base


class LlmSettingsWriteIn(BaseModel):
    provider: str = Field(default="ollama")
    endpoint: str = Field(default="http://127.0.0.1:11434")
    model: str = Field(default="gemma4:12b")
    api_key: str | None = Field(default=None, description="Write-only; stored in 0600 keystore")
    select: bool = Field(
        default=True,
        description="False saves a card key without switching the active selection (BUG-043)",
    )


@router.post("/settings/llm")
async def api_llm_settings_save(body: LlmSettingsWriteIn) -> dict[str, Any]:
    """Save LLM provider config to data dir; API key goes to the keystore only."""
    from arxiv_mcp.config import load_settings

    settings = load_settings()
    try:
        llm_providers.require_provider(body.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload = {"provider": body.provider, "endpoint": body.endpoint, "model": body.model}
    if not body.select:
        # Key-only save for a non-active card: persist the key, leave the
        # active provider/endpoint/model untouched (BUG-043).
        if not body.api_key:
            raise HTTPException(status_code=400, detail="api_key required when select is false") from None
        try:
            llm_providers.save_key(body.provider, body.api_key, settings)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"success": True, "key_saved": True, "select": False}
    path = settings.resolved_data_dir() / "llm_settings.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    key_saved = False
    if body.api_key:
        try:
            llm_providers.save_key(body.provider, body.api_key, settings)
            key_saved = True
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    # Saving a selection switches VRAM, not just config: evict every other
    # loaded Ollama model and warm the chosen one, so a leftover hog can't
    # keep blocking the card while the new choice can't fit.
    switch: dict[str, Any] = {}
    if body.provider == "ollama" and body.model.strip():
        switch = await llm_providers.switch_ollama_model(body.model.strip(), body.endpoint)
    return {"success": True, **payload, "key_saved": key_saved, "switch": switch}


@router.delete("/settings/llm/key")
async def api_llm_key_delete(provider: str = Query(...)) -> dict[str, Any]:
    """Delete one stored cloud API key."""
    from arxiv_mcp.config import load_settings

    try:
        removed = llm_providers.delete_key(provider, load_settings())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "provider": provider, "removed": removed}


class LlmUnloadIn(BaseModel):
    provider: str = Field(default="ollama")
    endpoint: str = Field(default="http://localhost:11434")


@router.post("/llm/unload")
async def api_llm_unload(body: LlmUnloadIn) -> dict[str, Any]:
    """Kick every loaded model out of the local engine (full VRAM release).

    Same engine call the llm_ops MCP tool uses — the Settings "kick out"
    button and agents share one path. Loads nothing; fails loudly when the
    engine is unreachable instead of pretending.
    """
    if body.provider != "ollama":
        raise HTTPException(status_code=400, detail="unload needs the ollama provider")
    switch = await llm_providers.switch_ollama_model("", body.endpoint)
    if not switch.get("engine"):
        raise HTTPException(status_code=502, detail="Ollama engine unreachable - start it first")
    return {"success": True, "provider": body.provider, **switch}


@router.get("/llm/loaded")
async def api_llm_loaded(provider: str = Query(...), endpoint: str = Query(default="")) -> dict[str, Any]:
    """Models currently resident on the local engine (name + VRAM + expiry).

    Powers the Settings loaded-model KPI and the llm_ops `loaded` op.
    """
    if provider != "ollama":
        raise HTTPException(status_code=400, detail="loaded residents need the ollama provider")
    base = endpoint.rstrip("/") or "http://localhost:11434"
    return {"success": True, "provider": provider, **await llm_providers.ollama_loaded(base)}


class LlmChatIn(BaseModel):
    provider: str = Field(...)
    model: str = Field(..., min_length=1)
    messages: list[dict[str, Any]] = Field(..., min_length=1)


@router.get("/llm/providers")
async def api_llm_providers() -> dict[str, Any]:
    """Provider registry with live local detection + cloud key flags (no key bytes)."""
    import asyncio

    from arxiv_mcp.config import load_settings

    settings = load_settings()
    infos = llm_providers.public_provider_info(settings)
    locals_ = [i for i in infos if i["kind"] == "local"]
    probes = await asyncio.gather(*(llm_providers.probe_local(i["id"]) for i in locals_))
    for info, (reachable, models) in zip(locals_, probes, strict=True):
        info["detected"] = reachable
        info["models"] = models
    for info in infos:
        if info["kind"] == "cloud":
            info["detected"] = info["configured"]
            info["models"] = []
    return {"providers": infos}


@router.get("/llm/gpus")
async def api_llm_gpus() -> dict[str, Any]:
    """Live GPU VRAM (used/total) via nvidia-smi. Empty list when unavailable."""
    return {"gpus": await asyncio.to_thread(llm_providers.gpu_vram)}


@router.get("/llm/models")
async def api_llm_models(provider: str = Query(...)) -> dict[str, Any]:
    """Model list for one provider: live when reachable/keyed, else curated."""
    from arxiv_mcp.config import load_settings

    try:
        return await llm_providers.list_models(provider, load_settings())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class LlmTestIn(BaseModel):
    provider: str = Field(...)
    api_key: str | None = Field(default=None, description="Typed-but-unsaved key; validated only, never stored")
    endpoint: str = Field(default="")


@router.post("/llm/test")
async def api_llm_test(body: LlmTestIn) -> dict[str, Any]:
    """Validate a provider without saving anything.

    ok is True only for a live list -- curated names without a key come
    back ok:false with key_missing so the UI never reports them as success
    (BUG-042).
    """
    from arxiv_mcp.config import load_settings

    try:
        result = await llm_providers.list_models(body.provider, load_settings(), body.api_key or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    ok = result.get("source") == "live" and len(result.get("models", [])) > 0
    return {"success": True, "ok": ok, **result}


@router.post("/llm/chat")
async def api_llm_chat(body: LlmChatIn) -> dict[str, Any]:
    """Non-streaming chat via the backend proxy (keys never leave the server)."""
    from arxiv_mcp.config import load_settings

    try:
        content = await llm_providers.chat_complete(body.provider, body.model, body.messages, load_settings())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"provider": body.provider, "model": body.model, "content": content}


@router.post("/llm/chat/stream")
async def api_llm_chat_stream(body: LlmChatIn) -> StreamingResponse:
    """Streaming chat (SSE, OpenAI-style chunks) via the backend proxy."""
    from arxiv_mcp.config import load_settings

    settings = load_settings()
    try:
        llm_providers.require_provider(body.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not body.model.strip():
        raise HTTPException(status_code=400, detail="Empty model name")
    gen = llm_providers.chat_stream(body.provider, body.model, body.messages, settings)
    return StreamingResponse(gen, media_type="text/event-stream")


@router.get("/llm/onboarding")
async def api_llm_onboarding() -> dict[str, Any]:
    """Fresh-install starter facts: what exists, what can be installed, best path."""
    from arxiv_mcp.config import load_settings

    return llm_providers.onboarding_state(load_settings())


class LlmInstallIn(BaseModel):
    engine: str = Field(...)


@router.post("/llm/install")
async def api_llm_install(body: LlmInstallIn) -> dict[str, Any]:
    """Start a fixed-command engine install (allowlist: ollama). No user input reaches the shell."""
    try:
        return llm_providers.start_install(body.engine.strip().lower())
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/llm/install/status")
async def api_llm_install_status(engine: str = Query(...)) -> dict[str, Any]:
    """Poll a background engine install: idle | running | done | error."""
    try:
        return llm_providers.install_status(engine.strip().lower())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _read_pyproject_desc(repo_path: Path) -> str | None:
    """Plain project description from pyproject (no marketing hype)."""
    p = repo_path / "pyproject.toml"
    if not p.is_file():
        return None
    try:
        import tomllib

        data = tomllib.loads(p.read_text(encoding="utf-8"))
        desc = str(data.get("project", {}).get("description") or "").strip()
        if desc and len(desc) >= 10 and "hardened substrate" not in desc.lower():
            return desc
    except (OSError, Exception) as e:
        logger.debug("Failed parsing %s via tomllib: %s", p, e)
    try:
        import re

        txt = p.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'description\s*=\s*["\']([^"\']+)["\']', txt)
        if m:
            d = m.group(1).strip()
            if len(d) >= 10 and "hardened substrate" not in d.lower():
                return d
    except OSError as e:
        logger.debug("Failed reading %s for regex fallback: %s", p, e)
    return None


def _is_hype(desc: str) -> bool:
    low = desc.lower()
    return (
        any(k in low for k in ["industrial-grade", "agentic revolution", "hardened substrate"])
        or len(desc.strip()) < 12
    )


@router.get("/apps")
async def api_apps() -> dict[str, Any]:
    """Fleet apps hub — entries with webapp ports from the fleet registry (enriched).

    Vendored per APPS_PAGE_STANDARD.md (reference: git-github-mcp).
    """
    from arxiv_mcp.services.fleet_catalog import load_registry

    rows = load_registry()
    apps: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        rid = str(row.get("id") or "")
        port = int(row.get("frontend_port") or row.get("port") or 0)
        if port <= 0:
            continue
        raw_desc = str(row.get("description") or "")
        cat = str(row.get("category") or "mcp")
        repo_path = Path(str(row.get("repo_path") or f"D:/Dev/repos/{rid}"))
        desc = raw_desc
        if _is_hype(raw_desc) or not raw_desc.strip():
            py_desc = _read_pyproject_desc(repo_path)
            if py_desc:
                desc = py_desc
            elif cat and cat.lower() != "mcp":
                desc = cat
            else:
                desc = raw_desc or "Fleet MCP — local webapp"
        has_tauri = (repo_path / "native" / "tauri.conf.json").is_file() or (
            repo_path / "src-tauri" / "tauri.conf.json"
        ).is_file()
        has_tauri_installed = False
        if has_tauri:
            for cand in [
                Path.home() / "AppData" / "Local" / "Programs" / rid / f"{rid}.exe",
                repo_path / "native" / "target" / "release" / f"{rid}.exe",
            ]:
                if cand.is_file():
                    has_tauri_installed = True
                    break
        gh_owner = str(row.get("github_owner") or "sandraschi")
        gh_repo = str(row.get("github_repo") or rid)
        apps.append(
            {
                "id": rid,
                "name": str(row.get("name") or rid),
                "description": desc,
                "port": port,
                "backend_port": int(row.get("port") or 0),
                "category": cat,
                "url": f"http://127.0.0.1:{port}",
                "gh_url": f"https://github.com/{gh_owner}/{gh_repo}",
                "repo_path": str(repo_path),
                "has_tauri": has_tauri,
                "has_tauri_installed": has_tauri_installed,
                "last_commit": None,
            }
        )
    apps.sort(key=lambda a: a["port"])
    logging.getLogger(__name__).info("apps hub listed %d entries", len(apps))
    return {"apps": apps, "fleet_total": len(rows)}


def _check_port_health_sync(port: int, timeout: float = 1.2) -> dict[str, Any]:
    """TCP connect + health-endpoint probe. Sync: run in a thread."""
    import socket

    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            pass
    except Exception as e:
        return {
            "port": port,
            "alive": False,
            "reason": f"tcp refused: {e}",
            "health_url": f"http://127.0.0.1:{port}/health",
        }
    for path in (
        "/health",
        "/api/health",
        "/api/status",
        "/api/capabilities",
        "/api/v1/health",
        "/api/capabilities/health",
    ):
        try:
            import httpx

            with httpx.Client(timeout=timeout) as c:
                r = c.get(f"http://127.0.0.1:{port}{path}")
                if 200 <= r.status_code < 500:
                    return {
                        "port": port,
                        "alive": True,
                        "status_code": r.status_code,
                        "health_url": f"http://127.0.0.1:{port}{path}",
                        "reason": "http ok",
                    }
        except Exception as e:
            logger.debug("Port %d probe to %s failed: %s", port, path, e)
            continue
    return {
        "port": port,
        "alive": True,
        "reason": "tcp open but health 404",
        "health_url": f"http://127.0.0.1:{port}/health",
    }


@router.get("/apps/health")
async def api_apps_health(port: int = Query(...)) -> dict[str, Any]:
    """Health dot backend proxy (avoids CORS): TCP + health-endpoint probe."""
    import asyncio

    return await asyncio.to_thread(_check_port_health_sync, int(port))


def _is_process_running(name: str) -> list[int]:
    import subprocess

    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {name}.exe"],
            capture_output=True,
            text=True,
            timeout=4,
        )
        pids: list[int] = []
        for line in out.stdout.splitlines():
            if name.lower() in line.lower() and ".exe" in line.lower():
                for p in line.split():
                    if p.isdigit():
                        try:
                            pid = int(p)
                            if pid > 4:
                                pids.append(pid)
                        except ValueError:
                            continue
        return pids
    except Exception as e:
        logger.debug("Process listing failed for %s: %s", name, e)
        return []


def _bring_to_foreground(pids: list[int]) -> bool:
    import subprocess

    if not pids:
        return False
    pid = pids[0]
    ps = f"""
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win {{ [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd); [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow); }}
'@
$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue
if ($p) {{
  $h = $p.MainWindowHandle
  if ($h -eq 0) {{ $h = $p.Handle }}
  [Win]::ShowWindow($h, 9) | Out-Null
  [Win]::SetForegroundWindow($h) | Out-Null
  exit 0
}}
exit 1
"""
    try:
        r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps], timeout=5)
        return r.returncode == 0
    except Exception:
        return False


def _find_starts_for_id(app_id: str) -> list[str]:
    candidates: list[str] = []

    def _try_ids(base_id: str) -> list[str]:
        ids_to_try = [base_id]
        if base_id.endswith("-mcp"):
            ids_to_try.append(base_id[:-4])
            ids_to_try.append(base_id[:-4].replace("-mcp", ""))
        return ids_to_try

    for cand_id in _try_ids(app_id):
        mcd = Path(r"D:\Dev\repos\mcp-central-docs\starts") / f"{cand_id}-start.bat"
        if mcd.exists() and str(mcd) not in candidates:
            candidates.append(str(mcd))
    for cand_id in _try_ids(app_id):
        repo_ps1 = Path(r"D:\Dev\repos") / cand_id / "start.ps1"
        if repo_ps1.exists() and str(repo_ps1) not in candidates:
            candidates.append(str(repo_ps1))
        repo_bat = Path(r"D:\Dev\repos") / cand_id / "start.bat"
        if repo_bat.exists() and str(repo_bat) not in candidates:
            candidates.append(str(repo_bat))
    for p in [
        Path.home() / "AppData" / "Local" / "Programs" / app_id / f"{app_id}.exe",
        Path.home() / "AppData" / "Local" / app_id / f"{app_id}.exe",
        Path(r"D:\Dev\repos") / app_id / "native" / "target" / "release" / f"{app_id}.exe",
    ]:
        if p.exists():
            candidates.append(str(p))
    return candidates


class AppsEnsureIn(BaseModel):
    id: str = ""
    app_id: str = ""
    port: int = 0


@router.post("/apps/ensure")
async def api_apps_ensure(body: AppsEnsureIn) -> dict[str, Any]:
    """Click-to-open backend: health first, foreground Tauri, else start detached.

    Vendored per APPS_PAGE_STANDARD.md (reference: git-github-mcp).
    """
    import asyncio

    from arxiv_mcp.services.fleet_catalog import load_registry

    app_id = (body.id or body.app_id).strip()
    port = int(body.port or 0)
    if not app_id and port:
        for row in load_registry():
            if int(row.get("frontend_port") or row.get("port") or 0) == port:
                app_id = str(row.get("id") or "")
                break
    if not port and app_id:
        for row in load_registry():
            if str(row.get("id")) == app_id:
                port = int(row.get("frontend_port") or row.get("port") or 0)
                break
    if not port:
        return {"success": False, "error": "port or id required", "alive": False}
    health = await asyncio.to_thread(_check_port_health_sync, port)
    if not health.get("alive") and app_id:
        try:
            for row in load_registry():
                if str(row.get("id")) == app_id:
                    bport = int(row.get("port") or 0)
                    fport = int(row.get("frontend_port") or 0)
                    cand = bport if bport != port and bport > 0 else (fport if fport != port and fport > 0 else 0)
                    if cand:
                        h2 = await asyncio.to_thread(_check_port_health_sync, cand)
                        if h2.get("alive"):
                            health = h2
                            port = cand
                    break
        except Exception as e:
            logger.warning("Failed resolving secondary ports from registry for %s: %s", app_id, e)
    if health.get("alive"):
        if app_id:
            pids = await asyncio.to_thread(_is_process_running, app_id)
            if pids:
                await asyncio.to_thread(_bring_to_foreground, pids)
                return {
                    "success": True,
                    "status": "brought_to_foreground",
                    "alive": True,
                    "url": f"http://127.0.0.1:{port}",
                    "pids": pids,
                    "port": port,
                    "id": app_id,
                }
        return {
            "success": True,
            "status": "already_running",
            "alive": True,
            "url": f"http://127.0.0.1:{port}",
            "port": port,
            "id": app_id,
        }
    if app_id:
        pids = await asyncio.to_thread(_is_process_running, app_id)
        if not pids:
            pids = await asyncio.to_thread(_is_process_running, f"{app_id}-native")
        if pids:
            ok = await asyncio.to_thread(_bring_to_foreground, pids)
            health2 = await asyncio.to_thread(_check_port_health_sync, port)
            return {
                "success": True,
                "status": "brought_to_foreground" if ok else "found_process",
                "alive": bool(health2.get("alive")),
                "url": f"http://127.0.0.1:{port}",
                "pids": pids,
                "port": port,
                "id": app_id,
            }
    if app_id:
        candidates = await asyncio.to_thread(_find_starts_for_id, app_id)
        start_cmd = None
        for c in candidates:
            if c.lower().endswith("-start.bat") or c.lower().endswith("start.ps1"):
                start_cmd = c
                break
        if start_cmd:
            try:
                import subprocess

                if start_cmd.lower().endswith(".ps1"):
                    subprocess.Popen(
                        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", start_cmd],
                        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
                    )
                else:
                    subprocess.Popen(
                        ["cmd.exe", "/c", start_cmd],
                        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
                    )
                for _ in range(12):
                    await asyncio.sleep(1)
                    h = await asyncio.to_thread(_check_port_health_sync, port)
                    if h.get("alive"):
                        return {
                            "success": True,
                            "status": "started",
                            "alive": True,
                            "url": f"http://127.0.0.1:{port}",
                            "port": port,
                            "id": app_id,
                            "via": start_cmd,
                        }
                return {
                    "success": True,
                    "status": "start_initiated",
                    "alive": False,
                    "url": f"http://127.0.0.1:{port}",
                    "port": port,
                    "id": app_id,
                    "via": start_cmd,
                    "note": "started but health not yet ok - wait a few seconds and retry",
                }
            except Exception as e:
                return {"success": False, "error": str(e), "port": port, "id": app_id}
        for c in candidates:
            if c.lower().endswith(".exe") and "setup" not in c.lower():
                try:
                    import subprocess

                    subprocess.Popen([c], creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0)
                    return {
                        "success": True,
                        "status": "tauri_started",
                        "alive": False,
                        "url": f"http://127.0.0.1:{port}",
                        "port": port,
                        "id": app_id,
                        "via": c,
                    }
                except Exception as e:
                    return {"success": False, "error": str(e), "port": port, "id": app_id}
        return {
            "success": False,
            "error": f"no start entry found for {app_id} (checked {candidates})",
            "port": port,
            "id": app_id,
        }
    return {"success": False, "error": "could not start - no id", "port": port}


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "arxiv-mcp"}


@router.get("/stats")
async def api_stats() -> dict[str, Any]:
    return corpus.depot_stats()


@router.get("/categories")
async def api_categories() -> dict[str, Any]:
    """Static arXiv subject codes (same catalog as MCP `listCategories`)."""
    return {"categories": list_categories_payload()}


@router.get("/search")
async def api_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("submitted"),
    categories: str | None = Query(None, description="Comma-separated arXiv categories"),
) -> dict[str, Any]:
    cats = [c.strip() for c in categories.split(",") if c.strip()] if categories else None
    rows = await papers.search_papers(q, categories=cats, limit=limit, sort_by=sort_by)
    return {"papers": [papers.paper_summary_to_dict(p) for p in rows]}


@router.get("/preprints/search")
async def api_preprints_search(
    q: str = Query(..., min_length=1),
    servers: str = Query("arxiv,biorxiv,medrxiv,chemrxiv,researchsquare"),
    limit: int = Query(20, ge=1, le=50),
    hours: int = Query(720, ge=1, le=8760),
) -> dict:
    """Search multiple preprint servers in parallel.

    Servers: arxiv, biorxiv, medrxiv, chemrxiv, researchsquare
    """
    import logging

    logger = logging.getLogger(__name__)
    from arxiv_mcp.services.preprint_servers import (
        SERVER_LABELS,
        merge_results,
        search_all,
    )

    srv_list = [s.strip() for s in servers.split(",") if s.strip()]
    errors: dict[str, str] = {}
    results_by_server = search_all(
        q,
        servers=[s for s in srv_list if s != "arxiv"],
        limit=limit,
        hours=hours,
        errors_out=errors,
    )

    # Add arXiv results
    if "arxiv" in srv_list:
        try:
            arxiv_results = await papers.search_papers(q, limit=limit)
            from arxiv_mcp.services.preprint_servers import Paper

            results_by_server["arxiv"] = [
                Paper(
                    paper_id=r.paper_id,
                    title=r.title,
                    summary=r.summary,
                    authors=list(r.authors),
                    categories=list(r.categories),
                    published=str(r.published or ""),
                    server="arxiv",
                    html_url=r.html_url or r.abs_url,
                    pdf_url=r.pdf_url,
                )
                for r in arxiv_results
            ]
        except Exception as e:
            logger.error("arXiv search in preprints endpoint failed: %s", e, exc_info=True)
            errors["arxiv"] = str(e)
            results_by_server["arxiv"] = []

    merged = merge_results(results_by_server, total_limit=limit * len(results_by_server))

    # Return per-server breakdown + merged + errors
    per_server = {}
    for srv, pp in results_by_server.items():
        label = SERVER_LABELS.get(srv, srv)
        per_server[srv] = {"label": label, "count": len(pp), "papers": [p.__dict__ for p in pp]}

    return {
        "merged": [p.__dict__ for p in merged],
        "per_server": per_server,
        "errors": errors,
        "total": len(merged),
    }


@router.get("/category/latest")
async def api_category_latest(
    category: str = Query(..., min_length=2),
    limit: int = Query(25, ge=1, le=100),
    hours: int = Query(24, ge=1, le=168),
) -> dict[str, Any]:
    rows = await papers.list_category_latest(category, limit=limit, hours=hours)
    return {"papers": [papers.paper_summary_to_dict(p) for p in rows]}


@router.get("/searchAdvanced")
async def api_search_advanced(
    title: str | None = Query(None, description="Search within paper titles (ti:)"),
    abstract: str | None = Query(None, description="Search within abstracts (abs:)"),
    author: str | None = Query(None, description="Author filter (au:)"),
    category: str | None = Query(None, description="Category filter (cat:)"),
    id_arxiv: str | None = Query(None, description="arXiv ID pattern (id:)"),
    date_from: str | None = Query(None, description="YYYY-MM-DD start date"),
    date_to: str | None = Query(None, description="YYYY-MM-DD end date"),
    sort_by: str = Query("relevance"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=50),
    limit: int | None = Query(None, description="Alias for page_size (convenience)"),
) -> dict[str, Any]:
    """Field-scoped search on arxiv.org HTML (same as MCP searchAdvanced tool)."""
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
        page_size=limit or page_size,
    )


@router.get("/paper")
async def api_paper(paper_id: str = Query(..., min_length=5)) -> dict[str, Any]:
    p = await papers.get_paper_details(paper_id)
    return {"paper": papers.paper_summary_to_dict(p)}


@router.get("/paper/full-text")
async def api_paper_full_text(paper_id: str = Query(..., min_length=4)) -> dict[str, Any]:
    from arxiv_mcp.server import fetch_full_text

    result = await fetch_full_text(paper_id=paper_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed to fetch full text"))
    return {"markdown": result.get("markdown") or ""}


@router.get("/corpus")
async def api_corpus(
    limit: int = Query(50, ge=1, le=500),
    primary_mode: str | None = Query(None, description="Filter by epistemic primary_mode"),
    needs_bench: bool | None = Query(None),
    needs_telescope_or_instrument: bool | None = Query(None),
    needs_formal_verification: bool | None = Query(None),
    has_deep_claims: bool | None = Query(None, description="True = only papers with LLM claim tables"),
) -> dict[str, Any]:
    if any(
        x is not None
        for x in (primary_mode, needs_bench, needs_telescope_or_instrument, needs_formal_verification, has_deep_claims)
    ):
        rows = corpus.list_ingested_filtered(
            limit=limit,
            primary_mode=primary_mode,
            needs_bench=needs_bench,
            needs_telescope_or_instrument=needs_telescope_or_instrument,
            needs_formal_verification=needs_formal_verification,
            has_deep_claims=has_deep_claims,
        )
        return {"ingested": rows, "filtered": True}
    rows = corpus.list_ingested(limit=limit)
    return {"ingested": rows, "filtered": False}


@router.get("/corpus/item")
async def api_corpus_item(arxiv_id: str = Query(..., min_length=4)) -> dict[str, Any]:
    row = corpus.get_paper_markdown(arxiv_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not in depot")
    return row


@router.get("/depot/search")
async def api_depot_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    mode: str = Query(
        "hybrid",
        pattern="^(fts|semantic|hybrid)$",
        description="Search engine: fts (BM25), semantic (LanceDB), hybrid (RRF merge)",
    ),
    max_age_days: int | None = Query(
        None,
        ge=1,
        le=3650,
        description=(
            "Exclude papers published more than N days ago. "
            "Recommended for AI/ML topics: 180 (six months). "
            "No filtering if omitted."
        ),
    ),
) -> dict[str, Any]:
    if mode == "fts":
        hits = corpus.search_depot_fts(q, limit=limit, max_age_days=max_age_days)
        engine = "sqlite_fts5"
    elif mode == "semantic":
        try:
            hits = corpus.search_depot_semantic(q, limit=limit)
            engine = "lancedb"
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    else:
        hits, engine = corpus.search_depot_hybrid(q, limit=limit, max_age_days=max_age_days)
    return {
        "query": q,
        "mode": mode,
        "max_age_days": max_age_days,
        "hits": hits,
        "engine": engine,
    }


@router.get("/depot/rag/status")
async def api_depot_rag_status() -> dict[str, Any]:
    from arxiv_mcp.services.vector_rag import vector_rag_status

    return vector_rag_status()


@router.post("/depot/rag/reindex")
async def api_depot_rag_reindex() -> dict[str, Any]:
    from arxiv_mcp.services.vector_rag import reindex_all_vectors

    result = reindex_all_vectors()
    if not result.get("success"):
        raise HTTPException(status_code=503, detail=result.get("error", "reindex failed"))
    return result


class FirefrontIn(BaseModel):
    topic: str = Field(..., min_length=1)
    categories: list[str] | None = None
    days: int = Field(7, ge=1, le=90)
    limit_per_category: int = Field(25, ge=1, le=100)
    ingest_top_n: int = Field(0, ge=0, le=20)


@router.post("/firefront/scan")
async def api_firefront_scan(body: FirefrontIn) -> dict[str, Any]:
    result = await run_firefront_scan(
        body.topic,
        categories=body.categories,
        days=body.days,
        limit_per_category=body.limit_per_category,
        ingest_top_n=body.ingest_top_n,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)
    return result


class CodehuntScanIn(BaseModel):
    categories: list[str] | None = None
    days: int = Field(3, ge=1, le=30)
    limit_per_category: int = Field(50, ge=1, le=100)
    fulltext_max_papers: int | None = Field(None, ge=0, le=50)
    push: bool = True


@router.post("/codehunt/scan")
async def api_codehunt_scan(body: CodehuntScanIn) -> dict[str, Any]:
    from arxiv_mcp.codehunt_service import run_codehunt_scan

    result = await run_codehunt_scan(
        categories=body.categories,
        days=body.days,
        limit_per_category=body.limit_per_category,
        fulltext_max_papers=body.fulltext_max_papers,
        push=body.push,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/codehunt/repoll")
async def api_codehunt_repoll(
    limit: int = Query(200, ge=1, le=1000),
    push: bool = Query(True),
) -> dict[str, Any]:
    from arxiv_mcp.codehunt_service import repoll_pending

    return await repoll_pending(limit=limit, push=push)


@router.get("/codehunt/stats")
async def api_codehunt_stats() -> dict[str, Any]:
    from arxiv_mcp.codehunt_service import codehunt_stats

    return codehunt_stats()


@router.post("/codehunt/media-check")
async def api_codehunt_media_check(
    limit: int = Query(40, ge=1, le=200),
    push: bool = Query(True),
) -> dict[str, Any]:
    from arxiv_mcp.codehunt_service import check_media_traction

    return await check_media_traction(limit=limit, push=push)


@router.get("/pipeline/liveness")
async def api_pipeline_liveness(
    stale_hours: int = Query(48, ge=1, le=168),
) -> dict[str, Any]:
    from arxiv_mcp.pipeline_liveness_service import check_pipeline_liveness

    return await check_pipeline_liveness(stale_hours=stale_hours)


@router.get("/settings/readly")
async def api_readly_settings() -> dict[str, Any]:
    from arxiv_mcp.readly_client import (
        load_readly_watch_magazines,
        readly_health,
        readly_subscription_status,
    )

    settings = load_settings()
    status = readly_subscription_status(settings)
    health = await readly_health(settings) if status.get("enabled") else {"ok": False, "skipped": True}
    return {
        "success": True,
        **status,
        "health": health,
        "watch_magazines": load_readly_watch_magazines(settings),
        "ingest_on_depot": settings.readly_ingest_on_depot,
        "ingest_magazines": settings.parsed_readly_ingest_magazines()
        or [m["readly_query"] for m in load_readly_watch_magazines(settings)],
        "docs": "/api/help/readly",
    }


@router.get("/settings/publications")
async def api_publication_subscriptions() -> dict[str, Any]:
    from arxiv_mcp.publication_subscriptions import (
        expired_subscription_alerts,
        list_subscription_statuses,
    )
    from arxiv_mcp.readly_client import readly_subscription_status

    rows = list_subscription_statuses()
    readly_row = readly_subscription_status()
    if readly_row.get("enabled") or readly_row.get("readly_mcp_url"):
        rows.append(
            {
                "id": "readly",
                "name": "Readly (magazine library)",
                "domains": ["readly.co", "readly.com"],
                "status": readly_row.get("status"),
                "valid_till": readly_row.get("valid_till"),
                "has_user": False,
                "has_password": False,
                "has_cookie": False,
                "configured": readly_row.get("enabled"),
                "usable": readly_row.get("status") == "valid",
                "expiring_soon": readly_row.get("status") == "expiring_soon",
                "expired": readly_row.get("status") == "expired",
                "env_keys": {
                    "url": "ARXIV_MCP_READLY_MCP_URL",
                    "valid_till": "ARXIV_MCP_READLY_VALID_TILL",
                    "token_on_readly": "READLY_AUTH_TOKEN",
                },
            }
        )
    alerts = expired_subscription_alerts()
    return {
        "success": True,
        "publications": rows,
        "alerts": alerts,
        "healthy": not any(a.get("severity") == "critical" for a in alerts),
        "message": "Secrets live in .env only - this endpoint never returns passwords or cookies.",
    }


@router.get("/settings/media")
async def api_media_settings_get() -> dict[str, Any]:
    from arxiv_mcp.runtime_settings import media_settings_payload

    return {"success": True, **media_settings_payload()}


@router.patch("/settings/media")
async def api_media_settings_patch(body: MediaSettingsIn) -> dict[str, Any]:
    from arxiv_mcp.runtime_settings import media_settings_payload, write_overrides

    updates: dict[str, bool] = {}
    if body.media_ignore_botblocks is not None:
        updates["media_ignore_botblocks"] = body.media_ignore_botblocks
    if body.media_use_brighthand is not None:
        updates["media_use_brighthand"] = body.media_use_brighthand
    if not updates:
        raise HTTPException(status_code=400, detail="No settings fields provided")
    write_overrides(updates)
    return {
        "success": True,
        "message": "Media settings updated",
        **media_settings_payload(),
    }


@router.get("/help")
async def api_help_index() -> dict[str, Any]:
    from arxiv_mcp.help_content import get_help

    return get_help(None)


@router.get("/help/{topic}")
async def api_help_topic(topic: str) -> dict[str, Any]:
    from arxiv_mcp.help_content import get_help

    result = get_help(topic)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result)
    return result


@router.post("/depot/ingest")
async def api_depot_ingest(body: IngestIn) -> dict[str, Any]:
    result = await ingest_paper_html(body.paper_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "ingest failed"))
    return result


@router.post("/depot/ingest-analyze")
async def api_depot_ingest_analyze(body: IngestIn, deep: bool = Query(True)) -> dict[str, Any]:
    """Ingest HTML-first; rule + deep LLM epistemic profile when LLM endpoint available."""
    result = await ingest_and_analyze_paper(body.paper_id, deep=deep)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "ingest-analyze failed"))
    return result


@router.post("/depot/analyze")
async def api_depot_analyze(
    body: IngestIn,
    ingest_if_missing: bool = Query(True, description="Ingest from HTML if not already in depot"),
) -> dict[str, Any]:
    result = await analyze_paper_epistemics(body.paper_id, ingest_if_missing=ingest_if_missing)
    if not result.get("success"):
        raise HTTPException(status_code=404 if result.get("error") == "not_in_depot" else 400, detail=result)
    return result


@router.post("/depot/deep-analyze")
async def api_depot_deep_analyze(
    body: IngestIn,
    ingest_if_missing: bool = Query(True),
    force_refresh: bool = Query(False),
) -> dict[str, Any]:
    """LLM claim-level epistemic profile (requires SAMPLING_BASE_URL or MCP sampling client)."""
    result = await deep_analyze_paper_epistemics(
        body.paper_id,
        ingest_if_missing=ingest_if_missing,
        force_refresh=force_refresh,
    )
    if not result.get("success"):
        status = 503 if "SAMPLING" in str(result.get("error", "")).upper() else 400
        raise HTTPException(status_code=status, detail=result)
    return result


@router.get("/depot/epistemics")
async def api_depot_epistemics_filter(
    primary_mode: str | None = Query(None),
    needs_bench: bool | None = Query(None),
    needs_telescope_or_instrument: bool | None = Query(None),
    needs_formal_verification: bool | None = Query(None),
    has_deep_claims: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    return list_depot_by_epistemics(
        primary_mode=primary_mode,
        needs_bench=needs_bench,
        needs_telescope_or_instrument=needs_telescope_or_instrument,
        needs_formal_verification=needs_formal_verification,
        has_deep_claims=has_deep_claims,
        limit=limit,
    )


@router.post("/calibre/ingest")
async def api_calibre_ingest(body: IngestIn) -> dict[str, Any]:
    from arxiv_mcp.server import store_paper_to_calibre

    result = await store_paper_to_calibre(body.paper_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "calibre ingest failed"))
    return result


@router.get("/favorites")
async def api_favorites_list(limit: int = Query(200, ge=1, le=500)) -> dict[str, Any]:
    return {"favorites": corpus.list_favorites(limit=limit)}


@router.post("/favorites")
async def api_favorites_add(body: FavoriteIn) -> dict[str, Any]:
    corpus.add_favorite(body.arxiv_id, title=body.title, note=body.note)
    return {"ok": True, "arxiv_id": body.arxiv_id}


@router.delete("/favorites/{arxiv_id:path}")
async def api_favorites_remove(arxiv_id: str) -> dict[str, Any]:
    ok = corpus.remove_favorite(arxiv_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"ok": True}


@router.get("/tools")
async def api_tools() -> dict[str, Any]:
    caps = await build_capabilities()
    return {
        "tools": caps["tools"],
        "tool_count": caps["tool_count"],
        "mcp_http_path": "/mcp",
        "source": "capabilities",
    }


@router.get("/capabilities")
async def api_capabilities() -> dict[str, Any]:
    """Runtime introspection: tools, prompts, skills, depot stats, feature flags."""
    return await build_capabilities()


@router.get("/skills")
async def api_skills() -> dict[str, Any]:
    caps = await build_capabilities()
    return {"skills": caps["skills"], "count": len(caps["skills"])}


@router.get("/llm/discover")
async def api_llm_discover() -> dict[str, Any]:
    """Scan common local LLM endpoints (Ollama, LM Studio)."""
    import httpx

    settings = load_settings()
    probes = [
        ("ollama", "http://localhost:11434/api/tags"),
        ("lmstudio", "http://localhost:1234/v1/models"),
    ]
    found: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=3.0) as client:
        for kind, url in probes:
            try:
                resp = await client.get(url)
                if resp.status_code < 500:
                    base_url = url.split("/api")[0].split("/v1")[0]
                    found.append({"kind": kind, "url": base_url, "status": resp.status_code})
            except Exception as exc:
                found.append({"kind": kind, "url": url, "error": str(exc)})

    ollama_up = any(f.get("kind") == "ollama" and f.get("status", 500) < 500 for f in found)
    return {
        "configured_sampling_url": settings.sampling_base_url,
        "configured_model": settings.sampling_model,
        "probes": found,
        "ollama_detected": ollama_up,
        "recommendation": (
            "Set ARXIV_MCP_SAMPLING_BASE_URL=http://localhost:11434/v1 for deep epistemic analysis."
            if ollama_up and not settings.sampling_base_url
            else None
        ),
    }


class AnthropicFetchIn(BaseModel):
    slug_or_url: str = Field(..., min_length=3)
    ingest: bool = Field(False, description="If true, also ingest into local corpus after fetch")


class LabFetchIn(BaseModel):
    slug_or_url: str = Field(..., min_length=3)
    ingest: bool = Field(False)


@router.get("/lab/sources")
async def api_lab_sources() -> dict[str, Any]:
    """List supported lab blog sources."""
    return {
        "sources": [
            {
                "id": k,
                "label": v["label"],
                "js_heavy": v["js_heavy"],
                "sections": list(v["sections"].keys()),
                "known_keys": list(v["known_posts"].keys()),
            }
            for k, v in LAB_SOURCES.items()
        ]
    }


@router.get("/lab/posts")
async def api_lab_posts(
    source: str = Query("google-research"),
    limit: int = Query(20, ge=1, le=50),
) -> dict[str, Any]:
    """List posts from any supported AI lab blog."""
    return await _list_lab_posts(source=source, limit=limit)


@router.post("/lab/fetch")
async def api_lab_fetch(body: LabFetchIn) -> dict[str, Any]:
    """Fetch a post from any supported AI lab blog, optionally ingest to corpus."""
    result = await _fetch_lab_post(body.slug_or_url)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "fetch failed"))
    if body.ingest and result.get("markdown"):
        try:
            settings = load_settings()
            rec = corpus.ingest_markdown(
                result["url"],
                result["title"],
                result["markdown"],
                source="external",
                meta={
                    "published": result.get("published", ""),
                    "source_type": f"lab_blog_{result.get('source', 'unknown')}",
                },
                settings=settings,
            )
            result["ingested"] = True
            result["corpus_record"] = rec
        except Exception as e:
            result["ingested"] = False
            result["ingest_error"] = str(e)
    else:
        result["ingested"] = False
    return result


@router.get("/anthropic/posts")
async def api_anthropic_posts(
    section: str = Query("research", pattern="^(research|news)$"),
    limit: int = Query(20, ge=1, le=50),
) -> dict[str, Any]:
    """List posts from anthropic.com/research or /news."""
    result = await _list_anthropic_posts(section=section, limit=limit)
    result["known_keys"] = list(KNOWN_POSTS.keys())
    return result


@router.post("/anthropic/fetch")
async def api_anthropic_fetch(body: AnthropicFetchIn) -> dict[str, Any]:
    """Fetch an Anthropic post and optionally ingest it into the local corpus."""
    result = await _fetch_anthropic_post(body.slug_or_url)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "fetch failed"))
    if body.ingest and result.get("markdown"):
        try:
            settings = load_settings()
            rec = corpus.ingest_markdown(
                result["url"],
                result["title"],
                result["markdown"],
                source="external",
                meta={"published": result.get("published", ""), "source_type": "anthropic_blog"},
                settings=settings,
            )
            result["ingested"] = True
            result["corpus_record"] = rec
        except Exception as e:
            result["ingested"] = False
            result["ingest_error"] = str(e)
    else:
        result["ingested"] = False
    return result


@router.get("/prompts")
async def api_prompts() -> dict[str, Any]:
    """Return the MCP prompt manifest for display in the webapp."""
    return {"prompts": MCP_PROMPTS}


@router.get("/fleet")
async def api_fleet() -> dict[str, Any]:
    if _FLEET_PATH.is_file():
        hubs = json.loads(_FLEET_PATH.read_text(encoding="utf-8"))
    else:
        hubs = []
    return {"hubs": hubs}


_start_time: float = 0.0


def build_app() -> FastAPI:
    global _start_time
    _start_time = __import__("time").time()
    settings = load_settings()
    from fastapi.middleware.cors import CORSMiddleware

    @asynccontextmanager
    async def _startup_lifespan(app: FastAPI):
        """Startup probes run inside MCP lifespan."""
        async with mcp_http.lifespan(app):
            await run_startup_probes(settings)
            yield

    app = FastAPI(
        title="arxiv-mcp",
        version=__version__,
        lifespan=_startup_lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:10770",
            "http://localhost:10770",
            "http://127.0.0.1:10771",
            "http://localhost:10771",
            "http://goliath:10770",
            "http://goliath:10771",
            "http://tauri.localhost",
            "https://tauri.localhost",
            "tauri://localhost",
        ],
        allow_origin_regex=r"https?://(?:[a-zA-Z0-9-]+\.ts\.net|.*?\.tail-[a-f0-9]+\.ts\.net|tauri\.localhost|localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|100\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::\d+)?$|^tauri://localhost$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    # Mount the MCP HTTP app. Since the internal route is at "/" and the
    # mount is at "/mcp", a request to "/mcp" (no trailing slash) leaves
    # an empty internal path after prefix stripping. This wrapper ensures
    # the internal path is always "/".
    class _MCPWrapper:
        def __init__(self, asgi_app):
            self.asgi_app = asgi_app

        async def __call__(self, scope, receive, send):
            if scope["type"] == "http":
                path = scope.get("path", "")
                if not path.endswith("/") and path != "":
                    scope["path"] = path + "/"
                    if scope.get("raw_path"):
                        scope["raw_path"] = scope["raw_path"] + b"/"
            await self.asgi_app(scope, receive, send)

    app.mount("/mcp", _MCPWrapper(mcp_http), name="mcp")

    @app.get("/api/v1/diagnostics")
    async def api_diagnostics() -> dict[str, Any]:
        """CUA-NSIS diagnostics endpoint: tool list, system info, errors."""
        caps = await build_capabilities()
        tool_list = [{"name": t.get("name", "?")} for t in caps.get("tools", [])]
        return {
            "status": "ok",
            "server": "arxiv-mcp",
            "version": __version__,
            "uptime_seconds": int(__import__("time").time() - _start_time),
            "tool_count": len(tool_list),
            "tools": tool_list,
            "system": {"windows": True},
            "errors": [],
        }

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {
            "service": "arxiv-mcp",
            "version": __version__,
            "transports": {
                "stdio": {
                    "command": "uv",
                    "args": ["run", "python", "-m", "arxiv_mcp", "--stdio"],
                },
                "streamable_http": {
                    "mcp_url": f"http://{settings.host}:{settings.port}/mcp",
                },
            },
            "mcp_http": f"http://{settings.host}:{settings.port}/mcp",
            "api": f"http://{settings.host}:{settings.port}/api",
            "webapp": "http://127.0.0.1:10771",
        }

    @app.get("/.well-known/mcp/manifest.json")
    async def well_known_mcp_manifest() -> dict[str, Any]:
        """Machine-readable dual-transport discovery (LobeHub / indexer friendly)."""
        s = load_settings()
        base = f"http://{s.host}:{s.port}"
        return {
            "name": "arxiv-mcp",
            "version": __version__,
            "repository": "https://github.com/sandraschi/arxiv-mcp",
            "transports": {
                "stdio": {
                    "command": "uv",
                    "args": ["run", "python", "-m", "arxiv_mcp", "--stdio"],
                },
                "streamable_http": {
                    "url": f"{base}/mcp",
                    "note": "FastMCP 3.2 http_app; start with: uv run python -m arxiv_mcp --serve",
                },
            },
        }

    return app


app = build_app()
