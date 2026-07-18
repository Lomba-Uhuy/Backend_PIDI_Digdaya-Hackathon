# TradeConnect — Hybrid Microservice Backend

AI-powered export execution infrastructure for Indonesian SMEs (UMKM).
Closes **Gap A**: the gap between export-readiness and a successful first international deal.

## Architecture

```
                    ┌──────────────────────────────┐
                    │  NGINX / Traefik (production)│
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │   GATEWAY  :3000  (NestJS)   │
                    │   JWT  Rate-limit  Proxy     │
                    └──┬───────┬──────────┬────────┘
                       │       │          │
              ┌────────┘       ▼          ▼
              │       ┌────────────┐  ┌──────────┐
              ▼       │  Matching  │  │  Comms   │
       ┌────────────┐ │  :8001     │  │  :8002   │
       │   User     │ │  FastAPI   │  │  FastAPI │
       │  :3001     │ │  Python    │  │  Python  │
       │  NestJS    │ │  pgvector  │  │  LangChn │
       └────────────┘ └────────────┘  └──────────┘
              │            │              │
              ▼            ▼              ▼
       ┌──────────────────────────────────────┐
       │  PostgreSQL 16 + pgvector  :5432     │
       │  Redis 7                   :6379     │
       └──────────────────────────────────────┘
              ▲            ▲              ▲
              │            │              │
         ┌────┴────┐  ┌────┴─────┐   ┌────┴─────┐
         │  ETL    │  │ Embed-   │   │ Verify-  │
         │ Worker  │  │ Worker   │   │ Worker   │
         │ Celery  │  │ Celery   │   │ Celery   │
         └─────────┘  └──────────┘   └──────────┘
```

## Stack

| Layer | Tech | Why |
|-------|------|-----|
| Gateway / User / Readiness | NestJS 11 + Fastify + TypeScript 5.7 | DX, modular DI, mature ecosystem |
| ORM (NestJS) | Drizzle ORM 0.36 | TypeScript-native, fast, SQL-first, edge-ready |
| Queue (NestJS) | BullMQ via @nestjs/bullmq 11 | Robust, Redis-backed, mature |
| Logger (NestJS) | nestjs-pino | JSON-native, fast, structured |
| Testing (NestJS) | Vitest + supertest | 10x faster than Jest |
| Matching / Comms | FastAPI 0.115 + Python 3.12 | AI/ML ecosystem (sentence-transformers, LangChain) |
| Vector store | pgvector + HNSW | Single DB, no extra ops burden |
| LLM | Anthropic Claude Sonnet 4.5 | Negotiation quality, safety, structured outputs |
| Embeddings | intfloat/multilingual-e5-large | Indonesian + English, 1024-dim, SOTA cross-lingual |
| Workers | Celery 5.4 | Battle-tested Python async tasks |
| Monorepo | pnpm + Turborepo | Standard 2026 JS/TS, fast caching |
| Lint/Format | Biome 1.9 | Rust-based, 25x faster than ESLint+Prettier |
| Python lint | Ruff + MyPy strict | Standard 2026 Python toolchain |

## Quickstart (Windows 11)

```powershell
# 1. Boot infra only
pnpm docker:infra

# 2. Install Node deps for all NestJS services
pnpm install

# 3. Install Python deps for each Python service
cd services/matching-service ; uv sync ; cd ../..
cd services/comms-service ; uv sync ; cd ../..
cd services/etl-worker ; uv sync ; cd ../..

# 4. Generate JWT secret and write .env
Copy-Item .env.example .env
# Edit .env: set JWT_SECRET, ANTHROPIC_API_KEY

# 5. Apply Drizzle migrations (User Service)
cd services/user-service ; pnpm db:migrate ; cd ../..

# 6. Apply Alembic migrations (Matching Service)
cd services/matching-service ; uv run alembic upgrade head ; cd ../..

# 7. Start everything in dev mode
pnpm dev

# OR: Start full stack in Docker with latest code
pnpm docker:up
pnpm --filter gateway dev                     # only gateway
cd services/matching-service ; uv run uvicorn matching_service.main:app --reload --port 8001
```

Open:
- API Gateway docs: http://localhost:3000/docs
- Matching Service docs: http://localhost:8001/docs
- Comms Service docs: http://localhost:8002/docs
- Bull Board (queue UI): http://localhost:3000/admin/queues
- Flower (Celery monitor): http://localhost:5555

## Service Responsibilities

### Gateway (NestJS, :3000)
- JWT validation, request-ID injection, audit logging
- Tier-aware rate limiting (free vs premium)
- HTTP proxy to all downstream services
- Bull Board UI mounted at /admin/queues
- **No business logic, no DB access**

### User Service (NestJS, :3001)
- UMKM onboarding, profile, certifications
- Product catalog CRUD
- JWT issuance (login, refresh)
- BullMQ producer (verification jobs, embedding jobs)
- Drizzle ORM, multi-tenant data isolation

### Readiness Service (NestJS, :3002)
- FOB → CFR → CIF pricing (Decimal.js for precision)
- Rule-based fraud red-flag detection (FinCEN/BIS/FATF patterns)
- Document checklist & compliance

### Matching Service (FastAPI, :8001)
- HS Code classification (sentence-transformers + cosine similarity)
- pgvector ANN search (HNSW index, cosine distance)
- Buyer credibility scoring + reranking
- Human-readable Indonesian explanations

### Comms Service (FastAPI, :8002)
- Intent classification of buyer inquiries
- RAG retrieval over export knowledge base
- LLM generation with strict guardrails
- Floor price / BATNA leak prevention

### Workers (Python Celery)
- **embedding-worker**: sentence-transformers, async embedding upsert
- **verification-worker**: OSS RBA, INATRADE NIB verification
- **etl-worker**: UN Comtrade, BPS data ingestion

## Security boundaries (non-negotiable)

- `hpp` and `floor_price` **never** appear in any API response or LLM prompt
- Every inter-service request carries `x-user-id`, `x-tenant-id`, `x-request-id`
- `GuardrailEngine.validate()` runs on every LLM output before return
- All synthetic buyers flagged `is_synthetic = true` and UI must label them

## Development phases

- **Phase 1** (week 1-2): Monorepo, Docker, User Service CRUD, pgvector init
- **Phase 2** (week 2-3): HS Classifier, ANN matching, FOB/CIF, RAG draft
- **Phase 3** (week 3): Full integration, demo seeding, polish

## License

Proprietary — TradeConnect / Lomba Uhuy team.
