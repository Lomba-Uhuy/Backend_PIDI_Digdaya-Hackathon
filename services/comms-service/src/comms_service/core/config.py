"""Settings."""
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

    redis_url: str = "redis://localhost:6379/3"

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    llm_model: str = "claude-sonnet-4-5"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2048

    prometheus_enabled: bool = True
    otel_service_name: str = "comms-service"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()