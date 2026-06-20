"""Rule-based epistemic profile: what kind of knowing a paper requires.

Runs on ingested markdown + arXiv metadata. No LLM required (v1).
Optional deep pass: MCP prompt ``epistemic_profile_prompt`` + host LLM.
"""

from __future__ import annotations

import re
from typing import Any

PRIMARY_MODES = (
    "formal_proof",
    "simulation",
    "computational",
    "observational_instrumental",
    "interventional_experiment",
    "mixed",
)

_SIGNAL_PATTERNS: dict[str, list[str]] = {
    "formal_proof": [
        r"\bproof\b",
        r"\btheorem\b",
        r"\blemma\b",
        r"\baxiom\b",
        r"\bformal(?:ly)?\s+verif",
        r"\blean\b",
        r"\bcoq\b",
        r"\brocq\b",
        r"\bmathlib\b",
        r"\bproof assistant",
    ],
    "simulation": [
        r"\bsimulation\b",
        r"\bsimulated\b",
        r"\bmonte carlo\b",
        r"\bmolecular dynamics\b",
        r"\bnumerical experiment",
        r"\bfinite element",
        r"\blattice\b",
    ],
    "computational": [
        r"\balgorithm\b",
        r"\bbenchmark\b",
        r"\bneural network",
        r"\bdeep learning\b",
        r"\bllm\b",
        r"\bmachine learning\b",
        r"\bcomputational\b",
        r"\bdataset\b",
    ],
    "observational_instrumental": [
        r"\bobserv(?:ed|ation|atory)\b",
        r"\btelescope\b",
        r"\bsurvey\b",
        r"\bcohort\b",
        r"\bspectroscop",
        r"\blight curve",
        r"\bretrospective\b",
        r"\barchival data",
        r"\binstrument\b",
        r"\bdetector\b",
    ],
    "interventional_experiment": [
        r"\brandomized\b",
        r"\bclinical trial",
        r"\bin vitro\b",
        r"\bin vivo\b",
        r"\bintervention\b",
        r"\bcell culture",
        r"\bknockout\b",
        r"\bcrispr\b",
        r"\bbench\b",
        r"\blaboratory experiment",
        r"\bwet lab",
    ],
}

_CATEGORY_BOOST: dict[str, tuple[str, float]] = {
    "math.": ("formal_proof", 0.35),
    "cs.lo": ("formal_proof", 0.25),
    "astro-ph": ("observational_instrumental", 0.4),
    "hep-ex": ("observational_instrumental", 0.35),
    "nucl-ex": ("interventional_experiment", 0.3),
    "physics.comp-ph": ("simulation", 0.35),
    "q-bio": ("interventional_experiment", 0.35),
    "cs.": ("computational", 0.25),
    "stat.": ("computational", 0.2),
}

_HIL_BY_MODE: dict[str, list[dict[str, str]]] = {
    "formal_proof": [
        {
            "kind": "human_judgment",
            "label": "Informal-to-formal translation",
            "detail": "Mapping claims to the intended formal statement (e.g. natural numbers start at 1).",
        },
        {
            "kind": "human_judgment",
            "label": "Insight and proof strategy",
            "detail": "Why the argument works — the 'smell test' beyond line-by-line correctness.",
        },
        {
            "kind": "formal_tooling",
            "label": "Proof assistant (optional)",
            "detail": "Lean/Coq/Rocq for machine-checked certainty; not always deployed.",
        },
    ],
    "simulation": [
        {
            "kind": "compute",
            "label": "Simulation infrastructure",
            "detail": "HPC or specialized numerics; validate against analytic limits or experiment.",
        },
        {
            "kind": "human_judgment",
            "label": "Model fidelity review",
            "detail": "Are boundary conditions and parameters physically plausible?",
        },
    ],
    "computational": [
        {
            "kind": "human_judgment",
            "label": "Evaluation design",
            "detail": "Benchmark choice, leakage checks, and whether metrics match the claim.",
        },
        {
            "kind": "data",
            "label": "Ground-truth labels or held-out data",
            "detail": "Often human-annotated or curated; AI can assist but not fully replace curation.",
        },
    ],
    "observational_instrumental": [
        {
            "kind": "telescope_or_instrument",
            "label": "Observational instrument time",
            "detail": "Survey pipelines, telescopes, detectors, or archival instrument data"
                " — AI analyzes outputs; new targets need observation.",
        },
        {
            "kind": "human_judgment",
            "label": "Systematics and calibration",
            "detail": "Instrument drift, selection effects, and follow-up on interesting candidates.",
        },
    ],
    "interventional_experiment": [
        {
            "kind": "bench",
            "label": "Interventional lab work",
            "detail": "Hands-on protocols, reagents, contamination control"
                " — robotics+AI can close much of this but replication still grounds truth.",
        },
        {
            "kind": "human_judgment",
            "label": "Experimental design & ethics",
            "detail": "Hypothesis, controls, IRB/biosafety — not derivable from text alone.",
        },
    ],
    "mixed": [
        {
            "kind": "human_judgment",
            "label": "Cross-method synthesis",
            "detail": "Paper combines several evidence types; verify each claim against its stated basis.",
        },
    ],
}


