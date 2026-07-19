"""BPS (Badan Pusat Statistik) ingestion task."""
from __future__ import annotations

import json
import zlib
from typing import TYPE_CHECKING, Any

import httpx
import structlog
from sqlalchemy import text

if TYPE_CHECKING:
    from celery import Task

from etl_worker.celery_app import celery_app
from etl_worker.config import settings
from etl_worker.db.session import get_session_factory
from etl_worker.utils import decimal_or_none, str_or_none

log = structlog.get_logger(__name__)

# Valid flow identifiers — used for explicit input validation
_VALID_FLOWS = {"export", "exports", "x", "1", "import", "imports", "m", "2"}

# Maps _flow_to_sumber int → (flow_code, flow_name) for unified lookup
_FLOW_META: dict[int, tuple[str, str]] = {
    1: ("X", "Export"),
    2: ("M", "Import"),
}


@celery_app.task(name="etl.ingest_bps", bind=True, queue="ingest")  # type: ignore[untyped-decorator]
def ingest_bps(
    self: Task,
    hs_code: str = "4602",
    year: int = 2024,
    flow: str = "both",
    frequency: str = "annual",
) -> dict[str, Any]:
    log.info("etl.bps.start", hs_code=hs_code, year=year, flow=flow, frequency=frequency)
    if not settings.bps_api_key:
        return {
            "hs_code": hs_code,
            "year": year,
            "flow": flow,
            "frequency": frequency,
            "status": "missing_api_key",
            "rows_inserted": 0,
            "message": "Set BPS_API_KEY in .env to fetch BPS data.",
        }

    url = f"{settings.bps_api_base_url.rstrip('/')}/api/dataexim/"
    normalized: list[dict[str, Any]] = []
    with httpx.Client(timeout=30.0) as client:
        for flow_name in _flows_to_fetch(flow):
            dataset_id = f"dataexim:{flow_name}:{frequency}:{hs_code}:{year}"
            bps_hs, jenishs = _bps_hs_and_jenishs(hs_code)
            params: dict[str, str | None] = {
                "sumber": str(_flow_to_sumber(flow_name)),
                "periode": str(_frequency_to_periode(frequency)),
                "kodehs": bps_hs,
                "jenishs": str(jenishs),
                "tahun": str(year),
                "key": settings.bps_api_key,
            }
            resp = client.get(url, params=params)
            resp.raise_for_status()
            payload = resp.json()
            rows = _extract_rows(payload)
            normalized.extend(
                _normalize_row(dataset_id, hs_code, year, flow_name, row, index)
                for index, row in enumerate(rows)
            )

    rows_inserted, trade_rows_inserted = _store_all(normalized)
    log.info("etl.bps.done", hs_code=hs_code, year=year, rows=rows_inserted)
    return {
        "hs_code": hs_code,
        "year": year,
        "flow": flow,
        "frequency": frequency,
        "status": "ok",
        "rows_fetched": len(normalized),
        "rows_inserted": rows_inserted,
        "trade_rows_inserted": trade_rows_inserted,
    }


def _extract_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") or payload.get("dataexim")
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        # Cast ke dict[str, Any] agar .get() mengembalikan tipe yang diketahui
        data_dict: dict[str, Any] = data  # type: ignore[assignment]
        for key in ("data", "dataexim", "datacontent", "records"):
            nested = data_dict.get(key)
            if isinstance(nested, list):
                return [row for row in nested if isinstance(row, dict)]
            if isinstance(nested, dict):
                return [{"key": k, "value": v} for k, v in nested.items()]
    return []


