"""Generate pgvector embeddings for existing products so /matching/search works.

Runs in the matching-service image. Encodes name + description with
intfloat/multilingual-e5-large (passage prefix) and upserts product_embedding.
"""
from __future__ import annotations

import os
from uuid import uuid4

from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, text

DSN = os.environ["DATABASE_URL_SYNC"]
MODEL = os.environ.get("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")


def main() -> None:
    engine = create_engine(DSN, pool_pre_ping=True)
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT id, name, COALESCE(description,'') AS description, COALESCE(hs_code,'') AS hs_code FROM product")
        ).fetchall()
        print(f"products: {len(rows)}")
        if not rows:
            return
        model = SentenceTransformer(MODEL)
        for r in rows:
            passage = f"passage: {r.name}. {r.description}. HS {r.hs_code}"
            vec = model.encode([passage], normalize_embeddings=True)[0].tolist()
            conn.execute(
                text(
                    """
                    INSERT INTO product_embedding (id, product_id, model, embedding)
                    VALUES (:id, :pid, :model, CAST(:emb AS vector))
                    ON CONFLICT (product_id) DO UPDATE
                        SET embedding = EXCLUDED.embedding, model = EXCLUDED.model, updated_at = NOW()
                    """
                ),
                {"id": str(uuid4()), "pid": str(r.id), "model": MODEL, "emb": str(vec)},
            )
            print(f"embedded {r.name} ({r.id})")
    print("done")


if __name__ == "__main__":
    main()