def _score_signals(text: str) -> dict[str, float]:
    sample = text.lower()[:120_000]
    scores = {k: 0.0 for k in _SIGNAL_PATTERNS}
    for mode, patterns in _SIGNAL_PATTERNS.items():
        for pat in patterns:
            hits = len(re.findall(pat, sample, flags=re.IGNORECASE))
            if hits:
                scores[mode] += min(hits, 12) * 1.0
    total = sum(scores.values()) or 1.0
    return {k: round(v / total, 4) for k, v in scores.items()}


def _apply_category_boost(scores: dict[str, float], categories: list[str] | None) -> dict[str, float]:
    out = dict(scores)
    for cat in categories or []:
        cl = cat.lower()
        for prefix, (mode, boost) in _CATEGORY_BOOST.items():
            if cl.startswith(prefix) or cl == prefix.rstrip("."):
                out[mode] = out.get(mode, 0.0) + boost
    total = sum(out.values()) or 1.0
    return {k: round(v / total, 4) for k, v in out.items()}


def _primary_mode(scores: dict[str, float]) -> str:
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top_mode, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    if top_score < 0.18:
        return "mixed"
    if top_score - second_score < 0.08 and second_score > 0.12:
        return "mixed"
    return top_mode


def _automation_readiness(primary: str, scores: dict[str, float]) -> str:
    if primary == "formal_proof":
        return "high_verify_medium_discover"
    if primary == "computational":
        return "high_assist_medium_claim"
    if primary == "observational_instrumental":
        return "high_analyze_medium_followup"
    if primary == "simulation":
        return "medium_assist"
    if primary == "interventional_experiment":
        return "low_without_robotics"
    if scores.get("formal_proof", 0) > 0.2 and scores.get("computational", 0) > 0.2:
        return "high_read_verify"
    return "mixed"


def _knowing_requires(primary: str, scores: dict[str, float]) -> list[str]:
    lines: list[str] = []
    if scores.get("formal_proof", 0) > 0.12 or primary == "formal_proof":
        lines.append("Claims rest substantially on deductive proof against shared mathematical foundations.")
    if scores.get("simulation", 0) > 0.12 or primary == "simulation":
        lines.append("Results depend on numerical simulation fidelity and parameter choices.")
    if scores.get("computational", 0) > 0.12 or primary == "computational":
        lines.append("Evidence comes from algorithms, models, or benchmarks on curated data.")
    if scores.get("observational_instrumental", 0) > 0.12 or primary == "observational_instrumental":
        lines.append("Knowledge is anchored in observational or instrument-generated data (not pure deduction).")
    if scores.get("interventional_experiment", 0) > 0.12 or primary == "interventional_experiment":
        lines.append("Claims require causal intervention in physical or biological systems.")
    if not lines:
        lines.append("Evidence mix is heterogeneous — inspect methods section per major claim.")
    return lines


def _summary(primary: str, categories: list[str] | None, still: list[dict[str, str]]) -> str:
    cat = ", ".join(categories or []) or "unknown category"
    top_hil = still[0]["label"] if still else "human review"
    return (
        f"Primary epistemic mode: {primary.replace('_', ' ')} (arXiv: {cat}). "
        f"AI can heavily assist literature extraction and verification where formal or computational; "
        f"physical closure still leans on: {top_hil}."
    )


def build_epistemic_profile(
    markdown: str,
    *,
    categories: list[str] | None = None,
    title: str = "",
) -> dict[str, Any]:
    """Build structured epistemic profile from full text + metadata."""
    scores = _score_signals(markdown)
    scores = _apply_category_boost(scores, categories)
    primary = _primary_mode(scores)

    still = list(_HIL_BY_MODE.get(primary, _HIL_BY_MODE["mixed"]))
    # Add secondary-mode requirements when significant
    for mode, weight in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[1:3]:
        if weight < 0.15 or mode == primary:
            continue
        for item in _HIL_BY_MODE.get(mode, [])[:1]:
            if item not in still:
                still.append(item)

    profile: dict[str, Any] = {
        "analyzer": "rule_v1",
        "primary_mode": primary,
        "evidence_signals": scores,
        "knowing_requires": _knowing_requires(primary, scores),
        "still_needs_human_or_physical": still,
        "automation_readiness": _automation_readiness(primary, scores),
        "summary": _summary(primary, categories, still),
        "title_hint": title[:200] if title else None,
    }
    # Back-compat shorthand used elsewhere
    profile["epistemic_mode"] = _legacy_mode(primary)
    return profile


def _legacy_mode(primary: str) -> str:
    return {
        "formal_proof": "formal",
        "simulation": "computational",
        "computational": "computational",
        "observational_instrumental": "observational_instrumental",
        "interventional_experiment": "experimental_lab",
        "mixed": "mixed",
    }.get(primary, "mixed")


def infer_epistemic_mode(categories: list[str] | None, markdown: str = "") -> str:
    """Legacy single-tag helper — prefer ``build_epistemic_profile``."""
    return build_epistemic_profile(markdown or " ", categories=categories)["epistemic_mode"]
