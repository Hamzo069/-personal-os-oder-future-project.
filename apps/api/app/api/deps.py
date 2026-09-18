"""Shared FastAPI dependencies: settings, DB session, current user, rate limits."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.factory import get_ai_provider
from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.errors import UnauthorizedError
from app.core.rate_limit import RateLimiter, client_ip
from app.core.security import decode_access_token
from app.models import User
from app.storage import get_storage
from app.storage.local import LocalStorage

_bearer = HTTPBearer(auto_error=False)

SettingsDep = Annotated[Settings, Depends(get_settings)]
DBDep = Annotated[Session, Depends(get_db)]
StorageDep = Annotated[LocalStorage, Depends(get_storage)]
AIDep = Annotated[AIProvider, Depends(get_ai_provider)]


def get_current_user(
    db: DBDep,
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Missing or invalid Authorization header")
    user_id = decode_access_token(credentials.credentials, secret_key=settings.secret_key)
    if user_id is None:
        raise UnauthorizedError("Access token is invalid or expired")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Account is not active")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

auth_limiter = RateLimiter(get_settings().rate_limit_auth_per_minute)
ai_limiter = RateLimiter(get_settings().rate_limit_ai_per_minute)


def limit_auth(request: Request) -> None:
    auth_limiter.check(f"auth:{client_ip(request)}")


def limit_ai(user: CurrentUser) -> None:
    ai_limiter.check(f"ai:{user.id}")
