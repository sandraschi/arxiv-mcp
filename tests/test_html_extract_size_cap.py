"""fetch_full_text input-size guard before HTML→Markdown conversion."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from arxiv_mcp.config import Settings
from arxiv_mcp.html_extract import fetch_html_markdown
from arxiv_mcp.http import HttpPayload


@pytest.mark.asyncio
async def test_fetch_html_markdown_skips_oversized_body() -> None:
    body = "<main>" + ("x" * 500) + "</main>"
    payload = HttpPayload(
        ok=True,
        status_code=200,
        text=body,
        content=None,
        headers={"content-type": "text/html"},
        content_type="text/html",
        error=None,
    )

    converted: list[str] = []

    def track(html: str) -> tuple[str, dict]:
        converted.append(html)
        return "# md", {"conversion": "ok"}

    settings = Settings(fetch_full_text_max_bytes=100)

    with patch("arxiv_mcp.html_extract._html_to_markdown_with_meta", track):
        with patch(
            "arxiv_mcp.html_extract.get_text",
            AsyncMock(return_value=payload),
        ):
            ok, msg, status, _ctype, meta = await fetch_html_markdown("2401.00001", settings=settings)

    assert ok is False
    assert not converted
    assert "too large" in msg.lower()
    assert status == 200
    assert meta.get("conversion") == "skipped_size"
