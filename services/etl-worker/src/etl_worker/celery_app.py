"""Celery app — handles 'external' and 'ingest' queues."""
from __future__ import annotations

from celery import Celery

from etl_worker.config import settings

celery_app = Celery(
    "etl-worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "etl_worker.tasks.verification_task",
        "etl_worker.tasks.un_comtrade_task",
        "etl_worker.tasks.bps_task",
        "etl_worker.tasks.buyer_seeding_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "verification.*": {"queue": "external"},
        "etl.*":          {"queue": "ingest"},
        "seeding.*":      {"queue": "ingest"},
    },
)