"""FTS5 depot indexing and search."""

from pathlib import Path

import pytest

from arxiv_mcp.config import Settings
from arxiv_mcp.services import corpus


@pytest.fixture
def tmp_settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path)


def test_ingest_and_search_fts(tmp_settings: Settings) -> None:
    md = (
        "Abstract. We study gradient methods for large models. "
        "Our contribution is a new optimizer. Experiments on benchmarks show gains.\n\n"
        "Introduction. Deep learning relies on optimization.\n"
    )
    corpus.ingest_markdown("2401.00001v1", "Test Paper", md, settings=tmp_settings)
    hits = corpus.search_depot_fts("optimizer", limit=10, settings=tmp_settings)
    assert len(hits) >= 1
    assert hits[0]["arxiv_id"] == "2401.00001v1"


def test_favorites_roundtrip(tmp_settings: Settings) -> None:
    corpus.add_favorite("2401.00002", title="Hello", note="n", settings=tmp_settings)
    rows = corpus.list_favorites(settings=tmp_settings)
    assert len(rows) == 1
    assert rows[0]["arxiv_id"] == "2401.00002"
    assert corpus.remove_favorite("2401.00002", settings=tmp_settings)
    assert corpus.list_favorites(settings=tmp_settings) == []