def _normalize_row(
    dataset_id: str,
    hs_code: str,
    year: int,
    flow: str,
    row: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    region_name = row.get("wilayah") or row.get("region") or row.get("region_name")
    commodity_name = row.get("komoditas") or row.get("commodity") or row.get("commodity_name")
    bps_hs = row.get("kodehs") or row.get("hs_code") or hs_code
    bps_year = row.get("tahun") or row.get("year") or row.get("period") or str(year)
    country_name = row.get("ctr") or row.get("country") or row.get("negara")
    port_name = row.get("pod") or row.get("port") or row.get("pelabuhan")
    trade_value = row.get("value") or row.get("nilai")
    net_weight = row.get("netweight") or row.get("net_weight") or row.get("berat")
    normalized_flow = _normalize_flow(flow)
    commodity_code = _extract_hs_code(bps_hs, hs_code)

    return {
        "dataset_id": dataset_id,
        "source": "bps",
        "hs_code": commodity_code,
        "period": str_or_none(bps_year),
        "region_code": str_or_none(row.get("kode_wilayah") or row.get("region_code")),
        "region_name": str_or_none(region_name),
        "commodity_code": commodity_code,
        "commodity_name": str_or_none(commodity_name or bps_hs),
        "country_name": str_or_none(country_name),
        "port_name": str_or_none(port_name),
        "country_code": _stable_bps_code(str_or_none(country_name), "country", index),
        "port_code": _stable_bps_code(str_or_none(port_name), "port", index),
        "flow_code": normalized_flow["flow_code"],
        "flow_name": normalized_flow["flow_name"],
        "value": decimal_or_none(trade_value),
        "net_weight_kg": decimal_or_none(net_weight),
        "unit": "USD",
        "raw_json": json.dumps(row),
    }


def _store_all(rows: list[dict[str, Any]]) -> tuple[int, int]:
    """Write BPS rows to bps_trade_data and trade_flows in one transaction."""
    if not rows:
        return 0, 0

    session_factory = get_session_factory()
    with session_factory() as session:
        # ── bps_trade_data ──────────────────────────────────────────────────
        for dataset_id in sorted({row["dataset_id"] for row in rows}):
            session.execute(
                text("DELETE FROM bps_trade_data WHERE dataset_id = :dataset_id"),
                {"dataset_id": dataset_id},
            )
        session.execute(
            text(
                """
                INSERT INTO bps_trade_data (
                    dataset_id, period, region_code, region_name,
                    commodity_code, commodity_name,
                    flow_code, flow_name, country_name, port_name,
                    value, net_weight_kg, unit, raw_json
                )
                VALUES (
                    :dataset_id, :period, :region_code, :region_name,
                    :commodity_code, :commodity_name,
                    :flow_code, :flow_name, :country_name, :port_name,
                    :value, :net_weight_kg, :unit,
                    CAST(:raw_json AS JSONB)
                )
                """
            ),
            rows,
        )

        # ── trade_flows ─────────────────────────────────────────────────────
        hs_codes = sorted({row["hs_code"] for row in rows})
        flow_codes = sorted({row["flow_code"] for row in rows})
        for hs_code in hs_codes:
            for flow_code in flow_codes:
                session.execute(
                    text(
                        """
                        DELETE FROM trade_flows
                        WHERE source = 'bps'
                          AND hs_code = :hs_code
                          AND flow_code = :flow_code
                        """
                    ),
                    {"hs_code": hs_code, "flow_code": flow_code},
                )
        trade_params = [
            {
                "source": row["source"],
                "hs_code": row["hs_code"],
                "partner_code": row["country_code"],
                "partner_name": row["country_name"],
                "partner2_code": row["port_code"],
                "partner2_name": row["port_name"],
                "flow_code": row["flow_code"],
                "flow_name": row["flow_name"],
                "period": _int_or_none(row["period"]),
                "trade_value_usd": row["value"],
                "net_weight_kg": row["net_weight_kg"],
                "raw_json": row["raw_json"],
            }
            for row in rows
        ]
        session.execute(
            text(
                """
                INSERT INTO trade_flows (
                    source, hs_code, reporter_code, reporter_iso, reporter_name,
                    partner_code, partner_name, partner2_code, partner2_name,
                    flow_code, flow_name, customs_code, customs_name,
                    transport_mode_code, transport_mode_name, period,
                    trade_value_usd, net_weight_kg, quantity_unit, raw_json
                )
                VALUES (
                    :source, :hs_code, '360', 'IDN', 'Indonesia',
                    :partner_code, :partner_name, :partner2_code, :partner2_name,
                    :flow_code, :flow_name, '0', 'General customs',
                    '0', 'Not classified', :period,
                    :trade_value_usd, :net_weight_kg, 'KG', CAST(:raw_json AS JSONB)
                )
                ON CONFLICT (
                    source, hs_code, reporter_code, partner_code,
                    partner2_code, flow_code, customs_code,
                    transport_mode_code, period
                )
                DO UPDATE SET
                    partner_name = EXCLUDED.partner_name,
                    partner2_name = EXCLUDED.partner2_name,
                    flow_name = EXCLUDED.flow_name,
                    trade_value_usd = EXCLUDED.trade_value_usd,
                    net_weight_kg = EXCLUDED.net_weight_kg,
                    raw_json = EXCLUDED.raw_json,
                    updated_at = NOW()
                """
            ),
            trade_params,
        )
        session.commit()
    return len(rows), len(rows)


def _bps_hs_and_jenishs(hs_code: str) -> tuple[str, int]:
    """Pick a (kodehs, jenishs) pair that BPS dataexim actually serves.

    BPS `jenishs` only accepts 1 (two-digit HS chapter) or 2 (full HS code).
    A bare heading like '4602' returns ``data-availability: unavailable`` and a
    wrong jenishs (e.g. 4) returns HTTP 500. To guarantee real output we fall
    back to the 2-digit chapter level unless a full 8+ digit code is supplied.
    Supports multiple ';'-separated chapters (e.g. '03;04').
    """
    codes = [c.strip() for c in hs_code.split(";") if c.strip()]
    digits_only = ["".join(ch for ch in c if ch.isdigit()) for c in codes]
    digits_only = [d for d in digits_only if d]
    if not digits_only:
        return "00", 1
    if len(digits_only) == 1 and len(digits_only[0]) >= 8:
        return digits_only[0], 2
    chapters = ";".join(d[:2] for d in digits_only)
    return chapters, 1


def _flows_to_fetch(flow: str) -> list[str]:
    normalized = flow.strip().lower()
    if normalized == "both":
        return ["export", "import"]
    if normalized not in _VALID_FLOWS:
        raise ValueError(f"flow must be export, import, or both; got {flow!r}")
    return [normalized]


def _flow_to_sumber(flow: str) -> int:
    normalized = flow.strip().lower()
    if normalized in {"export", "exports", "x", "1"}:
        return 1
    if normalized in {"import", "imports", "m", "2"}:
        return 2
    raise ValueError("flow must be export or import")


def _frequency_to_periode(frequency: str) -> int:
    normalized = frequency.strip().lower()
    if normalized in {"monthly", "month", "m", "1"}:
        return 1
    if normalized in {"annual", "annually", "yearly", "year", "a", "2"}:
        return 2
    raise ValueError("frequency must be annual or monthly")


def _normalize_flow(flow: str) -> dict[str, str]:
    flow_code, flow_name = _FLOW_META[_flow_to_sumber(flow)]
    return {"flow_code": flow_code, "flow_name": flow_name}


def _extract_hs_code(value: Any, fallback: str) -> str:
    value_str = str_or_none(value)
    if not value_str:
        return fallback
    token = value_str.split()[0].strip()
    return "".join(ch for ch in token if ch.isdigit()) or fallback


def _stable_bps_code(value: str | None, prefix: str, index: int) -> str:
    if not value:
        return f"{prefix[:1]}unk{index}"
    cleaned = value.strip().lower()
    checksum = zlib.crc32(cleaned.encode("utf-8"))
    return f"{prefix[:1]}{checksum:08x}"


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(str(value))
