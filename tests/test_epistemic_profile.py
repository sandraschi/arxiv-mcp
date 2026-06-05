"""Epistemic profile classification."""

from arxiv_mcp.services.epistemic_profile import build_epistemic_profile


def test_tao_paper_formal_dominant() -> None:
    md = """
## Abstract
We argue artificial intelligence should remain human-centered while integrating into mathematics.

## Proof standards
Mathematical proof has an objective standard starting with Euclid. Formal proof assistants such as Lean
and Mathlib can verify arguments. The smell test guides mathematicians before line-by-line checking.

## Experiments
We ran computational experiments on benchmark datasets.
"""
    profile = build_epistemic_profile(md, categories=["math.HO"], title="Tao AI paper")
    assert profile["primary_mode"] in {"formal_proof", "mixed"}
    assert profile["evidence_signals"]["formal_proof"] > 0.1
    kinds = {x["kind"] for x in profile["still_needs_human_or_physical"]}
    assert "human_judgment" in kinds or "formal_tooling" in kinds


def test_astro_observational() -> None:
    md = "We analyze survey data from the telescope archive and fit light curves to observed spectra."
    profile = build_epistemic_profile(md, categories=["astro-ph.GA"])
    assert profile["primary_mode"] == "observational_instrumental"
    assert any(x["kind"] == "telescope_or_instrument" for x in profile["still_needs_human_or_physical"])


def test_wet_lab_interventional() -> None:
    md = "We performed a randomized clinical trial with in vitro cell culture and CRISPR knockout validation."
    profile = build_epistemic_profile(md, categories=["q-bio.BM"])
    assert profile["primary_mode"] == "interventional_experiment"
    assert any(x["kind"] == "bench" for x in profile["still_needs_human_or_physical"])
