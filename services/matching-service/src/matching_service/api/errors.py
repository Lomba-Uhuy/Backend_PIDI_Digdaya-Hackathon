"""Domain exception -> HTTP translation."""
from __future__ import annotations

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse

from matching_service.core.exceptions import MatchingError

log = structlog.get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(MatchingError)
    async def _handle_domain(_: Request, exc: MatchingError) -> ORJSONResponse:
        log.warning("domain.error", code=exc.code, message=exc.message, details=exc.details)
        return ORJSONResponse(
            status_code=exc.status,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    @app.exception_handler(Exception)
    async def _handle_unhandled(_: Request, _exc: Exception) -> ORJSONResponse:
        log.exception("unhandled.exception")
        return ORJSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "An unexpected error occurred."}},
        )