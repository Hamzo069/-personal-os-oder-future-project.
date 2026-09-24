from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import CurrentUser, DBDep, SettingsDep, limit_auth
from app.core.errors import UnauthorizedError
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserRead
from app.schemas.common import Message
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, token: str, settings: SettingsDep) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        max_age=settings.refresh_token_expire_days * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure_flag,
        samesite="lax",
        path=f"{settings.api_v1_prefix}/auth",
    )


def _clear_refresh_cookie(response: Response, settings: SettingsDep) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name, path=f"{settings.api_v1_prefix}/auth",
        httponly=True, secure=settings.cookie_secure_flag, samesite="lax",
    )  # fmt: skip


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_auth)],
)
def register(
    payload: RegisterRequest, request: Request, response: Response, db: DBDep, settings: SettingsDep
) -> TokenResponse:
    user = auth_service.register_user(
        db, email=payload.email, password=payload.password, name=payload.name
    )
    access, expires_in = auth_service.issue_access_token(user, settings)
    refresh = auth_service.issue_refresh_token(
        db, user, settings, user_agent=request.headers.get("user-agent")
    )
    _set_refresh_cookie(response, refresh, settings)
    return TokenResponse(access_token=access, expires_in=expires_in)


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(limit_auth)])
def login(
    payload: LoginRequest, request: Request, response: Response, db: DBDep, settings: SettingsDep
) -> TokenResponse:
    user = auth_service.authenticate(db, email=payload.email, password=payload.password)
    access, expires_in = auth_service.issue_access_token(user, settings)
    refresh = auth_service.issue_refresh_token(
        db, user, settings, user_agent=request.headers.get("user-agent")
    )
    _set_refresh_cookie(response, refresh, settings)
    return TokenResponse(access_token=access, expires_in=expires_in)


@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(limit_auth)])
def refresh(
    request: Request, response: Response, db: DBDep, settings: SettingsDep
) -> TokenResponse:
    raw = request.cookies.get(settings.refresh_cookie_name)
    if not raw:
        raise UnauthorizedError("No refresh token")
    try:
        user, new_refresh = auth_service.rotate_refresh_token(
            db, raw, settings, user_agent=request.headers.get("user-agent")
        )
    except UnauthorizedError:
        _clear_refresh_cookie(response, settings)
        raise
    access, expires_in = auth_service.issue_access_token(user, settings)
    _set_refresh_cookie(response, new_refresh, settings)
    return TokenResponse(access_token=access, expires_in=expires_in)


@router.post("/logout", response_model=Message)
def logout(request: Request, response: Response, db: DBDep, settings: SettingsDep) -> Message:
    raw = request.cookies.get(settings.refresh_cookie_name)
    if raw:
        auth_service.revoke_refresh_token(db, raw)
    _clear_refresh_cookie(response, settings)
    return Message(message="Logged out")


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
