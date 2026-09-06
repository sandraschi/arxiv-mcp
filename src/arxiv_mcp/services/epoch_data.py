"""Epoch AI data service - cached lookup for model/benchmark claims.

Downloads and caches two CSVs from epoch.ai:
  - all_ai_models.csv:  model metadata (parameters, training compute, domain, …)
  - benchmarks.csv:     per-model per-task benchmark scores (mean_score, best_score)

Cache is per-file mtime with 24h TTL.  Refresh on read when stale.
All results carry source attribution per CC-BY 4.0 license.

Usage:
    from arxiv_mcp.services.epoch_data import EpochDataService
    svc = await EpochDataService.create()
    result = await svc.check_benchmark_claim("DeepSeek-V4-Pro", "GPQA diamond", 0.89)
    info = await svc.model_info("DeepSeek-V4-Pro")
"""

from __future__ import annotations

import io
import logging
import re
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from arxiv_mcp.config import Settings, load_settings

log = logging.getLogger("arxiv_mcp.epoch_data")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MODELS_URL = "https://epoch.ai/data/all_ai_models.csv"
_BENCHMARKS_URL = "https://epoch.ai/data/benchmarks.csv"
_EXTERNAL_BENCHMARKS_ZIP_URL = "https://epoch.ai/data/benchmark_data.zip"
_CACHE_TTL_HOURS = 24
_HTTP_TIMEOUT = 60.0
_SOURCE_ATTR = "source: Epoch AI (CC-BY 4.0)"

# External benchmark name -> (csv_filename, score_column, model_column) mapping.
# These are 3rd-party leaderboard CSVs bundled in benchmark_data.zip.
_EXTERNAL_BENCHMARK_MAP: dict[str, tuple[str, str, str]] = {
    "mmlu": ("mmlu_external.csv", "EM", "Model version"),
    "gsm8k": ("gsm8k_external.csv", "EM", "Model version"),
    "arc-agi": ("arc_agi_external.csv", "Score", "Model version"),
    "arc-agi-2": ("arc_agi_2_external.csv", "Score", "Model version"),
    "arc-ai2": ("arc_ai2_external.csv", "Challenge score", "Model version"),
    "hellaswag": ("hella_swag_external.csv", "Overall accuracy", "Model version"),
    "boolq": ("bool_q_external.csv", "Score", "Model version"),
    "piqa": ("piqa_external.csv", "Score", "Model version"),
    "lambada": ("lambada_external.csv", "Score", "Model version"),
    "bbh": ("bbh_external.csv", "Average", "Model version"),
    "livebench": ("live_bench_external.csv", "Global average", "Model version"),
    "simplebench": ("simplebench_external.csv", "Score (AVG@5)", "Model version"),
    "aider": ("aider_polyglot_external.csv", "Percent correct", "Model version"),
    "hle": ("hle_external.csv", "Accuracy", "Model version"),
    "triviaqa": ("trivia_qa_external.csv", "EM", "Model version"),
    "winogrande": ("wino_grande_external.csv", "Accuracy", "Model version"),
    "cybench": ("cybench_external.csv", "Unguided % Solved", "Model version"),
    "arc": ("arc_agi_external.csv", "Score", "Model version"),
    "superglue": ("superglue_external.csv", "Score", "Model version"),
    "cad-eval": ("cad_eval_external.csv", "Overall pass (%)", "Model version"),
    "science-qa": ("science_qa_external.csv", "Score", "Model version"),
    "open-book-qa": ("open_book_qa_external.csv", "Accuracy", "Model version"),
    "geobench": ("geobench_external.csv", "ACW Avg Score", "Model version"),
    "vpct": ("vpct_external.csv", "Correct", "Model version"),
    "gdpval": ("gdpval_external.csv", "Win Rate (%)", "Model version"),
    "gdp-pdf": ("gdp_pdf_external.csv", "GDP.pdf score", "Model version"),
    "webdev-arena": ("webdev_arena_external.csv", "Arena Score", "Model version"),
    "metr": ("metr_time_horizons_external.csv", "Time horizon", "Model version"),
    "frontierswe": ("frontierswe_external.csv", "Dominance", "Model version"),
    "posttrainbench": ("posttrainbench_external.csv", "Average (%)", "Model version"),
    "terminalbench": ("terminalbench_external.csv", "Accuracy mean", "Model version"),
    "gso": ("gso_external.csv", "Score OPT@1", "Model version"),
    "os-world": ("os_world_external.csv", "Score", "Model version"),
    "deepresearchbench": ("deepresearchbench_external.csv", "Average score", "Model version"),
    "gbaeval": ("gbaeval_external.csv", "Overall score", "Model version"),
    "common-sense-qa": ("common_sense_qa_2_external.csv", "Score", "Model version"),
    "video-mme": ("video_mme_external.csv", "Overall (no subtitles)", "Model version"),
    "balrog": ("balrog_external.csv", "Average progress", "Model version"),
    "weirdml": ("weirdml_external.csv", "Accuracy", "Model version"),
    "fiction-livebench": ("fictionlivebench_external.csv", "120k token score", "Model version"),
    "lech-mazur-writing": ("lech_mazur_writing_external.csv", "Mean score", "Model version"),
    "the-agent-company": ("the_agent_company_external.csv", "Score", "Model version"),
}

