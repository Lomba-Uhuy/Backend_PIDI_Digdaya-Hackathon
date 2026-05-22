"""Unit tests for MatchingService scoring + explanation."""
import pytest
from matching_service.application.matching_service import MatchingService


@pytest.mark.unit
def test_enrich_combines_similarity_and_credibility() -> None:
    svc = MatchingService(session=None)  # type: ignore[arg-type]
    raw = {
        "buyer_id": "11111111-1111-1111-1111-111111111111",
        "name": "Demo GmbH",
        "country": "DE",
        "hs_codes": ["4602", "9403"],
        "credibility_score": 0.8,
        "is_synthetic": True,
        "distance": 0.10,  # similarity = 0.90
    }
    m = svc._enrich(raw)
    # final = 0.7 * 0.90 + 0.3 * 0.80 = 0.87
    assert m.similarity_score == pytest.approx(0.87, abs=1e-3)
    assert m.is_synthetic is True
    assert "Kesesuaian produk 90%" in m.explanation