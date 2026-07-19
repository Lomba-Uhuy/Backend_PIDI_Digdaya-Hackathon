"""Buyer matching endpoint."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field

from matching_service.application.matching_service import MatchingService, MatchRequest
from matching_service.infrastructure.db.session import get_session

router = APIRouter()


class MatchSearchBody(BaseModel):
    product_id: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=50)
    country_filter: list[str] | None = None


class MatchBuyersBody(BaseModel):
    embedding: list[float] = Field(min_length=1, description="Product embedding vector (1024-dim)")
    top_k: int = Field(default=10, ge=1, le=50)
    country_filter: list[str] | None = Field(default=None, description="ISO-2 country codes, e.g. ['DE','NL']")
    min_volume: int | None = Field(default=None, ge=1, description="Minimum buyer MOQ filter")
    category: str | None = Field(default=None, description="HS code prefix filter, e.g. '09' or '0901'")


class MatchResult(BaseModel):
    buyer_id: str
    name: str
    country: str
    hs_codes: list[str]
    credibility_score: float
    similarity_score: float
    distance: float
    explanation: str
    is_synthetic: bool
    min_order_qty: int = 0


def _to_match_result(m: object) -> MatchResult:
    return MatchResult(
        buyer_id=m.buyer_id,  # type: ignore[attr-defined]
        name=m.name,  # type: ignore[attr-defined]
        country=m.country,  # type: ignore[attr-defined]
        hs_codes=m.hs_codes,  # type: ignore[attr-defined]
        credibility_score=m.credibility_score,  # type: ignore[attr-defined]
        similarity_score=m.similarity_score,  # type: ignore[attr-defined]
        distance=m.distance,  # type: ignore[attr-defined]
        explanation=m.explanation,  # type: ignore[attr-defined]
        is_synthetic=m.is_synthetic,  # type: ignore[attr-defined]
        min_order_qty=getattr(m, "min_order_qty", 0),  # type: ignore[attr-defined]
    )


@router.post("/match", response_model=list[MatchResult])
async def search_buyers(
    body: MatchSearchBody,
    x_user_id: Annotated[str | None, Header(alias="x-user-id")] = None,
    session=Depends(get_session),
) -> list[MatchResult]:
    svc = MatchingService(session)
    matches = await svc.find_buyers(
        MatchRequest(
            product_id=body.product_id,
            product_description="",
            hs_code=None,
            moq=1,
            top_k=body.top_k,
            country_filter=body.country_filter,
        )
    )
    return [_to_match_result(m) for m in matches]


@router.post("/match-buyers", response_model=list[MatchResult])
async def match_buyers(
    body: MatchBuyersBody,
    x_user_id: Annotated[str | None, Header(alias="x-user-id")] = None,
    session=Depends(get_session),
) -> list[MatchResult]:
    """Accept a product embedding vector directly and return the top-K buyer shortlist.

    Filters (all optional):
    - country_filter: restrict to specific importing countries
    - min_volume: only buyers whose MOQ >= min_volume (serious large-order buyers)
    - category: HS code prefix to restrict to buyers active in that product category
    """
    svc = MatchingService(session)
    matches = await svc.find_buyers_by_embedding(
        embedding=body.embedding,
        top_k=body.top_k,
        country_filter=body.country_filter,
        min_volume=body.min_volume,
        category=body.category,
    )
    return [_to_match_result(m) for m in matches]