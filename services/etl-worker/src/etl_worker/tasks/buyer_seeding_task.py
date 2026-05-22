"""Buyer seeding task — synthetic buyer profiles flagged is_synthetic = TRUE."""
from __future__ import annotations

import json
import random
from uuid import uuid4

import structlog
from sqlalchemy import text

from etl_worker.celery_app import celery_app
from etl_worker.db.session import get_session_factory

log = structlog.get_logger(__name__)

COUNTRIES = ["DE", "NL", "US", "JP", "AE", "FR", "GB", "AU", "CA", "SG", "KR"]
HS_CODES = ["4602", "1404", "9403", "0901", "0902", "1801", "1513", "0801", "2106", "6302", "3305"]


@celery_app.task(name="seeding.synthetic_buyers", bind=True, queue="ingest")
def seed_synthetic_buyers(self, count: int = 100) -> dict:  # type: ignore[no-untyped-def]
    """Seed N synthetic buyers, all flagged is_synthetic = TRUE.

    Per the v2 spec's transparency requirement: every synthetic buyer
    is labeled in the DB, and the UI must show 'Data Simulasi' to users.
    """
    log.info("seeding.synthetic.start", count=count)
    random.seed(42)
    inserted = 0

    Session = get_session_factory()
    with Session() as session:
        for i in range(count):
            buyer_id = str(uuid4())
            country = random.choice(COUNTRIES)
            hs = random.sample(HS_CODES, k=random.randint(1, 3))
            cred = round(random.uniform(0.5, 0.95), 3)
            session.execute(
                text(
                    """
                    INSERT INTO buyer (
                        id, name, country, hs_codes, credibility_score,
                        min_order_qty, description, is_active, is_synthetic, metadata
                    )
                    VALUES (
                        :id, :name, :country, :hs, :cred,
                        :moq, :desc, TRUE, TRUE, CAST(:meta AS JSONB)
                    )
                    """
                ),
                {
                    "id": buyer_id,
                    "name": f"Synthetic Importer {i:04d} GmbH",
                    "country": country,
                    "hs": hs,
                    "cred": cred,
                    "moq": random.choice([100, 250, 500, 1000]),
                    "desc": (
                        f"Buyer importing categories {', '.join(hs)} from Southeast Asia. "
                        f"Mirrors UN Comtrade flow patterns. SYNTHETIC for demo."
                    ),
                    "meta": json.dumps({"source": "synthetic_v1", "seed": 42}),
                },
            )
            inserted += 1
        session.commit()

    log.info("seeding.synthetic.done", inserted=inserted)
    return {"inserted": inserted}