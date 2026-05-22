"""Async + sync SQLAlchemy engines."""
from __future__ import annotations

from typing import AsyncIterator

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine

from matching_service.core.config import settings

log = structlog.get_logger(__name__)

_async_engine: AsyncEngine | None = None
_async_factory: async_sessionmaker[AsyncSession] | None = None
_sync_factory: sessionmaker[Session] | None = None


def init_engine() -> None:
    global _async_engine, _async_factory, _sync_factory
    if _async_engine is not None:
        return

    _async_engine = create_async_engine(
        settings.database_url_async,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
    )
    _async_factory = async_sessionmaker(_async_engine, expire_on_commit=False, autoflush=False)

    sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True, pool_size=5)
    _sync_factory = sessionmaker(sync_engine, expire_on_commit=False, autoflush=False)

    log.info("matching.db.initialized")


async def close_engine() -> None:
    global _async_engine, _async_factory
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_factory = None


async def get_session() -> AsyncIterator[AsyncSession]:
    if _async_factory is None:
        init_engine()
    assert _async_factory is not None
    async with _async_factory() as s:
        try:
            yield s
        except Exception:
            await s.rollback()
            raise


def sync_session_factory() -> sessionmaker[Session]:
    if _sync_factory is None:
        init_engine()
    assert _sync_factory is not None
    return _sync_factory