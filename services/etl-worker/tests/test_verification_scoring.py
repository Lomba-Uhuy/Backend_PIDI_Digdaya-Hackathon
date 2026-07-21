"""Test verification score calculation."""
from etl_worker.tasks.verification_task import _calculate_verification_score


def test_full_verification_compliant_menengah() -> None:
    score = _calculate_verification_score({
        "is_valid": True,
        "compliance_status": "COMPLIANT",
        "business_scale": "MENENGAH",
    })
    # 0.5 (valid) + 0.3 (compliant) + 0.2 (menengah) = 1.0
    assert score == 1.0


def test_partial_conditional_mikro() -> None:
    score = _calculate_verification_score({
        "is_valid": True,
        "compliance_status": "CONDITIONAL",
        "business_scale": "MIKRO",
    })
    # 0.5 + 0.15 + 0.05 = 0.7
    assert score == 0.7


def test_invalid_nib() -> None:
    score = _calculate_verification_score({"is_valid": False})
    assert score == 0.0
