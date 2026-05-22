-- ============================================================
-- TradeConnect — Database initialization
-- Executed once when postgres container starts with empty volume.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- ──────────── Buyer (seeded by ETL or synthetic generator) ────────────
CREATE TABLE IF NOT EXISTS buyer (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                VARCHAR(255) NOT NULL,
    country             CHAR(2)      NOT NULL,
    hs_codes            TEXT[]       DEFAULT '{}',
    credibility_score   DECIMAL(4,3) DEFAULT 0.0,
    min_order_qty       INTEGER      DEFAULT 1,
    description         TEXT,
    is_active           BOOLEAN      DEFAULT TRUE,
    is_synthetic        BOOLEAN      DEFAULT FALSE,
    metadata            JSONB        DEFAULT '{}',
    created_at          TIMESTAMPTZ  DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_buyer_country     ON buyer(country);
CREATE INDEX IF NOT EXISTS idx_buyer_credibility ON buyer(credibility_score DESC);
CREATE INDEX IF NOT EXISTS idx_buyer_hs_codes    ON buyer USING GIN(hs_codes);
CREATE INDEX IF NOT EXISTS idx_buyer_synthetic   ON buyer(is_synthetic);

-- ──────────── Embedding tables (1024-dim for e5-large) ────────────
CREATE TABLE IF NOT EXISTS buyer_embedding (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    buyer_id    UUID NOT NULL REFERENCES buyer(id) ON DELETE CASCADE,
    model       VARCHAR(64) NOT NULL,
    embedding   vector(1024),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(buyer_id)
);

CREATE TABLE IF NOT EXISTS product_embedding (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id  UUID NOT NULL,
    model       VARCHAR(64) NOT NULL,
    embedding   vector(1024),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(product_id)
);

-- ──────────── Knowledge base for RAG ────────────
CREATE TABLE IF NOT EXISTS export_knowledge_base (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title       VARCHAR(255) NOT NULL,
    content     TEXT NOT NULL,
    category    VARCHAR(50) NOT NULL,
    source      VARCHAR(255),
    embedding   vector(1024),
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ekb_category ON export_knowledge_base(category);

-- ──────────── Audit log ────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id            BIGSERIAL PRIMARY KEY,
    request_id    UUID,
    user_id       UUID,
    tenant_id     UUID,
    action        VARCHAR(64) NOT NULL,
    resource      VARCHAR(128),
    resource_id   VARCHAR(128),
    metadata      JSONB DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_user      ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_tenant    ON audit_log(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_created   ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_request   ON audit_log(request_id);

-- NOTE: HNSW indexes on vector columns are created via migrations
-- (NOT here) once we have >=100 records, so the index is meaningful.
-- See services/matching-service/alembic/versions/0002_hnsw_indexes.py