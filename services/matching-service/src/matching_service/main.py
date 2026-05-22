"""FastAPI Matching Service composition root."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from matching_service.api.errors import register_exception_handlers
from matching_service.api.middleware import RequestContextMiddleware
from matching_service.api.v1.router import api_v1_router
from matching_service.core.config import settings
from matching_service.core.logging import configure_logging
from matching_service.infrastructure.db.session import close_engine, init_engine

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.log_level)
    log.info("matching.starting", env=settings.app_env)
    init_engine()
    log.info("matching.started")
    try:
        yield
    finally:
        log.info("matching.stopping")
        await close_engine()
        log.info("matching.stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="TradeConnect Matching Service",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],   # Internal service; gateway handles public CORS
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix="/api/v1")

    @app.get("/health", tags=["Health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    if settings.prometheus_enabled:
        Instrumentator(
            should_group_status_codes=True,
            excluded_handlers=["/metrics", "/health", "/docs", "/openapi.json"],
        ).instrument(app).expose(app, include_in_schema=False, endpoint="/metrics")
    return app


app = create_app()