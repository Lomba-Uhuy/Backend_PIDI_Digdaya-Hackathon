"""Celery app — handles 'external' and 'ingest' queues."""
from __future__ import annotations

from datetime import timedelta

from celery import Celery
from kombu import Queue  # type: ignore[import-untyped]

from etl_worker.config import settings

# Semua config diberikan langsung di constructor Celery agar sesuai dengan
# signature yang dideklarasikan oleh celery-stubs (conf.update() stubnya
# hanya menerima Iterable, bukan keyword args).
celery_app = Celery(
    "etl-worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "etl_worker.tasks.verification_task",
        "etl_worker.tasks.un_comtrade_task",
        "etl_worker.tasks.bps_task",
        "etl_worker.tasks.inatrade_task",
        "etl_worker.tasks.buyer_seeding_task",
        "etl_worker.tasks.product_seeding_task",
        "etl_worker.tasks.tradeatlas_buyer_sync_task",
    ],
    # ── Serialization ──────────────────────────────────────────────────────
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # ── Timezone ───────────────────────────────────────────────────────────
    timezone="Asia/Jakarta",
    enable_utc=True,
    # ── Reliability ────────────────────────────────────────────────────────
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Wajib di Celery 5.3+ — mencegah deprecation warning saat startup
    broker_connection_retry_on_startup=True,
    # Restart worker process setiap 500 task untuk cegah memory leak
    worker_max_tasks_per_child=500,
    # ── Queues ─────────────────────────────────────────────────────────────
    # Deklarasi eksplisit agar worker mengenali kedua queue
    task_queues=[
        Queue("external"),
        Queue("ingest"),
    ],
    task_default_queue="ingest",
    task_routes={
        "verification.*": {"queue": "external"},
        "etl.*":          {"queue": "ingest"},
        "seeding.*":      {"queue": "ingest"},
    },
    # ── Results ────────────────────────────────────────────────────────────
    # timedelta wajib — stubs Celery menolak plain int untuk result_expires
    result_expires=timedelta(hours=1),
)
