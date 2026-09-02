"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_STORAGE = Path(__file__).resolve().parent.parent / "storage"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM providers (set at least one)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # Whisper — tiny is safest on Render free (512MB); use base/small locally
    whisper_model_size: str = "tiny"

    # Storage & processing limits
    storage_dir: Path = _DEFAULT_STORAGE
    max_video_duration_seconds: int = 600
    max_upload_size_mb: int = 500
    highlight_target_duration_seconds: int = 60
    max_concurrent_jobs: int = 2
    max_summary_input_tokens: int = 50_000
    # Skip heavy embedding models (needed on Render free tier ~512MB RAM)
    light_mode: bool = True

    # Database — Supabase Postgres URL preferred; falls back to local SQLite
    database_url: str | None = None
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None

    # CORS / frontend
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @field_validator(
        "openai_api_key",
        "anthropic_api_key",
        "database_url",
        "supabase_url",
        "supabase_service_role_key",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("light_mode", mode="before")
    @classmethod
    def parse_bool(cls, v):
        if isinstance(v, bool):
            return v
        if v is None or (isinstance(v, str) and not v.strip()):
            return True
        if isinstance(v, str):
            return v.strip().lower() in {"1", "true", "yes", "on"}
        return bool(v)

    @field_validator("storage_dir", mode="before")
    @classmethod
    def default_storage_if_empty(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return _DEFAULT_STORAGE
        return v

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            url = self.database_url.strip()
            # Supabase / managed Postgres require TLS from cloud hosts like Render
            if url.startswith(("postgres://", "postgresql://")) and "sslmode=" not in url:
                sep = "&" if "?" in url else "?"
                url = f"{url}{sep}sslmode=require"
            return url
        db_path = Path(self.storage_dir) / "jobs.db"
        return f"sqlite:///{db_path.as_posix()}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_dir = Path(settings.storage_dir)
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    (settings.storage_dir / "uploads").mkdir(parents=True, exist_ok=True)
    return settings
