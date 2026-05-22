"""Structured logging via structlog."""
from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)
tenant_id_ctx: ContextVar[str | None] = ContextVar("tenant_id", default=None)


def _inject_ctx(_l: Any, _n: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    for key, ctx in (
        ("request_id", request_id_ctx),
        ("user_id", user_id_ctx),
        ("tenant_id", tenant_id_ctx),
    ):
        v = ctx.get()
        if v:
            event_dict[key] = v
    event_dict["service"] = "comms-service"
    return event_dict


def configure_logging(level: str = "INFO", *, json_logs: bool | None = None) -> None:
    log_level = getattr(logging, level.upper(), logging.INFO)
    if json_logs is None:
        from comms_service.core.config import settings
        json_logs = settings.app_env != "development"

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.stdlib.add_logger_name,
        _inject_ctx,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    renderer: Any = (
        structlog.processors.JSONRenderer() if json_logs
        else structlog.dev.ConsoleRenderer(colors=True)
    )
    structlog.configure(
        processors=[*processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level)
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)