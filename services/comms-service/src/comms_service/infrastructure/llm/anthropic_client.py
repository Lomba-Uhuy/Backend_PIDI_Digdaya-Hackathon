"""Anthropic LLM client wrapper.

Falls back to a deterministic stub when ANTHROPIC_API_KEY is unset, so dev
environments and CI can run without external dependencies.
"""
from __future__ import annotations

from typing import Protocol

import structlog

from comms_service.core.config import settings
from comms_service.core.exceptions import LLMUnavailableError

log = structlog.get_logger(__name__)


class LLMProvider(Protocol):
    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> str: ...


class AnthropicLLM:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.llm_model
        self._client = None  # lazy

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        if not settings.anthropic_api_key:
            log.warning("llm.anthropic.no_api_key")
            return
        from anthropic import AsyncAnthropic
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> str:
        self._ensure_client()
        if self._client is None:
            log.warning("llm.anthropic.stub_response")
            return _stub_response()

        try:
            resp = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            # Anthropic returns content as a list of content blocks; join text blocks
            text_parts: list[str] = []
            for block in resp.content:
                if getattr(block, "type", None) == "text":
                    text_parts.append(block.text)  # type: ignore[attr-defined]
            return "\n".join(text_parts).strip()
        except Exception as e:  # noqa: BLE001
            log.error("llm.anthropic.failed", error=str(e))
            raise LLMUnavailableError("Anthropic API call failed") from e


def _stub_response() -> str:
    """Deterministic fallback used when no API key is configured."""
    return (
        "Dear Valued Partner,\n\n"
        "Thank you for your interest in our products. We appreciate the opportunity "
        "to discuss this potential collaboration. Our pricing is competitive within "
        "current market ranges, and we are happy to share details once we understand "
        "your specific volume, delivery, and payment requirements.\n\n"
        "Best regards,\n"
        "Sales Team\n"
        "---INDONESIAN EXPLANATION---\n"
        "Strategi: respon profesional dengan price anchoring soft. Kami tidak "
        "menyebut angka, namun mengundang buyer untuk berbagi konteks (volume, "
        "delivery, payment) sebelum kami quote. Ini menjaga posisi tawar dan "
        "menghindari low-ball.\n"
        "---END EXPLANATION---"
    )


_singleton: LLMProvider | None = None


def get_llm() -> LLMProvider:
    global _singleton
    if _singleton is None:
        # Gemini is the primary LLM provider across TradeConnect.
        if settings.gemini_api_key:
            from comms_service.infrastructure.llm.gemini_client import GeminiLLM
            log.info("llm.provider.selected", provider="gemini", model=settings.gemini_model)
            _singleton = GeminiLLM()
        elif settings.anthropic_api_key:
            log.info("llm.provider.selected", provider="anthropic", model=settings.llm_model)
            _singleton = AnthropicLLM()
        else:
            from comms_service.infrastructure.llm.gemini_client import GeminiLLM
            _singleton = GeminiLLM()
    return _singleton