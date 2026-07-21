"""POST /ai/chat — TradeConnect export-consultation assistant.

Reuses the existing infrastructure: the Gemini/Anthropic LLM (`get_llm`) and the
export knowledge base retriever (RAG, full-text). Answers are grounded in (a) the
user's real business context passed from the frontend and (b) retrieved knowledge
base entries — the model is instructed to prefer this project data over generic
knowledge and to be honest when data is missing.
"""
from __future__ import annotations

from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from comms_service.infrastructure.db.session import get_session
from comms_service.infrastructure.llm.anthropic_client import get_llm
from comms_service.infrastructure.rag.knowledge_base import KnowledgeBaseRetriever

log = structlog.get_logger(__name__)
router = APIRouter()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class BusinessContext(BaseModel):
    product_name: str | None = None
    hs_code: str | None = None
    hs_category: str | None = None
    company: str | None = None
    floor_price_usd: float | None = None
    asking_price_usd: float | None = None
    top_markets: list[str] = Field(default_factory=list)
    buyer_total: int | None = None
    buyer_verified: int | None = None
    deals_total: int | None = None
    deals_active: int | None = None
    readiness_score: int | None = None


class ChatBody(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)
    context: BusinessContext | None = None


class Source(BaseModel):
    title: str
    category: str


class ChatResponse(BaseModel):
    reply: str
    sources: list[Source]
    grounded: bool


_SYSTEM = (
    "Anda adalah \"Mentor Ekspor AI\" TradeConnect — konsultan ekspor senior untuk "
    "UMKM Indonesia. Jawab dalam Bahasa Indonesia yang ringkas, praktis, dan berbasis data.\n"
    "Prioritaskan KONTEKS BISNIS PENGGUNA dan BASIS PENGETAHUAN di bawah dibanding "
    "pengetahuan umum. Jika data yang diminta tidak tersedia dalam konteks, katakan dengan "
    "jujur dan sarankan langkah untuk memperolehnya (mis. buka menu terkait). Jangan mengarang "
    "angka atau nama pembeli. Gunakan poin/tabel Markdown bila membantu.\n"
    "Domain keahlian: klasifikasi HS, pembeli/importir, intelijen pasar (BPS & UN Comtrade), "
    "negosiasi, kesiapan ekspor, kepatuhan, Incoterms, dan dokumen ekspor."
)


def _format_context(ctx: BusinessContext | None) -> str:
    if ctx is None:
        return "Belum ada konteks produk yang dibagikan pengguna."
    lines: list[str] = []
    if ctx.product_name:
        lines.append(f"- Produk: {ctx.product_name}")
    if ctx.hs_code:
        lines.append(f"- Kode HS: {ctx.hs_code}" + (f" ({ctx.hs_category})" if ctx.hs_category else ""))
    if ctx.company:
        lines.append(f"- Perusahaan: {ctx.company}")
    if ctx.floor_price_usd is not None or ctx.asking_price_usd is not None:
        lines.append(
            f"- Harga: dasar ${ctx.floor_price_usd or '-'} / penawaran ${ctx.asking_price_usd or '-'} per unit"
        )
    if ctx.top_markets:
        lines.append(f"- Pasar impor teratas (nilai): {', '.join(ctx.top_markets[:5])}")
    if ctx.buyer_total is not None:
        lines.append(
            f"- Direktori pembeli: {ctx.buyer_total} total"
            + (f", {ctx.buyer_verified} terverifikasi" if ctx.buyer_verified is not None else "")
        )
    if ctx.deals_total is not None:
        lines.append(
            f"- Negosiasi: {ctx.deals_total} total"
            + (f", {ctx.deals_active} aktif" if ctx.deals_active is not None else "")
        )
    if ctx.readiness_score is not None:
        lines.append(f"- Skor kesiapan ekspor: {ctx.readiness_score}/100")
    return "\n".join(lines) if lines else "Belum ada konteks produk yang dibagikan pengguna."


@router.post("/ai/chat", response_model=ChatResponse)
async def ai_chat(
    body: ChatBody,
    session=Depends(get_session),
) -> ChatResponse:
    last_user = next((m.content for m in reversed(body.messages) if m.role == "user"), "")

    # RAG: retrieve relevant export-knowledge-base entries (full-text, no embeddings needed).
    entries: list[dict] = []
    try:
        retriever = KnowledgeBaseRetriever(session)
        entries = await retriever.search_by_text(last_user, intent="general", top_k=4)
    except Exception as exc:  # noqa: BLE001
        log.warning("consultation.rag_failed", error=str(exc))

    kb_context = KnowledgeBaseRetriever.format_context(entries)
    biz_context = _format_context(body.context)

    system = (
        f"{_SYSTEM}\n\n=== KONTEKS BISNIS PENGGUNA ===\n{biz_context}\n\n"
        f"=== BASIS PENGETAHUAN EKSPOR ===\n{kb_context}"
    )

    # Format the recent conversation as the user turn.
    transcript = "\n".join(
        f"{'Pengguna' if m.role == 'user' else 'Asisten'}: {m.content}" for m in body.messages[-12:]
    )
    user = (
        f"Riwayat percakapan:\n{transcript}\n\n"
        f"Berikan jawaban Asisten berikutnya untuk pesan terakhir pengguna."
    )

    try:
        reply = await get_llm().complete(system=system, user=user, max_tokens=1200, temperature=0.4)
    except Exception as exc:  # noqa: BLE001
        log.error("consultation.llm_failed", error=str(exc))
        reply = (
            "Maaf, layanan AI sedang tidak tersedia saat ini (kuota/kredit model). "
            "Silakan coba lagi beberapa saat lagi."
        )

    return ChatResponse(
        reply=(reply or "").strip() or "Maaf, saya tidak dapat menghasilkan jawaban saat ini.",
        sources=[
            Source(title=str(e.get("title", "")), category=str(e.get("category", "general")))
            for e in entries
        ],
        grounded=bool(entries),
    )
