-- Product initialization workflow engine: workflows, stages, events. Idempotent.
DO $$ BEGIN CREATE TYPE workflow_status AS ENUM ('queued','running','completed','failed'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE workflow_stage_status AS ENUM ('queued','running','completed','failed','retrying','skipped'); EXCEPTION WHEN duplicate_object THEN null; END $$;

CREATE TABLE IF NOT EXISTS product_workflow (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id        UUID NOT NULL UNIQUE REFERENCES product(id) ON DELETE CASCADE,
    umkm_id           UUID NOT NULL,
    workflow_type     VARCHAR(48) NOT NULL DEFAULT 'product_initialization',
    status            workflow_status NOT NULL DEFAULT 'queued',
    current_stage     VARCHAR(48),
    retry_count       INTEGER NOT NULL DEFAULT 0,
    failure_reason    TEXT,
    current_worker    VARCHAR(64),
    execution_version INTEGER NOT NULL DEFAULT 1,
    started_at        TIMESTAMPTZ,
    finished_at       TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workflow_stage (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id   UUID NOT NULL REFERENCES product_workflow(id) ON DELETE CASCADE,
    stage_name    VARCHAR(48) NOT NULL,
    sequence      INTEGER NOT NULL,
    status        workflow_stage_status NOT NULL DEFAULT 'queued',
    worker_name   VARCHAR(64),
    job_id        VARCHAR(128),
    retry_count   INTEGER NOT NULL DEFAULT 0,
    duration_ms   INTEGER,
    error_message TEXT,
    metadata      JSONB,
    started_at    TIMESTAMPTZ,
    finished_at   TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS workflow_stage_wf_idx ON workflow_stage(workflow_id, sequence);

CREATE TABLE IF NOT EXISTS workflow_event (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID NOT NULL REFERENCES product_workflow(id) ON DELETE CASCADE,
    type        VARCHAR(48) NOT NULL,
    stage_name  VARCHAR(48),
    message     TEXT,
    metadata    JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS workflow_event_wf_idx ON workflow_event(workflow_id, created_at);
