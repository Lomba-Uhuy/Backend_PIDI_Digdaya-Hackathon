"""BPS (Badan Pusat Statistik) ingestion stub."""
from __future__ import annotations

import structlog

from etl_worker.celery_app import celery_app

log = structlog.get_logger(__name__)


@celery_app.task(name="etl.ingest_bps", bind=True, queue="ingest")
def ingest_bps(self, dataset_id: str) -> dict:  # type: ignore[no-untyped-def]
    log.info("etl.bps.start", dataset_id=dataset_id)
    # TODO: BPS web API integration
    return {"dataset_id": dataset_id, "status": "stub"}