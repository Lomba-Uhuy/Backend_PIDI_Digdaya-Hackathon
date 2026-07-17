"""POST /generate-reply — email reply drafting for UMKM exporters.

Accepts an importer email + product context, retrieves relevant knowledge from
the export knowledge base, and generates a professional English reply via LLM.
Guardrails ensure no sensitive pricing information leaks in the output.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field

from comms_service.application.rag_service import NegotiationRAGService
from comms_service.infrastructure.cache.umkm_context_loader import load_umkm_context
from comms_service.infrastructure.db.session import get_session

router = APIRouter()


class GenerateReplyBody(BaseModel):
    importer_email: str = Field(
        min_length=10,
        max_length=10_000,
        description="Raw email text received from the importer",
    )
    product_id: str = Field(min_length=1, description="UMKM product UUID")
    buyer_id: str | None = Field(default=None, description="Known buyer UUID for context enrichment")


class GenerateReplyResponse(BaseModel):
    draft_en: str = Field(description="Professional English reply draft")
    intent: str = Field(description="Detected buyer intent (rfq, price_negotiation, complaint, general)")
    warnings: list[str] = Field(description="Guardrail warning messages (empty if clean)")
    confidence: float = Field(description="Draft quality confidence score [0, 1]")


@router.post("/generate-reply", response_model=GenerateReplyResponse)
async def generate_reply(
    body: GenerateReplyBody,
    x_user_id: Annotated[str | None, Header(alias="x-user-id")] = None,
    session=Depends(get_session),
) -> GenerateReplyResponse:
    """Generate a professional English reply to an importer email.

    Pipeline:
    1. Load UMKM product context (pricing, MOQ, certifications) from DB
    2. Retrieve relevant documents from export knowledge base (Incoterms, regs, templates)
    3. LLM generates reply with negotiation strategy embedded in system prompt
    4. Guardrail validation — regenerates up to 2× if violations detected
    5. Final sanitization: below-floor prices replaced with placeholder
    """
    umkm_ctx = await load_umkm_context(
        session, product_id=body.product_id, user_id=x_user_id
    )
    svc = NegotiationRAGService(session=session)
    result = await svc.draft_reply(
        inquiry_text=body.importer_email,
        umkm_context=umkm_ctx,
        buyer_id=body.buyer_id,
    )
    # Extract intent label from strategy_id (e.g. "rag_rfq_v1" → "rfq")
    parts = result.strategy_id.split("_")
    intent = parts[1] if len(parts) >= 3 else "general"
    return GenerateReplyResponse(
        draft_en=result.draft_en,
        intent=intent,
        warnings=result.warnings,
        confidence=result.confidence,
    )
