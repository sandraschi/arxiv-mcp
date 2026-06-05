"""On-disk HTTP cache under resolved_data_dir."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from arxiv_mcp.config import Settings
from arxiv_mcp.http import get_text


@pytest.mark.asyncio
async def test_get_text_uses_disk_cache(tmp_path) -> None:
    settings = Settings(
        data_dir=tmp_path,
        http_cache_enabled=True,
        arxiv_max_retries=0,
    )
    url = "https://example.test/cached-page"

    mock_client = AsyncMock()
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html>live</html>"
    mock_resp.headers = {"content-type": "text/html"}
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("arxiv_mcp.http.httpx.AsyncClient", return_value=mock_client):
        first = await get_text(url, settings=settings, cache_endpoint="test")
        second = await get_text(url, settings=settings, cache_endpoint="test")

    assert first.ok and first.text == "<html>live</html>"
    assert second.ok and second.from_cache
    assert second.text == "<html>live</html>"
    assert mock_client.get.await_count == 1
