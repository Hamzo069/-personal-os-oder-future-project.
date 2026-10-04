"""Serving the built single-page app from the API process."""

from __future__ import annotations

from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class SPAStaticFiles(StaticFiles):
    """Static files with a client-side-routing fallback.

    A reload on /receipts has no file of that name, so unknown paths return index.html and
    the React router takes over. Paths below /api keep their JSON 404 so API clients are not
    handed an HTML page.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or path == "api" or path.startswith("api/"):
                raise
            return await super().get_response("index.html", scope)
