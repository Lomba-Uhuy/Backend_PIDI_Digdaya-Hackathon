"""Deterministic cleaning/normalisation of raw TradeAtlas shipment fields.

Every function is pure and deterministic (Decision 10). Records that cannot be
turned into a valid buyer are rejected *explicitly* by the caller (which logs and
counts them) — never silently dropped.
"""
from __future__ import annotations

import re

# Importer names that are placeholders, not real companies.
_JUNK_NAMES: frozenset[str] = frozenset(
    {
        "",
        "N/A",
        "NA",
        "N A",
        "NONE",
        "NULL",
        "UNKNOWN",
        "INTERNATIONAL",
        "ACCOUNTS PAYABLE",
        "TO THE ORDER",
        "TO ORDER",
        "TO THE ORDER OF",
        "CONSIGNEE",
        "SAME AS CONSIGNEE",
    }
)

_WS = re.compile(r"\s+")
_HS_SPLIT = re.compile(r"[|,;/\s]+")


def clean_company_name(raw: str | None) -> str | None:
    """Trim/collapse whitespace; return ``None`` for placeholder/junk names."""
    if not raw:
        return None
    name = _WS.sub(" ", raw.strip())
    if len(name) < 2:
        return None
    normalized = name.upper().rstrip(".").strip()
    if normalized in _JUNK_NAMES:
        return None
    # Names that begin with "TO THE ORDER ..." are B/L placeholders, not firms.
    if normalized.startswith("TO THE ORDER") or normalized.startswith("TO ORDER"):
        return None
    return name


def normalize_hs(raw: str | None) -> list[str]:
    """Normalise a possibly-composite HS field into distinct 6-digit-max codes.

    Handles ``"09011110"``, ``"090111"``, ``"090111|090111|09011110"`` etc.
    """
    if not raw:
        return []
    out: list[str] = []
    for token in _HS_SPLIT.split(raw.strip()):
        digits = re.sub(r"\D", "", token)
        if len(digits) >= 6:
            code = digits[:6]
        elif len(digits) in (2, 4):
            code = digits
        else:
            continue  # malformed → skip this token (caller still keeps the buyer)
        if code not in out:
            out.append(code)
    return out


def valid_country_code(raw: str | None) -> str | None:
    """Return a 2-letter uppercase ISO code, or ``None`` if invalid."""
    if not raw:
        return None
    code = raw.strip().upper()
    return code if len(code) == 2 and code.isalpha() else None


def parse_money(raw: str | None) -> float:
    """Parse a money-ish string to float; non-numeric/empty → 0.0."""
    if raw is None:
        return 0.0
    try:
        value = float(str(raw).replace(",", "").strip() or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return value if value > 0 else 0.0


def year_month(arrival_date: str | None) -> str | None:
    """Extract 'YYYY-MM' from an ISO-ish date, for continuity signals."""
    if not arrival_date or len(arrival_date) < 7:
        return None
    ym = arrival_date[:7]
    return ym if re.fullmatch(r"\d{4}-\d{2}", ym) else None
