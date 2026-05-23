#!/usr/bin/env python3
"""Synthetic buyer seeder with pgvector embeddings for TradeConnect.

Generates 200 realistic synthetic buyers across 15 Indonesian export product
categories, computes 1024-dim embeddings (intfloat/multilingual-e5-large),
and seeds both the buyer and buyer_embedding tables.

All rows are flagged is_synthetic = TRUE for full transparency.

Usage:
    python scripts/seed-buyers-with-embeddings.py
    python scripts/seed-buyers-with-embeddings.py --count 200 --skip-embeddings
    python scripts/seed-buyers-with-embeddings.py --clear --count 200 --with-embeddings
    python scripts/seed-buyers-with-embeddings.py --dsn postgresql+psycopg://...

Requirements:
    uv pip install sqlalchemy "psycopg[binary]" pgvector
    # For embeddings:
    uv pip install "sentence-transformers>=3.3" "torch>=2.0" numpy
"""
from __future__ import annotations

import argparse
import json
import os
import random
from dataclasses import dataclass, field
from uuid import uuid4

try:
    from sqlalchemy import create_engine, text
except ImportError as exc:
    raise SystemExit("Install sqlalchemy: uv pip install sqlalchemy 'psycopg[binary]'") from exc


# ─────────────────────────────────────────────────────────────────────────────
# Buyer Templates per Product Category
# Each template defines realistic importers for Indonesian export sectors.
# Descriptions are rich and multilingual so embeddings match UMKM products.
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BuyerTemplate:
    name_prefix: str
    name_suffix: str
    countries: list[str]
    hs_codes: list[str]
    moq_range: tuple[int, int]
    credibility_range: tuple[float, float]
    description_template: str
    tags: list[str] = field(default_factory=list)


