"""Worker config."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url_sync: str = (
        "postgresql+psycopg://tc_user:tc_pass_dev@localhost:5432/tradeconnect"
    )

    celery_broker_url: str = "redis://localhost:6379/4"
    celery_result_backend: str = "redis://localhost:6379/5"

    oss_rba_base_url: str = "https://oss.go.id/api"
    oss_rba_api_key: str | None = None

    inatrade_base_url: str = "https://inatrade.kemendag.go.id"
    inatrade_api_key: str | None = None

    un_comtrade_base_url: str = "https://comtradeapi.un.org"
    un_comtrade_api_key: str | None = None

    bps_api_base_url: str = "https://webapi.bps.go.id/v1"
    bps_api_key: str | None = None

    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()