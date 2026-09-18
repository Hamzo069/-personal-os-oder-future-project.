# LedgerLens API

FastAPI backend for LedgerLens. See the [root README](../../README.md) for setup instructions
and [`docs/`](../../docs) for architecture, data model, authentication, and AI integration details.

```bash
cd apps/api
uv sync --extra dev          # or: pip install -e ".[dev]"
cp ../../.env.example .env   # adjust SECRET_KEY etc.
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Run the tests with `uv run pytest`.