BUYER_TEMPLATES: list[BuyerTemplate] = [

    # ─── COFFEE & TEA ────────────────────────────────────────────────────────
    BuyerTemplate(
        name_prefix="",
        name_suffix="",
        countries=["DE", "NL", "US", "JP", "AU", "CA", "GB", "NO", "SE", "DK"],
        hs_codes=["0901", "090111", "090121", "090122", "2101"],
        moq_range=(200, 1000),
        credibility_range=(0.65, 0.95),
        description_template=(
            "{name} is a specialty coffee importer and green bean trader based in {country}. "
            "We source single-origin arabica and robusta coffees from Sumatra (Gayo, Mandheling), "
            "Java Estate, Flores (Bajawa, Manggarai), Toraja, and Bali Kintamani. "
            "We serve specialty coffee roasters, artisan cafes, and premium grocery chains. "
            "Annual import volume 20-50 metric tons. Preferred payment: T/T or Sight L/C. "
            "Certifications preferred: RFA, Fairtrade, Organic. Min HS 0901 grade requirements apply."
        ),
        tags=["coffee", "specialty", "arabica", "robusta", "fair-trade"],
    ),

    BuyerTemplate(
        name_prefix="",
        name_suffix="",
        countries=["GB", "DE", "AU", "JP", "US", "NL", "CN"],
        hs_codes=["0902", "090210", "090230", "090240"],
        moq_range=(100, 500),
        credibility_range=(0.60, 0.90),
        description_template=(
            "{name} imports premium loose-leaf and specialty teas from Southeast Asia "
            "and South Asia. We source Indonesian teas including Java green tea, "
            "Sumatran black tea, and herbal infusions. Our clients include wellness brands, "
            "premium tea rooms, and health food retailers. "
            "Annual volume: 15-40 MT. Payment: T/T 30/70. Halal certification preferred."
        ),
        tags=["tea", "herbal", "wellness", "green-tea", "black-tea"],
    ),

    # ─── COCONUT PRODUCTS ────────────────────────────────────────────────────
    BuyerTemplate(
        name_prefix="",
        name_suffix="",
        countries=["US", "AU", "DE", "NL", "GB", "CA", "FR", "AE"],
        hs_codes=["1513", "151311", "151321", "0801", "1404"],
        moq_range=(500, 5000),
        credibility_range=(0.65, 0.92),
        description_template=(
            "{name} is a natural ingredient distributor specializing in coconut-derived "
            "products for food, cosmetics, and nutraceutical industries. "
            "We import coconut oil (virgin, RBD, fractionated), coconut milk powder, "
            "desiccated coconut, coconut sugar, coconut fiber (coir), and coconut shell products. "
            "We serve manufacturers of natural personal care products, organic food brands, "
            "and supplement companies. Annual import: 100-500 MT. "
            "Organic certification highly preferred. Payment: L/C or T/T 30/70."
        ),
        tags=["coconut", "vco", "natural", "organic", "cosmetics", "food-ingredient"],
    ),

    # ─── PALM OIL & DERIVATIVES ──────────────────────────────────────────────
    BuyerTemplate(
        name_prefix="",
        name_suffix="",
        countries=["IN", "CN", "PK", "BD", "NL", "MY", "PH", "AE"],
        hs_codes=["1511", "151110", "151190", "151321", "2915"],
        moq_range=(5000, 50000),
        credibility_range=(0.70, 0.95),
        description_template=(
            "{name} is a commodity trader and food ingredient manufacturer importing "
            "Indonesian palm oil products. We purchase CPO, RBD Palm Olein, "
            "Palm Kernel Oil, and oleochemical derivatives. "
            "Our clients include food manufacturers, biodiesel producers, "
            "and personal care ingredient companies. "
            "RSPO or ISCC certification required. Payment: Sight L/C. "
            "Monthly volume: 500-5,000 MT. Experienced with Indonesian export regulations."
        ),
        tags=["palm-oil", "cpo", "oleochemical", "food-ingredient", "bulk-commodity"],
    ),

    # ─── HANDICRAFTS & RATTAN ────────────────────────────────────────────────
    BuyerTemplate(
        name_prefix="",
        name_suffix="",
        countries=["US", "DE", "FR", "AU", "NL", "GB", "JP", "CA", "IT", "SE"],
        hs_codes=["4602", "460190", "460210", "460220", "460290"],
        moq_range=(50, 500),
        credibility_range=(0.55, 0.88),
        description_template=(
            "{name} is a home decor and lifestyle products importer specializing in "
            "handcrafted Indonesian products. We source rattan baskets, bamboo organizers, "
            "water hyacinth storage baskets, seagrass rugs, pandanus weavings, "
            "and natural fiber home accessories. "
            "We serve boutique home stores, sustainable lifestyle retailers, "
            "and eco-friendly interior design companies. "
            "MOQ flexible for first trial order. Payment: T/T 30/70. "
            "Looking for UMKM artisans with consistent quality and on-time delivery."
        ),
        tags=["rattan", "bamboo", "handicraft", "home-decor", "natural-fiber", "sustainable"],
    ),

    # ─── WOODEN FURNITURE ────────────────────────────────────────────────────
    BuyerTemplate(
        name_prefix="",
        name_suffix="",
        countries=["US", "AU", "NL", "DE", "GB", "FR", "BE", "JP", "CA", "SG"],
        hs_codes=["9403", "940330", "940340", "940360", "9401"],
        moq_range=(20, 200),
        credibility_range=(0.65, 0.92),
        description_template=(
            "{name} is a furniture importer and retailer specializing in "
            "Indonesian teak, mahogany, and reclaimed wood furniture. "
            "We purchase outdoor garden furniture (teak dining sets, sun loungers, benches), "
            "indoor living room sets, bedroom furniture, and bespoke pieces. "
            "Our clients are furniture retailers, garden centers, and hospitality buyers. "
            "SVLK certification MANDATORY. FSC or PEFC preferred. "
            "Payment: T/T 30% deposit, 70% before shipment. Annual: 2-5 containers."
        ),
        tags=["teak", "furniture", "outdoor", "wood", "svlk", "fsc", "sustainable-wood"],
    ),

    # ─── BATIK & TEXTILES ────────────────────────────────────────────────────
    BuyerTemplate(
        name_prefix="",
        name_suffix="",
        countries=["US", "AU", "NL", "JP", "FR", "DE", "GB", "CN", "MY", "SG"],
        hs_codes=["6302", "520811", "520821", "630291", "5208"],
        moq_range=(100, 2000),
        credibility_range=(0.55, 0.85),
        description_template=(
            "{name} is a textile importer sourcing traditional and contemporary "
            "Indonesian handmade textiles. We purchase batik fabric (hand-drawn batik tulis, "
            "cap batik, printed batik), Javanese lurik, Balinese tenun, "
            "NTT ikat weaving, Lombok songket, and Toraja traditional cloth. "
            "Our clients include fashion designers, interior decorators, "
            "ethnic textile retailers, and museum gift shops. "
            "Payment: T/T or Western Union for small orders. Trial orders welcome."
        ),
        tags=["batik", "textile", "ikat", "traditional-fabric", "fashion", "handmade"],
    ),

    # ─── PROCESSED FOOD & SNACKS ─────────────────────────────────────────────
    BuyerTemplate(
        name_prefix="",
        name_suffix="",
        countries=["MY", "SG", "AU", "US", "NL", "AE", "SA", "NZ", "GB", "JP"],
        hs_codes=["2106", "210690", "1704", "190590", "2103"],
        moq_range=(200, 2000),
        credibility_range=(0.60, 0.88),
        description_template=(
            "{name} is a specialty food importer distributing authentic Indonesian "
            "and Asian food products. We source Indonesian snacks (rempeyek, keripik tempe, "
            "emping, kacang telur), condiments (kecap manis, sambal, bumbu), "
            "instant seasoning packs, and traditional food products. "
            "Our distribution network covers Asian grocery stores, "
            "Indonesian restaurants, and online food platforms. "
            "Halal certification MANDATORY. BPOM MD preferred. "
            "Payment: T/T 50/50. Annual volume: 5-20 MT per SKU."
        ),
        tags=["food", "snack", "halal", "indonesian-food", "condiment", "grocery"],
    ),

    # ─── ESSENTIAL OILS & AROMATHERAPY ───────────────────────────────────────
    BuyerTemplate(
        name_prefix="",
        name_suffix="",
        countries=["US", "FR", "DE", "GB", "AU", "NL", "IN", "JP", "AE", "CA"],
        hs_codes=["3301", "330112", "330113", "330119", "330125"],
        moq_range=(25, 200),
        credibility_range=(0.60, 0.90),
        description_template=(
            "{name} is a natural fragrance and wellness ingredient company "
            "importing essential oils from Indonesia. "
            "We source citronella oil, lemongrass oil, patchouli oil, "
            "clove leaf/bud oil, nutmeg oil, cananga (ylang-ylang) oil, "
            "vetiver (akar wangi) oil, ginger oil, and cardamom oil. "
            "We supply perfumers, aromatherapy brands, cosmetic manufacturers, "
            "and wellness companies. "
            "Purity certification (GC/MS analysis) required. "
            "Payment: T/T 50/50. Annual volume 500kg-5MT per variety."
        ),
        tags=["essential-oil", "aromatherapy", "patchouli", "lemongrass", "natural-fragrance"],
    ),

    # ─── SEAFOOD ─────────────────────────────────────────────────────────────
    BuyerTemplate(
        name_prefix="",
        name_suffix="",
        countries=["JP", "US", "AU", "DE", "FR", "KR", "CN", "SG", "NL", "AE"],
        hs_codes=["0302", "030231", "030236", "0303", "0306", "1604", "160414"],
        moq_range=(1000, 10000),
        credibility_range=(0.65, 0.92),
        description_template=(
            "{name} is a seafood trader and processor importing Indonesian "
            "wild-caught and aquaculture seafood products. "
            "We purchase yellowfin tuna (loin, steak, whole), bigeye tuna, "
            "skipjack/katsuwonus, grouper (kerapu), snapper (kakap), "
            "tiger prawns, vannamei shrimp, crab, squid (cumi), octopus, "
            "and seaweed. "
            "Products must comply with BKIPM/KKP export requirements. "
            "HACCP and cold chain documentation REQUIRED. "
            "Payment: Sight L/C or T/T 30/70. Annual: 50-500 MT."
        ),
        tags=["seafood", "tuna", "shrimp", "fish", "aquaculture", "frozen", "fresh"],
    ),

    # ─── SPICES & CONDIMENTS ─────────────────────────────────────────────────
    BuyerTemplate(
        name_prefix="",
        name_suffix="",
        countries=["DE", "US", "IN", "NL", "GB", "AE", "JP", "FR", "CA", "AU"],
        hs_codes=["0904", "0905", "0906", "0907", "0908", "0910"],
        moq_range=(100, 2000),
        credibility_range=(0.62, 0.90),
        description_template=(
            "{name} is a premium spice importer and processor sourcing Indonesian "
            "heritage spices. We import black pepper (Bangka, Lampung), "
            "white pepper (Muntok), cloves (Zanzibar-grade Maluku), "
            "nutmeg and mace (Banda Neira, Ternate), "
            "cinnamon (Kerinci cassia, Java cassia), "
            "turmeric (kunyit), galangal (lengkuas), ginger, "
            "cardamom, and star anise. "
            "Pesticide residue testing required (EU MRL standards). "
            "Payment: T/T or D/P. Volume: 5-100 MT annually."
        ),
        tags=["spice", "pepper", "clove", "cinnamon", "nutmeg", "ginger", "organic"],
    ),

    # ─── COCOA & CHOCOLATE ───────────────────────────────────────────────────
    BuyerTemplate(
        name_prefix="",
        name_suffix="",
        countries=["NL", "BE", "DE", "CH", "FR", "US", "GB", "JP", "AU", "SG"],
        hs_codes=["1801", "1803", "1804", "1805", "1806"],
        moq_range=(500, 10000),
        credibility_range=(0.68, 0.93),
        description_template=(
            "{name} is a chocolate manufacturer and cocoa ingredient company "
            "sourcing fine flavor and bulk cocoa from Indonesia. "
            "We purchase fermented dried cocoa beans (bulk: Java/Sulawesi, "
            "fine flavor: Flores, Bali), cocoa mass, cocoa butter, "
            "cocoa powder (alkalized and natural), and couverture chocolate. "
            "Indonesia's cocoa varieties (Trinitario, Criollo crossbreeds) "
            "are highly valued for their unique flavor profile. "
            "Fermentation certificate and moisture/pH specs required. "
            "Payment: Sight L/C. Volume: 20-500 MT/year."
        ),
        tags=["cocoa", "chocolate", "cacao", "fine-flavor", "fermented", "food-ingredient"],
    ),

    # ─── NATURAL BEAUTY & COSMETICS ──────────────────────────────────────────
    BuyerTemplate(
        name_prefix="",
        name_suffix="",
        countries=["US", "FR", "AU", "DE", "GB", "JP", "KR", "NL", "AE", "SG"],
        hs_codes=["3304", "3305", "3307", "3301", "1404"],
        moq_range=(100, 1000),
        credibility_range=(0.58, 0.88),
        description_template=(
            "{name} is a natural and organic beauty brand and private label "
            "cosmetics importer sourcing Indonesian botanical ingredients "
            "and finished beauty products. "
            "We import virgin coconut oil (skincare grade), "
            "rosehip and tamanu oil, red rice extract, centella asiatica, "
            "natural hair care products (coconut-based shampoo/conditioner), "
            "Indonesian jamu-inspired beauty formulas, "
            "and handmade artisanal cosmetics. "
            "BPOM notification or CPNP registration preferred. "
            "Halal certification for Muslim markets. "
            "Payment: T/T 50/50. MOQ flexible."
        ),
        tags=["cosmetics", "natural-beauty", "skincare", "organic", "halal-beauty", "vegan"],
    ),

    # ─── HERBAL & NUTRACEUTICALS ─────────────────────────────────────────────
    BuyerTemplate(
        name_prefix="",
        name_suffix="",
        countries=["US", "DE", "AU", "NL", "GB", "JP", "KR", "CA", "AE", "CN"],
        hs_codes=["1211", "121190", "0910", "1302", "3004"],
        moq_range=(50, 500),
        credibility_range=(0.60, 0.88),
        description_template=(
            "{name} is a dietary supplement and herbal products importer "
            "sourcing Indonesian traditional medicinal and nutraceutical ingredients. "
            "We purchase dried herbs (temulawak/Curcuma xanthorrhiza, "
            "sambiloto/andrographis, kayu manis bark, jahe extract, "
            "mahkota dewa, daun sirsak), "
            "standardized plant extracts, and jamu formulations. "
            "GMP certificate and heavy metal/pesticide testing mandatory. "
            "FDA GRAS status or EU Novel Food notification preferred. "
            "Payment: T/T. Volume: 100-2,000 kg annually."
        ),
        tags=["herbal", "nutraceutical", "supplement", "medicinal-plant", "jamu", "extract"],
    ),

    # ─── ECO PRODUCTS & SUSTAINABLE PACKAGING ───────────────────────────────
    BuyerTemplate(
        name_prefix="",
        name_suffix="",
        countries=["NL", "DE", "US", "AU", "GB", "SE", "NO", "DK", "FR", "CA"],
        hs_codes=["4602", "1404", "4601", "4420", "3923"],
        moq_range=(200, 2000),
        credibility_range=(0.62, 0.90),
        description_template=(
            "{name} is a sustainable packaging and eco-product company "
            "importing Indonesian biodegradable and compostable alternatives "
            "to plastic products. "
            "We source coconut shell products (bowls, cups, cutlery), "
            "bamboo packaging (boxes, trays, containers), "
            "banana leaf-based packaging, rattan and bamboo storage solutions, "
            "coconut fiber (coir) pots and growing media, "
            "and other plant-based sustainable alternatives. "
            "We supply zero-waste stores, eco-friendly brands, "
            "and sustainable hospitality venues. "
            "B Corp or equivalent sustainability certification preferred. "
            "Payment: T/T 30/70."
        ),
        tags=["sustainable", "eco-friendly", "biodegradable", "bamboo", "coconut-shell", "zero-waste"],
    ),
]

