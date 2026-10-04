.PHONY: install dev api web test lint check build up down desktop-build

install:        ## install backend and frontend dependencies
	cd apps/api && uv sync --extra dev
	cd apps/web && npm ci

api:            ## run the API with auto-reload on :8000
	cd apps/api && uv run alembic upgrade head && uv run uvicorn app.main:app --reload --port 8000

web:            ## run the frontend dev server on :5173
	cd apps/web && npm run dev

test:           ## run all tests
	cd apps/api && uv run pytest -q
	cd apps/web && npm test -- --run

lint:           ## lint and type-check everything
	cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run mypy app
	cd apps/web && npm run lint && npm run typecheck

check: lint test ## everything CI runs

up:             ## start the production-like stack with Docker Compose
	docker compose up --build -d

down:
	docker compose down

desktop-build:  ## freeze the desktop program for this OS (see apps/desktop/README.md)
	cd apps/web && npm ci && npm run build
	cd apps/api && uv sync --extra desktop && uv run pyinstaller ../desktop/ledgerlens.spec --noconfirm --distpath ../desktop/dist --workpath ../desktop/build
