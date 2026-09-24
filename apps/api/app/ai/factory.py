"""Builds the configured AI provider (singleton per process)."""

from __future__ import annotations

from functools import lru_cache

from app.ai.base import AIProvider
from app.core.config import get_settings


@lru_cache
def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if settings.ai_provider == "anthropic":
        from app.ai.anthropic_provider import AnthropicProvider

        assert settings.anthropic_api_key  # validated in Settings
        return AnthropicProvider(
            settings.anthropic_api_key,
            settings.anthropic_model,
            effort=settings.anthropic_effort,
            timeout_seconds=settings.ai_timeout_seconds,
        )
    from app.ai.mock_provider import MockProvider

    return MockProvider()
