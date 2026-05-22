"""Domain -> HTTP."""
from __future__ import annotations

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse

from comms_service.core.exceptions import CommsError

log = structlog.get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(CommsError)
    async def _domain(_: Request, exc: CommsError) -> ORJSONResponse:
        log.warning("domain.error", code=exc.code, message=exc.message)
        return ORJSONResponse(
            status_code=exc.status,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, _exc: Exception) -> ORJSONResponse:
        log.exception("unhandled")
        return ORJSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "An unexpected error occurred."}},
        )