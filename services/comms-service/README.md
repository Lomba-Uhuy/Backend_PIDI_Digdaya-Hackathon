# Comms Service

FastAPI service for Deal Communication Assistant — RAG-driven negotiation drafts
with strict guardrails against floor-price and BATNA disclosure.

```bash
uv sync
uv run uvicorn comms_service.main:app --reload --port 8002
```