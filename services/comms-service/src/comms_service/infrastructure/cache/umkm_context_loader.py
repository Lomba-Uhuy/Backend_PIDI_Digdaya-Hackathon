"""Load UMKM context for the negotiation draft.

In production: HTTP call to user-service /internal/umkm/by-product/{product_id}.
For now: direct DB read with safe fallback so dev/demos work end-to-end.
"""
from __future__ import annotations

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from comms_service.application.rag_service import UMKMContext

log = structlog.get_logger(__name__)


async def load_umkm_context(
    session: AsyncSession,
    *,
    product_id: str,
    user_id: str | None,
) -> UMKMContext:
    try:
        result = await session.execute(
            text(
                """
                SELECT u.id           AS umkm_id,
                       u.legal_name   AS legal_name,
                       u.certifications AS certifications,
                       p.name         AS product_name,
                       p.moq          AS moq,
                       p.monthly_capacity AS monthly_capacity,
                       p.price_min    AS price_min,
                       p.price_max    AS price_max,
                       p.hpp          AS hpp
                FROM product p
                JOIN umkm u ON u.id = p.umkm_id
                WHERE p.id = :pid
                """
            ),
            {"pid": product_id},
        )
        row = result.mappings().first()
        if row is None:
            log.warning("umkm_ctx.not_found", product_id=product_id)
            return _stub_context(product_id)

        # floor_price = HPP (true bottom line)
        # target_price = price_max (anchor high in negotiations)
        return UMKMContext(
            umkm_id=str(row["umkm_id"]),
            legal_name=row["legal_name"],
            product_name=row["product_name"],
            floor_price_idr=float(row["hpp"]),
            target_price_idr=float(row["price_max"]),
            moq=int(row["moq"]),
            monthly_capacity=int(row["monthly_capacity"]),
            lead_time_days=30,  # TODO: per-product config
            certifications=list(row["certifications"] or []),
            accepted_payment_terms=["LC at sight", "TT 30%/70%", "CAD"],
            batna="(internal) alternative buyers under exploration",
        )
    except Exception as e:  # noqa: BLE001
        log.warning("umkm_ctx.load_failed.using_stub", error=str(e))
        return _stub_context(product_id)


def _stub_context(product_id: str) -> UMKMContext:
    return UMKMContext(
        umkm_id="stub-umkm",
        legal_name="Demo UMKM (stub)",
        product_name=f"Demo product {product_id}",
        floor_price_idr=150_000.0,
        target_price_idr=300_000.0,
        moq=100,
        monthly_capacity=5_000,
        lead_time_days=30,
        certifications=["SNI"],
        accepted_payment_terms=["LC at sight", "TT 30%/70%"],
        batna="(internal) alternative buyer under negotiation",
    )