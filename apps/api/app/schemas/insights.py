from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class CategoryTotal(BaseModel):
    category_id: str | None
    category_name: str
    color: str
    total: Decimal
    count: int


class MonthTotal(BaseModel):
    month: str  # YYYY-MM
    total: Decimal
    count: int


class MerchantTotal(BaseModel):
    merchant: str
    total: Decimal
    count: int


class SummaryResponse(BaseModel):
    date_from: date
    date_to: date
    currency: str
    total: Decimal
    count: int
    vat_total: Decimal
    average: Decimal
    previous_period_total: Decimal
    change_percent: float | None
    receipts_pending_review: int
    by_category: list[CategoryTotal]
    by_month: list[MonthTotal]
    top_merchants: list[MerchantTotal]


class AIQueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class AIQueryResponse(BaseModel):
    question: str
    answer: str
    plan: dict
    result: dict


class AIUsageResponse(BaseModel):
    calls: int
    input_tokens: int
    output_tokens: int
    by_kind: dict[str, int]
