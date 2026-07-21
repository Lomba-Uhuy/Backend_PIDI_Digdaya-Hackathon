"""Google Gemini LLM client (generativelanguage REST API).

Implements the same ``complete()`` protocol as the Anthropic client. Tries the
configured primary model first, then falls through a fallback chain when a model
is overloaded (503) / quota-limited (429) / gated (404), so drafting keeps working
on a busy free tier. Raises ``LLMUnavailableError`` only when every model fails.
"""
from __future__ import annotations

import time

import httpx
import structlog

from comms_service.core.config import settings
from comms_service.core.exceptions import LLMUnavailableError

log = structlog.get_logger(__name__)

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
# Transient/soft failures worth trying the next model for.
_SOFT_STATUS = {404, 429, 503}
# After a model returns a soft failure, skip it for this long so we don't re-hit an
# overloaded/quota'd model on every call (keeps latency low, still recovers later).
_COOLDOWN_SECONDS = 90.0
_model_cooldown: dict[str, float] = {}  # model -> epoch until which to skip


class GeminiLLM:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.gemini_api_key
        primary = settings.gemini_model.strip()
        fallbacks = [m.strip() for m in settings.gemini_fallback_models.split(",") if m.strip()]
        # De-duplicate while preserving order (primary first).
        self.models: list[str] = []
        for m in [primary, *fallbacks]:
            if m and m not in self.models:
                self.models.append(m)

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> str:
        if not self.api_key:
            raise LLMUnavailableError("Gemini API key is not configured")

        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}

        last_error = "no models configured"
        now = time.monotonic()
        # Prefer models not currently cooling down; if all are cooling down, fall
        # back to trying every model anyway (better a slow answer than none).
        ready = [m for m in self.models if _model_cooldown.get(m, 0.0) <= now]
        candidates = ready or self.models

        async with httpx.AsyncClient(timeout=45.0) as client:
            for model in candidates:
                try:
                    resp = await client.post(
                        f"{_BASE_URL}/{model}:generateContent",
                        headers=headers,
                        json=payload,
                    )
                except Exception as exc:  # noqa: BLE001 — network/timeout
                    last_error = f"{model}: {exc}"
                    log.warning("llm.gemini.network_error", model=model, error=str(exc))
                    continue

                if resp.status_code == 200:
                    text = self._extract_text(resp.json())
                    if text:
                        log.info("llm.gemini.ok", model=model)
                        return text
                    last_error = f"{model}: empty response"
                    log.warning("llm.gemini.empty", model=model)
                    continue

                if resp.status_code in _SOFT_STATUS:
                    _model_cooldown[model] = time.monotonic() + _COOLDOWN_SECONDS
                    last_error = f"{model}: HTTP {resp.status_code}"
                    log.warning("llm.gemini.unavailable", model=model, status=resp.status_code)
                    continue

                # Hard error (401/400/etc.) — record and try remaining models.
                last_error = f"{model}: HTTP {resp.status_code} {resp.text[:200]}"
                log.error("llm.gemini.failed", model=model, status=resp.status_code)

        raise LLMUnavailableError(f"Gemini call failed for all models ({last_error})")

    @staticmethod
    def _extract_text(data: dict) -> str:
        candidates = data.get("candidates") or []
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", []) or []
        return "".join(p.get("text", "") for p in parts).strip()
