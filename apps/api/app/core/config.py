"""Application configuration.

All runtime configuration is read from environment variables (or a `.env` file)
via pydantic-settings. Nothing sensitive is hard-coded: the defaults below are
safe for local development only and the production checks in
`Settings.validate_for_environment` refuse to start with insecure values.
"""

from __future__ import annotations

import json
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["development", "test", "production", "desktop"]
AIProviderName = Literal["anthropic", "mock"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General -------------------------------------------------------------
    app_name: str = "LedgerLens"
    app_env: Environment = "development"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    # --- Security ------------------------------------------------------------
    # In development a random key is generated on every start (sessions do not
    # survive restarts). Production MUST set SECRET_KEY explicitly.
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    refresh_cookie_name: str = "ledgerlens_refresh"
    cookie_secure: bool | None = None  # None -> derived from app_env
    # NoDecode: read the raw string so a comma-separated list works. Without it
    # pydantic-settings expects JSON for list fields and refuses to start.
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    rate_limit_auth_per_minute: int = 10
    rate_limit_ai_per_minute: int = 20

    # --- Database ------------------------------------------------------------
    database_url: str = "sqlite:///./data/ledgerlens.db"

    # --- Storage -------------------------------------------------------------
    upload_dir: Path = Path("./data/uploads")
    max_upload_mb: int = 10

    # --- Frontend ------------------------------------------------------------
    # When set, the API also serves the built web app from this folder (single-process
    # setups such as the Windows desktop program). Normally nginx or Vite serves it.
    frontend_dist: Path | None = None

    # --- AI ------------------------------------------------------------------
    ai_provider: AIProviderName = "mock"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-5"
    anthropic_effort: Literal["low", "medium", "high"] = "medium"
    ai_timeout_seconds: float = 90.0

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        # Accept "https://a.example,https://b.example" and the JSON form '["https://a.example"]'.
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                return json.loads(text)
            return [origin.strip() for origin in text.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_for_environment(self) -> Settings:
        if self.app_env == "production":
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters in production")
            if self.database_url.startswith("sqlite"):
                raise ValueError("Use PostgreSQL (DATABASE_URL) in production, not SQLite")
        if self.ai_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when AI_PROVIDER=anthropic")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cookie_secure_flag(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.is_production

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
