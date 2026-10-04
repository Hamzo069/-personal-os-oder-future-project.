"""Database schema check at application start-up.

A database without tables made the first request fail with a generic
"Internal server error" (`no such table: users`). The API now checks the
Alembic revision when it starts:

* development: pending migrations are applied automatically, so the quick
  start needs no separate migration step;
* production: the API refuses to start with a clear message. Deployments
  run `alembic upgrade head` explicitly (see the Dockerfile), so schema
  changes never happen as a side effect of starting a replica;
* test: skipped, the test suite creates its tables itself.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# In a PyInstaller bundle the alembic folder is unpacked next to the executable.
API_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))


class DatabaseNotMigratedError(RuntimeError):
    """Raised when the database schema is behind the code."""


def _alembic_config() -> Config:
    # Built without alembic.ini on purpose: loading the ini file would call
    # logging.fileConfig() and replace the running server's logging setup.
    config = Config()
    config.set_main_option("script_location", str(API_DIR / "alembic"))
    return config


def has_pending_migrations(engine: Engine) -> bool:
    heads = set(ScriptDirectory.from_config(_alembic_config()).get_heads())
    with engine.connect() as connection:
        current = set(MigrationContext.configure(connection).get_current_heads())
    return current != heads


def ensure_database_schema(engine: Engine, *, auto_upgrade: bool) -> None:
    if not has_pending_migrations(engine):
        return
    if not auto_upgrade:
        raise DatabaseNotMigratedError(
            "The database schema is not up to date. "
            "Run `uv run alembic upgrade head` in apps/api, then start the API again."
        )
    logger.info("Database schema is behind the code, applying migrations")
    command.upgrade(_alembic_config(), "head")
    logger.info("Database migrations applied")
