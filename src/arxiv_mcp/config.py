"""Runtime configuration for arxiv-mcp."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ARXIV_MCP_",
        env_file=".env",
        extra="ignore",
    )

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
    sampling_max_tokens: int = 2500
    sampling_timeout_seconds: float = 120.0

    # Code-hunt: track open-weight code/repo drops (esp. PRC labs) and push to aiwatcher.
    codehunt_categories: str = "cs.AI,cs.LG,cs.RO,cs.SD"
    # cs.SD (sound/audio): always push code drops — FunASR stack, speech models, etc.
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
    # Bright Hand (Bright Data Web Unlocker) after Jina fails — billed; needs token + zone.
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
            base = Path.cwd() / "data" / "arxiv_mcp"
        base.mkdir(parents=True, exist_ok=True)
        return base

    def resolved_temp_dir(self) -> Path:
        base = self.temp_dir
        if base is None:
            base = Path.cwd() / "data" / "arxiv_mcp" / "tmp"
        base.mkdir(parents=True, exist_ok=True)
        return base


def load_settings() -> Settings:
    return Settings()
