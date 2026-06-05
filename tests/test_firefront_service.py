"""Firefront scan digest writer."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from arxiv_mcp.config import Settings
from arxiv_mcp.firefront_service import run_firefront_scan
from arxiv_mcp.services.papers import PaperSummary


@pytest.mark.asyncio
async def test_run_firefront_scan_writes_digest(tmp_path) -> None:
    fake = PaperSummary(
        paper_id="2401.00001",
        title="Test",
        authors=["A"],
        summary="Abstract",
        categories=["cs.AI"],
        published="2024-01-01T00:00:00+00:00",
        updated=None,
        pdf_url=None,
        abs_url="https://arxiv.org/abs/2401.00001",
        html_url="https://arxiv.org/html/2401.00001",
    )

    with patch(
        "arxiv_mcp.firefront_service.papers.list_category_latest",
        AsyncMock(return_value=[fake]),
    ):
        result = await run_firefront_scan(
            "consciousness",
            categories=["cs.AI"],
            days=3,
            settings=Settings(data_dir=tmp_path),
        )

    assert result["success"] is True
    assert result["paper_count"] == 1
    assert result["digest_path"]
    from pathlib import Path

    assert Path(result["digest_path"]).is_file()
