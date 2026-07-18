"""UMKM verification result update helper."""
from __future__ import annotations

import json
from typing import Any

import structlog
from sqlalchemy import text

from etl_worker.db.session import get_session_factory

log = structlog.get_logger(__name__)


def update_umkm_verification_result(
    *,
    umkm_id: str,
    oss_data: dict[str, Any],
    verified_score: float,
    status: str,
) -> None:
    session_factory = get_session_factory()
    with session_factory() as session:
        session.execute(
            text(
                """
                UPDATE umkm
                SET verification_status = :status,
                    verified_score      = :score,
                    oss_rba_data        = CAST(:oss AS JSONB),
                    updated_at          = NOW()
                WHERE id = :id
                """
            ),
            {
                "id": umkm_id,
                "status": status,
                "score": verified_score,
                "oss": json.dumps(oss_data),
            },
        )
        session.commit()
    log.info("umkm.verification.persisted", umkm_id=umkm_id, status=status, score=verified_score)
