"""Typed domain exceptions."""
from __future__ import annotations


class MatchingError(Exception):
    code = "internal_error"
    status = 500

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(MatchingError):
    code = "not_found"
    status = 404


class AuthenticationError(MatchingError):
    code = "unauthenticated"
    status = 401


class ExternalError(MatchingError):
    code = "external_error"
    status = 502