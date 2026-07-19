#!/usr/bin/env python3
"""Embed knowledge base documents into pgvector.

Reads all export_knowledge_base rows that lack embeddings, chunks long content
into ≤512-token segments, generates embeddings using the same multilingual-e5-large
model used by the matching-service, and writes results back to the DB.

Usage:
    # With local Python (requires deps: psycopg, sentence-transformers)
    python infra/scripts/embed_knowledge_base.py

    # Via Docker (if matching-service container is running)
    docker exec -it matching-service python /scripts/embed_knowledge_base.py

Environment variables (read from .env or shell):
    DATABASE_URL_SYNC  — psycopg-compatible DB URL (default: postgresql+psycopg://...)
    EMBEDDING_MODEL    — HuggingFace model ID (default: intfloat/multilingual-e5-large)
    HF_TOKEN           — optional HuggingFace auth token for gated models
    CHUNK_SIZE         — max characters per chunk (default: 1800, ~512 tokens)
    CHUNK_OVERLAP      — overlap between chunks in characters (default: 200)
"""
from __future__ import annotations

import os
import textwrap
import time
from pathlib import Path

# ── Load .env if present ─────────────────────────────────────────────────────
_env_file = Path(__file__).parent.parent.parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

DATABASE_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg://tc_user:tc_pass_dev@localhost:5432/tradeconnect",
).replace("postgresql+psycopg://", "postgresql://")

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
HF_TOKEN = os.environ.get("HF_TOKEN") or None
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "1800"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "200"))

# ── Chunking ─────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks on paragraph or sentence boundaries."""
    if len(text) <= chunk_size:
        return [text.strip()]

    chunks: list[str] = []
    # Split on double newline (paragraph) first, then fall back to single newline
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            # Para itself longer than chunk_size? Split by lines
            if len(para) > chunk_size:
                lines = textwrap.wrap(para, width=chunk_size - overlap)
                for line in lines:
                    chunks.append(line)
                current = lines[-1][-overlap:] if lines else ""
            else:
                current = para
    if current:
        chunks.append(current)

    # Apply overlap: prepend tail of previous chunk to each subsequent chunk
    if len(chunks) > 1:
        overlapped: list[str] = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-overlap:] if len(chunks[i - 1]) >= overlap else chunks[i - 1]
            overlapped.append((tail + " " + chunks[i]).strip())
        return overlapped
    return chunks


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    try:
        import psycopg
    except ImportError:
        raise SystemExit("psycopg not installed. Run: pip install psycopg[binary]")

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise SystemExit(
            "sentence-transformers not installed. "
            "Run: pip install sentence-transformers"
        )

    print(f"Connecting to DB: {DATABASE_URL[:40]}...")
    conn = psycopg.connect(DATABASE_URL)

    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(
        EMBEDDING_MODEL,
        use_auth_token=HF_TOKEN,
        device="cpu",
    )
    print("Model loaded.")

    # Fetch rows without embeddings
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, content, category FROM export_knowledge_base "
            "WHERE embedding IS NULL ORDER BY created_at"
        )
        rows = cur.fetchall()

    if not rows:
        print("All knowledge base entries already have embeddings. Nothing to do.")
        conn.close()
        return

    print(f"Found {len(rows)} rows without embeddings.")

    processed = 0
    for row_id, title, content, category in rows:
        # Build text to embed: prefix per E5 convention + title + content chunk
        chunks = chunk_text(content)
        print(f"  [{category}] '{title[:60]}' → {len(chunks)} chunk(s)")

        for i, chunk in enumerate(chunks):
            passage = f"passage: {title}\n\n{chunk}"
            embedding: list[float] = model.encode(passage, normalize_embeddings=True).tolist()
            vec_str = "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"

            if i == 0 and len(chunks) == 1:
                # Single chunk: update existing row
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE export_knowledge_base SET embedding = %s::vector WHERE id = %s",
                        (vec_str, row_id),
                    )
            else:
                if i == 0:
                    # First chunk: update original row
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE export_knowledge_base SET "
                            "  content = %s, embedding = %s::vector "
                            "WHERE id = %s",
                            (chunk, vec_str, row_id),
                        )
                else:
                    # Additional chunks: insert as new rows with source reference
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO export_knowledge_base "
                            "  (title, content, category, source, embedding) "
                            "SELECT "
                            "  title || ' (part ' || %s || ')', %s, category, source, %s::vector "
                            "FROM export_knowledge_base WHERE id = %s",
                            (i + 1, chunk, vec_str, row_id),
                        )
            conn.commit()

        processed += 1
        if processed % 5 == 0:
            print(f"  Progress: {processed}/{len(rows)} rows embedded")
        time.sleep(0.05)  # brief pause to avoid CPU spike on small machines

    print(f"\nDone. Embedded {processed} knowledge base entries.")

    # Optionally create HNSW index if enough rows
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM export_knowledge_base WHERE embedding IS NOT NULL")
        count = cur.fetchone()[0]

    if count >= 50:
        print(f"Creating HNSW index on export_knowledge_base ({count} rows)...")
        with conn.cursor() as cur:
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_ekb_embedding_hnsw
                ON export_knowledge_base
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """)
        conn.commit()
        print("HNSW index created.")
    else:
        print(f"Skipping HNSW index ({count} rows < 50 minimum).")

    conn.close()
    print("Connection closed. Knowledge base embedding complete.")


if __name__ == "__main__":
    main()
