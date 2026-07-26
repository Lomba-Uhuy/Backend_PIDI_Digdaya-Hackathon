"""HS Code classification via multilingual sentence-transformers.

Model: intfloat/multilingual-e5-large
- Supports Indonesian + English in one model
- 1024-dim embeddings
- Requires 'query:' / 'passage:' prefix per E5 family convention
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import structlog

log = structlog.get_logger(__name__)

# Expanded Indonesian export corpus — 50 HS codes covering major UMKM categories.
# In production: ingest full WCO HS database (~5K codes) via ETL worker.
HS_CORPUS: dict[str, str] = {
    # ── COFFEE & TEA ──────────────────────────────────────────────────────────
    "0901": (
        "coffee, whether or not roasted or decaffeinated; coffee husks and skins; "
        "kopi arabika robusta specialty single origin Gayo Mandheling Toraja Flores Java Bali"
    ),
    "090111": "coffee, not roasted, not decaffeinated; green coffee beans raw arabica robusta",
    "090121": "coffee, roasted, not decaffeinated; roasted coffee beans specialty",
    "090122": "coffee, roasted, decaffeinated; decaf roasted coffee",
    "2101": "extracts, essences, concentrates of coffee or tea; instant coffee powder liquid",
    "0902": "tea, whether or not flavoured; green tea black tea oolong herbal tea",
    "090210": "green tea, not fermented; Chinese Japanese Indonesian green tea",
    "090230": "black tea fermented; Ceylon Assam Java black tea",

    # ── COCOA & CHOCOLATE ─────────────────────────────────────────────────────
    "1801": (
        "cocoa beans, whole or broken, raw or roasted; "
        "fine flavor Trinitario Criollo Sulawesi Java Flores Bali kakao"
    ),
    "1803": "cocoa paste, whether or not defatted; cocoa mass liquor",
    "1804": "cocoa butter, fat and oil; cocoa butter cosmetic food ingredient",
    "1805": "cocoa powder, not containing added sugar; dark cocoa powder natural alkalized",
    "1806": "chocolate and other food preparations containing cocoa; couverture chocolate dark milk",

    # ── PALM OIL & COCONUT ────────────────────────────────────────────────────
    "1511": "palm oil and its fractions; crude palm oil CPO RBD palm olein stearin",
    "151110": "crude palm oil not chemically modified; CPO palm oil commodity",
    "151190": "palm oil refined bleached deodorized; RBD palm olein cooking oil",
    "1513": "coconut oil palm kernel oil babassu oil; VCO fractionated MCT oil",
    "151311": "crude coconut oil copra oil; VCO virgin coconut oil cold pressed",
    "151321": "palm kernel oil refined; PKO fractionated palm kernel",
    "0801": "coconuts brazil nuts cashew nuts; kelapa segar kacang mede cashew snack",

    # ── SPICES ────────────────────────────────────────────────────────────────
    "0904": "pepper piperine; black pepper white pepper lada hitam putih Bangka Lampung Muntok",
    "0905": "vanilla beans; vanilla planifolia madagascar indonesian vanilla",
    "0906": "cinnamon and cinnamon-tree flowers; cassia kayu manis Kerinci Java",
    "0907": "cloves whole and stems; cengkeh bunga cengkeh Maluku Ternate Zanzibar grade",
    "0908": "nutmeg mace cardamom; pala bunga pala Banda kapulaga",
    "0909": "anise seeds caraway cumin; biji adas jinten",
    "0910": (
        "ginger saffron turmeric thyme bay leaves curry; "
        "jahe kunyit lengkuas temulawak rempah-rempah Indonesian spices"
    ),

    # ── HANDICRAFTS & NATURAL FIBER ──────────────────────────────────────────
    "4601": (
        "plaiting materials vegetable; rattan bamboo strips seagrass pandanus "
        "water hyacinth enceng gondok natural fiber"
    ),
    "4602": (
        "basketwork wickerwork articles from plaiting materials; "
        "rattan basket bamboo organizer seagrass storage water hyacinth tray "
        "coconut shell bowl handcraft kerajinan rotan bambu"
    ),
    "460210": "basketwork articles bamboo; bamboo box tray storage furniture",
    "460220": "basketwork articles rattan; rattan basket tray plate placemat",
    "460290": "basketwork other vegetable materials; seagrass pandanus water hyacinth",
    "1404": (
        "vegetable products not elsewhere specified; coconut fiber coir "
        "sabut kelapa natural fiber cocopeat growing media"
    ),

    # ── FURNITURE ─────────────────────────────────────────────────────────────
    "9403": (
        "other furniture and parts; teak mahogany reclaimed wood outdoor garden "
        "indoor living bedroom furniture mebel kayu jati"
    ),
    "940330": "wooden furniture other than for offices bedrooms dining; teak outdoor garden bench",
    "940340": "wooden furniture for kitchens; kitchen cabinet wooden",
    "940350": "wooden furniture for bedrooms; bed frame wardrobe dresser teak",
    "940360": "other wooden furniture; teak dining set coffee table rattan sofa bamboo",
    "9401": "seats and parts thereof; rattan chair bamboo stool teak bench garden seating",
    "4420": (
        "wood marquetry inlaid wood; decorative wooden articles "
        "figurines frames boxes carved wood ukiran kayu"
    ),

    # ── TEXTILES & BATIK ──────────────────────────────────────────────────────
    "5208": "woven fabrics cotton; batik fabric kain batik printed hand-drawn",
    "520811": "plain woven cotton fabric bleached; cotton fabric base for batik printing",
    "520821": "plain woven cotton fabric dyed; dyed cotton batik background",
    "6302": (
        "bed linen table linen toilet kitchen linen; "
        "batik bed cover tablecloth sarong lurik tenun ikat traditional woven"
    ),
    "630291": "other bed linen knitted crocheted; batik sheet pillowcase traditional textile",

    # ── FOOD PREPARATIONS ────────────────────────────────────────────────────
    "2106": (
        "food preparations not elsewhere specified; "
        "Indonesian snack processed food packaged food tempeh chips keripik "
        "rempeyek emping kacang kecap sambal bumbu masak"
    ),
    "210690": "other food preparations; Indonesian ready-to-eat packaged snack condiment",
    "2103": "sauces mixed condiments seasonings; kecap manis sambal chili sauce bumbu",
    "1704": "sugar confectionery not containing cocoa; candy gula-gula traditional sweet",
    "190590": "other bakery pastry products; traditional Indonesian cake kue basah kering",

    # ── ESSENTIAL OILS & COSMETICS ────────────────────────────────────────────
    "3301": (
        "essential oils terpeneless or not; citronella patchouli lemongrass "
        "clove leaf oil nutmeg oil ylang-ylang cananga nilam serai wangi "
        "akar wangi vetiver Indonesian essential oil"
    ),
    "330112": "essential oils of orange; orange oil citrus",
    "330113": "essential oils of lemon; lemon bergamot citrus oil",
    "330119": "essential oils of other citrus fruit; lime grapefruit citrus",
    "330125": "essential oils of other mint; peppermint spearmint",
    "3304": (
        "beauty makeup skin care preparations; natural skincare "
        "coconut oil moisturizer face cream body lotion Indonesian cosmetics"
    ),
    "3305": (
        "preparations for use on hair; shampoo conditioner hair mask "
        "coconut oil hair treatment natural hair care produk rambut"
    ),
    "3307": (
        "shaving toilet preparations deodorants bath preparations; "
        "natural body care bath bomb scrub aromatherapy"
    ),

    # ── SEAFOOD ──────────────────────────────────────────────────────────────
    "0302": "fish fresh or chilled; segar tuna yellowfin skipjack grouper snapper",
    "030231": "yellowfin tuna thunnus albacares fresh chilled; tuna loin fillet segar",
    "030236": "bigeye tuna thunnus obesus fresh; tuna mata besar segar",
    "0303": "fish frozen; tuna shrimp squid frozen seafood beku",
    "0306": "crustaceans frozen; shrimp prawn udang vannamei tiger lobster kepiting",
    "1604": "prepared preserved fish caviar; canned tuna sardine abon ikan olahan",
    "160414": "tunas skipjack bonito prepared preserved; canned tuna in oil water",

    # ── HERBAL & MEDICINAL ────────────────────────────────────────────────────
    "1211": (
        "plants plant parts used in perfumery pharmacy; "
        "herbal medicinal plants temulawak sambiloto kayu manis kulit "
        "andrographis curcuma xanthorrhiza simplicia jamu"
    ),
    "121190": "other plants parts used in pharmacy; dried herbs extract powders",
    "1302": "vegetable saps extracts; plant extract herbal concentrate standardized",

    # ── ECO PRODUCTS ─────────────────────────────────────────────────────────
    "3923": (
        "articles for conveyance packing of goods plastics; "
        "eco sustainable biodegradable packaging coconut shell bamboo alternative"
    ),

    # ── JEWELRY & PRECIOUS METAL CRAFTS ──────────────────────────────────────
    "7113": (
        "articles of jewelry precious metal gold silver platinum; "
        "perhiasan emas perak cincin kalung gelang anting silver jewelry handcrafted"
    ),
    "711311": (
        "articles of silver jewelry sterling silver; "
        "perhiasan perak sterling silver cincin kalung gelang anting Yogyakarta Kotagede"
    ),
    "711319": (
        "articles of other precious metal jewelry gold platinum; "
        "perhiasan emas platinum fine jewelry artisan"
    ),
    "7116": (
        "articles of natural precious semi-precious stones; "
        "batu mulia permata akik cincin batu alam gemstone jewelry"
    ),
    "7117": (
        "imitation jewelry fashion accessories; "
        "perhiasan imitasi fashion jewelry aksesoris tembaga kuningan brass copper"
    ),
}

# Maps HS chapter (2-digit prefix) to human-readable category label.
_HS_CATEGORIES: dict[str, str] = {
    "09": "Kopi, Teh & Rempah",
    "21": "Produk Olahan Makanan",
    "18": "Kakao & Cokelat",
    "15": "Minyak Nabati",
    "08": "Buah & Kacang",
    "46": "Kerajinan Anyaman & Rotan",
    "14": "Produk Nabati",
    "94": "Furnitur & Perlengkapan Rumah",
    "52": "Kapas & Kain Tenun",
    "63": "Tekstil Lainnya (Batik, Sarung)",
    "33": "Minyak Esensial & Kosmetik",
    "03": "Ikan & Hasil Laut",
    "16": "Olahan Ikan & Daging",
    "12": "Tanaman Herbal & Obat",
    "13": "Sari & Ekstrak Tumbuhan",
    "44": "Kayu & Produk Kayu",
    "39": "Plastik & Kemasan",
    "17": "Gula & Kembang Gula",
    "19": "Produk Roti & Kue",
    "71": "Perhiasan & Kerajinan Logam Mulia",
    "10": "Serealia",
    "20": "Olahan Sayur & Buah",
    "25": "Garam & Mineral",
}


def _hs_to_category(hs_code: str) -> str:
    """Return Indonesian category label for a given HS code."""
    return _HS_CATEGORIES.get(hs_code[:2], "Produk Ekspor Lainnya")


@dataclass
class HSCodeResult:
    hs_code: str
    description: str
    confidence: float
    category: str
    top_k: list[dict]


class HSCodeClassifierService:
    """Multilingual semantic classifier — singleton, lazy-loaded.

    Uses the configured embedding provider (Gemini API or local model)
    via the shared embedder factory.
    """

    def __init__(self) -> None:
        self._embedder = None  # lazy
        self._corpus_embeddings: np.ndarray | None = None
        self._corpus_keys: list[str] = list(HS_CORPUS.keys())

    def _ensure_loaded(self) -> None:
        if self._embedder is not None:
            return
        from matching_service.infrastructure.embeddings.sentence_transformer import get_embedder

        self._embedder = get_embedder()
        log.info("hs_classifier.model.loading", model=self._embedder.model_name)
        corpus_texts = list(HS_CORPUS.values())
        corpus_vecs = self._embedder.embed_sync(corpus_texts)
        self._corpus_embeddings = np.array(corpus_vecs)
        log.info("hs_classifier.corpus.precomputed", size=len(HS_CORPUS))

    def classify(self, product_description: str, top_k: int = 3) -> HSCodeResult:
        self._ensure_loaded()
        assert self._embedder is not None and self._corpus_embeddings is not None

        query_embedding = np.array(self._embedder.embed_sync([product_description])[0])

        # Cosine similarity (since both sides are normalized -> dot product)
        similarities = np.dot(self._corpus_embeddings, query_embedding)
        ranked = np.argsort(similarities)[::-1]

        candidates = []
        for idx in ranked[:top_k]:
            code = self._corpus_keys[idx]
            candidates.append({
                "hs_code": code,
                "description": HS_CORPUS[code],
                "confidence": float(similarities[idx]),
                "category": _hs_to_category(code),
            })

        best = candidates[0]
        log.info(
            "hs_classifier.classified",
            preview=product_description[:60],
            hs_code=best["hs_code"],
            confidence=best["confidence"],
            category=best["category"],
        )
        return HSCodeResult(
            hs_code=best["hs_code"],
            description=best["description"],
            confidence=best["confidence"],
            category=best["category"],
            top_k=candidates,
        )


_singleton: HSCodeClassifierService | None = None


def get_hs_classifier() -> HSCodeClassifierService:
    global _singleton
    if _singleton is None:
        _singleton = HSCodeClassifierService()
    return _singleton