# Company name components for generating realistic buyer names
COMPANY_PREFIXES = [
    "Global", "Pacific", "Euro", "Nordic", "Trans", "Premier", "Allied",
    "United", "Continental", "Atlantic", "Orient", "Prime", "Summit",
    "Heritage", "Horizon", "Pinnacle", "Core", "Central", "New", "Modern",
]

COMPANY_SUFFIXES_BY_COUNTRY: dict[str, list[str]] = {
    "DE": ["GmbH", "AG", "GmbH & Co. KG", "KG", "OHG"],
    "NL": ["B.V.", "N.V.", "C.V.", "VOF"],
    "US": ["LLC", "Inc.", "Corp.", "Co.", "International LLC"],
    "JP": ["Co., Ltd.", "K.K.", "Corporation"],
    "AU": ["Pty Ltd", "Pty. Ltd.", "Ltd"],
    "GB": ["Ltd", "Limited", "PLC", "LLP"],
    "FR": ["SARL", "SAS", "SA"],
    "CA": ["Inc.", "Ltd.", "Corp."],
    "SG": ["Pte Ltd", "Pte. Ltd."],
    "AE": ["LLC", "FZE", "FZCO"],
    "SA": ["LLC", "Co. Ltd."],
    "CN": ["Co., Ltd.", "Trading Co., Ltd."],
    "KR": ["Co., Ltd.", "Corp."],
    "IN": ["Pvt Ltd", "Ltd."],
    "BE": ["BVBA", "NV", "SA"],
    "SE": ["AB", "HB"],
    "NO": ["AS", "ASA"],
    "DK": ["A/S", "ApS"],
    "CH": ["AG", "GmbH", "SA"],
    "IT": ["S.r.l.", "S.p.A."],
    "PK": ["Pvt Ltd", "Ltd"],
    "BD": ["Ltd.", "Private Ltd."],
    "MY": ["Sdn Bhd", "Bhd"],
    "PH": ["Inc.", "Corp."],
    "NZ": ["Ltd", "Limited"],
}

