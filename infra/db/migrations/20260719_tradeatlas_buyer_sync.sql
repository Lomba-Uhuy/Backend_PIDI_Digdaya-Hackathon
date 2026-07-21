-- ============================================================================
-- TradeAtlas buyer synchronisation — schema additions
-- Idempotent (safe to run on fresh or existing databases).
-- Apply to an existing DB (PowerShell):
--   Get-Content infra/db/migrations/20260719_tradeatlas_buyer_sync.sql |
--     docker compose exec -T postgres psql -U tc_user -d tradeconnect
-- (Also folded into infra/db/init.sql for fresh installs.)
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Canonical dedup key for externally-sourced buyers: (metadata.source, metadata.source_id).
-- Enables idempotent upserts keyed on importerUrlCode; never dedup by name.
CREATE UNIQUE INDEX IF NOT EXISTS uq_buyer_source_identity
    ON buyer ((metadata ->> 'source'), (metadata ->> 'source_id'))
    WHERE metadata ->> 'source_id' IS NOT NULL;

-- Fast lookup of real (non-synthetic) buyers by source.
CREATE INDEX IF NOT EXISTS idx_buyer_source
    ON buyer ((metadata ->> 'source'));

-- Synchronisation history / resumable checkpoints.
CREATE TABLE IF NOT EXISTS buyer_sync_run (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider         VARCHAR(64)  NOT NULL,
    params           JSONB        NOT NULL DEFAULT '{}',
    status           VARCHAR(24)  NOT NULL DEFAULT 'running', -- running|completed|failed|auth_required
    last_page        INTEGER      NOT NULL DEFAULT 0,         -- checkpoint (resume-from)
    total_pages      INTEGER      NOT NULL DEFAULT 0,
    shipments_seen   INTEGER      NOT NULL DEFAULT 0,
    buyers_upserted  INTEGER      NOT NULL DEFAULT 0,
    buyers_skipped   INTEGER      NOT NULL DEFAULT 0,
    error            TEXT,
    started_at       TIMESTAMPTZ  DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  DEFAULT NOW(),
    finished_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_buyer_sync_run_status  ON buyer_sync_run(status);
CREATE INDEX IF NOT EXISTS idx_buyer_sync_run_started ON buyer_sync_run(started_at DESC);
