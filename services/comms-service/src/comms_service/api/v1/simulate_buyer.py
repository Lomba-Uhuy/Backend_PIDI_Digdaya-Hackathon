"""POST /negotiations/simulate-buyer-reply — AI-simulated importer counterparty.

No real inbound email/webhook channel exists, so the buyer's turns are generated
here and persisted (by the caller) + attributed as simulated. The NUMERIC
negotiation is deterministic so it always converges to a real settlement price
derived from the seller's actual CIF and the real BPS export benchmark; only the
prose is LLM-generated (falling back to a template when no API key is set).
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field

from comms_service.core.config import settings
from comms_service.infrastructure.llm.anthropic_client import get_llm

log = structlog.get_logger(__name__)
router = APIRouter()


class BuyerTurnMessage(BaseModel):
    sender: str
    text: str


class SimulateBuyerBody(BaseModel):
    history: list[BuyerTurnMessage] = Field(default_factory=list)
    product_name: str | None = None
    hs_code: str | None = None
    buyer_name: str | None = None
    buyer_country: str | None = None
    seller_price: float | None = Field(
        default=None, description="Latest CIF/unit the seller proposed (USD/kg)"
    )
    floor_price: float | None = Field(default=None, description="Seller minimum (USD/kg)")
    benchmark_unit_value: float | None = Field(
        default=None, description="Real BPS export unit value (USD/kg)"
    )


class SimulateBuyerResponse(BaseModel):
    text: str
    intent: str
    proposed_price: float | None
    accept: bool
    agreed_price: float | None
    confidence: float


def _round2(v: float) -> float:
    return round(v + 1e-9, 2)


@router.post("/simulate-buyer-reply", response_model=SimulateBuyerResponse)
async def simulate_buyer_reply(body: SimulateBuyerBody) -> SimulateBuyerResponse:
    buyer_turns = sum(1 for m in body.history if m.sender == "buyer")

    # Anchor the negotiation to real numbers.
    seller_price = body.seller_price or body.benchmark_unit_value or 1.0
    bench = body.benchmark_unit_value
    # A market-informed target the buyer pushes toward (never above the seller's ask).
    market_floor = (bench * 0.95) if bench else seller_price * 0.9
    market_floor = min(market_floor, seller_price)
    settlement = _round2((seller_price + market_floor) / 2)
    # Never settle below the seller's floor price.
    if body.floor_price:
        settlement = max(settlement, _round2(body.floor_price))
    settlement = min(settlement, _round2(seller_price))

    if buyer_turns == 0:
        # Opening counter-offer, below the eventual settlement.
        proposed = _round2(market_floor)
        accept = False
        agreed: float | None = None
        intent = "price_negotiation"
    else:
        # Converge: accept at the settlement price.
        proposed = settlement
        accept = True
        agreed = settlement
        intent = "acceptance"

    text = await _compose_text(body, proposed=proposed, agreed=agreed, accept=accept)
    return SimulateBuyerResponse(
        text=text,
        intent=intent,
        proposed_price=proposed,
        accept=accept,
        agreed_price=agreed,
        confidence=0.9,
    )


async def _compose_text(
    body: SimulateBuyerBody, *, proposed: float, agreed: float | None, accept: bool
) -> str:
    buyer = body.buyer_name or "Tim Pembelian"
    country = f" ({body.buyer_country})" if body.buyer_country else ""
    product = body.product_name or "produk Anda"

    # Deterministic template — always embeds the real computed numbers.
    if accept:
        template = (
            f"Baik, kami setuju menutup kesepakatan di ${agreed:.2f}/kg CIF dengan "
            f"struktur pembayaran 30% uang muka dan 70% L/C. Mohon terbitkan Purchase "
            f"Order resmi agar kami lanjut ke penandatanganan dokumen dan pemeriksaan "
            f"kepatuhan ekspor.\n\nHormat kami,\n{buyer}{country}"
        )
    else:
        template = (
            f"Terima kasih atas penawaran untuk {product}. Namun harga tersebut masih di "
            f"atas ekspektasi kami. Mengacu pada harga pasar acuan, kami mengajukan "
            f"${proposed:.2f}/kg CIF. Apakah harga ini dapat dipertimbangkan untuk "
            f"membangun kemitraan jangka panjang?\n\nHormat kami,\n{buyer}{country}"
        )

    if not (settings.gemini_api_key or settings.anthropic_api_key):
        return template

    # LLM phrasing — numbers are fixed in the instruction so they cannot drift.
    history_text = "\n".join(f"[{m.sender}] {m.text}" for m in body.history[-8:])
    system = (
        f"You role-play {buyer}, a professional B2B importer{country} negotiating to "
        f"buy {product} (HS {body.hs_code or 'n/a'}) from an Indonesian exporter. "
        f"Reply ONLY in Indonesian, concise and professional (max ~90 words). "
        f"Do NOT change any price numbers you are given."
    )
    if accept:
        user = (
            f"Conversation so far:\n{history_text}\n\n"
            f"Write your reply ACCEPTING the deal at exactly ${agreed:.2f}/kg CIF, "
            f"payment 30% DP + 70% L/C, and ask the seller to issue a formal Purchase "
            f"Order to proceed to signing and compliance."
        )
    else:
        user = (
            f"Conversation so far:\n{history_text}\n\n"
            f"Write your reply making a counter-offer of exactly ${proposed:.2f}/kg CIF, "
            f"politely explaining it reflects the market reference price."
        )
    try:
        out = await get_llm().complete(system=system, user=user, max_tokens=400, temperature=0.5)
        out = (out or "").strip()
        # Guard: require the exact figure to be present, else fall back.
        figure = f"{(agreed if accept else proposed):.2f}"
        return out if (out and figure in out) else template
    except Exception as e:  # noqa: BLE001
        log.warning("simulate_buyer.llm_failed", error=str(e))
        return template
