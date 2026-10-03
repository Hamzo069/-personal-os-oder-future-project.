"""The Alembic migrations must produce exactly the schema the models describe."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.core.db import Base
from app.core.migrations import (
    DatabaseNotMigratedError,
    ensure_database_schema,
    has_pending_migrations,
)
from sqlalchemy import create_engine, inspect

API_DIR = Path(__file__).resolve().parents[1]


def test_migrations_create_all_model_tables(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    db_url = f"sqlite:///{tmp_path / 'migrated.db'}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    from app.core import config

    config.get_settings.cache_clear()
    try:
        cfg = Config(str(API_DIR / "alembic.ini"))
        cfg.set_main_option("script_location", str(API_DIR / "alembic"))
        command.upgrade(cfg, "head")
    finally:
        config.get_settings.cache_clear()

    inspector = inspect(create_engine(db_url))
    migrated = set(inspector.get_table_names()) - {"alembic_version"}
    assert migrated == set(Base.metadata.tables)
    tx_columns = {c["name"] for c in inspector.get_columns("transactions")}
    assert {"amount", "vat_rate", "category_id", "receipt_id"} <= tx_columns


def test_startup_check_applies_migrations_in_development(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    db_url = f"sqlite:///{tmp_path / 'fresh.db'}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    from app.core import config

    config.get_settings.cache_clear()
    try:
        engine = create_engine(db_url)
        assert has_pending_migrations(engine)
        ensure_database_schema(engine, auto_upgrade=True)
        assert not has_pending_migrations(engine)
        assert "users" in inspect(engine).get_table_names()
        ensure_database_schema(engine, auto_upgrade=False)  # up to date: no error
    finally:
        config.get_settings.cache_clear()


def test_startup_check_refuses_unmigrated_database_in_production(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    with pytest.raises(DatabaseNotMigratedError, match="alembic upgrade head"):
        ensure_database_schema(engine, auto_upgrade=False)
    assert inspect(engine).get_table_names() == []


def _offline_sql(monkeypatch, database_url: str) -> str:  # type: ignore[no-untyped-def]
    """The SQL `alembic upgrade head --sql` would emit; needs no database connection."""
    import io

    monkeypatch.setenv("DATABASE_URL", database_url)
    from app.core import config

    config.get_settings.cache_clear()
    try:
        cfg = Config(str(API_DIR / "alembic.ini"))
        cfg.set_main_option("script_location", str(API_DIR / "alembic"))
        cfg.output_buffer = io.StringIO()
        command.upgrade(cfg, "head", sql=True)
        return cfg.output_buffer.getvalue()
    finally:
        config.get_settings.cache_clear()


def test_postgres_migrations_enable_row_level_security(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    sql = _offline_sql(monkeypatch, "postgresql+psycopg://u:pw@localhost:5432/db")
    assert "CREATE TABLE users" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql


def test_sqlite_migrations_skip_row_level_security(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    sql = _offline_sql(monkeypatch, "sqlite:///./unused.db")
    assert "CREATE TABLE users" in sql
    assert "ROW LEVEL SECURITY" not in sql


def test_database_url_with_percent_encoded_password(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Cloud providers hand out passwords with characters that must be URL-encoded (% in the URL).
    Alembic's ConfigParser used to reject those with 'invalid interpolation syntax'."""
    sql = _offline_sql(
        monkeypatch, "postgresql+psycopg://postgres.abc:p%40ss%2Fw0rd@db.example.com:5432/postgres"
    )
    assert "CREATE TABLE users" in sql
