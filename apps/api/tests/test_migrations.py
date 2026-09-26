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
