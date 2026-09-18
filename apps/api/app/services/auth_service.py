"""User registration, login and refresh-token lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    needs_rehash,
    verify_password,
)
from app.models import DEFAULT_CATEGORIES, Category, RefreshToken, User

# Valid Argon2id hash of a random string; used so unknown emails take as long as wrong passwords.
_DUMMY_HASH = hash_password("dummy-password-for-constant-time-login")


def register_user(db: Session, *, email: str, password: str, name: str) -> User:
    email = email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise ConflictError("An account with this email already exists")
    user = User(email=email, password_hash=hash_password(password), name=name.strip())
    db.add(user)
    db.flush()  # assigns user.id
    for cat_name, color in DEFAULT_CATEGORIES:
        db.add(Category(user_id=user.id, name=cat_name, color=color, is_default=True))
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, *, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    # Always run the hash check to keep timing similar for unknown emails.
    ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok or not user.is_active:
        raise UnauthorizedError("Invalid email or password")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.commit()
    return user


def issue_access_token(user: User, settings: Settings) -> tuple[str, int]:
    token = create_access_token(
        user.id,
        secret_key=settings.secret_key,
        expires_minutes=settings.access_token_expire_minutes,
    )
    return token, settings.access_token_expire_minutes * 60


def issue_refresh_token(
    db: Session, user: User, settings: Settings, *, user_agent: str | None = None
) -> str:
    raw = generate_refresh_token()
    now = datetime.now(UTC)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
            created_at=now,
            user_agent=(user_agent or "")[:255] or None,
        )
    )
    db.commit()
    return raw


def rotate_refresh_token(
    db: Session, raw_token: str, settings: Settings, *, user_agent: str | None = None
) -> tuple[User, str]:
    """Validate a refresh token, revoke it and issue a new one (rotation)."""
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token)))
    now = datetime.now(UTC)
    if stored is None:
        raise UnauthorizedError("Invalid refresh token")
    expires_at = stored.expires_at
    if expires_at.tzinfo is None:  # SQLite returns naive datetimes
        expires_at = expires_at.replace(tzinfo=UTC)
    if stored.revoked_at is not None:
        # Reuse of a revoked token is a strong signal of theft: revoke the whole family.
        revoke_all_for_user(db, stored.user_id)
        raise UnauthorizedError("Refresh token was already used")
    if expires_at < now:
        raise UnauthorizedError("Refresh token expired")
    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Account is not active")
    stored.revoked_at = now
    db.commit()
    new_raw = issue_refresh_token(db, user, settings, user_agent=user_agent)
    return user, new_raw


def revoke_refresh_token(db: Session, raw_token: str) -> None:
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token)))
    if stored and stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
        db.commit()


def revoke_all_for_user(db: Session, user_id: str) -> None:
    now = datetime.now(UTC)
    for token in db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
        )
    ):
        token.revoked_at = now
    db.commit()
