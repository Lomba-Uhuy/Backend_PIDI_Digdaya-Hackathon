"""UN Comtrade ingestion task.

Free tier limit: 500 requests/month. Schedule daily, not on demand.
"""
from __future__ import annotations

import asyncio

import structlog
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from etl_worker.celery_app import celery_app
from etl_worker.config import settings

log = structlog.get_logger(__name__)

UN_COMTRADE_V2_URL = "https://comtradeapi.un.org/data/v1/get/C/A/HS"


@celery_app.task(
    name="etl.ingest_un_comtrade",
    bind=True,
    queue="ingest",
    max_retries=3,
    soft_time_limit=300,
)
def ingest_un_comtrade(self, hs_code: str, year: int = 2024) -> dict:  # type: ignore[no-untyped-def]
    log.info("etl.comtrade.start", hs_code=hs_code, year=year)
    try:
        result = asyncio.run(_fetch_and_store(hs_code, year))
        log.info("etl.comtrade.done", hs_code=hs_code, rows=result["rows_inserted"])
        return result
    except Exception as exc:
        log.error("etl.comtrade.failed", hs_code=hs_code, exc=str(exc))
        raise self.retry(exc=exc, countdown=60)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
async def _fetch_and_store(hs_code: str, year: int) -> dict:
    params = {
        "reporterCode": "all",
        "period": str(year),
        "partnerCode": "360",   # Indonesia
        "cmdCode": hs_code,
        "flowCode": "M",         # imports (from importer side)
        "maxRecords": 500,
    }
    headers: dict[str, str] = {}
    if settings.un_comtrade_api_key:
        headers["Ocp-Apim-Subscription-Key"] = settings.un_comtrade_api_key

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(UN_COMTRADE_V2_URL, params=params, headers=headers)
        if resp.status_code == 429:
            log.warning("etl.comtrade.rate_limited")
            return {"hs_code": hs_code, "year": year, "rows_inserted": 0, "rate_limited": True}
        resp.raise_for_status()
        data = resp.json()

    raw = data.get("data", [])
    # TODO: normalize + bulk_upsert to trade_flows table (build out in milestone 2)
    return {"hs_code": hs_code, "year": year, "rows_inserted": len(raw)}