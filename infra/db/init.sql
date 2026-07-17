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

-- ──────────── External trade data normalized by ETL workers ────────────
CREATE TABLE IF NOT EXISTS trade_flows (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source            VARCHAR(32) NOT NULL,
    hs_code           VARCHAR(16) NOT NULL,
    reporter_code     VARCHAR(16),
    reporter_iso      VARCHAR(8),
    reporter_name     VARCHAR(255),
    partner_code      VARCHAR(16),
    partner_iso       VARCHAR(8),
    partner_name      VARCHAR(255),
    partner2_code     VARCHAR(16),
    partner2_iso      VARCHAR(8),
    partner2_name     VARCHAR(255),
    flow_code         VARCHAR(16),
    flow_name         VARCHAR(64),
    customs_code      VARCHAR(16),
    customs_name      VARCHAR(255),
    transport_mode_code VARCHAR(16),
    transport_mode_name VARCHAR(255),
    period            INTEGER,
    trade_value_usd   NUMERIC(18, 2),
    net_weight_kg     NUMERIC(18, 3),
    quantity          NUMERIC(18, 3),
    quantity_unit     VARCHAR(64),
    raw_json          JSONB NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(
        source, hs_code, reporter_code, partner_code, partner2_code,
        flow_code, customs_code, transport_mode_code, period
    )
);

CREATE INDEX IF NOT EXISTS idx_trade_flows_source_period ON trade_flows(source, period);
CREATE INDEX IF NOT EXISTS idx_trade_flows_hs_code       ON trade_flows(hs_code);
CREATE INDEX IF NOT EXISTS idx_trade_flows_reporter      ON trade_flows(reporter_code);

CREATE TABLE IF NOT EXISTS bps_trade_data (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dataset_id         VARCHAR(128) NOT NULL,
    period             VARCHAR(64),
    region_code        VARCHAR(64),
    region_name        VARCHAR(255),
    commodity_code     VARCHAR(64),
    commodity_name     VARCHAR(255),
    flow_code          VARCHAR(16),
    flow_name          VARCHAR(64),
    country_name       VARCHAR(255),
    port_name          VARCHAR(255),
    value              NUMERIC(18, 3),
    net_weight_kg      NUMERIC(18, 3),
    unit               VARCHAR(64),
    raw_json           JSONB NOT NULL DEFAULT '{}',
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    updated_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bps_trade_dataset  ON bps_trade_data(dataset_id);
CREATE INDEX IF NOT EXISTS idx_bps_trade_period   ON bps_trade_data(period);
CREATE INDEX IF NOT EXISTS idx_bps_trade_flow     ON bps_trade_data(flow_code);
CREATE INDEX IF NOT EXISTS idx_bps_trade_country  ON bps_trade_data(country_name);

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

-- ──────────── Deal / negotiation lifecycle (M4) ────────────
-- FKs to umkm/product are added at runtime by the app layer (those tables are
-- created by the user-service). Kept FK-free here so first-boot init never fails.
DO $$ BEGIN
  CREATE TYPE deal_status AS ENUM ('contacted','negotiating','compliance','po_sent','po_signed','closed');
EXCEPTION WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS deal (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    umkm_id       UUID NOT NULL,
    product_id    UUID,
    buyer_id      UUID,
    buyer_name    VARCHAR(255),
    buyer_country VARCHAR(64),
    status        deal_status NOT NULL DEFAULT 'contacted',
    agreed_price  NUMERIC(12,4),
    last_message  TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS deal_umkm_status_idx ON deal(umkm_id, status);

-- ──────────── Reminders (M7) ────────────
CREATE TABLE IF NOT EXISTS reminder (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID NOT NULL,
    title      VARCHAR(255) NOT NULL,
    remind_at  TIMESTAMPTZ NOT NULL,
    type       VARCHAR(64) NOT NULL DEFAULT 'general',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS reminder_user_idx ON reminder(user_id, remind_at);

-- Compatibility views for early planning docs that used plural/profile names.
CREATE OR REPLACE VIEW umkm_profiles AS SELECT * FROM umkm;
CREATE OR REPLACE VIEW products AS SELECT * FROM product;
CREATE OR REPLACE VIEW buyers AS SELECT * FROM buyer;
CREATE OR REPLACE VIEW embeddings AS
    SELECT
        id,
        buyer_id AS owner_id,
        'buyer'::TEXT AS owner_type,
        model,
        embedding,
        created_at,
        updated_at
    FROM buyer_embedding
    UNION ALL
    SELECT
        id,
        product_id AS owner_id,
        'product'::TEXT AS owner_type,
        model,
        embedding,
        created_at,
        updated_at
    FROM product_embedding;