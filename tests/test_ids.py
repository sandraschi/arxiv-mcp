import pytest

from arxiv_mcp.ids import normalize_arxiv_id


def test_normalize_bare() -> None:
    assert normalize_arxiv_id("2401.00001v2") == "2401.00001v2"


def test_normalize_prefix() -> None:
    assert normalize_arxiv_id("arxiv:2401.00001") == "2401.00001"


def test_normalize_abs_url() -> None:
    u = "https://arxiv.org/abs/2401.00001v1"
    assert normalize_arxiv_id(u) == "2401.00001v1"


def test_normalize_bad() -> None:
    with pytest.raises(ValueError):
        normalize_arxiv_id("not-an-id")
