"""DOI content truncation."""

from arxiv_mcp.sanitize import wrap_untrusted


def test_wrap_untrusted_respects_long_text() -> None:
    body = "word " * 20_000
    wrapped = wrap_untrusted(body, "doi_body")
    assert len(wrapped) > 1000


def test_truncation_logic() -> None:
    text = wrap_untrusted("x " * 100, "doi_body")
    cap = 50
    truncated = False
    if len(text) > cap:
        text = text[:cap].rsplit(" ", 1)[0] + " …"
        truncated = True
    assert truncated
    assert len(text) <= cap + 4
