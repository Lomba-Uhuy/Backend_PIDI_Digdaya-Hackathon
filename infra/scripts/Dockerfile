# Tiny one-shot image for the knowledge-base embedder (Render cron / manual run).
# Keeps embed_knowledge_base.py as the single source of truth (no volume mount,
# no coupling to the matching-service image). Build context = infra/scripts.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN pip install "psycopg[binary]>=3.2" "google-genai>=1.0.0"

WORKDIR /app
COPY embed_knowledge_base.py /app/embed_knowledge_base.py

# Reads DATABASE_URL_SYNC, GEMINI_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS,
# CHUNK_SIZE, CHUNK_OVERLAP from the environment. Idempotent (skips rows that
# already have an embedding).
CMD ["python", "/app/embed_knowledge_base.py"]
