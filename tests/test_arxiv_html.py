"""Unit tests for arxiv.org HTML helpers."""

from __future__ import annotations

import pytest

from arxiv_mcp.arxiv_html import (
    arxiv_abs_metadata_from_html,
    arxiv_org_search_html,
    extract_paper_id_loose,
    list_categories_payload,
    list_categories_response,
    parse_search_results,
)


def test_extract_paper_id_loose_bare() -> None:
    assert extract_paper_id_loose("2401.00001v2") == "2401.00001v2"


def test_extract_paper_id_loose_abs_url() -> None:
    assert extract_paper_id_loose("https://arxiv.org/abs/2401.00001") == "2401.00001"


def test_list_categories_sorted_and_nonempty() -> None:
    cats = list_categories_payload()
    assert len(cats) >= 30
    keys = [(c["group"], c["code"]) for c in cats]
    assert keys == sorted(keys)


def test_list_categories_response_shape() -> None:
    r = list_categories_response()
    assert r["success"] is True
    assert len(r["categories"]) >= 30


def test_parse_search_results_minimal() -> None:
    html = """
    <div class="arxiv-result">
      <p class="title">Test Title</p>
      <span class="abstract">Abstract: Hello world.</span>
      <span class="list-title"><span><a href="/abs/2401.00001">link</a></span></span>
      <div class="authors"><a>Alice</a></div>
      <span class="tag is-small">cs.AI</span>
    </div>
    """
    out = parse_search_results(html, "q", 1, 25)
    assert out["query"] == "q"
    assert len(out["papers"]) == 1
    p = out["papers"][0]
    assert p["id_arxiv"] == "2401.00001"
    assert "Hello" in p["abstract"]
    ps = out["parse_stats"]
    assert ps["blocks_seen"] == 1
    assert ps["parsed_ok"] == 1
    assert ps["parse_failed"] == 0


def test_parse_search_results_unwrapped_for_human_ui() -> None:
    html = """
    <div class="arxiv-result">
      <p class="title">Test Title</p>
      <span class="abstract">Abstract: Hello world.</span>
      <span class="list-title"><span><a href="/abs/2401.00001">link</a></span></span>
      <div class="authors"><a>Alice</a></div>
      <span class="tag is-small">cs.AI</span>
    </div>
    """
    out = parse_search_results(html, "q", 1, 25, wrap=False)
    p = out["papers"][0]
    assert p["title"] == "Test Title"
    assert "UNTRUSTED" not in p["title"]
    assert "UNTRUSTED" not in p["abstract"]
    wrapped = parse_search_results(html, "q", 1, 25)
    assert "UNTRUSTED" in wrapped["papers"][0]["title"]


def test_advanced_result_to_paper_card_shape() -> None:
    from arxiv_mcp.arxiv_html import advanced_result_to_paper_card

    card = advanced_result_to_paper_card(
        {
            "id_arxiv": "1706.03762",
            "title": "Attention Is All You Need",
            "abstract": "We propose the Transformer.",
            "authors": ["Vaswani et al."],
            "categories": ["cs.CL"],
            "url_abstract": "https://arxiv.org/abs/1706.03762",
            "url_pdf": "https://arxiv.org/pdf/1706.03762.pdf",
            "date_published": "12 Jun 2017",
        }
    )
    assert card["paper_id"] == "1706.03762"
    assert card["summary"] == "We propose the Transformer."
    assert card["html_url"] == "https://arxiv.org/abs/1706.03762"
    assert card["pdf_url"].endswith(".pdf")
    assert card["server"] == "arxiv"


@pytest.mark.asyncio
async def test_arxiv_org_search_validation() -> None:
    r = await arxiv_org_search_html("", category=None, author=None)
    assert r["success"] is False
    assert r["error_type"] == "ValidationError"
    assert r["recovery_options"]


@pytest.mark.asyncio
async def test_arxiv_abs_bad_id() -> None:
    r = await arxiv_abs_metadata_from_html("%%%not-an-id%%%")
    assert r["success"] is False
    assert r["error_type"] == "ValidationError"
