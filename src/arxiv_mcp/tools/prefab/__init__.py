"""Prefab UI tools for arxiv-mcp (optional — requires prefab-ui>=0.14.0).

Install: uv sync --extra apps
Disable: set ARXIV_PREFAB_APPS=0
"""

from __future__ import annotations

import logging

log = logging.getLogger("arxiv_mcp.prefab")


def register_prefab_tools(mcp) -> None:  # noqa: ANN001
    """Register all @mcp.tool(app=True) prefab tools.

    Called from register_tools() inside try/except so optional deps never
    break core tools.
    """
    import os

    if os.environ.get("ARXIV_PREFAB_APPS", "1") == "0":
        log.info("ARXIV_PREFAB_APPS=0 — prefab tools skipped.")
        return

    try:
        from arxiv_mcp.tools.prefab.paper_card import register_paper_card_tool

        register_paper_card_tool(mcp)
        log.info("arxiv-mcp prefab tools registered.")
    except ImportError as e:
        log.info("prefab-ui not installed — prefab tools skipped. (%s)", e)
