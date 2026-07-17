"""Guardrail engine — validates LLM output before returning to user.

Four checks:
  1. FLOOR_PRICE_LEAK   — any number within ±10% of floor price (leak of internal cost)
  2. BELOW_FLOOR_PRICE  — price-context number explicitly below HPP (below-cost offer)
  3. DESPERATE_LANGUAGE — submissive / desperate phrasing patterns
  4. BATNA_DISCLOSURE   — text contains the seller's BATNA description

CRITICAL: floor price and BATNA are NEVER passed into LLM prompts as literal
values. They live only in the validator, which checks the LLM output.

sanitize_draft() handles the "replace below-floor prices with placeholder" requirement:
after max regeneration attempts, any residual below-floor price figures are
replaced with [PRICE_RANGE_ON_REQUEST] to prevent accidental under-pricing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

BELOW_FLOOR_PLACEHOLDER = "[PRICE_RANGE_ON_REQUEST]"


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

# Price-context numbers: number preceded or followed by currency indicator within a short window.
# Group 1 captures currency-prefix numbers; group 2 captures currency-suffix numbers.
_PRICE_CONTEXT_RE = re.compile(
    r"""
    (?:USD|IDR|EUR|GBP|\$|€|£)\s*               # currency prefix
    (\d{1,3}(?:[,.\s]\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)   # the number
    |
    (\d{1,3}(?:[,.\s]\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*  # the number
    (?:USD|IDR|EUR|GBP|per\s+unit|per\s+kg|/\s*(?:unit|kg|pcs?|piece|ton))  # unit/currency suffix
    """,
    re.I | re.X,
)


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


def _parse_price_number(raw: str) -> float | None:
    """Parse a number that appeared in price context (may have decimals like 5.50)."""
    cleaned = re.sub(r"\s", "", raw)
    # If it looks like a decimal price (e.g. "5.50", "12.00") keep the decimal
    try:
        return float(cleaned.replace(",", ""))
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

        if floor_price and floor_price > 0:
            low, high = floor_price * 0.90, floor_price * 1.10

            # Check 1: floor price leak (number ≈ floor_price — reveals internal cost basis)
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

            # Check 2: below-floor price in price context (offer price below HPP)
            for match in _PRICE_CONTEXT_RE.finditer(draft):
                raw_num = match.group(1) or match.group(2)
                if raw_num is None:
                    continue
                num = _parse_price_number(raw_num)
                if num is not None and 0 < num < floor_price * 0.90:
                    violations.append(
                        GuardrailViolation(
                            violation_id="BELOW_FLOOR_PRICE",
                            description=f"Draft contains a price ({num}) below HPP floor ({floor_price})",
                            warning_message=(
                                "Draf menyebut harga di bawah HPP. "
                                "Harga akan diganti dengan placeholder aman."
                            ),
                            remediation_hint=(
                                "Replace the specific price figure with a range or placeholder such as "
                                f"'{BELOW_FLOOR_PLACEHOLDER}'. Never commit to prices below your cost basis."
                            ),
                            severity="CRITICAL",
                        )
                    )
                    break

        # Check 3: desperate language
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

        # Check 4: BATNA disclosure
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

    def sanitize_draft(self, draft: str, floor_price: float | None) -> str:
        """Replace below-floor price figures with a safe placeholder.

        Called as a last resort after max regeneration attempts. Ensures the final
        draft never surfaces an accidental below-HPP price commitment even if the
        LLM persists after two regeneration cycles.
        """
        if not floor_price or floor_price <= 0:
            return draft

        def _replace_if_below_floor(m: re.Match[str]) -> str:
            raw_num = m.group(1) or m.group(2)
            if raw_num is None:
                return m.group(0)
            num = _parse_price_number(raw_num)
            if num is not None and 0 < num < floor_price * 0.90:
                # Replace only the number part within the full match
                return m.group(0).replace(raw_num, BELOW_FLOOR_PLACEHOLDER, 1)
            return m.group(0)

        return _PRICE_CONTEXT_RE.sub(_replace_if_below_floor, draft)