"""LLM deep epistemic analysis: per-claim evidence mapping (v2)."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from arxiv_mcp.config import Settings, load_settings
from arxiv_mcp.services.epistemic_profile import PRIMARY_MODES, _legacy_mode, build_epistemic_profile

logger = logging.getLogger(__name__)

EVIDENCE_MODES = PRIMARY_MODES
NEEDS_KEYS = (
    "needs_human_judgment",
    "needs_bench",
    "needs_telescope_or_instrument",
    "needs_formal_verification",
    "needs_simulation_compute",
)

DEEP_SYSTEM_PROMPT = """You are an epistemic analyst for scientific papers.
Extract the paper's major claims and classify each by evidence type.
Output ONLY valid JSON (no markdown fences) matching this schema:
{
  "deep_summary": "2-4 sentences: thesis, evidence basis, what still needs physical or human closure",
  "claims": [
    {
      "claim": "short statement of one substantive claim",
      "evidence_mode": "formal_proof|simulation|computational|observational_instrumental|interventional_experiment|mixed",
      "confidence": "high|medium|low",
      "needs_human_judgment": true,
      "needs_bench": false,
      "needs_telescope_or_instrument": false,
      "needs_formal_verification": false,
      "needs_simulation_compute": false,
      "falsifier": "what observation or experiment would refute this claim, or null",
      "section_hint": "methods|results|discussion|introduction or null"
    }
  ]
}
Rules:
- 3 to 8 claims; prefer distinctive claims over boilerplate.
- Distinguish philosophical/normative claims from empirical ones.
- needs_bench=true when causal wet-lab or interventional biology/chemistry is required to establish the claim.
- needs_telescope_or_instrument=true when new observational data or instrument time is required (includes large survey follow-up).
- needs_formal_verification=true when machine-checked proof or rigorous formalization is the closure path.
- needs_simulation_compute=true when credible closure requires running simulations or large compute.
- needs_human_judgment=true when taste, ethics, interpretation, or proof-strategy judgment remains essential.
- Do NOT treat AI automation as impossible; flag what closure modality the claim still requires today."""


def epistemic_profile_prompt_text(paper_id: str | None = None, max_claims: int = 8) -> str:
    """Text for MCP prompt ``epistemic_profile_prompt``."""
    pid = paper_id or "<paper_id>"
    return (
        "Deep epistemic analysis workflow:\n"
        f"1. ingest_and_analyze_paper('{pid}') or ensure paper is in depot with full text (HTML preferred).\n"
        "2. deep_analyze_paper_epistemics(paper_id) for LLM claim-level profile (or use this prompt with host LLM).\n"
        "3. Read epistemic_profile.claims[] — each maps a claim to evidence_mode and physical/human loop flags.\n"
        "4. search_depot_corpus / list_depot_by_epistemics to compare papers by knowing type.\n\n"
        f"Extract up to {max_claims} major claims. For each: evidence_mode, falsifier, and whether closure needs "
        "bench, telescope/instrument, formal verification, simulation, or human judgment.\n"
        "Use fetch_full_text for source text. Merge with rule-based profile; do not over-generalize from one field."
    )


def _extract_json_object(text: str) -> dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("No JSON object in model output")
    return json.loads(raw[start : end + 1])


def _normalize_claim(raw: dict[str, Any]) -> dict[str, Any]:
    mode = str(raw.get("evidence_mode", "mixed")).lower().replace(" ", "_")
    if mode not in EVIDENCE_MODES:
        mode = "mixed"
    conf = str(raw.get("confidence", "medium")).lower()
    if conf not in {"high", "medium", "low"}:
        conf = "medium"
    out: dict[str, Any] = {
        "claim": str(raw.get("claim", "")).strip()[:500],
        "evidence_mode": mode,
        "confidence": conf,
        "falsifier": (str(raw["falsifier"]).strip()[:400] if raw.get("falsifier") else None),
        "section_hint": (str(raw["section_hint"]).strip()[:80] if raw.get("section_hint") else None),
    }
    for key in NEEDS_KEYS:
        out[key] = bool(raw.get(key, False))
    return out


def parse_deep_analysis_response(text: str) -> dict[str, Any]:
    data = _extract_json_object(text)
    claims_raw = data.get("claims") or []
    if not isinstance(claims_raw, list):
        claims_raw = []
    claims = [_normalize_claim(c) for c in claims_raw if isinstance(c, dict) and c.get("claim")]
    return {
        "deep_summary": str(data.get("deep_summary", "")).strip()[:1200],
        "claims": claims[:8],
    }


def aggregate_claim_needs(claims: list[dict[str, Any]]) -> dict[str, bool]:
    agg = {k: False for k in NEEDS_KEYS}
    for c in claims:
        for k in NEEDS_KEYS:
            if c.get(k):
                agg[k] = True
    return agg


def merge_profiles(
    rule_profile: dict[str, Any],
    deep: dict[str, Any],
    *,
    model_label: str = "llm_v2",
) -> dict[str, Any]:
    """Merge rule-based v1 profile with LLM claim table."""
    claims = deep.get("claims") or []
    merged = dict(rule_profile)
    merged["analyzer"] = f"rule_v1+{model_label}"
    merged["deep_summary"] = deep.get("deep_summary") or merged.get("summary")
    merged["claims"] = claims
    merged["aggregate_needs"] = aggregate_claim_needs(claims)
    if claims:
        mode_counts: dict[str, int] = {}
        for c in claims:
            m = c.get("evidence_mode", "mixed")
            mode_counts[m] = mode_counts.get(m, 0) + 1
        top = max(mode_counts.items(), key=lambda kv: kv[1])[0]
        if mode_counts[top] >= 2:
            merged["primary_mode"] = top
            merged["epistemic_mode"] = _legacy_mode(top)
    return merged


def build_analysis_prompt(markdown: str, *, title: str, categories: list[str] | None) -> str:
    excerpt = markdown[:48_000]
    cats = ", ".join(categories or []) or "unknown"
    return f"Title: {title}\narXiv categories: {cats}\n\nPaper text (markdown excerpt):\n{excerpt}\n\nReturn JSON only."


async def http_llm_complete(
    user_message: str,
    *,
    system_prompt: str = DEEP_SYSTEM_PROMPT,
    settings: Settings | None = None,
) -> str:
    settings = settings or load_settings()
    base = (settings.sampling_base_url or "").strip()
    if not base:
        raise RuntimeError(
            "No LLM endpoint configured. Set ARXIV_MCP_SAMPLING_BASE_URL (OpenAI-compatible, e.g. http://localhost:11434/v1)."
        )
    url = f"{base.rstrip('/')}/chat/completions"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.sampling_api_key:
        headers["Authorization"] = f"Bearer {settings.sampling_api_key}"
    payload = {
        "model": settings.sampling_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.2,
        "max_tokens": settings.sampling_max_tokens,
    }
    async with httpx.AsyncClient(timeout=settings.sampling_timeout_seconds) as client:
        resp = await client.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("LLM returned no choices")
    return str(choices[0].get("message", {}).get("content", ""))


SampleFn = Callable[[str, str], Awaitable[str]]


async def run_deep_epistemic_analysis(
    markdown: str,
    *,
    title: str,
    categories: list[str] | None = None,
    sample_fn: SampleFn | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Run LLM claim extraction and merge with rule profile."""
    settings = settings or load_settings()
    rule = build_epistemic_profile(markdown, categories=categories, title=title)
    if not settings.epistemic_deep_enabled:
        rule["analyzer"] = "rule_v1"
        rule["claims"] = []
        rule["aggregate_needs"] = aggregate_claim_needs([])
        return rule

    prompt = build_analysis_prompt(markdown, title=title, categories=categories)
    if sample_fn is not None:
        raw = await sample_fn(prompt, DEEP_SYSTEM_PROMPT)
        model_label = "mcp_sample"
    else:
        raw = await http_llm_complete(prompt, settings=settings)
        model_label = settings.sampling_model

    deep = parse_deep_analysis_response(raw)
    return merge_profiles(rule, deep, model_label=model_label)


async def make_mcp_sample_fn(ctx: Any) -> SampleFn:
    async def _sample(user_message: str, system_prompt: str) -> str:
        result = await ctx.sample(
            messages=user_message,
            system_prompt=system_prompt,
            max_tokens=2500,
        )
        return getattr(result, "text", None) or str(result)

    return _sample
