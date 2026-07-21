"""POST /classify-intent — email intent classification for trade communications.

Returns intent label (inquiry, negotiation, complaint, spam) with confidence score.
Uses multi-pattern scoring: each intent has N signal patterns, score = matches/N,
confidence = dominance of winning intent over all scores combined.
"""
from __future__ import annotations

import re

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()

# Each intent has multiple regex patterns. Score = matched_patterns / total_patterns.
_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "inquiry": [
        re.compile(r"\b(request for quotation|rfq|price list|quote|proforma invoice|pro forma)\b", re.I),
        re.compile(r"\b(interested in|inquiry|enquiry|information about|tell me about|please advise)\b", re.I),
        re.compile(r"\b(specification|certificate|test report|compliance|standard|catalogue|brochure)\b", re.I),
        re.compile(r"\b(available|availability|stock|capacity|lead time|delivery time|sample)\b", re.I),
        re.compile(r"\b(minimum order|moq|quantity|unit price|bulk price|wholesale)\b", re.I),
    ],
    "negotiation": [
        re.compile(r"\b(too expensive|reduce price|best price|discount|lower price|negotiate|negotiation)\b", re.I),
        re.compile(r"\b(can you offer|price adjustment|revised quote|better rate|competitive price)\b", re.I),
        re.compile(r"\b(counter offer|counter-offer|if you can do|what if|our budget|our target price)\b", re.I),
        re.compile(r"\b(payment terms|lc|letter of credit|tt|telegraphic transfer|net [0-9]+)\b", re.I),
        re.compile(r"\b(we would like to discuss|open to negotiation|flexible on|room for)\b", re.I),
    ],
    "complaint": [
        re.compile(r"\b(damage|damaged|defect|defective|broken|faulty|wrong item|incorrect)\b", re.I),
        re.compile(r"\b(delay|delayed|late delivery|not arrived|missing|short shipment|short-shipped)\b", re.I),
        re.compile(r"\b(not as described|not as ordered|quality issue|poor quality|below standard)\b", re.I),
        re.compile(r"\b(refund|replacement|compensation|claim|dispute|return|chargeback)\b", re.I),
        re.compile(r"\b(disappointed|dissatisfied|unhappy|complaint|complain|lodge a complaint)\b", re.I),
    ],
    "spam": [
        re.compile(r"\b(click here|you have won|congratulations|lottery|prize|winner)\b", re.I),
        re.compile(r"\b(wire transfer urgently|transfer immediately|urgent bank|account number)\b", re.I),
        re.compile(r"\b(no obligation|free offer|limited time only|act now|guaranteed profit)\b", re.I),
        re.compile(r"\b(dear friend|dear sir or madam|to whom it may concern|undisclosed recipient)\b", re.I),
        re.compile(r"\b(nigerian prince|inheritance|million dollars|unclaimed funds|secret deal)\b", re.I),
    ],
}


def classify_intent(text: str) -> tuple[str, float, dict[str, float]]:
    """Score each intent by proportion of matching patterns, return winner + confidence."""
    raw_scores: dict[str, float] = {}
    for intent, patterns in _PATTERNS.items():
        hits = sum(1 for p in patterns if p.search(text))
        raw_scores[intent] = round(hits / len(patterns), 3)

    best = max(raw_scores, key=lambda k: raw_scores[k])
    best_score = raw_scores[best]

    if best_score == 0.0:
        # No signals at all — default to inquiry with low confidence
        return "inquiry", 0.40, raw_scores

    total = sum(raw_scores.values())
    # Confidence = how dominant the top intent is relative to all signals
    dominance = best_score / total if total > 0 else 0.5
    # Map dominance [0,1] to confidence [0.50, 0.99]
    confidence = round(0.50 + dominance * 0.49, 3)
    return best, confidence, raw_scores


class IntentBody(BaseModel):
    email_text: str = Field(min_length=5, max_length=10_000, description="Raw email text to classify")


class IntentResponse(BaseModel):
    intent: str = Field(description="Predicted intent label: inquiry | negotiation | complaint | spam")
    confidence: float = Field(description="Confidence score [0, 1]")
    all_scores: dict[str, float] = Field(description="Raw pattern-match ratio per intent class")


@router.post("/classify-intent", response_model=IntentResponse)
async def classify_email_intent(body: IntentBody) -> IntentResponse:
    """Classify the intent of an importer email into one of four categories.

    Intent labels:
    - **inquiry** — product info, RFQ, spec questions
    - **negotiation** — price negotiation, counter-offers, payment terms
    - **complaint** — quality, delivery, or order issues
    - **spam** — unsolicited commercial or phishing patterns
    """
    intent, confidence, all_scores = classify_intent(body.email_text)
    return IntentResponse(intent=intent, confidence=confidence, all_scores=all_scores)
