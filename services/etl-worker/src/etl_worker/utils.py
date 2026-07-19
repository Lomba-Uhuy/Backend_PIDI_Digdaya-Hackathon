"""Shared type-coercion helpers used across ETL tasks."""
from __future__ import annotations

from decimal import Decimal
from typing import Any


def str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    value_str = str(value).strip()
    return value_str or None


def decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None
