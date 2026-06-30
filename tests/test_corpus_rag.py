"""Section chunking, epistemic tags, hybrid merge."""

from pathlib import Path

import pytest

from arxiv_mcp.config import Settings
from arxiv_mcp.services import corpus
from arxiv_mcp.services.epistemic_profile import infer_epistemic_mode
from arxiv_mcp.services.vector_rag import rag_deps_available


@pytest.fixture
def tmp_settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path, rag_enabled=False)


def test_section_aware_chunking() -> None:
    md = "## Intro\n\nShort intro.\n\n## Methods\n\n" + ("word " * 400) + "\n\n## Conclusion\n\nDone."
    chunks = corpus._chunk_text(md, size=200, overlap=20)
    assert any("## Intro" in c for c in chunks)
    assert any("## Methods" in c or "word" in c for c in chunks)


def test_epistemic_mode_math() -> None:
    assert infer_epistemic_mode(["math.HO"]) == "formal"


def test_epistemic_mode_astro() -> None:
    assert infer_epistemic_mode(["astro-ph.GA"]) == "observational_instrumental"


def test_hybrid_rrf_prefers_overlap() -> None:
    fts = [
        {"arxiv_id": "a", "chunk_idx": 0, "title": "A", "snippet": "x", "rank": 1.0},
        {"arxiv_id": "b", "chunk_idx": 0, "title": "B", "snippet": "y", "rank": 2.0},
    ]
    sem = [
        {"arxiv_id": "a", "chunk_idx": 0, "title": "A", "snippet": "x", "rank": 0.9},
        {"arxiv_id": "c", "chunk_idx": 1, "title": "C", "snippet": "z", "rank": 0.8},
    ]
    merged = corpus._rrf_merge([fts, sem], limit=2)
    assert merged[0]["arxiv_id"] == "a"


def test_ingest_and_search_fts(tmp_settings: Settings) -> None:
    md = (
        "Abstract. We study gradient methods for large models. "
        "Our contribution is a new optimizer. Experiments on benchmarks show gains.\n\n"
        "## Introduction\n\nDeep learning relies on optimization.\n"
    )
    rec = corpus.ingest_markdown(
        "2401.00001v1",
        "Test Paper",
        md,
        meta={"categories": ["cs.LG"]},
        settings=tmp_settings,
    )
    assert rec["chunks"] >= 1
    assert rec.get("epistemic_mode") == "computational"
    hits = corpus.search_depot_fts("optimizer", limit=10, settings=tmp_settings)
    assert len(hits) >= 1
    assert hits[0]["arxiv_id"] == "2401.00001v1"


@pytest.mark.skipif(not rag_deps_available(), reason="rag extra not installed")
def test_semantic_roundtrip(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, rag_enabled=True)
    md = "## Philosophy\n\nCopernican intelligence and human-centered AI coexistence.\n"
    corpus.ingest_markdown("2603.26524v1", "Tao paper", md, meta={"categories": ["math.HO"]}, settings=settings)
    hits = corpus.search_depot_semantic("human centered artificial intelligence", limit=5, settings=settings)
    assert len(hits) >= 1
    assert hits[0]["arxiv_id"] == "2603.26524v1"
