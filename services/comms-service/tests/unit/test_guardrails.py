"""Tests for the GuardrailEngine."""
import pytest

from comms_service.core.guardrails import GuardrailEngine


@pytest.mark.unit
def test_no_violations_on_clean_draft() -> None:
    engine = GuardrailEngine()
    draft = (
        "Dear Buyer, thank you for your inquiry. Our pricing reflects market norms "
        "for premium quality. We can discuss volume-based incentives."
    )
    violations = engine.validate(draft, floor_price=150_000.0, batna="competitor X")
    assert violations == []


@pytest.mark.unit
def test_detects_floor_price_leak() -> None:
    engine = GuardrailEngine()
    # 150,000 is exactly the floor price -> should trip
    draft = "Our cost basis is 150,000 IDR per unit."
    violations = engine.validate(draft, floor_price=150_000.0, batna=None)
    assert any(v.violation_id == "FLOOR_PRICE_LEAK" for v in violations)


@pytest.mark.unit
def test_detects_desperate_language() -> None:
    engine = GuardrailEngine()
    draft = "We must close this deal this week, we can do any price you want."
    violations = engine.validate(draft, floor_price=None, batna=None)
    assert any(v.violation_id == "DESPERATE_LANGUAGE" for v in violations)


@pytest.mark.unit
def test_detects_batna_disclosure() -> None:
    engine = GuardrailEngine()
    batna = "Australian importer at 90% of target"
    draft = f"We have an Australian importer at 90% of target waiting in the wings."
    violations = engine.validate(draft, floor_price=None, batna=batna)
    assert any(v.violation_id == "BATNA_DISCLOSURE" for v in violations)


@pytest.mark.unit
def test_price_outside_window_does_not_trip() -> None:
    engine = GuardrailEngine()
    # floor 150,000, draft mentions 500,000 -> outside ±10% window
    draft = "Our list price starts at 500,000 IDR per unit for premium tier."
    violations = engine.validate(draft, floor_price=150_000.0, batna=None)
    assert all(v.violation_id != "FLOOR_PRICE_LEAK" for v in violations)