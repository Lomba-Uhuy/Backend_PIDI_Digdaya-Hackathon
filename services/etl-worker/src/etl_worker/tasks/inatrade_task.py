"""INA-Trade (Kemendag) ingestion task.

Mengambil statistik ekspor/impor Indonesia dari portal INA-Trade Kemendag
(https://inatrade.kemendag.go.id) dan menyimpannya ke:
  1. trade_flows  — data aliran perdagangan per HS code / negara tujuan
  2. umkm.inatrade_data  — ringkasan data untuk UMKM dengan HS code serupa

Endpoint INA-Trade yang digunakan:
  GET /api/statistik/ekspor  ?hs_code=XXXX&tahun=YYYY&key=API_KEY
  GET /api/statistik/impor   ?hs_code=XXXX&tahun=YYYY&key=API_KEY

Jika API key tidak tersedia atau API tidak merespons, task mengembalikan
status "missing_api_key" atau "api_unavailable" tanpa raise exception.
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

# Endpoint INA-Trade — Kemendag menggunakan beberapa path berbeda antar versi
_INATRADE_ENDPOINTS = [
    "/api/statistik/ekspor",
    "/api/trade/export",
    "/api/v1/export",
]
_INATRADE_IMPOR_ENDPOINTS = [
    "/api/statistik/impor",
    "/api/trade/import",
    "/api/v1/import",
]


@celery_app.task(  # type: ignore[untyped-decorator]
    name="etl.ingest_inatrade",
    bind=True,
    queue="ingest",
    max_retries=3,
    soft_time_limit=180,
)
def ingest_inatrade(
    self: Task,
    hs_code: str = "4602",
    year: int = 2024,
    flow: str = "both",
) -> dict[str, Any]:
    """Ingest statistik ekspor/impor dari INA-Trade Kemendag.

    Args:
        hs_code: Kode HS produk (4-10 digit).
        year: Tahun data (default 2024).
        flow: "export", "import", atau "both".
    """
    log.info("etl.inatrade.start", hs_code=hs_code, year=year, flow=flow)

    if not settings.inatrade_api_key:
        log.warning("etl.inatrade.missing_key", hs_code=hs_code)
        return {
            "hs_code": hs_code,
            "year": year,
            "flow": flow,
            "status": "missing_api_key",
            "rows_inserted": 0,
            "message": "Set INATRADE_API_KEY in .env to fetch INA-Trade data.",
        }

    try:
        total_rows = 0
        flows_to_fetch: list[str] = []
        if flow in ("export", "both"):
            flows_to_fetch.append("export")
        if flow in ("import", "both"):
            flows_to_fetch.append("import")

        for flow_type in flows_to_fetch:
            rows = _fetch_flow(hs_code, year, flow_type)
            if rows:
                inserted = _store_rows(rows)
                total_rows += inserted
                log.info(
                    "etl.inatrade.flow_done",
                    flow=flow_type,
                    fetched=len(rows),
                    inserted=inserted,
                )

        log.info("etl.inatrade.done", hs_code=hs_code, total_rows=total_rows)
        return {
            "hs_code": hs_code,
            "year": year,
            "flow": flow,
            "status": "ok",
            "rows_inserted": total_rows,
        }
    except Exception as exc:
        log.error("etl.inatrade.failed", hs_code=hs_code, exc=str(exc))
        raise self.retry(exc=exc, countdown=60) from exc


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20))
def _fetch_flow(hs_code: str, year: int, flow_type: str) -> list[dict[str, Any]]:
    """Coba beberapa endpoint INA-Trade sampai ada yang berhasil."""
    base = settings.inatrade_base_url.rstrip("/")
    endpoints = (
        _INATRADE_ENDPOINTS if flow_type == "export" else _INATRADE_IMPOR_ENDPOINTS
    )
    params: dict[str, str] = {
        "hs_code": hs_code,
        "kode_hs": hs_code,
        "tahun": str(year),
        "year": str(year),
    }
    if settings.inatrade_api_key:
        params["key"] = settings.inatrade_api_key
        params["api_key"] = settings.inatrade_api_key

    with httpx.Client(timeout=20.0) as client:
        for path in endpoints:
            try:
                resp = client.get(f"{base}{path}", params=params)
                if resp.status_code == 404:
                    continue
                if resp.status_code == 429:
                    log.warning("etl.inatrade.rate_limited", path=path)
                    return []
                resp.raise_for_status()
                data = resp.json()
                rows = _extract_rows(data)
                if rows:
                    log.info("etl.inatrade.endpoint_hit", path=path, rows=len(rows))
                    return _normalize_rows(rows, hs_code, year, flow_type)
            except (httpx.TimeoutException, httpx.NetworkError):
                log.warning("etl.inatrade.endpoint_timeout", path=path)
                continue
            except httpx.HTTPStatusError as exc:
                log.warning("etl.inatrade.endpoint_error", path=path, status=exc.response.status_code)
                continue

    log.warning("etl.inatrade.api_unavailable", hs_code=hs_code, flow=flow_type)
    return []


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("data", "result", "records", "items", "statistik", "rows"):
            nested = payload.get(key)
            if isinstance(nested, list):
                return [r for r in nested if isinstance(r, dict)]
    return []


def _normalize_rows(
    rows: list[dict[str, Any]],
    hs_code: str,
    year: int,
    flow_type: str,
) -> list[dict[str, Any]]:
    flow_code = "X" if flow_type == "export" else "M"
    flow_name = "Export" if flow_type == "export" else "Import"
    normalized = []
    for row in rows:
        # INA-Trade menggunakan berbagai nama field — coba semua kemungkinan
        partner_name = str_or_none(
            row.get("negara_tujuan")
            or row.get("negara_asal")
            or row.get("country")
            or row.get("partner")
            or row.get("negara")
        )
        partner_code = str_or_none(
            row.get("kode_negara")
            or row.get("country_code")
            or row.get("partner_code")
        ) or "000"
        period_val = row.get("tahun") or row.get("year") or row.get("periode") or year
        trade_value = decimal_or_none(
            row.get("nilai_usd")
            or row.get("value_usd")
            or row.get("nilai")
            or row.get("value")
            or row.get("fob_value")
        )
        net_weight = decimal_or_none(
            row.get("berat_bersih_kg")
            or row.get("net_weight")
            or row.get("berat")
            or row.get("weight")
        )
        qty = decimal_or_none(row.get("volume") or row.get("quantity") or row.get("qty"))
        qty_unit = str_or_none(row.get("satuan") or row.get("unit") or row.get("qty_unit"))
        row_hs = str_or_none(row.get("kode_hs") or row.get("hs_code") or row.get("cmd_code")) or hs_code

        normalized.append({
            "source": "inatrade",
            "hs_code": row_hs,
            "reporter_code": "360",
            "reporter_iso": "IDN",
            "reporter_name": "Indonesia",
            "partner_code": partner_code,
            "partner_iso": None,
            "partner_name": partner_name,
            "partner2_code": "0",
            "partner2_iso": None,
            "partner2_name": None,
            "flow_code": flow_code,
            "flow_name": flow_name,
            "customs_code": "0",
            "customs_name": "General",
            "transport_mode_code": "0",
            "transport_mode_name": "Not classified",
            "period": int(str(period_val)[:4]) if period_val else year,
            "trade_value_usd": trade_value,
            "net_weight_kg": net_weight,
            "quantity": qty,
            "quantity_unit": qty_unit,
            "raw_json": json.dumps(row),
        })
    return normalized


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
                    partner2_code, partner2_iso, partner2_name,
                    flow_code, flow_name,
                    customs_code, customs_name,
                    transport_mode_code, transport_mode_name,
                    period, trade_value_usd, net_weight_kg,
                    quantity, quantity_unit, raw_json
                )
                VALUES (
                    :source, :hs_code, :reporter_code, :reporter_iso, :reporter_name,
                    :partner_code, :partner_iso, :partner_name,
                    :partner2_code, :partner2_iso, :partner2_name,
                    :flow_code, :flow_name,
                    :customs_code, :customs_name,
                    :transport_mode_code, :transport_mode_name,
                    :period, :trade_value_usd, :net_weight_kg,
                    :quantity, :quantity_unit, CAST(:raw_json AS JSONB)
                )
                ON CONFLICT (
                    source, hs_code, reporter_code, partner_code,
                    partner2_code, flow_code, customs_code,
                    transport_mode_code, period
                )
                DO UPDATE SET
                    reporter_name      = EXCLUDED.reporter_name,
                    partner_iso        = EXCLUDED.partner_iso,
                    partner_name       = EXCLUDED.partner_name,
                    flow_name          = EXCLUDED.flow_name,
                    trade_value_usd    = EXCLUDED.trade_value_usd,
                    net_weight_kg      = EXCLUDED.net_weight_kg,
                    quantity           = EXCLUDED.quantity,
                    quantity_unit      = EXCLUDED.quantity_unit,
                    raw_json           = EXCLUDED.raw_json,
                    updated_at         = NOW()
                """
            ),
            rows,
        )
        session.commit()
    return len(rows)


