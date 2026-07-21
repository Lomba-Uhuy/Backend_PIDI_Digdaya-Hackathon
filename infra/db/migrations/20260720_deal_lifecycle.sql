-- Deal lifecycle backend: negotiation thread, purchase order, compliance checks.
-- Idempotent; safe to re-run. Applied to already-running DBs (init.sql covers fresh).

-- ── Phase 1: negotiation thread ──────────────────────────────────────────────
DO $$ BEGIN
  CREATE TYPE deal_message_sender AS ENUM ('umkm','buyer','system');
EXCEPTION WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS deal_message (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deal_id    UUID NOT NULL REFERENCES deal(id) ON DELETE CASCADE,
    sender     deal_message_sender NOT NULL,
    text       TEXT NOT NULL,
    intent     VARCHAR(32),
    meta       JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS deal_message_deal_created_idx ON deal_message(deal_id, created_at);

-- ── Phase 3: purchase orders ─────────────────────────────────────────────────
DO $$ BEGIN
  CREATE TYPE po_status AS ENUM ('draft','sent','signed');
EXCEPTION WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS purchase_order (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deal_id       UUID NOT NULL UNIQUE REFERENCES deal(id) ON DELETE CASCADE,
    po_number     VARCHAR(40) NOT NULL,
    product_id    UUID,
    product_name  VARCHAR(255),
    buyer_name    VARCHAR(255),
    buyer_country VARCHAR(64),
    incoterm      VARCHAR(16) NOT NULL DEFAULT 'CIF',
    unit_price    NUMERIC(18,4) NOT NULL,
    qty           INTEGER NOT NULL DEFAULT 1,
    currency      VARCHAR(8) NOT NULL DEFAULT 'USD',
    subtotal      NUMERIC(18,4) NOT NULL,
    payment_terms VARCHAR(255) NOT NULL DEFAULT '30% DP / 70% L/C',
    status        po_status NOT NULL DEFAULT 'draft',
    signed_by     VARCHAR(255),
    signature     TEXT,
    signed_at     TIMESTAMPTZ,
    terms         JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Phase 4: compliance checks ───────────────────────────────────────────────
DO $$ BEGIN
  CREATE TYPE compliance_kind AS ENUM ('nib','fraud_scan','document');
EXCEPTION WHEN duplicate_object THEN null;
END $$;
DO $$ BEGIN
  CREATE TYPE compliance_status AS ENUM ('pass','warn','fail');
EXCEPTION WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS compliance_check (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deal_id    UUID NOT NULL REFERENCES deal(id) ON DELETE CASCADE,
    kind       compliance_kind NOT NULL,
    label      VARCHAR(160) NOT NULL,
    status     compliance_status NOT NULL,
    detail     JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS compliance_check_deal_idx ON compliance_check(deal_id, created_at);
