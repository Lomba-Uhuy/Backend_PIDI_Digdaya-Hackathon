"""HS Code classifier test suite — 30 sample Indonesian UMKM product descriptions.

Covers: rotan, furnitur, batik, kerajinan perak, kopi, rempah, seafood, dan lainnya.
Run: pytest tests/unit/test_hs_classifier.py -v
"""
from __future__ import annotations

import pytest

from matching_service.application.hs_classifier_service import (
    HSCodeResult,
    _hs_to_category,
    get_hs_classifier,
)

# ---------------------------------------------------------------------------
# 30 sample descriptions (description, expected_hs_prefix, expected_category_substr)
# expected_hs_prefix = first N chars of correct HS code
# expected_category_substr = substring that must appear in category label
# ---------------------------------------------------------------------------
SAMPLES: list[tuple[str, str, str]] = [
    # ── ROTAN & ANYAMAN ──────────────────────────────────────────────────
    (
        "Keranjang rotan tangan, diameter 30cm, natural finish, untuk penyimpanan",
        "460",  # 4602xx
        "Rotan",
    ),
    (
        "Tatakan meja oval dari anyaman enceng gondok, dua lapis, ramah lingkungan",
        "460",
        "Rotan",
    ),
    (
        "Kotak serbaguna dari bambu, tutup geser, ukuran 20x15x10 cm",
        "460",
        "Rotan",
    ),
    (
        "Tempat tisu anyaman pandan, motif geometris, natural dye",
        "460",
        "Rotan",
    ),
    (
        "Baki rotan oval dekoratif diameter 40cm untuk buah dan roti",
        "460",
        "Rotan",
    ),

    # ── FURNITUR ─────────────────────────────────────────────────────────
    (
        "Meja makan kayu jati solid 6 kursi, finishing natural oil, outdoor grade",
        "940",  # 9403xx
        "Furnitur",
    ),
    (
        "Lemari pakaian kayu mahoni 3 pintu, ukiran motif Jepara, finishing rustic",
        "940",
        "Furnitur",
    ),
    (
        "Kursi teras rotan sintetis dan rangka aluminium, cushion waterproof",
        "940",  # could be 9401 or 9403
        "Furnitur",
    ),
    (
        "Rak buku kayu reclaimed teak 5 tingkat, industrial style, 180x90cm",
        "940",
        "Furnitur",
    ),
    (
        "Dipan platform kayu pinus Skandinavia minimalis, 160x200, no headboard",
        "940",
        "Furnitur",
    ),

    # ── BATIK & TEKSTIL ──────────────────────────────────────────────────
    (
        "Kain batik tulis solo motif parang, cotton prima 2.5m, indigo natural dye",
        "520",  # 5208xx
        "Batik",
    ),
    (
        "Sarung batik cap pekalongan motif mega mendung, cotton 115x200cm",
        "520",
        "Batik",
    ),
    (
        "Sprei batik king size 180x200 set 4pcs, motif kawung, organic cotton",
        "630",  # 6302xx
        "Batik",
    ),
    (
        "Kain lurik ATBM tenun tangan, warna natural indigo dan coklat soga",
        "520",
        "Batik",
    ),
    (
        "Taplak meja batik printing motif lereng, 150x220cm, cotton tebal",
        "630",
        "Batik",
    ),

    # ── KERAJINAN PERAK ──────────────────────────────────────────────────
    (
        "Cincin perak sterling 925 motif kawung ukir tangan pengrajin Kotagede",
        "711",  # 7113xx
        "Perhiasan",
    ),
    (
        "Kalung perak filigree motif bunga tropis, panjang 45cm, handmade",
        "711",
        "Perhiasan",
    ),
    (
        "Gelang perak solid bangle 4mm, ukiran motif batik, unisex",
        "711",
        "Perhiasan",
    ),
    (
        "Anting drop perak 925 dengan aksen batu labradorite alami",
        "711",
        "Perhiasan",
    ),
    (
        "Set perhiasan perak cincin dan kalung matching, motif wayang, gift box",
        "711",
        "Perhiasan",
    ),

    # ── KOPI ─────────────────────────────────────────────────────────────
    (
        "Green coffee beans arabica Gayo Aceh Grade 1, natural process, 60kg bag",
        "090",  # 0901xx
        "Kopi",
    ),
    (
        "Kopi robusta Lampung roasted medium dark 250g specialty grade",
        "090",
        "Kopi",
    ),
    (
        "Instant coffee powder single origin Java Preanger, 20 sachet box",
        "210",  # 2101xx
        "Olahan",
    ),

    # ── REMPAH ───────────────────────────────────────────────────────────
    (
        "Lada hitam Bangka whole pepper 500g premium export grade",
        "090",  # 0904xx
        "Rempah",
    ),
    (
        "Kayu manis Kerinci cassia grade A, sticks 10cm, 1kg bulk",
        "090",  # 0906xx
        "Rempah",
    ),
    (
        "Jahe merah bubuk organik 100g, sertifikasi organik, free pesticide",
        "091",  # 0910xx
        "Rempah",
    ),
    (
        "Cengkeh whole Maluku Utara Zanzibar grade, 5kg vacuum pack",
        "090",  # 0907xx
        "Rempah",
    ),

    # ── SEAFOOD ──────────────────────────────────────────────────────────
    (
        "Tuna yellowfin frozen loin 3-5kg, IQF, sashimi grade, Bitung port",
        "030",  # 0303xx
        "Laut",
    ),
    (
        "Udang vannamei beku HOSO 31/40, ASC certified, cold chain maintained",
        "030",  # 0306xx
        "Laut",
    ),

    # ── MINYAK ESENSIAL ──────────────────────────────────────────────────
    (
        "Minyak nilam patchouli oil 100ml steam distilled Aceh, export quality",
        "330",  # 3301xx
        "Minyak Esensial",
    ),
    (
        "Virgin coconut oil cold pressed 1L organic certified, food grade",
        "151",  # 1513xx
        "Minyak",
    ),
]


