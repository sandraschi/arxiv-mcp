"""Help content and topic index."""

from __future__ import annotations

from arxiv_mcp.help_content import get_help


def test_help_index_lists_topics():
    out = get_help(None)
    assert out["success"] is True
    assert "codehunt" in out["topics"]
    assert "api_keys" in out["topics"]


def test_help_codehunt_loads():
    out = get_help("codehunt")
    assert out["success"] is True
    assert "code-hunt" in out["markdown"].lower() or "Code-hunt" in out["markdown"]


def test_help_unknown_topic():
    out = get_help("not_a_real_topic_xyz")
    assert out["success"] is False
