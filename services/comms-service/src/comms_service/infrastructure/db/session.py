"""Async SQLAlchemy engine — read-only context loads."""
from __future__ import annotations

from typing import AsyncIterator

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from comms_service.core.config import settings

log = structlog.get_logger(__name__)

_engine: AsyncEngine | None = None
_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine() -> None:
    global _engine, _factory
    if _engine is not None:
        return
    _engine = create_async_engine(
        settings.database_url_async,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    _factory = async_sessionmaker(_engine, expire_on_commit=False, autoflush=False)
    log.info("comms.db.initialized")


async def close_engine() -> None:
    global _engine, _factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _factory = None


async def get_session() -> AsyncIterator[AsyncSession]:
    if _factory is None:
        init_engine()
    assert _factory is not None
    async with _factory() as s:
        try:
            yield s
        except Exception:
            await s.rollback()
            raise