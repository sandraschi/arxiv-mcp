"""fetch_full_text wall-clock budget (no event-loop hang)."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest

from arxiv_mcp.config import Settings
from arxiv_mcp.html_extract import fetch_html_markdown
from arxiv_mcp.http import HttpPayload


@pytest.mark.asyncio
async def test_fetch_html_markdown_budget_timeout() -> None:
    def slow_convert(html: str) -> tuple[str, dict]:
        time.sleep(2.0)
        return "# converted", {"conversion": "ok"}

    settings = Settings(
        fetch_full_text_budget_seconds=0.2,
        fetch_full_text_max_bytes=8_000_000,
        arxiv_http_timeout_seconds=30.0,
    )

    payload = HttpPayload(
        ok=True,
        status_code=200,
        text="<main><p>section</p></main>",
        content=None,
        headers={"content-type": "text/html"},
        content_type="text/html; charset=utf-8",
        error=None,
    )

    with patch("arxiv_mcp.html_extract._html_to_markdown_with_meta", slow_convert):
        with patch(
            "arxiv_mcp.html_extract.get_text",
            AsyncMock(return_value=payload),
        ):
            ok, msg, status, ctype, meta = await fetch_html_markdown(
                "2509.11766", settings=settings
            )

    assert ok is False
    assert status is None
    assert ctype is None
    assert meta.get("conversion") == "timeout"
    assert "budget" in msg.lower()