@celery_app.task(  # type: ignore[untyped-decorator]
    name="etl.update_umkm_inatrade",
    bind=True,
    queue="ingest",
    max_retries=2,
)
def update_umkm_inatrade_data(
    self: Task,
    umkm_id: str,
    hs_code: str,
    year: int = 2024,
) -> dict[str, Any]:
    """Perbarui field inatrade_data pada UMKM tertentu berdasarkan data trade_flows.

    Mengambil ringkasan data ekspor dari trade_flows (source=inatrade)
    untuk hs_code yang relevan, lalu menyimpannya ke umkm.inatrade_data.
    """
    log.info("etl.umkm_inatrade.start", umkm_id=umkm_id, hs_code=hs_code)
    session_factory = get_session_factory()
    with session_factory() as session:
        rows = session.execute(
            text(
                """
                SELECT
                    flow_code,
                    partner_name,
                    period,
                    trade_value_usd,
                    net_weight_kg
                FROM trade_flows
                WHERE source IN ('inatrade', 'bps', 'un_comtrade')
                  AND hs_code LIKE :hs_prefix
                  AND period = :year
                ORDER BY trade_value_usd DESC NULLS LAST
                LIMIT 20
                """
            ),
            {"hs_prefix": f"{hs_code[:4]}%", "year": year},
        ).fetchall()

        if not rows:
            log.info("etl.umkm_inatrade.no_data", umkm_id=umkm_id)
            return {"umkm_id": umkm_id, "status": "no_data"}

        summary = {
            "hs_code": hs_code,
            "year": year,
            "top_export_markets": [
                {
                    "country": r[1] or "Unknown",
                    "flow": r[0],
                    "period": r[2],
                    "trade_value_usd": float(r[3]) if r[3] else None,
                    "net_weight_kg": float(r[4]) if r[4] else None,
                }
                for r in rows
                if r[0] in ("X", "Export")
            ][:10],
            "top_import_sources": [
                {
                    "country": r[1] or "Unknown",
                    "flow": r[0],
                    "period": r[2],
                    "trade_value_usd": float(r[3]) if r[3] else None,
                }
                for r in rows
                if r[0] in ("M", "Import")
            ][:5],
            "data_sources": ["inatrade", "bps", "un_comtrade"],
        }

        session.execute(
            text(
                """
                UPDATE umkm
                SET inatrade_data = CAST(:data AS JSONB),
                    updated_at    = NOW()
                WHERE id = :id
                """
            ),
            {"id": umkm_id, "data": json.dumps(summary)},
        )
        session.commit()

    log.info("etl.umkm_inatrade.done", umkm_id=umkm_id, markets=len(summary["top_export_markets"]))
    return {
        "umkm_id": umkm_id,
        "hs_code": hs_code,
        "status": "ok",
        "export_markets": len(summary["top_export_markets"]),
    }
