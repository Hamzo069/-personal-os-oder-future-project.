"""Provider-agnostic interface for the AI features.

The rest of the application only talks to `AIProvider`; concrete providers
(Anthropic, mock) live next to it. Swapping the model vendor - or running the
whole app without any API key - is a configuration change, not a code change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from app.ai.schemas import QueryPlan, ReceiptExtraction


@dataclass
class CategoryHint:
    """A merchant -> category mapping learned from earlier user confirmations."""

    merchant: str
    category: str


@dataclass
class AIUsage:
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class ExtractionResult:
    extraction: ReceiptExtraction
    usage: AIUsage


@dataclass
class QueryPlanResult:
    plan: QueryPlan
    usage: AIUsage


@dataclass
class ExtractionContext:
    categories: list[str]
    hints: list[CategoryHint] = field(default_factory=list)
    default_currency: str = "EUR"


class AIProvider(Protocol):
    name: str

    def extract_receipt(
        self, data: bytes, media_type: str, context: ExtractionContext
    ) -> ExtractionResult: ...

    def plan_query(self, question: str, categories: list[str], today: date) -> QueryPlanResult: ...
