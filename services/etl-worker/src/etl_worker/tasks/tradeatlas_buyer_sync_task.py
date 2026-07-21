"""Celery task: synchronise real importer/buyer records from a BuyerSourceProvider.

Dynamic inputs only — HS codes + markets are supplied by the caller (product RAG /
classification / user target markets); nothing is hardcoded (Decisions 5 & 6).

Production properties (Decision 8): pagination, retries+backoff (in the provider),
timeouts, structured logging, per-run checkpoints, transactional per-buyer upserts
via savepoints, deduplication by source_id, and idempotent re-execution (re-running
with the same params overwrites to identical values, so an interrupted run is
safely repaired by simply running again).
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from celery import Task

from etl_worker.celery_app import celery_app
from etl_worker.config import get_settings
from etl_worker.db.buyer_sync_repo import (
    checkpoint_sync_run,
    create_sync_run,
    finish_sync_run,
    upsert_buyer,
)
from etl_worker.db.session import get_session_factory
from etl_worker.domain.buyer_intelligence import BuyerAggregate
from etl_worker.providers.base import ProviderAuthError, ProviderError, ShipmentQuery
from etl_worker.providers.factory import get_buyer_source_provider

log = structlog.get_logger(__name__)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


@celery_app.task(name="etl.sync_tradeatlas_buyers", bind=True, queue="ingest")  # type: ignore[untyped-decorator]
def sync_tradeatlas_buyers(
    self: "Task",
    hs_codes: list[str] | str,
    importer_countries: list[str] | None = None,
    exporter_countries: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    max_pages: int | None = None,
) -> dict[str, Any]:
    """Pull importer companies for the given HS codes / markets into the ``buyer`` table."""
    settings = get_settings()
    hs_list = [hs_codes] if isinstance(hs_codes, str) else list(hs_codes or [])
    hs_list = [str(h).strip() for h in hs_list if str(h).strip()]
    if not hs_list:
        raise ValueError("sync_tradeatlas_buyers requires at least one HS code")

    importer_countries = importer_countries or []
    exporter_countries = exporter_countries or []
    page_cap = int(max_pages or settings.tradeatlas_max_pages)

    query = ShipmentQuery(
        hs_codes=hs_list,
        importer_countries=importer_countries,
        exporter_countries=exporter_countries,
        start_date=_parse_date(start_date),
        end_date=_parse_date(end_date),
    )
    params = {
        "hs_codes": hs_list,
        "importer_countries": importer_countries,
        "exporter_countries": exporter_countries,
        "start_date": start_date,
        "end_date": end_date,
        "max_pages": page_cap,
    }

    log.info("tradeatlas.sync.start", **params)
    session_factory = get_session_factory()

    with session_factory() as session:
        run_id = create_sync_run(session, settings.buyer_source_provider, params)

        aggregates: dict[str, BuyerAggregate] = {}
        shipments_seen = 0
        total_pages = 0

        # ── Fetch + aggregate (checkpoint per page) ──────────────────────────────
        try:
            provider = get_buyer_source_provider(settings)
            for page in provider.iter_pages(query, page_cap):
                total_pages = page.total_pages
                for raw in page.shipments:
                    source_id = raw.get("importerUrlCode")
                    if not source_id:
                        continue
                    agg = aggregates.get(source_id)
                    if agg is None:
                        agg = BuyerAggregate(source_id=source_id)
                        aggregates[source_id] = agg
                    agg.add_shipment(raw)
                    shipments_seen += 1
                checkpoint_sync_run(
                    session,
                    run_id,
                    last_page=page.page,
                    total_pages=total_pages,
                    shipments_seen=shipments_seen,
                )
                log.info(
                    "tradeatlas.sync.page",
                    run_id=run_id,
                    page=page.page,
                    total_pages=total_pages,
                    buyers_so_far=len(aggregates),
                )
        except ProviderAuthError as exc:
            # Allowed stop condition: credential expired. Recorded so it resumes later.
            finish_sync_run(
                session, run_id, status="auth_required",
                buyers_upserted=0, buyers_skipped=0, error=str(exc),
            )
            log.error("tradeatlas.sync.auth_required", run_id=run_id, error=str(exc))
            return {"status": "auth_required", "run_id": run_id, "error": str(exc)}
        except ProviderError as exc:
            finish_sync_run(
                session, run_id, status="failed",
                buyers_upserted=0, buyers_skipped=0, error=str(exc),
            )
            log.error("tradeatlas.sync.provider_error", run_id=run_id, error=str(exc))
            raise

        # ── Clean → score → upsert (transactional per buyer) ─────────────────────
        upserted = 0
        skipped = 0
        pending = 0
        buyer_ids: list[str] = []
        batch = settings.buyer_sync_batch_size

        for source_id, agg in aggregates.items():
            if not agg.is_valid_buyer:
                skipped += 1
                log.info(
                    "tradeatlas.sync.skip",
                    run_id=run_id,
                    source_id=source_id,
                    reason="placeholder_name_or_invalid_country",
                    name=agg.name,
                    country=agg.country,
                )
                continue
            fields = agg.to_buyer_fields(settings.buyer_source_provider)
            try:
                with session.begin_nested():  # SAVEPOINT — isolates per-buyer failures
                    buyer_id, _created = upsert_buyer(session, fields)
            except Exception as exc:  # noqa: BLE001 — never let one bad row abort the run
                skipped += 1
                log.error(
                    "tradeatlas.sync.upsert_failed",
                    run_id=run_id, source_id=source_id, error=str(exc),
                )
                continue
            buyer_ids.append(buyer_id)
            upserted += 1
            pending += 1
            if pending >= batch:
                session.commit()
                pending = 0

        session.commit()
        finish_sync_run(
            session, run_id, status="completed",
            buyers_upserted=upserted, buyers_skipped=skipped,
        )

    # ── Dispatch embeddings for the real buyers (after commit) ───────────────────
    for buyer_id in buyer_ids:
        celery_app.send_task(
            "embeddings.generate_buyer", args=[buyer_id], queue="ai", ignore_result=True
        )

    result = {
        "status": "completed",
        "run_id": run_id,
        "shipments_seen": shipments_seen,
        "buyers_upserted": upserted,
        "buyers_skipped": skipped,
        "embedding_tasks_dispatched": len(buyer_ids),
    }
    log.info("tradeatlas.sync.done", **result)
    return result
