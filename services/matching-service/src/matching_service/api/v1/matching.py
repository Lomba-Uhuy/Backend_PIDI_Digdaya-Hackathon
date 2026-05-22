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
    return [
        MatchResult(
            buyer_id=m.buyer_id,
            name=m.name,
            country=m.country,
            hs_codes=m.hs_codes,
            credibility_score=m.credibility_score,
            similarity_score=m.similarity_score,
            distance=m.distance,
            explanation=m.explanation,
            is_synthetic=m.is_synthetic,
        )
        for m in matches
    ]