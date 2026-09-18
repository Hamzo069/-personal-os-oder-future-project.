"""Unit tests for the AI layer that do not need a network connection."""

from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

import anthropic
import httpx2 as httpx
import pytest
from app.ai.anthropic_provider import AnthropicProvider
from app.ai.base import CategoryHint, ExtractionContext
from app.ai.mock_provider import MockProvider
from app.ai.schemas import ReceiptExtraction
from app.core.errors import AIServiceError
from app.services.receipt_service import _normalise, sniff_media_type


def test_sniff_media_type() -> None:
    assert sniff_media_type(b"\xff\xd8\xff\xe0" + b"\x00" * 10) == "image/jpeg"
    assert sniff_media_type(b"\x89PNG\r\n\x1a\n") == "image/png"
    assert sniff_media_type(b"%PDF-1.7") == "application/pdf"
    assert sniff_media_type(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp"
    assert sniff_media_type(b"GIF89a") is None
    assert sniff_media_type(b"") is None


def test_normalise_extraction_cleans_model_output() -> None:
    raw = ReceiptExtraction(
        merchant="Shop", date="2026-09-12T10:00:00", total_amount=-12.345, currency="eur",
        vat_rate=19, vat_amount=None, category="food & drinks", description=None,
        line_items=[], confidence=0.9, notes=None,
    )  # fmt: skip
    cleaned = _normalise(raw, ["Food & Drinks", "Other"], "EUR")
    assert cleaned.date == "2026-09-12"
    assert cleaned.total_amount == 12.35
    assert cleaned.currency == "EUR"
    assert cleaned.category == "Food & Drinks"

    weird = _normalise(
        raw.model_copy(update={"date": "12.09.2026", "currency": "euros", "category": "Nope"}),
        ["Other"],
        "CHF",
    )
    assert weird.date is None and weird.currency == "CHF" and weird.category is None


def test_mock_provider_plan_query_heuristics() -> None:
    provider = MockProvider()
    today = dt.date(2026, 9, 18)
    plan = provider.plan_query("Wie viel habe ich letzten Monat für Software ausgegeben?",
                               ["Software & Subscriptions"], today).plan  # fmt: skip
    assert plan.intent == "sum"
    assert plan.date_from == "2026-08-01" and plan.date_to == "2026-08-31"
    assert plan.categories == ["Software & Subscriptions"]

    plan = provider.plan_query("How many receipts in March?", [], today).plan
    assert (
        plan.intent == "count" and plan.date_from == "2026-03-01" and plan.date_to == "2026-03-31"
    )

    plan = provider.plan_query("Where did most of my money go this year?", [], today).plan
    assert plan.intent == "top_merchants" and plan.date_from == "2026-01-01"


def test_mock_provider_uses_category_hints() -> None:
    result = MockProvider().extract_receipt(
        b"x", "image/png",
        ExtractionContext(categories=["A", "B"], hints=[CategoryHint("Rewe", "B")]),
    )  # fmt: skip
    assert result.extraction.merchant == "Rewe" and result.extraction.category == "B"


class _FakeMessages:
    def __init__(self, response: object = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict] = []

    def parse(self, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def _provider_with(messages: _FakeMessages) -> AnthropicProvider:
    provider = AnthropicProvider("sk-test", "claude-opus-5")
    provider._client = SimpleNamespace(messages=messages)  # type: ignore[assignment]
    return provider


def _fake_response(parsed: object, stop_reason: str = "end_turn") -> SimpleNamespace:
    usage = SimpleNamespace(input_tokens=1200, output_tokens=150)
    return SimpleNamespace(parsed_output=parsed, stop_reason=stop_reason, usage=usage)


def test_anthropic_provider_builds_image_and_pdf_requests() -> None:
    extraction = ReceiptExtraction(
        merchant="Rewe", date="2026-09-12", total_amount=12.3, currency="EUR", vat_rate=7,
        vat_amount=0.8, category="Food & Drinks", description="Groceries", line_items=[],
        confidence=0.95, notes=None,
    )  # fmt: skip
    messages = _FakeMessages(response=_fake_response(extraction))
    provider = _provider_with(messages)
    context = ExtractionContext(
        categories=["Food & Drinks"], hints=[CategoryHint("Rewe", "Food & Drinks")]
    )

    result = provider.extract_receipt(b"png-bytes", "image/png", context)
    assert result.extraction.merchant == "Rewe"
    assert result.usage.input_tokens == 1200 and result.usage.model == "claude-opus-5"

    call = messages.calls[0]
    assert call["model"] == "claude-opus-5"
    assert call["output_format"] is ReceiptExtraction
    assert call["output_config"] == {"effort": "medium"}
    assert call["system"][0]["cache_control"] == {"type": "ephemeral"}
    blocks = call["messages"][0]["content"]
    assert blocks[0]["type"] == "image" and blocks[0]["source"]["media_type"] == "image/png"
    assert "Rewe -> Food & Drinks" in blocks[1]["text"]

    provider.extract_receipt(b"%PDF-", "application/pdf", context)
    pdf_block = messages.calls[1]["messages"][0]["content"][0]
    assert pdf_block["type"] == "document"
    assert pdf_block["source"]["media_type"] == "application/pdf"

    with pytest.raises(AIServiceError):
        provider.extract_receipt(b"x", "text/plain", context)


def test_anthropic_provider_maps_errors() -> None:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    context = ExtractionContext(categories=["Other"])

    rate_limited = anthropic.RateLimitError(
        "slow down", response=httpx.Response(429, request=request), body=None
    )
    with pytest.raises(AIServiceError, match="rate limit"):
        _provider_with(_FakeMessages(error=rate_limited)).extract_receipt(
            b"x", "image/png", context
        )

    auth = anthropic.AuthenticationError(
        "bad key", response=httpx.Response(401, request=request), body=None
    )
    with pytest.raises(AIServiceError, match="API key"):
        _provider_with(_FakeMessages(error=auth)).extract_receipt(b"x", "image/png", context)

    connection = anthropic.APIConnectionError(request=request)
    with pytest.raises(AIServiceError, match="reach"):
        _provider_with(_FakeMessages(error=connection)).extract_receipt(b"x", "image/png", context)

    refused = _fake_response(None, stop_reason="refusal")
    with pytest.raises(AIServiceError, match="declined"):
        _provider_with(_FakeMessages(response=refused)).extract_receipt(b"x", "image/png", context)

    truncated = _fake_response(None, stop_reason="max_tokens")
    with pytest.raises(AIServiceError, match="incomplete"):
        _provider_with(_FakeMessages(response=truncated)).plan_query("q", [], dt.date.today())
