"""Sync SQLAlchemy session factory for Celery workers."""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from etl_worker.config import settings


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True, pool_size=5)
    return sessionmaker(engine, expire_on_commit=False, autoflush=False)
