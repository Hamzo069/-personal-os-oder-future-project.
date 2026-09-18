from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.category import CategoryRead
from app.schemas.common import ORMModel

Money = Decimal


class TransactionBase(BaseModel):
    date: dt.date
    merchant: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    amount: Money = Field(gt=0, le=Decimal("9999999999.99"), decimal_places=2)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    vat_rate: Decimal | None = Field(default=None, ge=0, le=100, decimal_places=2)
    vat_amount: Money | None = Field(default=None, ge=0, decimal_places=2)
    category_id: str | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("currency")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.upper()


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    date: dt.date | None = None
    merchant: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    amount: Money | None = Field(default=None, gt=0, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    vat_rate: Decimal | None = Field(default=None, ge=0, le=100, decimal_places=2)
    vat_amount: Money | None = Field(default=None, ge=0, decimal_places=2)
    category_id: str | None = None
    notes: str | None = Field(default=None, max_length=2000)


class TransactionRead(ORMModel):
    id: str
    date: dt.date
    merchant: str
    description: str | None
    amount: Money
    currency: str
    vat_rate: Decimal | None
    vat_amount: Money | None
    category: CategoryRead | None
    receipt_id: str | None
    source: str
    notes: str | None
    created_at: dt.datetime
    updated_at: dt.datetime


class TransactionFilters(BaseModel):
    date_from: dt.date | None = None
    date_to: dt.date | None = None
    category_id: str | None = None
    q: str | None = Field(default=None, max_length=200)
    min_amount: Decimal | None = Field(default=None, ge=0)
    max_amount: Decimal | None = Field(default=None, ge=0)
    source: Literal["manual", "receipt"] | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=200)
    sort: Literal["date_desc", "date_asc", "amount_desc", "amount_asc"] = "date_desc"
