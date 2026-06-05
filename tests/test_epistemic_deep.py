"""Deep epistemic analysis (v2): JSON parse, merge, depot filters."""

from pathlib import Path

import pytest

from arxiv_mcp.config import Settings
from arxiv_mcp.services import corpus
from arxiv_mcp.services.epistemic_deep import (
    aggregate_claim_needs,
    merge_profiles,
    parse_deep_analysis_response,
    run_deep_epistemic_analysis,
)
from arxiv_mcp.services.epistemic_profile import build_epistemic_profile


@pytest.fixture
def tmp_settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path, epistemic_deep_enabled=False)


SAMPLE_LLM_JSON = """
{
  "deep_summary": "The paper argues for formal proof culture in AI-assisted mathematics.",
  "claims": [
    {
      "claim": "Proof assistants can verify core lemmas in Mathlib-scale libraries.",
      "evidence_mode": "formal_proof",
      "confidence": "high",
      "needs_human_judgment": true,
      "needs_bench": false,
      "needs_telescope_or_instrument": false,
      "needs_formal_verification": true,
      "needs_simulation_compute": false,
      "falsifier": "A counterexample in a machine-checked formalization",
      "section_hint": "discussion"
    },
    {
      "claim": "Benchmark experiments show optimizer gains on standard ML tasks.",
      "evidence_mode": "computational",
      "confidence": "medium",
      "needs_human_judgment": false,
      "needs_bench": false,
      "needs_telescope_or_instrument": false,
      "needs_formal_verification": false,
      "needs_simulation_compute": true,
      "falsifier": null,
      "section_hint": "results"
    },
    {
      "claim": "Survey telescope data supports the cosmological constant model.",
      "evidence_mode": "observational_instrumental",
      "confidence": "low",
      "needs_human_judgment": true,
      "needs_bench": false,
      "needs_telescope_or_instrument": true,
      "needs_formal_verification": false,
      "needs_simulation_compute": false,
      "falsifier": "New survey contradicting the fit",
      "section_hint": null
    }
  ]
}
"""


def test_parse_deep_analysis_response() -> None:
    parsed = parse_deep_analysis_response(SAMPLE_LLM_JSON)
    assert "formal proof culture" in parsed["deep_summary"].lower()
    assert len(parsed["claims"]) == 3
    assert parsed["claims"][0]["evidence_mode"] == "formal_proof"
    assert parsed["claims"][0]["needs_formal_verification"] is True
    assert parsed["claims"][2]["needs_telescope_or_instrument"] is True


def test_merge_profiles_primary_mode_from_claims() -> None:
    rule = build_epistemic_profile("Lean proof assistant discussion.", categories=["math.HO"])
    deep = parse_deep_analysis_response(SAMPLE_LLM_JSON)
    merged = merge_profiles(rule, deep, model_label="test")
    assert merged["analyzer"] == "rule_v1+test"
    assert merged["primary_mode"] == "formal_proof"
    assert len(merged["claims"]) == 3
    assert merged["aggregate_needs"]["needs_formal_verification"] is True
    assert merged["aggregate_needs"]["needs_telescope_or_instrument"] is True


def test_aggregate_claim_needs_empty() -> None:
    agg = aggregate_claim_needs([])
    assert all(v is False for v in agg.values())


@pytest.mark.asyncio
async def test_run_deep_disabled_returns_rule_only(tmp_settings: Settings) -> None:
    md = "Formal proof in Lean and Mathlib verification."
    profile = await run_deep_epistemic_analysis(
        md,
        title="Test",
        categories=["math.HO"],
        settings=tmp_settings,
    )
    assert profile["analyzer"] == "rule_v1"
    assert profile["claims"] == []


def test_list_ingested_filtered_by_needs(tmp_settings: Settings) -> None:
    md = "Telescope survey data and spectral analysis."
    corpus.ingest_markdown("2401.00010v1", "Astro", md, settings=tmp_settings)
    profile = merge_profiles(
        build_epistemic_profile(md, categories=["astro-ph.GA"]),
        parse_deep_analysis_response(SAMPLE_LLM_JSON),
    )
    corpus.persist_epistemic_profile("2401.00010v1", profile, settings=tmp_settings)

    bench_rows = corpus.list_ingested_filtered(needs_bench=True, settings=tmp_settings)
    assert all(r["arxiv_id"] != "2401.00010v1" for r in bench_rows)

    tel_rows = corpus.list_ingested_filtered(
        needs_telescope_or_instrument=True,
        settings=tmp_settings,
    )
    assert any(r["arxiv_id"] == "2401.00010v1" for r in tel_rows)

    deep_rows = corpus.list_ingested_filtered(has_deep_claims=True, settings=tmp_settings)
    assert deep_rows[0]["claim_count"] == 3


def test_list_ingested_filtered_excludes_unprofiled_positive_filters(tmp_settings: Settings) -> None:
    corpus.ingest_markdown("2401.00011v1", "No profile filters", "Short text.", settings=tmp_settings)
    assert corpus.list_ingested_filtered(needs_formal_verification=True, settings=tmp_settings) == []
    assert corpus.list_ingested_filtered(has_deep_claims=True, settings=tmp_settings) == []
    assert any(
        r["arxiv_id"] == "2401.00011v1"
        for r in corpus.list_ingested_filtered(has_deep_claims=False, settings=tmp_settings)
    )
