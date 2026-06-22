"""Runtime capability introspection for webapp and fleet discovery."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from arxiv_mcp import __version__
from arxiv_mcp.config import Settings, load_settings
from arxiv_mcp.services import corpus
from arxiv_mcp.tools_manifest import MCP_PROMPTS, MCP_TOOLS


def _list_skills() -> list[dict[str, Any]]:
    skills_root = Path(__file__).resolve().parent / "skills"
    out: list[dict[str, Any]] = []
    if not skills_root.is_dir():
        return out
    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(encoding="utf-8")
        desc = ""
        if text.startswith("---"):
            end = text.find("---", 3)
            if end > 0:
                front = text[3:end]
                for line in front.splitlines():
                    if line.strip().startswith("description:"):
                        desc = line.split(":", 1)[1].strip().strip(">").strip()
                        break
        out.append(
            {
                "id": skill_dir.name,
                "name": skill_dir.name,
                "description": desc or f"Skill bundle at {skill_dir.name}",
                "uri": f"skill://{skill_dir.name}/SKILL.md",
                "path": str(skill_md),
            }
        )
    return out


async def build_capabilities(settings: Settings | None = None) -> dict[str, Any]:
    """Aggregate tools, prompts, skills, depot stats, and feature flags."""
    settings = settings or load_settings()
    tools: list[dict[str, Any]] = list(MCP_TOOLS)
    prompts: list[dict[str, Any]] = list(MCP_PROMPTS)

    try:
        from arxiv_mcp.server import mcp

        listed = await mcp.list_tools()
        runtime_tools: list[dict[str, Any]] = []
        for t in listed:
            name = getattr(t, "name", None) or (t.get("name") if isinstance(t, dict) else None)
            if not name:
                continue
            desc = getattr(t, "description", None) or (t.get("description") if isinstance(t, dict) else "")
            runtime_tools.append({"name": name, "description": desc or "", "source": "runtime"})
        if runtime_tools:
            tools = runtime_tools
    except Exception:
        pass

    stats = corpus.depot_stats(settings)
    rag = stats.get("rag") or {}

    return {
        "service": "arxiv-mcp",
        "version": __version__,
        "fastmcp": ">=3.2.0",
        "transports": {
            "stdio": {"command": "uv", "args": ["run", "python", "-m", "arxiv_mcp", "--stdio"]},
            "streamable_http": {"path": "/mcp", "port": settings.port},
        },
        "webapp": {"url": "http://127.0.0.1:10771", "api_url": f"http://{settings.host}:{settings.port}/api"},
        "tools": tools,
        "tool_count": len(tools),
        "prompts": prompts,
        "prompt_count": len(prompts),
        "skills": _list_skills(),
        "depot": stats,
        "features": {
            "rag_enabled": settings.rag_enabled,
            "rag_available": bool(rag.get("available")),
            "embedding_model": settings.embedding_model,
            "depot_search_mode": settings.depot_search_mode,
            "epistemic_deep_enabled": settings.epistemic_deep_enabled,
            "sampling_configured": bool((settings.sampling_base_url or "").strip()),
            "unpaywall_configured": bool(settings.unpaywall_email.strip()),
            "calibre_configured": settings.calibre_library_path is not None,
        },
        "openapi": {
            "swagger": f"http://{settings.host}:{settings.port}/docs",
            "redoc": f"http://{settings.host}:{settings.port}/redoc",
            "openapi_json": f"http://{settings.host}:{settings.port}/openapi.json",
        },
    }
