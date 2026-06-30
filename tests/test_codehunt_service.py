"""Unit tests for code-hunt extraction and push policy."""

from __future__ import annotations

import json

import pytest

from arxiv_mcp.codehunt_service import (
    _classify_china,
    _extract_repo_links,
    _has_promise,
    _should_push_finding,
    _vla_signal,
)
from arxiv_mcp.codehunt_watch_authors import classify_watch_authors, clear_watch_author_cache
from arxiv_mcp.config import load_settings


def test_extract_repo_links_gitee_and_hf():
    text = "Weights: https://huggingface.co/Qwen/Qwen-Audio code at https://gitee.com/qwen/audio"
    urls = {x["url"] for x in _extract_repo_links(text)}
    assert "https://huggingface.co/Qwen/Qwen-Audio" in urls
    assert "https://gitee.com/qwen/audio" in urls


def test_promise_detection():
    assert _has_promise("The code will be made publicly available upon acceptance.")


def test_cs_sd_pushes_without_china_signal(monkeypatch):
    monkeypatch.setenv("ARXIV_MCP_CODEHUNT_CHINA_ONLY_PUSH", "1")
    monkeypatch.setenv("ARXIV_MCP_CODEHUNT_PRIORITY_CATEGORIES", "cs.SD")
    settings = load_settings()
    finding = {"china_signal": False, "categories": ["cs.SD"]}
    assert _should_push_finding(finding, settings) is True
    assert _should_push_finding({"china_signal": False, "categories": ["cs.CV"]}, settings) is False


def test_watch_author_matches_and_pushes(monkeypatch):
    monkeypatch.setenv("ARXIV_MCP_CODEHUNT_CHINA_ONLY_PUSH", "1")
    clear_watch_author_cache()
    settings = load_settings()
    hits = classify_watch_authors(["Yann LeCun", "Someone Else"], settings=settings)
    assert "Yann LeCun" in hits
    finding = {
        "china_signal": False,
        "categories": ["cs.CV"],
        "watch_author_signal": True,
        "watch_authors": hits,
        "title": "A new architecture",
    }
    assert _should_push_finding(finding, settings) is True


def test_vla_title_pushes_without_china(monkeypatch):
    monkeypatch.setenv("ARXIV_MCP_CODEHUNT_CHINA_ONLY_PUSH", "1")
    settings = load_settings()
    finding = {
        "china_signal": False,
        "categories": ["cs.CV"],
        "title": "Wall-OSS: Open Vision-Language-Action for Manipulation",
    }
    assert _vla_signal(finding) is True
    assert _should_push_finding(finding, settings) is True


def test_china_terms_include_funasr():
    terms = _classify_china("We use FunASR from Alibaba DAMO for ASR.")
    assert "funasr" in terms or "alibaba" in terms


@pytest.mark.asyncio
async def test_run_codehunt_scan_persists_finding(tmp_path, monkeypatch):
    monkeypatch.setenv("ARXIV_MCP_DATA_DIR", str(tmp_path))
    from arxiv_mcp.codehunt_service import run_codehunt_scan
    from arxiv_mcp.config import load_settings
    from arxiv_mcp.services import papers

    class FakePaper:
        paper_id = "2401.00099"
        title = "Speech model"
        authors = ["A Author"]
        summary = "Code will be made publicly available. https://github.com/alibaba-damo-academy/FunASR"
        categories = ["cs.SD"]
        published = "2024-01-02"
        updated = "2024-01-02"
        pdf_url = "https://arxiv.org/pdf/2401.00099"
        abs_url = "https://arxiv.org/abs/2401.00099"
        html_url = "https://arxiv.org/html/2401.00099"

    async def fake_list(cat, limit, hours, settings=None):
        return [FakePaper()]

    monkeypatch.setattr(papers, "list_category_latest", fake_list)
    settings = load_settings()
    result = await run_codehunt_scan(
        categories=["cs.SD"],
        days=1,
        limit_per_category=5,
        push=False,
        settings=settings,
    )
    assert result["new_findings"]
    assert result["new_findings"][0]["priority_category"] is True
    db_file = tmp_path / "codehunt" / "tracking.sqlite3"
    assert db_file.exists()

    digest_dir = tmp_path / "codehunt"
    digests = list(digest_dir.glob("digest_codehunt_*.json"))
    assert digests
    payload = json.loads(digests[0].read_text(encoding="utf-8"))
    assert payload["new_findings"]
