"""Buyer seeding task — synthetic buyer profiles flagged is_synthetic = TRUE."""
from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import structlog
from sqlalchemy import text

if TYPE_CHECKING:
    from celery import Task

from etl_worker.celery_app import celery_app
from etl_worker.db.session import get_session_factory

log = structlog.get_logger(__name__)

COUNTRIES = ["DE", "NL", "US", "JP", "AE", "FR", "GB", "AU", "CA", "SG", "KR"]
HS_CODES = ["4602", "1404", "9403", "0901", "0902", "1801", "1513", "0801", "2106", "6302", "3305"]

# Konteks negara untuk memperkaya deskripsi buyer → embedding lebih diskriminatif
_COUNTRY_CONTEXT: dict[str, str] = {
    "DE": "Germany, European Union. Strong demand for certified organic products, sustainable furniture, and specialty foods.",
    "NL": "Netherlands, European Union. Major re-export hub; imports natural fibers, rattan, spices, and tropical commodities.",
    "US": "United States. Large consumer market; values certifications (USDA Organic, Fair Trade), artisan crafts, and specialty coffee.",
    "JP": "Japan. Premium quality focus; high demand for specialty coffee, spices, traditional crafts, and natural cosmetics.",
    "AE": "United Arab Emirates. Middle East re-export hub; demand for luxury goods, specialty foods, halal-certified products, and home decor.",
    "FR": "France, European Union. Imports luxury textiles, specialty foods, essential oils, perfumery ingredients, and artisan goods.",
    "GB": "United Kingdom. Imports fair-trade coffee, natural fibers, hand-crafted goods, batik textiles, and organic spices.",
    "AU": "Australia. Sustainable products focus; demand for organic food, natural timber furniture, and artisan crafts.",
    "CA": "Canada. Natural and organic products market; imports specialty coffee, maple-certified goods, and sustainable furniture.",
    "SG": "Singapore. Southeast Asia trading hub; premium food imports, specialty coffee, fine jewelry, and luxury home goods.",
    "KR": "South Korea (Republic of Korea). High-value consumer market; demand for specialty coffee, natural cosmetics, and premium spices.",
}

# Nama produk representatif per HS code untuk memperkaya deskripsi
_HS_PRODUCT_NAMES: dict[str, str] = {
    "4602": "rattan baskets, wicker furniture, and woven handicrafts",
    "1404": "natural plant-based materials and vegetable products",
    "9403": "wooden furniture, teak tables, and reclaimed wood home furnishings",
    "0901": "specialty coffee beans, arabica green beans, and roasted coffee",
    "0902": "premium tea leaves and herbal teas",
    "1801": "cocoa beans and raw cocoa products",
    "1513": "virgin coconut oil (VCO), coconut derivatives, and palm oil",
    "0801": "tropical nuts, coconut products, and cashews",
    "2106": "food preparations, herbal extracts, and functional food ingredients",
    "6302": "batik bed linen, traditional textiles, and woven household linens",
    "3305": "hair care products, natural cosmetics, and essential oil-based preparations",
}


def _hash_to_int(seed: int, label: str, index: int, *extra: Any) -> int:
    """SHA-256 of (seed, label, index[, extra...]) → uint64."""
    parts = [str(seed), label, str(index), *[str(v) for v in extra]]
    return int.from_bytes(hashlib.sha256(":".join(parts).encode()).digest()[:8], "big")


def _deterministic_index(seed: int, label: str, index: int, modulo: int) -> int:
    return _hash_to_int(seed, label, index) % modulo


def _deterministic_sample(
    seed: int,
    label: str,
    index: int,
    values: list[str],
    count: int,
) -> list[str]:
    ranked = sorted(values, key=lambda value: _hash_to_int(seed, label, index, value))
    return ranked[:count]


def _deterministic_float(
    seed: int,
    label: str,
    index: int,
    minimum: float,
    maximum: float,
) -> float:
    fraction = _hash_to_int(seed, label, index) / 2**64
    return minimum + (maximum - minimum) * fraction


@celery_app.task(name="seeding.synthetic_buyers", bind=True, queue="ingest")  # type: ignore[untyped-decorator]
def seed_synthetic_buyers(self: Task, count: int = 100) -> dict[str, Any]:
    """Seed N synthetic buyers, all flagged is_synthetic = TRUE.

    Per the v2 spec's transparency requirement: every synthetic buyer
    is labeled in the DB, and the UI must show 'Data Simulasi' to users.
    """
    log.info("seeding.synthetic.start", count=count)
    seed = 42
    inserted = 0
    buyer_ids: list[str] = []

    session_factory = get_session_factory()
    with session_factory() as session:
        # Hapus synthetic buyer lama agar task ini idempoten (aman dijalankan ulang)
        session.execute(text("DELETE FROM buyer_embedding WHERE buyer_id IN (SELECT id FROM buyer WHERE is_synthetic = TRUE)"))
        session.execute(text("DELETE FROM buyer WHERE is_synthetic = TRUE"))

        for i in range(count):
            buyer_id = str(uuid4())
            country = COUNTRIES[_deterministic_index(seed, "country", i, len(COUNTRIES))]
            hs_count = 1 + _deterministic_index(seed, "hs_count", i, 3)
            hs = _deterministic_sample(seed, "hs", i, HS_CODES, hs_count)
            cred = round(_deterministic_float(seed, "cred", i, 0.5, 0.95), 3)
            moq = [100, 250, 500, 1000][_deterministic_index(seed, "moq", i, 4)]
            country_ctx = _COUNTRY_CONTEXT.get(country, f"{country} importer.")
            hs_products = "; ".join(
                _HS_PRODUCT_NAMES.get(code, f"HS {code} goods") for code in hs
            )
            company_suffix = _deterministic_index(seed, "suffix", i, 5)
            company_names = ["GmbH", "B.V.", "LLC", "Co. Ltd.", "Pty Ltd"]
            buyer_name = f"Synthetic Importer {i:04d} {company_names[company_suffix]}"
            description = (
                f"{country_ctx} "
                f"Actively sourcing {hs_products} from Indonesian UMKM suppliers. "
                f"Minimum order quantity: {moq} units. "
                f"Credibility rating: {cred:.3f}. "
                f"Prefers suppliers with export certifications and verified NIB."
            )

            session.execute(
                text(
                    """
                    INSERT INTO buyer (
                        id, name, country, hs_codes, credibility_score,
                        min_order_qty, description, is_active, is_synthetic, metadata
                    )
                    VALUES (
                        :id, :name, :country, :hs, :cred,
                        :moq, :desc, TRUE, TRUE, CAST(:meta AS JSONB)
                    )
                    """
                ),
                {
                    "id": buyer_id,
                    "name": buyer_name,
                    "country": country,
                    "hs": hs,
                    "cred": cred,
                    "moq": moq,
                    "desc": description,
                    "meta": json.dumps({"source": "synthetic_v1", "seed": seed}),
                },
            )
            buyer_ids.append(buyer_id)
            inserted += 1
        session.commit()

    log.info("seeding.synthetic.db_done", inserted=inserted)

    # Dispatch embedding generation ke embedding-worker
    embedding_dispatched = 0
    for buyer_id in buyer_ids:
        celery_app.send_task(
            "embeddings.generate_buyer",
            args=[buyer_id],
            queue="ai",
            ignore_result=True,
        )
        embedding_dispatched += 1

    log.info("seeding.synthetic.done", inserted=inserted, embedding_tasks_dispatched=embedding_dispatched)
    return {"inserted": inserted, "embedding_tasks_dispatched": embedding_dispatched}
