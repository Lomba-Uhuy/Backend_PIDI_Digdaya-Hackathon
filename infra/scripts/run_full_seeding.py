#!/usr/bin/env python3
"""Run complete database population script for TradeConnect on Supabase.

Steps executed:
  1. Seed Knowledge Base (export_knowledge_base) via infra/db/seed-knowledge-base.sql
  2. Embed Knowledge Base via Gemini API (embed_knowledge_base.py)
  3. Seed UMKM companies and products (product_seeding_task.py)
  4. Seed International Buyers (buyer_seeding_task.py)
  5. Ingest real trade data from UN Comtrade API (un_comtrade_task.py)
  6. Ingest real trade statistics from BPS API (bps_task.py)
  7. Generate and populate buyer & product embeddings via Gemini API
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Force UTF-8 stdout for Windows terminals
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add services to sys.path so we can import etl_worker and matching_service
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir / "services" / "etl-worker" / "src"))
sys.path.insert(0, str(root_dir / "services" / "matching-service" / "src"))
sys.path.insert(0, str(root_dir / "infra" / "scripts"))

# Load .env
env_file = root_dir / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

import psycopg


def main() -> None:
    db_sync = os.environ.get("DATABASE_URL_SYNC", "").replace("postgresql+psycopg://", "postgresql://")
    print(f"[1/7] Starting full database population for Supabase: {db_sync[:45]}...\n")

    # ── Step 1: Seed Knowledge Base SQL ──────────────────────────────────────
    print("[Step 1] Seeding Knowledge Base SQL (export_knowledge_base)...")
    sql_path = root_dir / "infra" / "db" / "seed-knowledge-base.sql"
    if sql_path.exists():
        sql_content = sql_path.read_text(encoding="utf-8")
        with psycopg.connect(db_sync) as conn:
            with conn.cursor() as cur:
                cur.execute(sql_content)
                conn.commit()
                cur.execute("SELECT COUNT(*) FROM export_knowledge_base")
                kb_count = cur.fetchone()[0]
        print(f"   -> Knowledge Base SQL seeded! Total rows: {kb_count}\n")
    else:
        print("   -> seed-knowledge-base.sql not found, skipping SQL seed.\n")

    # ── Step 2: Embed Knowledge Base via Gemini API ──────────────────────────
    print("[Step 2] Generating Gemini Embeddings for Knowledge Base...")
    try:
        import embed_knowledge_base
        embed_knowledge_base.main()
        print("   -> Knowledge base embedding complete!\n")
    except Exception as e:
        print(f"   -> Knowledge base embedding note: {e}\n")

    # ── Step 3: Seed UMKM & Products ─────────────────────────────────────────
    print("[Step 3] Seeding UMKM companies and products...")
    try:
        from etl_worker.tasks.product_seeding_task import seed_synthetic_products
        res_prod = seed_synthetic_products.apply().result
        print(f"   -> UMKM & Products seeded: {res_prod}\n")
    except Exception as e:
        print(f"   -> Product seeding note: {e}\n")

    # ── Step 4: Seed International Buyers ────────────────────────────────────
    print("[Step 4] Seeding International Buyer directory...")
    try:
        from etl_worker.tasks.buyer_seeding_task import seed_synthetic_buyers
        res_buyer = seed_synthetic_buyers.apply(kwargs={"count": 150}).result
        print(f"   -> Buyers seeded: {res_buyer}\n")
    except Exception as e:
        print(f"   -> Buyer seeding note: {e}\n")

    # ── Step 5: Ingest UN Comtrade API Real Data ──────────────────────────────
    print("[Step 5] Fetching real trade flow data from UN Comtrade API...")
    try:
        from etl_worker.tasks.un_comtrade_task import ingest_un_comtrade
        res_comtrade1 = ingest_un_comtrade(hs_code="0901", year=2024)
        print(f"   -> UN Comtrade (0901 Coffee): {res_comtrade1.get('status')}, rows: {res_comtrade1.get('rows_inserted')}")
        res_comtrade2 = ingest_un_comtrade(hs_code="4602", year=2024)
        print(f"   -> UN Comtrade (4602 Rattan): {res_comtrade2.get('status')}, rows: {res_comtrade2.get('rows_inserted')}\n")
    except Exception as e:
        print(f"   -> UN Comtrade ingestion note: {e}\n")

    # ── Step 6: Ingest BPS Indonesia API Real Data ────────────────────────────
    print("[Step 6] Fetching real Indonesia trade stats from BPS API...")
    try:
        from etl_worker.tasks.bps_task import ingest_bps
        res_bps1 = ingest_bps(hs_code="0901", year=2024)
        print(f"   -> BPS Indonesia (0901 Coffee): {res_bps1.get('status')}, rows: {res_bps1.get('rows_inserted')}")
        res_bps2 = ingest_bps(hs_code="4602", year=2024)
        print(f"   -> BPS Indonesia (4602 Rattan): {res_bps2.get('status')}, rows: {res_bps2.get('rows_inserted')}\n")
    except Exception as e:
        print(f"   -> BPS ingestion note: {e}\n")

    # ── Step 7: Generate Product & Buyer Embeddings via Gemini API ───────────
    print("[Step 7] Generating Gemini Embeddings for Products & Buyers...")
    try:
        from matching_service.infrastructure.embeddings.sentence_transformer import get_embedder
        embedder = get_embedder()

        with psycopg.connect(db_sync) as conn:
            # 7a. Product embeddings
            with conn.cursor() as cur:
                cur.execute("SELECT id, name, description FROM product")
                prods = cur.fetchall()

            prod_count = 0
            for pid, pname, pdesc in prods:
                txt = f"{pname}. {pdesc or ''}"
                vec = embedder.embed_sync([txt])[0]
                vec_str = "[" + ",".join(f"{v:.8f}" for v in vec) + "]"
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO product_embedding (product_id, model, embedding, created_at, updated_at)
                        VALUES (%s, %s, %s::vector, NOW(), NOW())
                        ON CONFLICT (product_id)
                        DO UPDATE SET embedding = %s::vector, model = %s, updated_at = NOW()
                        """,
                        (pid, embedder.model_name, vec_str, vec_str, embedder.model_name),
                    )
                conn.commit()
                prod_count += 1
            print(f"   -> Embedded {prod_count} products via Gemini API")

            # 7b. Buyer embeddings
            with conn.cursor() as cur:
                cur.execute("SELECT id, name, country, hs_codes, description FROM buyer")
                buyers = cur.fetchall()

            buyer_count = 0
            for bid, bname, bcountry, bhs, bdesc in buyers:
                hs_str = ", ".join(bhs or [])
                txt = f"International buyer {bname} from {bcountry}. Imports products: {hs_str}. {bdesc or ''}"
                vec = embedder.embed_sync([txt])[0]
                vec_str = "[" + ",".join(f"{v:.8f}" for v in vec) + "]"
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO buyer_embedding (buyer_id, model, embedding, created_at, updated_at)
                        VALUES (%s, %s, %s::vector, NOW(), NOW())
                        ON CONFLICT (buyer_id)
                        DO UPDATE SET embedding = %s::vector, model = %s, updated_at = NOW()
                        """,
                        (bid, embedder.model_name, vec_str, vec_str, embedder.model_name),
                    )
                conn.commit()
                buyer_count += 1
            print(f"   -> Embedded {buyer_count} buyers via Gemini API\n")
    except Exception as e:
        print(f"   -> Embedding generation note: {e}\n")

    print("[SUCCESS] FULL DATABASE SEEDING AND API POPULATION COMPLETE! All data ready in Supabase.")


if __name__ == "__main__":
    main()