# Benchmarks tracked in the CSV (cached after first read)
_BENCHMARK_TASKS: list[str] = []

# Regex to normalise model names for fuzzy matching
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
# Strip Epoch API-style suffixes for fuzzy matching
_SUFFIX_RE = re.compile(r"_(xhigh|high|max|none|unknown|medium|low)$", re.IGNORECASE)


def _normalise(name: str) -> str:
    """Lowercase, strip non-alphanumeric separators."""
    return _NON_ALNUM.sub(" ", name.lower()).strip()


def _build_alias_map(models_df: pd.DataFrame) -> dict[str, str]:
    """Build {normalised_human_name: api_style_name_prefix} map.

    Epoch's models CSV uses human-readable names (e.g. 'DeepSeek-V4-Pro')
    while the benchmarks CSV uses API-style names ('deepseek-v4-pro_max').
    This map helps fuzzy-match paper claims against benchmark entries.
    """
    aliases = {}
    for name in models_df["Model"].dropna().unique():
        norm = _normalise(name)
        # Store multiple normalisation levels
        aliases[norm] = name
        # Also store compact form (no spaces at all)
        compact = norm.replace(" ", "")
        if compact != norm:
            aliases[compact] = name
    return aliases


def _parse_date_from_filename(csv_path: Path) -> datetime | None:
    """Read Last-Modified from cached file mtime."""
    if not csv_path.exists():
        return None
    mtime = csv_path.stat().st_mtime
    return datetime.fromtimestamp(mtime, tz=UTC)


