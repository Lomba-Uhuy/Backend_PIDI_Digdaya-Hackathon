"""Typed domain exceptions."""
from __future__ import annotations


class CommsError(Exception):
    code = "internal_error"
    status = 500

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthenticationError(CommsError):
    code = "unauthenticated"
    status = 401


class GuardrailViolationError(CommsError):
    """LLM output failed guardrail validation after retries."""

    code = "ai_guardrail_violation"
    status = 422


class LLMUnavailableError(CommsError):
    code = "llm_unavailable"
    status = 503