# Matching Service

FastAPI service for HS Code classification (sentence-transformers) and buyer
matching via pgvector ANN search.

```bash
uv sync
uv run uvicorn matching_service.main:app --reload --port 8001
```