"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import __version__
from app.api.v1 import router as v1_router
from app.core.config import Settings, get_settings
from app.core.db import engine
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.migrations import ensure_database_schema
from app.core.spa import SPAStaticFiles


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if settings.app_env != "test":
            ensure_database_schema(engine, auto_upgrade=not settings.is_production)
        yield

    app = FastAPI(
        lifespan=lifespan,
        title=f"{settings.app_name} API",
        version=__version__,
        description="AI-assisted receipt capture and expense intelligence.",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        if settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response

    if settings.app_env == "desktop":
        # The desktop program listens on 127.0.0.1 only. Rejecting other Host headers also
        # stops DNS-rebinding attacks from web pages the user happens to have open.
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])

    register_exception_handlers(app)
    app.include_router(v1_router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    if settings.frontend_dist is not None:
        if not (settings.frontend_dist / "index.html").is_file():
            raise RuntimeError(f"FRONTEND_DIST has no index.html: {settings.frontend_dist}")
        # Mounted last: the API routes and /health above take precedence.
        app.mount("/", SPAStaticFiles(directory=settings.frontend_dist, html=True), name="web")

    return app


app = create_app()
