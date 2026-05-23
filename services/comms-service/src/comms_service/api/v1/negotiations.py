"""Negotiation drafting endpoint."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field

from comms_service.application.rag_service import NegotiationRAGService, UMKMContext
from comms_service.infrastructure.db.session import get_session
from comms_service.infrastructure.cache.umkm_context_loader import load_umkm_context

router = APIRouter()


class DraftBody(BaseModel):
    inquiry_text: str = Field(min_length=10, max_length=10_000)
    product_id: str = Field(min_length=1)
    buyer_id: str | None = None


class DraftResponse(BaseModel):
    draft_en: str
    strategy_id: str
    rationale_id: str
    warnings: list[str]
    confidence: float


@router.post("/draft", response_model=DraftResponse)
async def draft_reply(
    body: DraftBody,
    x_user_id: Annotated[str | None, Header(alias="x-user-id")] = None,
    session=Depends(get_session),
) -> DraftResponse:
    # In production, load UMKM context via internal gRPC/HTTP call to user-service.
    # Here we load via DB read with stub fallback so the service is usable in dev.
    umkm_ctx = await load_umkm_context(session, product_id=body.product_id, user_id=x_user_id)

    # Pass the session so the RAG service can access the knowledge base
    svc = NegotiationRAGService(session=session)
    result = await svc.draft_reply(
        inquiry_text=body.inquiry_text,
        umkm_context=umkm_ctx,
        buyer_id=body.buyer_id,
    )
    return DraftResponse(
        draft_en=result.draft_en,
        strategy_id=result.strategy_id,
        rationale_id=result.rationale_id,
        warnings=result.warnings,
        confidence=result.confidence,
    )
