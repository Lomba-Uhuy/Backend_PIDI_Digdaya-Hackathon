"""Buyer directory API — search / detail / statistics.

Serves the synchronised production `buyer` table (real + synthetic). The frontend
never talks to TradeAtlas directly (Decision 13): every response originates here,
from the database. `is_synthetic` is always exposed so the UI can label simulated
records.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from matching_service.infrastructure.db.models.buyer import BuyerORM
from matching_service.infrastructure.db.session import get_session
from matching_service.infrastructure.workers.celery_app import celery_app

router = APIRouter()

_SORTABLE = {
    "credibility": BuyerORM.credibility_score,
    "name": BuyerORM.name,
    "created_at": BuyerORM.created_at,
    "min_order_qty": BuyerORM.min_order_qty,
}


# ── Schemas ────────────────────────────────────────────────────────────────────
class BuyerSummary(BaseModel):
    buyer_id: str
    name: str
    country: str
    hs_codes: list[str]
    credibility_score: float
    min_order_qty: int
    is_synthetic: bool
    source: str | None = None
    shipment_count: int | None = None


class BuyerListResponse(BaseModel):
    items: list[BuyerSummary]
    page: int
    per_page: int
    total: int
    total_pages: int


class BuyerDetail(BuyerSummary):
    description: str | None = None
    is_active: bool
    metadata: dict[str, Any]
    created_at: str | None = None
    updated_at: str | None = None


class SourceCount(BaseModel):
    source: str
    count: int


class CountryCount(BaseModel):
    country: str
    count: int


class BuyerStats(BaseModel):
    total: int
    real: int
    synthetic: int
    by_source: list[SourceCount]
    top_countries: list[CountryCount]


class BuyerSyncRequest(BaseModel):
    # Dynamic inputs — HS from the product RAG/classifier, markets from user selection.
    hs_codes: list[str] = Field(min_length=1)
    importer_countries: list[str] = Field(default_factory=list)
    exporter_countries: list[str] = Field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None
    max_pages: int | None = Field(default=None, ge=1, le=1000)


class BuyerSyncResponse(BaseModel):
    status: str
    task_id: str
    hs_codes: list[str]
    importer_countries: list[str]


# ── Helpers ────────────────────────────────────────────────────────────────────
def _summary(b: BuyerORM) -> BuyerSummary:
    meta = b.metadata_json or {}
    return BuyerSummary(
        buyer_id=str(b.id),
        name=b.name,
        country=b.country,
        hs_codes=list(b.hs_codes or []),
        credibility_score=float(b.credibility_score),
        min_order_qty=int(b.min_order_qty),
        is_synthetic=bool(b.is_synthetic),
        source=meta.get("source"),
        shipment_count=meta.get("shipment_count"),
    )


# ── Endpoints (order: static paths before /{buyer_id}) ─────────────────────────
@router.get("/buyers", response_model=BuyerListResponse)
async def list_buyers(
    session: Annotated[AsyncSession, Depends(get_session)],
    q: str | None = Query(default=None, description="Name contains (case-insensitive)"),
    country: list[str] | None = Query(default=None, description="ISO-2 country code(s)"),
    hs: str | None = Query(default=None, description="HS heading the buyer sources (prefix match, e.g. 0901 → 0901xx)"),
    source: str | None = Query(default=None, description="Provider, e.g. 'tradeatlas'"),
    is_synthetic: bool | None = Query(default=None, description="Filter real vs simulated"),
    min_credibility: float | None = Query(default=None, ge=0.0, le=1.0),
    sort_by: str = Query(default="credibility"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> BuyerListResponse:
    conds = []
    if q:
        conds.append(BuyerORM.name.ilike(f"%{q}%"))
    if country:
        conds.append(BuyerORM.country.in_([c.strip().upper() for c in country]))
    if hs:
        # Prefix match: buyer sources any HS code under this heading (0901 → 0901, 090111…).
        conds.append(
            text("EXISTS (SELECT 1 FROM unnest(buyer.hs_codes) AS _c WHERE _c LIKE :hs_prefix)").bindparams(
                hs_prefix=f"{hs.strip()}%"
            )
        )
    if source:
        conds.append(BuyerORM.metadata_json["source"].astext == source)
    if is_synthetic is not None:
        conds.append(BuyerORM.is_synthetic.is_(is_synthetic))
    if min_credibility is not None:
        conds.append(BuyerORM.credibility_score >= min_credibility)

    where = and_(*conds) if conds else None

    count_stmt = select(func.count()).select_from(BuyerORM)
    if where is not None:
        count_stmt = count_stmt.where(where)
    total = int((await session.execute(count_stmt)).scalar_one())

    col = _SORTABLE.get(sort_by, BuyerORM.credibility_score)
    order = col.asc() if sort_dir == "asc" else col.desc()

    stmt = select(BuyerORM)
    if where is not None:
        stmt = stmt.where(where)
    stmt = stmt.order_by(order).limit(per_page).offset((page - 1) * per_page)
    rows = (await session.execute(stmt)).scalars().all()

    total_pages = (total + per_page - 1) // per_page if per_page else 0
    return BuyerListResponse(
        items=[_summary(b) for b in rows],
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
    )


@router.post("/buyers/sync", response_model=BuyerSyncResponse, status_code=202)
async def trigger_buyer_sync(body: BuyerSyncRequest) -> BuyerSyncResponse:
    """Enqueue a real-buyer sync for the given HS codes + target markets.

    Fully dynamic (Decisions 5 & 6): the caller passes the product's HS codes
    (from the RAG/classifier) and the user-selected markets. Enqueues the ETL task
    ``etl.sync_tradeatlas_buyers`` on the ``ingest`` queue; returns immediately.
    """
    async_result = celery_app.send_task(
        "etl.sync_tradeatlas_buyers",
        kwargs={
            "hs_codes": body.hs_codes,
            "importer_countries": body.importer_countries,
            "exporter_countries": body.exporter_countries,
            "start_date": body.start_date,
            "end_date": body.end_date,
            "max_pages": body.max_pages,
        },
        queue="ingest",
    )
    return BuyerSyncResponse(
        status="queued",
        task_id=str(async_result.id),
        hs_codes=body.hs_codes,
        importer_countries=body.importer_countries,
    )


@router.get("/buyers/stats", response_model=BuyerStats)
async def buyer_stats(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BuyerStats:
    total = int((await session.execute(select(func.count()).select_from(BuyerORM))).scalar_one())
    synthetic = int(
        (
            await session.execute(
                select(func.count()).select_from(BuyerORM).where(BuyerORM.is_synthetic.is_(True))
            )
        ).scalar_one()
    )

    src_col = BuyerORM.metadata_json["source"].astext
    by_source_rows = (
        await session.execute(
            select(src_col, func.count())
            .where(BuyerORM.is_synthetic.is_(False))
            .group_by(src_col)
            .order_by(func.count().desc())
        )
    ).all()

    country_rows = (
        await session.execute(
            select(BuyerORM.country, func.count())
            .group_by(BuyerORM.country)
            .order_by(func.count().desc())
            # High cap so this also serves as the source of truth for the buyer
            # country filter dropdown (every country actually present, by volume).
            .limit(250)
        )
    ).all()

    return BuyerStats(
        total=total,
        real=total - synthetic,
        synthetic=synthetic,
        by_source=[SourceCount(source=(s or "unknown"), count=int(c)) for s, c in by_source_rows],
        top_countries=[CountryCount(country=(k or "??"), count=int(c)) for k, c in country_rows],
    )


class CredibilityBand(BaseModel):
    band: str
    count: int


class HsCount(BaseModel):
    hs: str
    count: int


class TopBuyer(BaseModel):
    name: str
    country: str
    credibility_score: float


class BuyerAnalytics(BaseModel):
    total: int
    by_credibility: list[CredibilityBand]
    by_hs: list[HsCount]
    missing_embeddings: int
    recently_synced: int
    without_hs: int
    top_credibility: list[TopBuyer]


@router.get("/buyers/analytics", response_model=BuyerAnalytics)
async def buyer_analytics(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BuyerAnalytics:
    """Buyer directory analytics — all aggregated from the real `buyer` table."""
    total = int((await session.execute(text("SELECT COUNT(*) FROM buyer"))).scalar_one())

    cred_rows = (
        await session.execute(
            text(
                "SELECT CASE WHEN credibility_score >= 0.6 THEN 'high' "
                "WHEN credibility_score >= 0.4 THEN 'medium' ELSE 'low' END AS band, "
                "COUNT(*) AS count FROM buyer GROUP BY band"
            )
        )
    ).all()

    hs_rows = (
        await session.execute(
            text(
                "SELECT hs, COUNT(*) AS count FROM (SELECT unnest(hs_codes) AS hs FROM buyer) x "
                "WHERE hs <> '' GROUP BY hs ORDER BY count DESC LIMIT 8"
            )
        )
    ).all()

    missing = int(
        (
            await session.execute(
                text(
                    "SELECT COUNT(*) FROM buyer b "
                    "LEFT JOIN buyer_embedding e ON e.buyer_id = b.id WHERE e.buyer_id IS NULL"
                )
            )
        ).scalar_one()
    )
    recent = int(
        (
            await session.execute(
                text("SELECT COUNT(*) FROM buyer WHERE updated_at >= NOW() - INTERVAL '7 days'")
            )
        ).scalar_one()
    )
    without_hs = int(
        (
            await session.execute(
                text("SELECT COUNT(*) FROM buyer WHERE hs_codes IS NULL OR cardinality(hs_codes) = 0")
            )
        ).scalar_one()
    )
    top_rows = (
        await session.execute(
            text(
                "SELECT name, country, credibility_score FROM buyer "
                "ORDER BY credibility_score DESC NULLS LAST LIMIT 5"
            )
        )
    ).all()

    return BuyerAnalytics(
        total=total,
        by_credibility=[
            CredibilityBand(band=r._mapping["band"], count=int(r._mapping["count"])) for r in cred_rows
        ],
        by_hs=[HsCount(hs=r._mapping["hs"], count=int(r._mapping["count"])) for r in hs_rows],
        missing_embeddings=missing,
        recently_synced=recent,
        without_hs=without_hs,
        top_credibility=[
            TopBuyer(
                name=r._mapping["name"],
                country=r._mapping["country"],
                credibility_score=float(r._mapping["credibility_score"] or 0),
            )
            for r in top_rows
        ],
    )


@router.get("/buyers/{buyer_id}", response_model=BuyerDetail)
async def buyer_detail(
    session: Annotated[AsyncSession, Depends(get_session)],
    buyer_id: str = Path(..., description="Buyer UUID"),
) -> BuyerDetail:
    row = (
        await session.execute(select(BuyerORM).where(BuyerORM.id == buyer_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Buyer not found")

    base = _summary(row)
    return BuyerDetail(
        **base.model_dump(),
        description=row.description,
        is_active=bool(row.is_active),
        metadata=row.metadata_json or {},
        created_at=row.created_at.isoformat() if row.created_at else None,
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )
