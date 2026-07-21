-- Persist RAG HS classification on the product (source of truth; no client cache).
-- Idempotent; safe to re-run.
ALTER TABLE product ADD COLUMN IF NOT EXISTS hs_candidates    JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE product ADD COLUMN IF NOT EXISTS hs_model_version VARCHAR(64);
ALTER TABLE product ADD COLUMN IF NOT EXISTS hs_classified_at TIMESTAMPTZ;
