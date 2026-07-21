"""Worker config."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# parents[4] = project root saat dev lokal (.../.../services/etl-worker/src/etl_worker/config.py)
# Di Docker, path hanya /app/src/etl_worker/config.py (3 level), jadi fallback ke Path("/")
_p = Path(__file__).resolve()
ROOT_DIR = _p.parents[4] if len(_p.parents) > 4 else _p.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url_sync: str = (
        "postgresql+psycopg://tc_user:tc_pass_dev@localhost:5432/tradeconnect"
    )

    celery_broker_url: str = "redis://localhost:6379/4"
    celery_result_backend: str = "redis://localhost:6379/5"

    insw_token: str | None = None

    oss_public_nib_url: str = "https://api-prd.oss.go.id/v1/reg/public/nib"
    oss_public_user_key: str | None = None
    oss_public_recaptcha_response: str | None = None
    oss_public_cookie: str | None = None

    inatrade_base_url: str = "https://inatrade.kemendag.go.id"
    inatrade_api_key: str | None = None

    un_comtrade_base_url: str = "https://comtradeapi.un.org/data/v1"
    un_comtrade_tools_base_url: str = "https://comtradeapi.un.org/tools/v1"
    un_comtrade_preview_base_url: str = "https://comtradeapi.un.org/public/v1"
    un_comtrade_api_key: str | None = None

    bps_api_base_url: str = "https://webapi.bps.go.id/v1"
    bps_api_key: str | None = None

    # ── Buyer data source (TradeAtlas) ──────────────────────────────────────
    # Pluggable provider for real importer/buyer records. Auth is the user's
    # login session cookie (secret) — supplied ONLY via env, never hardcoded.
    buyer_source_provider: str = "tradeatlas"
    tradeatlas_base_url: str = "https://app.tradeatlas.com"
    tradeatlas_search_path: str = "/api/search/unified"
    tradeatlas_session_cookie: str | None = None  # secret; full Cookie header value
    tradeatlas_timeout_seconds: float = 30.0
    tradeatlas_max_retries: int = 4
    tradeatlas_backoff_base_seconds: float = 1.0
    tradeatlas_page_size: int = 30  # server-fixed (informational)
    tradeatlas_max_pages: int = 40  # safety cap per sync run
    tradeatlas_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0"
    )
    # curl_cffi browser fingerprint to impersonate (TLS/JA3 + HTTP2) — helps pass
    # Cloudflare's bot checks that block plain HTTP clients.
    tradeatlas_impersonate: str = "chrome"
    buyer_sync_batch_size: int = 100

    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
