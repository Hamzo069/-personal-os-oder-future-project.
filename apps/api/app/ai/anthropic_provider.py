"""Claude implementation of `AIProvider` using structured outputs.

`client.messages.parse()` sends the Pydantic schema as the required output
format and validates the response for us, so the application receives a typed
object or an exception - never half-parsed JSON.
"""

from __future__ import annotations

import base64
import logging
from datetime import date
from typing import Any, Literal

import anthropic

from app.ai.base import (
    AIUsage,
    ExtractionContext,
    ExtractionResult,
    QueryPlanResult,
)
from app.ai.prompts import (
    QUERY_SYSTEM_PROMPT,
    RECEIPT_SYSTEM_PROMPT,
    query_user_prompt,
    receipt_user_prompt,
)
from app.ai.schemas import QueryPlan, ReceiptExtraction
from app.core.errors import AIServiceError

Effort = Literal["low", "medium", "high"]

logger = logging.getLogger(__name__)

IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        effort: Literal["low", "medium", "high"] = "medium",
        timeout_seconds: float = 90.0,
    ) -> None:
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout_seconds, max_retries=2)
        self._model = model
        self._effort: Effort = effort

    # -- helpers ----------------------------------------------------------
    @staticmethod
    def _document_block(data: bytes, media_type: str) -> dict[str, Any]:
        encoded = base64.standard_b64encode(data).decode("ascii")
        if media_type in IMAGE_TYPES:
            return {
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": encoded},
            }
        if media_type == "application/pdf":
            return {
                "type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": encoded},
            }
        raise AIServiceError(f"Unsupported media type for extraction: {media_type}")

    def _usage(self, response: Any) -> AIUsage:
        usage = getattr(response, "usage", None)
        return AIUsage(
            provider=self.name,
            model=self._model,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
        )

    def _parse(self, *, system: str, content: Any, output_format: type, max_tokens: int) -> Any:
        try:
            response = self._client.messages.parse(
                model=self._model,
                max_tokens=max_tokens,
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": content}],
                output_format=output_format,
                output_config={"effort": self._effort},
            )
        except anthropic.AuthenticationError as exc:
            raise AIServiceError("AI provider rejected the API key") from exc
        except anthropic.RateLimitError as exc:
            raise AIServiceError("AI provider rate limit reached, try again shortly") from exc
        except anthropic.APIStatusError as exc:
            logger.warning("Anthropic API error %s: %s", exc.status_code, exc.message)
            raise AIServiceError("AI provider returned an error") from exc
        except anthropic.APIConnectionError as exc:
            raise AIServiceError("Could not reach the AI provider") from exc

        if response.stop_reason == "refusal":
            raise AIServiceError("The AI provider declined to process this document")
        if response.stop_reason == "max_tokens" or response.parsed_output is None:
            raise AIServiceError("AI response was incomplete, please retry")
        return response

    # -- AIProvider -------------------------------------------------------
    def extract_receipt(
        self, data: bytes, media_type: str, context: ExtractionContext
    ) -> ExtractionResult:
        content = [
            self._document_block(data, media_type),
            {
                "type": "text",
                "text": receipt_user_prompt(
                    context.categories, context.hints, context.default_currency
                ),
            },
        ]
        response = self._parse(
            system=RECEIPT_SYSTEM_PROMPT,
            content=content,
            output_format=ReceiptExtraction,
            max_tokens=4096,
        )
        return ExtractionResult(extraction=response.parsed_output, usage=self._usage(response))

    def plan_query(self, question: str, categories: list[str], today: date) -> QueryPlanResult:
        response = self._parse(
            system=QUERY_SYSTEM_PROMPT,
            content=query_user_prompt(question, categories, today),
            output_format=QueryPlan,
            max_tokens=1024,
        )
        return QueryPlanResult(plan=response.parsed_output, usage=self._usage(response))
