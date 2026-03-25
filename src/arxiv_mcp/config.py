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
    client_delay_seconds: float = 1.0
    data_dir: Path | None = None
    semantic_scholar_api_key: str | None = None
    arxiv_http_timeout_seconds: float = 30.0
    jina_reader_base_url: str = "https://r.jina.ai"

    def resolved_data_dir(self) -> Path:
        base = self.data_dir
        if base is None:
            base = Path.cwd() / "data" / "arxiv_mcp"
        base.mkdir(parents=True, exist_ok=True)
        return base


def load_settings() -> Settings:
    return Settings()
