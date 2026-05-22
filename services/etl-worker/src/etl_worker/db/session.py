"""Sync SQLAlchemy session factory for Celery workers."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from etl_worker.config import settings

_engine = None
_factory: sessionmaker[Session] | None = None


def get_session_factory() -> sessionmaker[Session]:
    global _engine, _factory
    if _factory is None:
        _engine = create_engine(settings.database_url_sync, pool_pre_ping=True, pool_size=5)
        _factory = sessionmaker(_engine, expire_on_commit=False, autoflush=False)
    return _factory