"""Structured-output schemas the AI provider must return.

These Pydantic models double as the JSON schema sent to Claude (structured
outputs) and as the validation layer: whatever the model returns is validated
here before it touches the database. The AI never writes SQL and never
returns free-form JSON that the application would have to trust.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExtractedLineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str
    quantity: float | None = None
    total: float | None = None


class ReceiptExtraction(BaseModel):
    """What we ask the model to read off a receipt or invoice."""

    model_config = ConfigDict(extra="forbid")

    merchant: str | None = Field(description="Name of the shop / vendor / service provider")
    date: str | None = Field(description="Purchase or invoice date as ISO 8601 (YYYY-MM-DD)")
    total_amount: float | None = Field(description="Grand total actually paid, including VAT")
    currency: str | None = Field(description="ISO 4217 currency code, e.g. EUR")
    vat_rate: float | None = Field(description="Dominant VAT rate in percent, e.g. 19 or 7")
    vat_amount: float | None = Field(description="Total VAT amount if printed on the receipt")
    category: str | None = Field(description="Exactly one of the category names provided")
    description: str | None = Field(description="Short summary of what was bought (max 100 chars)")
    line_items: list[ExtractedLineItem] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1, description="Overall confidence in the extraction, 0..1")
    notes: str | None = Field(description="Problems, e.g. unreadable total or missing date")


QueryIntent = Literal["sum", "count", "average", "list", "by_category", "by_month", "top_merchants"]


class QueryPlan(BaseModel):
    """A validated, declarative query the application executes itself.

    The model translates a natural-language question into this plan; the
    application then runs a parameterised ORM query. This keeps the LLM away
    from the database entirely (no text-to-SQL).
    """

    model_config = ConfigDict(extra="forbid")

    intent: QueryIntent
    date_from: str | None = Field(description="Inclusive start date YYYY-MM-DD or null")
    date_to: str | None = Field(description="Inclusive end date YYYY-MM-DD or null")
    categories: list[str] = Field(
        default_factory=list, description="Category names from the provided list, empty = all"
    )
    merchant_contains: str | None = Field(description="Case-insensitive merchant substring or null")
    min_amount: float | None = None
    max_amount: float | None = None
    limit: int = Field(default=10, ge=1, le=50)
    explanation: str = Field(description="One sentence restating how the question was interpreted")
