# ETL & Verification Worker

Celery workers for:
- **external** queue: NIB verification via OSS RBA + INATRADE
- **ingest** queue: UN Comtrade & BPS trade data ETL

```bash
uv sync
uv run celery -A etl_worker.celery_app worker -Q external,ingest -l info
```