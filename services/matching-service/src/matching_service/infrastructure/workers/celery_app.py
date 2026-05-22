"""Celery application — Redis broker."""
from __future__ import annotations

from celery import Celery

from matching_service.core.config import settings

celery_app = Celery(
    "matching",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["matching_service.infrastructure.workers.tasks.embedding_tasks"],
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
        "embeddings.*": {"queue": "ai"},
    },
)