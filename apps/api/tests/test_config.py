"""Settings are read from the environment exactly as Docker Compose and .env files set them."""

from __future__ import annotations

import pytest
from app.core.config import Settings


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("http://localhost:8080", ["http://localhost:8080"]),
        ("https://a.example, https://b.example", ["https://a.example", "https://b.example"]),
        ('["https://a.example"]', ["https://a.example"]),
    ],
)
def test_cors_origins_accepts_comma_separated_and_json(monkeypatch, raw, expected) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CORS_ORIGINS", raw)
    assert Settings().cors_origins == expected


def test_production_requires_secret_key_and_postgres(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "short")
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings()
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./data/prod.db")
    with pytest.raises(ValueError, match="PostgreSQL"):
        Settings()
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db:5432/ledgerlens")
    assert Settings().is_production
