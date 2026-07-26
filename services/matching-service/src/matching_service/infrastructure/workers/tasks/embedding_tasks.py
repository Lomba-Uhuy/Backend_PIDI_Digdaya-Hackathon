"""Background tasks: generate product / buyer embeddings, upsert to pgvector."""
from __future__ import annotations

import structlog
from celery import Task
from sqlalchemy import text

from matching_service.infrastructure.db.session import sync_session_factory
from matching_service.infrastructure.embeddings.sentence_transformer import get_embedder
from matching_service.infrastructure.workers.celery_app import celery_app

log = structlog.get_logger(__name__)


class EmbeddingTask(Task):
    abstract = True
    max_retries = 3
    default_retry_delay = 10

    def on_failure(self, exc, task_id, args, kwargs, einfo):  # type: ignore[no-untyped-def]
        log.error("task.failed", task_id=task_id, exc=str(exc))
        super().on_failure(exc, task_id, args, kwargs, einfo)


@celery_app.task(
    base=EmbeddingTask,
    name="embeddings.generate_product",
    bind=True,
    queue="ai",
    soft_time_limit=120,
    time_limit=180,
)
def generate_product_embedding(  # type: ignore[no-untyped-def]
    self,
    product_id: str,
    description: str,
    umkm_id: str | None = None,
) -> dict:
    """Generate and upsert product embedding.

    Called by User Service via BullMQ -> bridge -> Celery (or directly).
    """
    log.info("task.embed.product.start", product_id=product_id)
    try:
        embedder = get_embedder()
        text_to_embed = description
        vec = embedder.embed_sync([text_to_embed])[0]

        Session = sync_session_factory()
        with Session() as session:
            session.execute(
                text(
                    """
                    INSERT INTO product_embedding (product_id, model, embedding, created_at, updated_at)
                    VALUES (:pid, :model, :emb, NOW(), NOW())
                    ON CONFLICT (product_id)
                    DO UPDATE SET embedding = :emb, model = :model, updated_at = NOW()
                    """
                ),
                {"pid": product_id, "model": embedder.model_name, "emb": vec},
            )
            session.commit()

        log.info("task.embed.product.done", product_id=product_id, dim=len(vec))
        return {"product_id": product_id, "status": "success", "dim": len(vec)}
    except Exception as exc:
        log.error("task.embed.product.failed", product_id=product_id, exc=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    base=EmbeddingTask,
    name="embeddings.generate_buyer",
    bind=True,
    queue="ai",
)
def generate_buyer_embedding(self, buyer_id: str) -> dict:  # type: ignore[no-untyped-def]
    log.info("task.embed.buyer.start", buyer_id=buyer_id)
    try:
        Session = sync_session_factory()
        with Session() as session:
            row = session.execute(
                text("SELECT name, country, hs_codes, description FROM buyer WHERE id = :bid"),
                {"bid": buyer_id},
            ).fetchone()
            if not row:
                log.warning("task.embed.buyer.not_found", buyer_id=buyer_id)
                return {"buyer_id": buyer_id, "status": "not_found"}

            name, country, hs_codes, description = row
            buyer_text = (
                f"International buyer {name} from {country}. "
                f"Imports products: {', '.join(hs_codes or [])}. "
                f"{description or ''}"
            )
            embedder = get_embedder()
            vec = embedder.embed_sync([buyer_text])[0]

            session.execute(
                text(
                    """
                    INSERT INTO buyer_embedding (buyer_id, model, embedding, created_at, updated_at)
                    VALUES (:bid, :model, :emb, NOW(), NOW())
                    ON CONFLICT (buyer_id)
                    DO UPDATE SET embedding = :emb, model = :model, updated_at = NOW()
                    """
                ),
                {"bid": buyer_id, "model": embedder.model_name, "emb": vec},
            )
            session.commit()
        log.info("task.embed.buyer.done", buyer_id=buyer_id)
        return {"buyer_id": buyer_id, "status": "success"}
    except Exception as exc:
        raise self.retry(exc=exc)