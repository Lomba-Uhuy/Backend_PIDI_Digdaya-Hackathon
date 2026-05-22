"""Typed settings."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    database_url_async: str = (
        "postgresql+asyncpg://tc_user:tc_pass_dev@localhost:5432/tradeconnect"
    )
    database_url_sync: str = (
        "postgresql+psycopg://tc_user:tc_pass_dev@localhost:5432/tradeconnect"
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20

    redis_url: str = "redis://localhost:6379/3"
    celery_broker_url: str = "redis://localhost:6379/4"
    celery_result_backend: str = "redis://localhost:6379/5"

    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_dimensions: int = 1024

    prometheus_enabled: bool = True
    otel_service_name: str = "matching-service"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()