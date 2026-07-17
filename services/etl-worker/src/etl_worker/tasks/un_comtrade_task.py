"""UN Comtrade ingestion task.

Free tier limit: 500 requests/month. Schedule daily, not on demand.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx
import structlog
from sqlalchemy import text
from tenacity import retry, stop_after_attempt, wait_exponential

if TYPE_CHECKING:
    from celery import Task

from etl_worker.celery_app import celery_app
from etl_worker.config import settings
from etl_worker.db.session import get_session_factory
from etl_worker.utils import decimal_or_none, str_or_none

log = structlog.get_logger(__name__)

UN_COMTRADE_V2_URL = f"{settings.un_comtrade_base_url.rstrip('/')}/get/C/A/HS"

# Negara importir utama produk Indonesia — diperluas dari 3 → 9 pasar
TARGET_REPORTER_CODES = (
    "392",  # Japan
    "251",  # France
    "842",  # United States
    "276",  # Germany
    "528",  # Netherlands
    "784",  # United Arab Emirates
    "826",  # United Kingdom
    "036",  # Australia
    "410",  # Korea (Republic of)
)


@celery_app.task(  # type: ignore[untyped-decorator]
    name="etl.ingest_un_comtrade",
    bind=True,
    queue="ingest",
    max_retries=3,
    soft_time_limit=300,
)
def ingest_un_comtrade(
    self: Task,
    hs_code: str = "4602",
    year: int = 2024,
    reporter_codes: list[str] | None = None,
    include_indonesia_as_reporter: bool = True,
) -> dict[str, Any]:
    """Ingest UN Comtrade data.

    Dua mode fetch:
    1. reporter=negara-importir, partner=Indonesia (360), flow=M
       → Berapa banyak negara X mengimpor dari Indonesia (= ekspor Indonesia)
    2. reporter=Indonesia (360), partner=World (0), flow=X+M  [include_indonesia_as_reporter]
       → Data ekspor dan impor Indonesia langsung dari perspektif Indonesia
    """
    reporters = reporter_codes or list(TARGET_REPORTER_CODES)
    log.info("etl.comtrade.start", hs_code=hs_code, year=year, reporter_codes=reporters)
    try:
        total_rows = 0

        # Mode 1: negara mitra memandang Indonesia sebagai sumber impor mereka
        result = _fetch_and_store(hs_code, year, reporters, partner_code="360", flow_code="M")
        total_rows += result.get("rows_inserted", 0)

        # Mode 2: Indonesia sebagai reporter — ekspor dan impor
        if include_indonesia_as_reporter:
            for flow in ("X", "M"):
                id_result = _fetch_and_store(
                    hs_code, year, ["360"], partner_code="0", flow_code=flow,
                )
                total_rows += id_result.get("rows_inserted", 0)

        combined = {**result, "rows_inserted": total_rows}
        log.info("etl.comtrade.done", hs_code=hs_code, rows=total_rows)
        return combined
    except Exception as exc:
        log.error("etl.comtrade.failed", hs_code=hs_code, exc=str(exc))
        raise self.retry(exc=exc, countdown=60) from exc


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
def _fetch_and_store(
    hs_code: str,
    year: int,
    reporter_codes: list[str],
    partner_code: str = "360",
    flow_code: str = "M",
) -> dict[str, Any]:
    if not settings.un_comtrade_api_key:
        return {
            "hs_code": hs_code,
            "year": year,
            "reporter_codes": reporter_codes,
            "rows_inserted": 0,
            "status": "missing_api_key",
            "message": "Set UN_COMTRADE_API_KEY in .env to fetch UN Comtrade data.",
        }

    params: dict[str, str] = {
        "reporterCode": ",".join(reporter_codes),
        "period": str(year),
        "partnerCode": partner_code,
        "cmdCode": hs_code,
        "flowCode": flow_code,
        "maxRecords": "500",
    }
    # api_key sudah dipastikan bukan None karena early-return di atas
    headers: dict[str, str] = {"Ocp-Apim-Subscription-Key": settings.un_comtrade_api_key}

    with httpx.Client(timeout=30.0) as client:
        resp = client.get(UN_COMTRADE_V2_URL, params=params, headers=headers)
        if resp.status_code == 429:
            log.warning("etl.comtrade.rate_limited", reporter_codes=reporter_codes, flow=flow_code)
            return {"hs_code": hs_code, "year": year, "rows_inserted": 0, "rate_limited": True}
        resp.raise_for_status()
        data = resp.json()

    raw = data.get("data", [])
    normalized = [_normalize_row(row, hs_code, year) for row in raw]
    rows_inserted = _store_rows(normalized)
    return {
        "hs_code": hs_code,
        "year": year,
        "reporter_codes": reporter_codes,
        "partner_code": partner_code,
        "flow_code": flow_code,
        "rows_fetched": len(raw),
        "rows_inserted": rows_inserted,
        "status": "ok",
    }


def _normalize_row(row: dict[str, Any], hs_code: str, year: int) -> dict[str, Any]:
    return {
        "source": "un_comtrade",
        "hs_code": str(row.get("cmdCode") or hs_code),
        "reporter_code": str_or_none(row.get("reporterCode")),
        "reporter_iso": str_or_none(row.get("reporterISO")),
        "reporter_name": str_or_none(row.get("reporterDesc")),
        "partner_code": str_or_none(row.get("partnerCode")),
        "partner_iso": str_or_none(row.get("partnerISO")),
        "partner_name": str_or_none(row.get("partnerDesc")),
        "partner2_code": str_or_none(row.get("partner2Code")),
        "partner2_iso": str_or_none(row.get("partner2ISO")),
        "partner2_name": str_or_none(row.get("partner2Desc")),
        "flow_code": str_or_none(row.get("flowCode")),
        "flow_name": str_or_none(row.get("flowDesc")),
        "customs_code": str_or_none(row.get("customsCode")),
        "customs_name": str_or_none(row.get("customsDesc")),
        "transport_mode_code": str_or_none(row.get("motCode")),
        "transport_mode_name": str_or_none(row.get("motDesc")),
        "period": int(row.get("period") or year),
        "trade_value_usd": decimal_or_none(row.get("primaryValue") or row.get("fobvalue")),
        "net_weight_kg": decimal_or_none(row.get("netWgt")),
        "quantity": decimal_or_none(row.get("qty")),
        "quantity_unit": str_or_none(row.get("qtyUnitAbbr") or row.get("qtyUnitCode")),
        "raw_json": json.dumps(row),
    }


def _store_rows(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0

    session_factory = get_session_factory()
    with session_factory() as session:
        session.execute(
            text(
                """
                INSERT INTO trade_flows (
                    source, hs_code, reporter_code, reporter_iso, reporter_name,
                    partner_code, partner_iso, partner_name,
                    partner2_code, partner2_iso, partner2_name, flow_code, flow_name,
                    customs_code, customs_name, transport_mode_code, transport_mode_name,
                    period, trade_value_usd, net_weight_kg, quantity, quantity_unit, raw_json
                )
                VALUES (
                    :source, :hs_code, :reporter_code, :reporter_iso, :reporter_name,
                    :partner_code, :partner_iso, :partner_name,
                    :partner2_code, :partner2_iso, :partner2_name, :flow_code, :flow_name,
                    :customs_code, :customs_name, :transport_mode_code, :transport_mode_name,
                    :period, :trade_value_usd, :net_weight_kg, :quantity,
                    :quantity_unit, CAST(:raw_json AS JSONB)
                )
                ON CONFLICT (
                    source, hs_code, reporter_code, partner_code,
                    partner2_code, flow_code, customs_code,
                    transport_mode_code, period
                )
                DO UPDATE SET
                    reporter_iso = EXCLUDED.reporter_iso,
                    reporter_name = EXCLUDED.reporter_name,
                    partner_iso = EXCLUDED.partner_iso,
                    partner_name = EXCLUDED.partner_name,
                    partner2_iso = EXCLUDED.partner2_iso,
                    partner2_name = EXCLUDED.partner2_name,
                    flow_name = EXCLUDED.flow_name,
                    customs_name = EXCLUDED.customs_name,
                    transport_mode_name = EXCLUDED.transport_mode_name,
                    trade_value_usd = EXCLUDED.trade_value_usd,
                    net_weight_kg = EXCLUDED.net_weight_kg,
                    quantity = EXCLUDED.quantity,
                    quantity_unit = EXCLUDED.quantity_unit,
                    raw_json = EXCLUDED.raw_json,
                    updated_at = NOW()
                """
            ),
            rows,
        )
        session.commit()
    return len(rows)