INDUSTRY_NOUNS = [
    "Trade", "Trading", "Imports", "Import & Export", "Commerce",
    "Foods", "Ingredients", "Commodities", "Products", "Solutions",
    "Provisions", "Naturals", "Organics", "Resources", "Supplies",
    "Distribution", "Distributors", "Wholesale", "International",
    "Enterprises", "Ventures", "Partners", "Group",
]


def generate_company_name(country: str, rng: random.Random) -> str:
    prefix = rng.choice(COMPANY_PREFIXES)
    noun = rng.choice(INDUSTRY_NOUNS)
    suffix_list = COMPANY_SUFFIXES_BY_COUNTRY.get(country, ["Ltd.", "LLC", "Inc."])
    suffix = rng.choice(suffix_list)
    return f"{prefix} {noun} {suffix}"


def generate_buyers(count: int, rng: random.Random) -> list[dict]:
    buyers = []
    # Distribute evenly across templates
    templates_cycle = []
    while len(templates_cycle) < count:
        rng.shuffle(BUYER_TEMPLATES)
        templates_cycle.extend(BUYER_TEMPLATES)
    templates_cycle = templates_cycle[:count]

    for i, tmpl in enumerate(templates_cycle):
        country = rng.choice(tmpl.countries)
        company_name = generate_company_name(country, rng)

        # Pick 1-3 HS codes from template
        hs = rng.sample(tmpl.hs_codes, k=min(rng.randint(1, 3), len(tmpl.hs_codes)))

        credibility = round(rng.uniform(*tmpl.credibility_range), 3)
        moq = rng.choice(
            [v for v in [50, 100, 200, 250, 500, 1000, 2000, 5000] if tmpl.moq_range[0] <= v <= tmpl.moq_range[1]]
            or [tmpl.moq_range[0]]
        )

        description = tmpl.description_template.format(
            name=company_name, country=country,
        )

        buyers.append({
            "id": str(uuid4()),
            "name": company_name,
            "country": country,
            "hs_codes": hs,
            "credibility_score": credibility,
            "min_order_qty": moq,
            "description": description,
            "is_synthetic": True,
            "metadata": {
                "source": "synthetic_v2",
                "category": tmpl.tags[0] if tmpl.tags else "general",
                "tags": tmpl.tags,
                "index": i,
            },
        })

    return buyers