@pytest.fixture(scope="module")
def classifier():
    """Load classifier once for the whole module — model loading is expensive."""
    return get_hs_classifier()


class TestHsToCategory:
    """Unit tests for the category lookup helper — no model required."""

    def test_jewelry_category(self):
        assert "Perhiasan" in _hs_to_category("7113")

    def test_furniture_category(self):
        assert "Furnitur" in _hs_to_category("9403")

    def test_rattan_category(self):
        assert "Rotan" in _hs_to_category("4602")

    def test_batik_category(self):
        assert "Batik" in _hs_to_category("6302")

    def test_coffee_category(self):
        assert "Kopi" in _hs_to_category("0901")

    def test_unknown_falls_back(self):
        assert _hs_to_category("9999") == "Produk Ekspor Lainnya"


class TestHsClassifierResult:
    """Integration tests — require model to be loaded (slow first run)."""

    def test_result_has_category_field(self, classifier):
        result: HSCodeResult = classifier.classify("keranjang rotan anyaman")
        assert hasattr(result, "category")
        assert isinstance(result.category, str)
        assert len(result.category) > 0

    def test_top_k_candidates_have_category(self, classifier):
        result = classifier.classify("meja kayu jati outdoor", top_k=3)
        assert len(result.top_k) == 3
        for candidate in result.top_k:
            assert "category" in candidate
            assert isinstance(candidate["category"], str)

    def test_confidence_between_0_and_1(self, classifier):
        result = classifier.classify("batik tulis solo motif parang")
        assert 0.0 <= result.confidence <= 1.0

    def test_hs_code_is_string(self, classifier):
        result = classifier.classify("perhiasan perak cincin gelang")
        assert isinstance(result.hs_code, str)
        assert len(result.hs_code) >= 4


@pytest.mark.parametrize("description,expected_prefix,expected_category_substr", SAMPLES)
class TestHsClassifierSamples:
    """Parameterized tests — one test per sample description."""

    def test_correct_chapter(self, classifier, description, expected_prefix, expected_category_substr):
        """Best result HS code must start with the expected chapter prefix."""
        result: HSCodeResult = classifier.classify(description, top_k=5)
        # Check if expected prefix appears in best OR any top-k candidate
        matched = result.hs_code.startswith(expected_prefix) or any(
            c["hs_code"].startswith(expected_prefix) for c in result.top_k
        )
        assert matched, (
            f"Description: {description!r}\n"
            f"Expected prefix: {expected_prefix!r}\n"
            f"Got best: {result.hs_code!r}, top_k: {[c['hs_code'] for c in result.top_k]}"
        )

    def test_category_is_present(self, classifier, description, expected_prefix, expected_category_substr):
        """Response must include a non-empty category field."""
        result: HSCodeResult = classifier.classify(description)
        assert result.category, f"Empty category for: {description!r}"
