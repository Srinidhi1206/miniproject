"""Application settings.

All configuration comes from environment variables (or a `.env` file at the
repo root / backend dir). Every external integration is optional: with no
configuration at all SENTINEL runs fully offline on SQLite with local models.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent


def _default_models_dir() -> Path:
    # In docker the repo `models/` dir is mounted at /srv/models.
    docker_path = Path("/srv/models")
    return docker_path if docker_path.exists() else REPO_DIR / "models"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(REPO_DIR / ".env"), str(BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    sentinel_env: str = "development"

    database_url: str = ""
    # Exact origins allowed to call the API from a browser (comma-separated).
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Optional regex for extra origins, e.g. Vercel preview deployments:
    #   ^https://miniproject-[a-z0-9-]+-<your-vercel-team>\.vercel\.app$
    cors_origin_regex: str = ""

    max_upload_mb: int = Field(default=8, ge=1, le=50)
    max_text_chars: int = 10_000
    rate_limit_per_minute: int = Field(default=30, ge=1)

    llm_provider: str = "none"  # none | anthropic
    llm_api_key: str = ""
    llm_model: str = "claude-opus-5"

    rag_embeddings: str = "local"
    url_reputation_api_key: str = ""

    models_dir: Path = Field(default_factory=_default_models_dir)
    knowledge_dir: Path = BACKEND_DIR / "knowledge"
    var_dir: Path = BACKEND_DIR / "var"

    @field_validator("llm_provider")
    @classmethod
    def _normalise_provider(cls, v: str) -> str:
        return (v or "none").strip().lower()

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return normalise_database_url(self.database_url)
        self.var_dir.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{(self.var_dir / 'sentinel.db').as_posix()}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def is_dev(self) -> bool:
        return self.sentinel_env.lower() in {"dev", "development", "local"}


def normalise_database_url(url: str) -> str:
    """Hosting providers (Render, Heroku, Neon) hand out `postgres://` or
    `postgresql://` URLs. SQLAlchemy needs the driver named explicitly; SENTINEL
    uses psycopg 3, so rewrite the scheme. Other URLs are returned unchanged."""
    url = url.strip()
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