def generate_embeddings(descriptions: list[str], model_name: str = "intfloat/multilingual-e5-large") -> list[list[float]]:
    """Generate 1024-dim embeddings using sentence-transformers."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("  [SKIP] sentence-transformers not installed.")
        print("  Install: uv pip install 'sentence-transformers>=3.3' 'torch>=2.0'")
        return []

    print(f"  Loading embedding model '{model_name}' (first run may download ~1.3 GB)…")
    model = SentenceTransformer(model_name)

    # E5 models require 'passage:' prefix for documents
    passages = [f"passage: {d}" for d in descriptions]
    print(f"  Encoding {len(passages)} buyer descriptions…")
    vecs = model.encode(
        passages,
        normalize_embeddings=True,
        batch_size=32,
        show_progress_bar=True,
    )
    return [v.tolist() for v in vecs]


def seed(dsn: str, count: int, with_embeddings: bool, clear_first: bool, seed_val: int) -> None:
    rng = random.Random(seed_val)
    engine = create_engine(dsn, pool_pre_ping=True)
    print(f"Connected to: {dsn.split('@')[-1]}")

    with engine.begin() as conn:
        if clear_first:
            conn.execute(text("DELETE FROM buyer_embedding"))
            conn.execute(text("DELETE FROM buyer WHERE is_synthetic = TRUE"))
            print("  Cleared existing synthetic buyers and their embeddings.")

        buyers = generate_buyers(count, rng)
        print(f"\nGenerated {len(buyers)} buyer profiles.")

        # Optionally generate embeddings
        embeddings: list[list[float]] = []
        if with_embeddings:
            descriptions = [b["description"] for b in buyers]
            embeddings = generate_embeddings(descriptions)

        # Insert buyers
        inserted_buyers = 0
        buyer_ids_inserted: list[str] = []
        for buyer in buyers:
            conn.execute(
                text("""
                    INSERT INTO buyer (
                        id, name, country, hs_codes, credibility_score,
                        min_order_qty, description, is_active, is_synthetic, metadata
                    ) VALUES (
                        :id, :name, :country, :hs, :cred,
                        :moq, :desc, TRUE, TRUE, CAST(:meta AS JSONB)
                    )
                """),
                {
                    "id":     buyer["id"],
                    "name":   buyer["name"],
                    "country": buyer["country"],
                    "hs":     buyer["hs_codes"],
                    "cred":   buyer["credibility_score"],
                    "moq":    buyer["min_order_qty"],
                    "desc":   buyer["description"],
                    "meta":   json.dumps(buyer["metadata"]),
                },
            )
            inserted_buyers += 1
            buyer_ids_inserted.append(buyer["id"])

        print(f"✅ Inserted {inserted_buyers} buyers into buyer table.")

        # Insert embeddings
        if embeddings:
            model_name = "intfloat/multilingual-e5-large"
            inserted_emb = 0
            for buyer_id, emb_vec in zip(buyer_ids_inserted, embeddings):
                conn.execute(
                    text("""
                        INSERT INTO buyer_embedding (id, buyer_id, model, embedding)
                        VALUES (:id, :buyer_id, :model, CAST(:emb AS vector))
                        ON CONFLICT (buyer_id) DO UPDATE
                            SET embedding = EXCLUDED.embedding,
                                model = EXCLUDED.model,
                                updated_at = NOW()
                    """),
                    {
                        "id":       str(uuid4()),
                        "buyer_id": buyer_id,
                        "model":    model_name,
                        "emb":      str(emb_vec),
                    },
                )
                inserted_emb += 1
            print(f"✅ Inserted {inserted_emb} embeddings into buyer_embedding table.")

            # Create HNSW index now that we have enough data
            total_buyers = conn.execute(
                text("SELECT COUNT(*) FROM buyer_embedding")
            ).scalar()
            print(f"   Total buyer embeddings now: {total_buyers}")

            if total_buyers >= 100:
                print("   Creating HNSW index on buyer_embedding…")
                try:
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_buyer_embedding_hnsw
                        ON buyer_embedding USING hnsw (embedding vector_cosine_ops)
                        WITH (m = 16, ef_construction = 64)
                    """))
                    print("✅ HNSW index created (idx_buyer_embedding_hnsw).")
                except Exception as e:
                    print(f"  [WARN] HNSW index creation failed (will retry later): {e}")
        else:
            print("\nNote: Embeddings NOT generated. Buyer matching will not work until embeddings exist.")
            print("Re-run with --with-embeddings flag when sentence-transformers is available.")

        # Stats
        print("\nBuyer distribution by category (top tag):")
        rows = conn.execute(text("""
            SELECT metadata->>'category' AS category, COUNT(*) AS n
            FROM buyer WHERE is_synthetic = TRUE
            GROUP BY metadata->>'category'
            ORDER BY n DESC
        """)).fetchall()
        for row in rows:
            print(f"  {str(row[0] or 'unknown'):25s}: {row[1]}")

        print("\nBuyer distribution by country:")
        rows = conn.execute(text("""
            SELECT country, COUNT(*) AS n
            FROM buyer WHERE is_synthetic = TRUE
            GROUP BY country ORDER BY n DESC LIMIT 15
        """)).fetchall()
        for row in rows:
            print(f"  {row[0]:5s}: {row[1]}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Seed TradeConnect with realistic synthetic buyers and pgvector embeddings."
    )
    ap.add_argument("--count", type=int, default=200,
                    help="Number of buyers to generate (default: 200)")
    ap.add_argument(
        "--dsn",
        default=os.environ.get(
            "DATABASE_URL_SYNC",
            "postgresql+psycopg://tc_user:tc_pass_dev@localhost:5432/tradeconnect",
        ),
        help="PostgreSQL DSN",
    )
    ap.add_argument(
        "--with-embeddings",
        action="store_true",
        help="Generate 1024-dim embeddings using intfloat/multilingual-e5-large",
    )
    ap.add_argument(
        "--skip-embeddings",
        action="store_true",
        help="Alias for NOT generating embeddings (default behavior)",
    )
    ap.add_argument(
        "--clear",
        action="store_true",
        help="Delete all existing synthetic buyers before seeding",
    )
    ap.add_argument("--seed", type=int, default=42,
                    help="Random seed for reproducibility (default: 42)")
    args = ap.parse_args()

    want_embeddings = args.with_embeddings and not args.skip_embeddings

    print("=" * 60)
    print("TradeConnect Synthetic Buyer Seeder v2")
    print(f"Buyers to generate: {args.count}")
    print(f"Categories covered: {len(BUYER_TEMPLATES)}")
    print(f"With embeddings   : {want_embeddings}")
    print(f"Clear existing    : {args.clear}")
    print(f"Random seed       : {args.seed}")
    print("=" * 60)

    if not want_embeddings:
        print("\n⚠️  Running WITHOUT embeddings.")
        print("   Buyer matching (ANN search) requires embeddings.")
        print("   Run again with --with-embeddings for full functionality.\n")

    seed(args.dsn, args.count, want_embeddings, args.clear, args.seed)

    print("\n" + "=" * 60)
    print("Done! 🎉")
    print("\nNext steps:")
    if not want_embeddings:
        print("  1. Re-run with --with-embeddings to generate vector embeddings")
        print("     (requires sentence-transformers and torch)")
    print("  2. Register a UMKM and product via POST /api/v1/umkm and /api/v1/products")
    print("     (this triggers buyer embedding generation via the ETL worker)")
    print("  3. Call POST /api/v1/matching/match with a product_id to test buyer discovery")
    print("=" * 60)


if __name__ == "__main__":
    main()
