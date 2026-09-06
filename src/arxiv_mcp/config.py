"""Runtime configuration for arxiv-mcp."""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    """Repo root, anchored on this module rather than the process CWD.

    Path.cwd() varies by launch method (NSSM AppDirectory, a dev shell, a Claude
    Desktop stdio instance, a scheduled task), so using it for storage defaults
    means the data location silently moves. Path(__file__) does not.

    Walks up to the .git marker rather than using a fixed parents[N] index, because
    this file has a TWIN at mcpb/src/arxiv_mcp/config.py which sits one level deeper.
    A fixed index that is correct for src/ resolves to mcpb/ in the twin, which is
    exactly the kind of silent divergence that caused the 2026-07-26 incident.
    Falls back to the fixed index when there is no .git (installed/packaged copies),
    where data_dir should come from the environment anyway.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists():
            return parent
    return here.parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ARXIV_MCP_",
        # Absolute, not ".env". A relative env_file is resolved against the process
        # CWD, so under a service (or any launcher with a different working dir) the
        # .env silently fails to load and every setting falls back to its default.
        # That is how a config file can appear to be ignored with no error at all.
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        extra="ignore",
    )

    @field_validator("data_dir", "temp_dir", "calibre_library_path", "calibredb_path", mode="before")
    @classmethod
    def _empty_str_is_unset(cls, v):
        """Treat an empty env value as unset.

        `ARXIV_MCP_DATA_DIR=` in a .env file yields "" rather than None. Pydantic
        coerces "" on a `Path | None` field to Path("."), which is NOT None, so the
        `if base is None` fallback in resolved_data_dir() never fires and the data
        directory silently becomes a RELATIVE path that follows the process working
        directory. That forked this repo's corpus.sqlite3 into two files.

        See mcp-central-docs/standards/TRAPS_AND_PITFALLS.md trap 14.
        """
        if isinstance(v, str) and not v.strip():
            return None
        return v

    host: str = "127.0.0.1"
    port: int = 10770
    client_delay_seconds: float = 3.0
    arxiv_max_retries: int = 4
    arxiv_backoff_base_seconds: float = 3.0
    arxiv_backoff_max_seconds: float = 30.0
    fetch_full_text_budget_seconds: float = 90.0
    fetch_full_text_max_bytes: int = 8_000_000
    fetch_full_text_pdf_max_chars: int = 100_000
    http_cache_enabled: bool = True
    data_dir: Path | None = None
    semantic_scholar_api_key: str | None = None
    arxiv_http_timeout_seconds: float = 30.0
    jina_reader_base_url: str = "https://r.jina.ai"
    unpaywall_email: str = ""
    calibre_library_path: Path | None = None
    calibredb_path: Path | None = None
    temp_dir: Path | None = None
    rag_enabled: bool = True
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    depot_search_mode: str = "hybrid"
    epistemic_deep_enabled: bool = True
    sampling_base_url: str | None = None
    sampling_model: str = "llama3.2"
    sampling_api_key: str | None = None
    llm_provider: str = "ollama"
    llm_model: str = "gemma4:12b"
    sampling_max_tokens: int = 2500
    sampling_timeout_seconds: float = 120.0

    # Code-hunt: track open-weight code/repo drops (esp. PRC labs) and push to aiwatcher.
    codehunt_categories: str = "cs.AI,cs.LG,cs.RO,cs.SD"
    # cs.SD (sound/audio): always push code drops - FunASR stack, speech models, etc.
    codehunt_priority_categories: str = "cs.SD"
    codehunt_china_only_push: bool = True
    codehunt_fulltext_max_papers: int = 12
    codehunt_repo_timeout_seconds: float = 12.0
    # JSON file path or data/codehunt/watch_authors.json; see config/codehunt_watch_authors.json
    codehunt_watch_authors_file: str | None = None
    codehunt_watch_authors_extra: str = ""
    codehunt_affiliations_file: str | None = None
    codehunt_affiliation_min_tier: str = "a"
    codehunt_media_enabled: bool = True
    codehunt_media_min_age_days: int = 7
    codehunt_media_max_age_days: int = 45
    codehunt_media_recheck_days: int = 14
    codehunt_media_timeout_seconds: float = 20.0
    codehunt_media_feeds_file: str | None = None
    codehunt_media_feed_cache_hours: int = 6
    # When true (or UI runtime override): Jina Reader enriches snippet-only RSS hits.
    codehunt_media_ignore_botblocks: bool = False
    # Bright Hand (Bright Data Web Unlocker) after Jina fails - billed; needs token + zone.
    codehunt_media_use_brighthand: bool = False
    brightdata_api_token: str | None = None
    brightdata_zone: str | None = None
    brightdata_timeout_seconds: float = 90.0
    publication_subscriptions_file: str | None = None
    publication_expiring_warn_days: int = 7
    publication_fetch_timeout_seconds: float = 45.0
    readly_enabled: bool = False
    readly_mcp_url: str | None = None
    readly_valid_till: str | None = None
    readly_timeout_seconds: float = 120.0
    readly_watch_magazines_file: str | None = None
    readly_ingest_on_depot: bool = False
    readly_ingest_magazines: str = ""
    aiwatcher_base_url: str | None = None
    aiwatcher_api_key: str | None = None

    def codehunt_category_list(self) -> list[str]:
        return [c.strip() for c in self.codehunt_categories.split(",") if c.strip()]

    def codehunt_priority_category_list(self) -> list[str]:
        return [c.strip() for c in self.codehunt_priority_categories.split(",") if c.strip()]

    def parsed_readly_ingest_magazines(self) -> list[str]:
        if not self.readly_ingest_magazines.strip():
            return []
        return [m.strip() for m in self.readly_ingest_magazines.split(",") if m.strip()]

    def resolved_data_dir(self) -> Path:
        base = self.data_dir
        if base is None:
            base = _repo_root() / "data" / "arxiv_mcp"
        base = Path(base).resolve()
        base.mkdir(parents=True, exist_ok=True)
        return base

    def resolved_temp_dir(self) -> Path:
        base = self.temp_dir
        if base is None:
            base = _repo_root() / "data" / "arxiv_mcp" / "tmp"
        base = Path(base).resolve()
        base.mkdir(parents=True, exist_ok=True)
        return base


def load_settings() -> Settings:
    return Settings()
