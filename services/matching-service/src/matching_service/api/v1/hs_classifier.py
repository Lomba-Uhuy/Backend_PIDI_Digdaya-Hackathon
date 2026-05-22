"""HS Code classification endpoint."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from matching_service.application.hs_classifier_service import get_hs_classifier

router = APIRouter()


class ClassifyRequest(BaseModel):
    description: str = Field(min_length=3, max_length=5000)
    top_k: int = Field(default=3, ge=1, le=10)


class ClassifyCandidate(BaseModel):
    hs_code: str
    description: str
    confidence: float


class ClassifyResponse(BaseModel):
    hs_code: str
    description: str
    confidence: float
    top_k: list[ClassifyCandidate]


@router.post("/classify", response_model=ClassifyResponse)
async def classify(body: ClassifyRequest) -> ClassifyResponse:
    result = get_hs_classifier().classify(body.description, top_k=body.top_k)
    return ClassifyResponse(
        hs_code=result.hs_code,
        description=result.description,
        confidence=result.confidence,
        top_k=[ClassifyCandidate(**c) for c in result.top_k],
    )