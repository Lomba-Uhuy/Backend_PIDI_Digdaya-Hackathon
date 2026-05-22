"""Guardrail engine — validates LLM output before returning to user.

Three checks:
  1. FLOOR_PRICE_LEAK   — any number within ±10% of floor price
  2. DESPERATE_LANGUAGE — submissive / desperate phrasing patterns
  3. BATNA_DISCLOSURE   — text contains the seller's BATNA description

CRITICAL: floor price and BATNA are NEVER passed into LLM prompts as literal
values. They live only in the validator, which checks the LLM output.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


@dataclass
class GuardrailViolation:
    violation_id: str
    description: str
    warning_message: str
    remediation_hint: str
    severity: Literal["WARNING", "CRITICAL"]


_DESPERATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(we can do any price|any discount you want|we are flexible on everything)\b", re.I),
    re.compile(r"\b(please buy|we really need|we must close this deal)\b", re.I),
    re.compile(r"\b(last stock|selling everything|urgent need to sell)\b", re.I),
)

# Match numeric values: 1234 | 1,234 | 1.234.567 | 1 234 (no decimals here — we want integers)
_NUMBER_RE = re.compile(r"\b\d{1,3}(?:[,.\s]\d{3})+\b|\b\d{4,}\b")


def _parse_number(s: str) -> float | None:
    """Parse various number formats to float."""
    cleaned = re.sub(r"[\s]", "", s)
    # Indonesian: '1.234.567' = 1234567 (dots as thousand separator)
    # US:         '1,234,567' = 1234567 (commas as thousand separator)
    # Strip both — we only care about magnitude here, not decimals
    cleaned = cleaned.replace(",", "").replace(".", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


class GuardrailEngine:
    """Output safety layer — runs after every LLM completion."""

    def validate(
        self,
        draft: str,
        floor_price: float | None,
        batna: str | None,
    ) -> list[GuardrailViolation]:
        violations: list[GuardrailViolation] = []

        # Check 1: floor price leak (±10%)
        if floor_price and floor_price > 0:
            low, high = floor_price * 0.90, floor_price * 1.10
            for match in _NUMBER_RE.finditer(draft):
                num = _parse_number(match.group(0))
                if num is not None and low <= num <= high:
                    violations.append(
                        GuardrailViolation(
                            violation_id="FLOOR_PRICE_LEAK",
                            description=f"Draft may contain floor-price-adjacent value: {num}",
                            warning_message="Draf mungkin mengandung informasi harga internal yang sensitif.",
                            remediation_hint=(
                                "Remove or replace any specific price figures that might reveal "
                                "your floor price. Use ranges or 'competitive pricing' language instead."
                            ),
                            severity="CRITICAL",
                        )
                    )
                    break  # one floor-price violation is enough to require regen

        # Check 2: desperate language
        for pat in _DESPERATE_PATTERNS:
            if pat.search(draft):
                violations.append(
                    GuardrailViolation(
                        violation_id="DESPERATE_LANGUAGE",
                        description="Draft contains desperate or submissive language",
                        warning_message="Draf mengandung bahasa yang terkesan terlalu membutuhkan deal.",
                        remediation_hint=(
                            "Replace with confident, professional language. "
                            "Emphasize value, not urgency to sell."
                        ),
                        severity="WARNING",
                    )
                )
                break

        # Check 3: BATNA disclosure
        if batna:
            batna_normalized = batna.strip().lower()
            if batna_normalized and batna_normalized in draft.lower():
                violations.append(
                    GuardrailViolation(
                        violation_id="BATNA_DISCLOSURE",
                        description="Draft may contain BATNA information",
                        warning_message="Draf mungkin mengungkap alternatif terbaik UMKM jika deal ini gagal.",
                        remediation_hint=(
                            "Remove any reference to alternative buyers or market alternatives."
                        ),
                        severity="CRITICAL",
                    )
                )

        return violations