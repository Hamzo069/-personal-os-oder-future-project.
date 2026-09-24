from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

_HEX_COLOR = r"^#[0-9a-fA-F]{6}$"


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str = Field(default="#9ca3af", pattern=_HEX_COLOR)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    color: str | None = Field(default=None, pattern=_HEX_COLOR)


class CategoryRead(ORMModel):
    id: str
    name: str
    color: str
    is_default: bool
