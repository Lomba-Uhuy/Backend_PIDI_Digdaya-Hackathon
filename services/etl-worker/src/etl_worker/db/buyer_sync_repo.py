"""Repository for buyer upserts + synchronisation-run checkpoints.

Idempotent upsert keyed on ``(metadata.source, metadata.source_id)`` — never on
company name (Decision 2). Real buyers are written with ``is_synthetic = FALSE``;
existing synthetic buyers are never touched (Decision 1).
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

_UPSERT_SELECT = text(
    "SELECT id FROM buyer "
    "WHERE metadata->>'source' = :src AND metadata->>'source_id' = :sid "
    "LIMIT 1"
)

_UPDATE = text(
    """
    UPDATE buyer SET
        name              = :name,
        country           = :country,
        hs_codes          = :hs,
        credibility_score = :cred,
        description       = :desc,
        metadata          = CAST(:meta AS JSONB),
        is_active         = TRUE,
        is_synthetic      = FALSE,
        updated_at        = NOW()
    WHERE id = :id
    """
)

_INSERT = text(
    """
    INSERT INTO buyer
        (name, country, hs_codes, credibility_score, description,
         is_active, is_synthetic, metadata)
    VALUES
        (:name, :country, :hs, :cred, :desc, TRUE, FALSE, CAST(:meta AS JSONB))
    RETURNING id
    """
)


def upsert_buyer(session: Session, fields: dict[str, Any]) -> tuple[str, bool]:
    """Insert or update one real buyer. Returns ``(buyer_id, created)``.

    Does not commit — the caller controls the transaction/batch boundary.
    """
    metadata = fields["metadata"]
    params = {
        "name": fields["name"],
        "country": fields["country"],
        "hs": fields["hs_codes"],  # psycopg adapts list -> TEXT[]
        "cred": fields["credibility_score"],
        "desc": fields["description"],
        "meta": json.dumps(metadata),
    }
    existing = session.execute(
        _UPSERT_SELECT, {"src": metadata["source"], "sid": metadata["source_id"]}
    ).first()

    if existing is not None:
        buyer_id = existing[0]
        session.execute(_UPDATE, {**params, "id": buyer_id})
        return str(buyer_id), False

    buyer_id = session.execute(_INSERT, params).scalar_one()
    return str(buyer_id), True


# ── Sync-run lifecycle (history + resumable checkpoints) ───────────────────────
def create_sync_run(session: Session, provider: str, params: dict[str, Any]) -> str:
    run_id = session.execute(
        text(
            "INSERT INTO buyer_sync_run (provider, params, status) "
            "VALUES (:p, CAST(:params AS JSONB), 'running') RETURNING id"
        ),
        {"p": provider, "params": json.dumps(params)},
    ).scalar_one()
    session.commit()
    return str(run_id)


def checkpoint_sync_run(
    session: Session,
    run_id: str,
    *,
    last_page: int,
    total_pages: int,
    shipments_seen: int,
) -> None:
    session.execute(
        text(
            "UPDATE buyer_sync_run SET last_page = :lp, total_pages = :tp, "
            "shipments_seen = :ss, updated_at = NOW() WHERE id = :id"
        ),
        {"lp": last_page, "tp": total_pages, "ss": shipments_seen, "id": run_id},
    )
    session.commit()


def finish_sync_run(
    session: Session,
    run_id: str,
    *,
    status: str,
    buyers_upserted: int,
    buyers_skipped: int,
    error: str | None = None,
) -> None:
    session.execute(
        text(
            "UPDATE buyer_sync_run SET status = :st, buyers_upserted = :bu, "
            "buyers_skipped = :bs, error = :err, updated_at = NOW(), "
            "finished_at = NOW() WHERE id = :id"
        ),
        {
            "st": status,
            "bu": buyers_upserted,
            "bs": buyers_skipped,
            "err": error,
            "id": run_id,
        },
    )
    session.commit()
