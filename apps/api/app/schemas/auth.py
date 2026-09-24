from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    name: str = Field(min_length=1, max_length=120)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        if value.strip() != value:
            raise ValueError("Password must not start or end with whitespace")
        if value.isdigit() or value.isalpha():
            raise ValueError("Password must contain both letters and digits/symbols")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - not a secret, an OAuth2 token type label
    expires_in: int


class UserRead(ORMModel):
    id: str
    email: EmailStr
    name: str
    default_currency: str
    created_at: datetime


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    default_currency: str | None = Field(default=None, min_length=3, max_length=3)

    @field_validator("default_currency")
    @classmethod
    def _upper(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class DeleteAccountRequest(BaseModel):
    password: str = Field(max_length=128)