def _cache_is_stale(csv_path: Path) -> bool:
    mtime = _parse_date_from_filename(csv_path)
    if mtime is None:
        return True
    return datetime.now(UTC) - mtime > timedelta(hours=_CACHE_TTL_HOURS)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class EpochDataService:
    """Cached Epoch AI data lookup for model benchmarks and metadata."""

    def __init__(
        self,
        cache_dir: Path,
        models_df: pd.DataFrame | None = None,
        benchmarks_df: pd.DataFrame | None = None,
        external_df: pd.DataFrame | None = None,
        alias_map: dict[str, str] | None = None,
    ) -> None:
        self._cache_dir = cache_dir
        self._models_df = models_df
        self._benchmarks_df = benchmarks_df
        self._external_df = external_df
        self._alias_map = alias_map or {}
        self._models_path = cache_dir / "all_ai_models.csv"
        self._benchmarks_path = cache_dir / "benchmarks.csv"
        self._external_path = cache_dir / "benchmark_data.zip"

    # ------------------------------------------------------------------
    # Factory / lifecycle
    # ------------------------------------------------------------------

    @classmethod
    async def create(
        cls,
        settings: Settings | None = None,
        force_refresh: bool = False,
    ) -> EpochDataService:
        settings = settings or load_settings()
        cache_dir = settings.resolved_data_dir() / "epoch"
        cache_dir.mkdir(parents=True, exist_ok=True)

        svc = cls(cache_dir=cache_dir)
        await svc._ensure_data(force=force_refresh)
        return svc

    async def refresh(self) -> None:
        """Force re-download both CSVs."""
        await self._ensure_data(force=True)

    # ------------------------------------------------------------------
    # Public lookup methods
    # ------------------------------------------------------------------

    async def check_benchmark_claim(
        self,
        model_name: str,
        benchmark: str,
        claimed_score: float | None = None,
        tolerance: float = 0.02,
    ) -> dict[str, Any]:
        """Check a claimed benchmark score against Epoch's tracked data.

        Args:
            model_name: Model name as cited in the paper (e.g. 'DeepSeek-V4-Pro',
                       'claude-3-7-sonnet', 'GPT-4o').
            benchmark: Benchmark name (e.g. 'GPQA diamond', 'SWE-Bench verified',
                      'MATH level 5'). Case-insensitive, fuzzy-matched.
            claimed_score: The score the paper claims (0-1 range). If None,
                          only checks whether Epoch tracks this model/benchmark.
            tolerance: Allowed absolute difference between claimed and actual
                      score before flagging a mismatch (default 0.02 = 2pp).

        Returns:
            dict with:
              success: bool
              source: "Epoch AI (CC-BY 4.0)"
              verdict: "match" | "mismatch" | "not_found" | "benchmark_not_tracked"
              claimed_score: float | None
              epoch_score: float | None (best_score from CSV)
              epoch_mean_score: float | None
              epoch_model_name: str | None (canonical name from CSV)
              epoch_benchmark_name: str | None
              matched_by: str - how the model was resolved
              message: human-readable summary
        """
        if self._benchmarks_df is None:
            return {
                "success": False,
                "source": _SOURCE_ATTR,
                "verdict": "not_found",
                "message": "Benchmark data not loaded - call refresh() first.",
            }

        # --- Resolve model ---
        epoch_model, match_method = self._resolve_model(model_name)
        if epoch_model is None:
            return {
                "success": True,
                "source": _SOURCE_ATTR,
                "verdict": "not_found",
                "claimed_score": claimed_score,
                "epoch_score": None,
                "epoch_mean_score": None,
                "epoch_model_name": None,
                "epoch_benchmark_name": None,
                "matched_by": None,
                "message": (
                    f"Model '{model_name}' not found in Epoch AI benchmark database. "
                    f"Epoch tracks {self._benchmarks_df['model'].nunique()} models. "
                    f"{_SOURCE_ATTR}"
                ),
            }

        # --- Resolve benchmark ---
        epoch_benchmark = self._resolve_benchmark(benchmark)
        if epoch_benchmark is None:
            # Fall back to external benchmark CSVs
            external_result = await self._lookup_external_benchmark(model_name, benchmark, claimed_score, tolerance)
            if external_result is not None:
                return external_result
            return {
                "success": True,
                "source": _SOURCE_ATTR,
                "verdict": "benchmark_not_tracked",
                "claimed_score": claimed_score,
                "epoch_score": None,
                "epoch_mean_score": None,
                "epoch_model_name": epoch_model,
                "epoch_benchmark_name": None,
                "matched_by": match_method,
                "message": (
                    f"Benchmark '{benchmark}' not found in Epoch AI database "
                    f"(Epoch-run tasks: {', '.join(sorted(self._benchmarks_df['task'].unique())[:10])}...; "
                    f"external: {len(_EXTERNAL_BENCHMARK_MAP)} benchmarks). "
                    f"{_SOURCE_ATTR}"
                ),
            }

        # --- Lookup score ---
        mask = (self._benchmarks_df["model"].str.lower() == epoch_model.lower()) & (
            self._benchmarks_df["task"].str.lower() == epoch_benchmark.lower()
        )
        matches = self._benchmarks_df[mask]

        if matches.empty:
            return {
                "success": True,
                "source": _SOURCE_ATTR,
                "verdict": "not_found",
                "claimed_score": claimed_score,
                "epoch_score": None,
                "epoch_mean_score": None,
                "epoch_model_name": epoch_model,
                "epoch_benchmark_name": epoch_benchmark,
                "matched_by": match_method,
                "message": (
                    f"Epoch AI tracks both model '{epoch_model}' and benchmark "
                    f"'{epoch_benchmark}', but no score entry exists for this pair. "
                    f"{_SOURCE_ATTR}"
                ),
            }

        row = matches.iloc[0]
        epoch_score = float(row["best_score"]) if pd.notna(row["best_score"]) else None
        epoch_mean = float(row["mean_score"]) if pd.notna(row["mean_score"]) else None

        if claimed_score is None:
            return {
                "success": True,
                "source": _SOURCE_ATTR,
                "verdict": "info_only",
                "claimed_score": None,
                "epoch_score": epoch_score,
                "epoch_mean_score": epoch_mean,
                "epoch_model_name": epoch_model,
                "epoch_benchmark_name": epoch_benchmark,
                "matched_by": match_method,
                "message": (
                    f"Epoch AI records {epoch_model} = {epoch_score:.4f} (best) / "
                    f"{epoch_mean:.4f} (mean) on {epoch_benchmark}. "
                    f"{_SOURCE_ATTR}"
                ),
            }

        # --- Compare ---
        if epoch_score is not None:
            diff = abs(claimed_score - epoch_score)
            if diff <= tolerance:
                verdict = "match"
                msg = (
                    f"Claim of {claimed_score:.4f} on {benchmark} for {model_name} "
                    f"matches Epoch AI record ({epoch_score:.4f}, diff={diff:.4f}). "
                    f"{_SOURCE_ATTR}"
                )
            else:
                verdict = "mismatch"
                msg = (
                    f"Claim of {claimed_score:.4f} on {benchmark} for {model_name} "
                    f"differs from Epoch AI record ({epoch_score:.4f}, diff={diff:.4f}). "
                    f"{_SOURCE_ATTR}"
                )
        else:
            verdict = "info_only"
            msg = f"Epoch AI has no numeric score for {epoch_model} on {epoch_benchmark}. {_SOURCE_ATTR}"

        return {
            "success": True,
            "source": _SOURCE_ATTR,
            "verdict": verdict,
            "claimed_score": claimed_score,
            "epoch_score": epoch_score,
            "epoch_mean_score": epoch_mean,
            "epoch_model_name": epoch_model,
            "epoch_benchmark_name": epoch_benchmark,
            "matched_by": match_method,
            "message": msg,
        }

    async def model_info(self, model_name: str) -> dict[str, Any]:
        """Look up model metadata (parameters, training compute, domain, org).

        Args:
            model_name: Model name (fuzzy-matched against the models CSV).

        Returns:
            dict with success, source, model_name (canonical), parameters,
            training_compute_flop, domain, task, organization, publication_date,
            message.
        """
        if self._models_df is None:
            return {"success": False, "source": _SOURCE_ATTR, "message": "Models data not loaded."}

        norm = _normalise(model_name)
        candidates = []
        for _, row in self._models_df.iterrows():
            name = str(row.get("Model", ""))
            if norm == _normalise(name):
                candidates.append(row)
            elif norm in _normalise(name) or _normalise(name) in norm:
                candidates.append(row)

        if not candidates:
            return {
                "success": True,
                "source": _SOURCE_ATTR,
                "model_name": model_name,
                "message": f"Model '{model_name}' not found in Epoch AI database. {_SOURCE_ATTR}",
            }

        best = candidates[0]
        params = best.get("Parameters")
        flop = best.get("Training compute (FLOP)")

        return {
            "success": True,
            "source": _SOURCE_ATTR,
            "model_name": str(best.get("Model", model_name)),
            "parameters": float(params) if pd.notna(params) else None,
            "training_compute_flop": float(flop) if pd.notna(flop) else None,
            "domain": str(best.get("Domain", "")),
            "task": str(best.get("Task", "")),
            "organization": str(best.get("Organization", "")),
            "publication_date": str(best.get("Publication date", "")),
            "model_accessibility": str(best.get("Model accessibility", "")),
            "message": _SOURCE_ATTR,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def list_available_benchmarks(self) -> dict[str, Any]:
        """List all benchmarks tracked by Epoch AI (primary + external).

        Returns:
            dict with success, source, primary (Epoch-run evals), external (leaderboards).
        """
        primary: list[str] = []
        if self._benchmarks_df is not None:
            primary = sorted(self._benchmarks_df["task"].dropna().unique().tolist())
        return {
            "success": True,
            "source": _SOURCE_ATTR,
            "primary_count": len(primary),
            "primary": primary,
            "external_count": len(_EXTERNAL_BENCHMARK_MAP),
            "external": sorted(_EXTERNAL_BENCHMARK_MAP.keys()),
            "message": (
                f"Epoch AI tracks {len(primary)} primary benchmarks (Epoch-run evals) "
                f"and {len(_EXTERNAL_BENCHMARK_MAP)} external benchmarks (3rd-party leaderboards). "
                f"{_SOURCE_ATTR}"
            ),
        }

    def _resolve_model(self, name: str) -> tuple[str | None, str | None]:
        """Resolve a paper-cited model name to an Epoch benchmarks CSV model name.

        Returns (canonical_name, method_used) or (None, None).
        """
        df = self._benchmarks_df
        if df is None:
            return None, None

        known = df["model"].dropna().unique()

        # 1. Exact (case-insensitive)
        name_lower = name.strip().lower()
        for k in known:
            if k.strip().lower() == name_lower:
                return k, "exact"

        # 2. Normalised (strip all non-alnum separators)
        norm_input = _normalise(name)
        for k in known:
            if _normalise(k) == norm_input:
                return k, "normalised"

        # 3. Prefix: input is a prefix of known name (handles _max, _16k suffixes)
        for k in known:
            k_norm = _normalise(k)
            if k_norm.startswith(norm_input) or norm_input.startswith(k_norm):
                return k, "prefix"

        # 4. Token overlap: Epoch names often have version tokens
        input_tokens = set(norm_input.split())
        for k in known:
            k_tokens = set(_normalise(k).split())
            if len(input_tokens & k_tokens) >= min(2, len(input_tokens), len(k_tokens)):
                return k, "token_overlap"

        # 5. Try alias map (human → API-style name)
        if self._alias_map:
            for api_name in known:
                api_norm = _normalise(api_name)
                alias_norm = _normalise(self._alias_map.get(api_norm, ""))
                if alias_norm and (norm_input == alias_norm or norm_input in alias_norm):
                    return api_name, "alias"

        return None, None

    def _resolve_benchmark(self, name: str) -> str | None:
        """Fuzzy-match a benchmark name against Epoch's task list."""
        if self._benchmarks_df is None:
            return None
        known = self._benchmarks_df["task"].dropna().unique()
        name_lower = name.strip().lower()
        norm_input = _normalise(name)

        for k in known:
            if k.strip().lower() == name_lower:
                return k
        for k in known:
            if _normalise(k) == norm_input:
                return k
        for k in known:
            if norm_input in _normalise(k) or _normalise(k) in norm_input:
                return k
        return None

    async def _ensure_data(self, force: bool = False) -> None:
        """Download CSVs if cache is missing or stale."""
        self._models_df = await self._load_or_fetch(self._models_path, _MODELS_URL, force)
        self._benchmarks_df = await self._load_or_fetch(self._benchmarks_path, _BENCHMARKS_URL, force)
        if self._models_df is not None:
            self._alias_map = _build_alias_map(self._models_df)
        # External benchmarks are lazy-loaded on first lookup, not at startup.

    # ------------------------------------------------------------------
    # External benchmark CSVs (benchmark_data.zip)
    # ------------------------------------------------------------------

    async def _ensure_external_data(self, force: bool = False) -> pd.DataFrame:
        """Download benchmark_data.zip and build a unified external benchmarks DataFrame."""
        if self._external_df is not None and not force:
            return self._external_df

        zip_path = self._external_path
        if not force and zip_path.exists() and not _cache_is_stale(zip_path):
            try:
                self._external_df = pd.read_parquet(self._cache_dir / "external_benchmarks.parquet")
                log.info("Loaded cached external benchmarks (%d rows)", len(self._external_df))
                return self._external_df
            except Exception:
                log.warning("External benchmark parquet missing/corrupt, rebuilding")

        # Download ZIP
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.get(_EXTERNAL_BENCHMARKS_ZIP_URL, follow_redirects=True)
                resp.raise_for_status()
                zip_path.write_bytes(resp.content)
        except Exception as e:
            log.error("Failed to fetch external benchmarks: %s", e)
            if self._external_df is not None:
                return self._external_df
            return pd.DataFrame()

        # Build unified DataFrame
        rows: list[dict[str, Any]] = []
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                for bench_name, (csv_file, score_col, model_col) in _EXTERNAL_BENCHMARK_MAP.items():
                    try:
                        data = zf.read(csv_file)
                    except KeyError:
                        continue
                    try:
                        df = pd.read_csv(io.BytesIO(data))
                    except Exception:
                        log.debug("Failed to read external CSV %s", csv_file, exc_info=True)
                        continue
                    if model_col not in df.columns or score_col not in df.columns:
                        continue
                    for _, row_data in df.iterrows():
                        model = row_data.get(model_col)
                        score = row_data.get(score_col)
                        if pd.isna(model) or pd.isna(score):
                            continue
                        rows.append(
                            {
                                "model": str(model).strip(),
                                "task": bench_name,
                                "best_score": float(score),
                                "source_csv": csv_file,
                            }
                        )
        except Exception as e:
            log.warning("Failed to parse external benchmarks: %s", e)
            if self._external_df is not None:
                return self._external_df
            return pd.DataFrame()

        self._external_df = (
            pd.DataFrame(rows) if rows else pd.DataFrame(columns=["model", "task", "best_score", "source_csv"])
        )
        if not self._external_df.empty:
            self._external_df.to_parquet(self._cache_dir / "external_benchmarks.parquet", index=False)
            log.info(
                "Built external benchmarks: %d rows, %d benchmarks",
                len(self._external_df),
                self._external_df["task"].nunique(),
            )
        return self._external_df

    async def _lookup_external_benchmark(
        self,
        model_name: str,
        benchmark: str,
        claimed_score: float | None = None,
        tolerance: float = 0.02,
    ) -> dict[str, Any] | None:
        """Try to resolve a benchmark claim via external benchmark CSVs.

        Returns None if the benchmark is not in the external map.
        """
        bench_key = benchmark.lower().strip().replace(" ", "-").replace("_", "-")
        if bench_key not in _EXTERNAL_BENCHMARK_MAP:
            return None

        df = await self._ensure_external_data()
        if df.empty:
            return {
                "success": True,
                "source": _SOURCE_ATTR,
                "verdict": "benchmark_not_tracked",
                "claimed_score": claimed_score,
                "epoch_score": None,
                "epoch_mean_score": None,
                "epoch_model_name": None,
                "epoch_benchmark_name": bench_key,
                "matched_by": None,
                "message": (
                    f"External benchmark '{bench_key}' is mapped but Epoch data could not be loaded. {_SOURCE_ATTR}"
                ),
            }

        # Filter to this benchmark
        bench_df = df[df["task"] == bench_key]
        if bench_df.empty:
            return None  # Not in external either - let caller fall through

        # Resolve model
        epoch_model, match_method = self._resolve_external_model(model_name, bench_df)
        if epoch_model is None:
            # Try models CSV for alias
            if self._models_df is not None:
                all_models = sorted(self._models_df["Model"].dropna().unique().tolist())
                norm_input = _normalise(model_name)
                for m in all_models:
                    if norm_input == _normalise(m) or norm_input in _normalise(m):
                        return {
                            "success": True,
                            "source": _SOURCE_ATTR,
                            "verdict": "not_found",
                            "claimed_score": claimed_score,
                            "epoch_score": None,
                            "epoch_mean_score": None,
                            "epoch_model_name": m,
                            "epoch_benchmark_name": bench_key,
                            "matched_by": "models_csv",
                            "message": (
                                f"Model '{m}' found in Epoch AI models database but has no "
                                f"tracked score for external benchmark '{bench_key}'. {_SOURCE_ATTR}"
                            ),
                        }
            return {
                "success": True,
                "source": _SOURCE_ATTR,
                "verdict": "not_found",
                "claimed_score": claimed_score,
                "epoch_score": None,
                "epoch_mean_score": None,
                "epoch_model_name": None,
                "epoch_benchmark_name": bench_key,
                "matched_by": None,
                "message": (
                    f"Model '{model_name}' not found in Epoch AI external benchmark '{bench_key}'. {_SOURCE_ATTR}"
                ),
            }

        # Get best score (latest entry)
        model_rows = bench_df[bench_df["model"] == epoch_model]
        epoch_score = float(model_rows.iloc[0]["best_score"])

        if claimed_score is None:
            return {
                "success": True,
                "source": _SOURCE_ATTR,
                "verdict": "info_only",
                "claimed_score": None,
                "epoch_score": epoch_score,
                "epoch_mean_score": None,
                "epoch_model_name": epoch_model,
                "epoch_benchmark_name": bench_key,
                "matched_by": match_method,
                "message": (
                    f"Epoch AI (external) records {epoch_model} = {epoch_score:.4f} on {bench_key}. {_SOURCE_ATTR}"
                ),
            }

        diff = abs(claimed_score - epoch_score)
        if diff <= tolerance:
            return {
                "success": True,
                "source": _SOURCE_ATTR,
                "verdict": "match",
                "claimed_score": claimed_score,
                "epoch_score": epoch_score,
                "epoch_mean_score": None,
                "epoch_model_name": epoch_model,
                "epoch_benchmark_name": bench_key,
                "matched_by": match_method,
                "message": (
                    f"Claim of {claimed_score:.4f} on {bench_key} for {model_name} "
                    f"matches Epoch AI external record ({epoch_score:.4f}, diff={diff:.4f}). "
                    f"{_SOURCE_ATTR}"
                ),
            }
        direction = "higher" if claimed_score > epoch_score else "lower"
        return {
            "success": True,
            "source": _SOURCE_ATTR,
            "verdict": "mismatch",
            "claimed_score": claimed_score,
            "epoch_score": epoch_score,
            "epoch_mean_score": None,
            "epoch_model_name": epoch_model,
            "epoch_benchmark_name": bench_key,
            "matched_by": match_method,
            "message": (
                f"Claim of {claimed_score:.4f} on {bench_key} for {model_name} "
                f"differs from Epoch AI external record ({epoch_score:.4f}, diff={diff:.4f}, "
                f"claimed is {direction}). {_SOURCE_ATTR}"
            ),
        }

    def _resolve_external_model(self, name: str, bench_df: pd.DataFrame) -> tuple[str | None, str | None]:
        """Resolve model name against external benchmark DataFrame."""
        known = bench_df["model"].dropna().unique()
        name_lower = name.strip().lower()
        norm_input = _normalise(name)

        # 1. Exact
        for k in known:
            if k.strip().lower() == name_lower:
                return k, "exact"

        # 2. Normalised
        for k in known:
            if _normalise(k) == norm_input:
                return k, "normalised"

        # 3. Strip suffix (_xhigh, _max, etc.) and compare
        stripped_input = _SUFFIX_RE.sub("", norm_input)
        for k in known:
            k_norm = _normalise(k)
            k_stripped = _SUFFIX_RE.sub("", k_norm)
            if k_stripped == stripped_input or stripped_input in k_stripped or k_stripped in stripped_input:
                return k, "prefix_nosuffix"

        # 4. Token overlap
        input_tokens = set(norm_input.split())
        for k in known:
            k_tokens = set(_normalise(k).split())
            if len(input_tokens & k_tokens) >= min(2, len(input_tokens), len(k_tokens)):
                return k, "token_overlap"

        # 5. Alias map
        if self._alias_map:
            alias_norm = _normalise(self._alias_map.get(norm_input, ""))
            if alias_norm:
                for k in known:
                    if _normalise(k) == alias_norm:
                        return k, "alias"

        return None, None

    async def _load_or_fetch(
        self,
        path: Path,
        url: str,
        force: bool,
    ) -> pd.DataFrame | None:
        if not force and path.exists() and not _cache_is_stale(path):
            try:
                df = pd.read_csv(path)
                log.info("Loaded cached %s (%d rows)", path.name, len(df))
                return df
            except Exception:
                log.warning("Cache corrupted for %s, re-fetching", path.name)

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.get(url, follow_redirects=True)
                resp.raise_for_status()
                content = resp.text
        except Exception as e:
            log.error("Failed to fetch %s: %s", url, e)
            if path.exists():
                log.info("Falling back to stale cache for %s", path.name)
                return pd.read_csv(path)
            return None

        path.write_text(content, encoding="utf-8")
        df = pd.read_csv(path)
        log.info("Downloaded %s (%d rows)", path.name, len(df))
        return df


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

_service_instance: EpochDataService | None = None


async def get_service(force_refresh: bool = False) -> EpochDataService:
    global _service_instance
    if _service_instance is None or force_refresh:
        _service_instance = await EpochDataService.create(force_refresh=force_refresh)
    return _service_instance
