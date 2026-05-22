"""Standalone synthetic buyer generator.

Run when you can't or don't want to use the Celery worker:
  python scripts/generate-synthetic-buyers.py --count 100

Writes to the buyer table directly (requires DATABASE_URL_SYNC).
All rows are flagged is_synthetic = TRUE for transparency.
"""
from __future__ import annotations

import argparse
import json
import os
import random
from uuid import uuid4

try:
    from sqlalchemy import create_engine, text
except ImportError as e:
    raise SystemExit(
        "This script needs SQLAlchemy. Install with: uv pip install sqlalchemy psycopg[binary]"
    ) from e

COUNTRIES = ["DE", "NL", "US", "JP", "AE", "FR", "GB", "AU", "CA", "SG", "KR"]
HS_CODES = ["4602", "1404", "9403", "0901", "0902", "1801", "1513", "0801", "2106", "6302"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument(
        "--dsn",
        default=os.environ.get(
            "DATABASE_URL_SYNC",
            "postgresql+psycopg://tc_user:tc_pass_dev@localhost:5432/tradeconnect",
        ),
    )
    args = ap.parse_args()
    random.seed(42)

    engine = create_engine(args.dsn, pool_pre_ping=True)
    with engine.begin() as conn:
        for i in range(args.count):
            hs = random.sample(HS_CODES, k=random.randint(1, 3))
            country = random.choice(COUNTRIES)
            conn.execute(
                text("""
                    INSERT INTO buyer (
                        id, name, country, hs_codes, credibility_score,
                        min_order_qty, description, is_active, is_synthetic, metadata
                    )
                    VALUES (
                        :id, :name, :country, :hs, :cred,
                        :moq, :desc, TRUE, TRUE, CAST(:meta AS JSONB)
                    )
                """),
                {
                    "id": str(uuid4()),
                    "name": f"Synthetic Importer {i:04d} GmbH",
                    "country": country,
                    "hs": hs,
                    "cred": round(random.uniform(0.5, 0.95), 3),
                    "moq": random.choice([100, 250, 500, 1000]),
                    "desc": (
                        f"Synthetic buyer importing categories {', '.join(hs)} "
                        f"from Southeast Asia. Mirrors UN Comtrade flow patterns."
                    ),
                    "meta": json.dumps({"source": "synthetic_v1", "seed": 42}),
                },
            )
    print(f"Inserted {args.count} synthetic buyers (is_synthetic = TRUE).")


if __name__ == "__main__":
    main()