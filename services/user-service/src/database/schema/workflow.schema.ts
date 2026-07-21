import {
  pgTable, uuid, varchar, integer, text, timestamp, pgEnum, jsonb, index,
} from 'drizzle-orm/pg-core';
import { products } from './product.schema';

export const workflowStatusEnum = pgEnum('workflow_status', [
  'queued',
  'running',
  'completed',
  'failed',
]);

export const stageStatusEnum = pgEnum('workflow_stage_status', [
  'queued',
  'running',
  'completed',
  'failed',
  'retrying',
  'skipped',
]);

// One initialization workflow per product (unique product_id → idempotent).
export const productWorkflows = pgTable('product_workflow', {
  id:               uuid('id').primaryKey().defaultRandom(),
  productId:        uuid('product_id').notNull().unique().references(() => products.id, { onDelete: 'cascade' }),
  umkmId:           uuid('umkm_id').notNull(),
  workflowType:     varchar('workflow_type', { length: 48 }).notNull().default('product_initialization'),
  status:           workflowStatusEnum('status').notNull().default('queued'),
  currentStage:     varchar('current_stage', { length: 48 }),
  retryCount:       integer('retry_count').notNull().default(0),
  failureReason:    text('failure_reason'),
  currentWorker:    varchar('current_worker', { length: 64 }),
  executionVersion: integer('execution_version').notNull().default(1),
  startedAt:        timestamp('started_at', { withTimezone: true }),
  finishedAt:       timestamp('finished_at', { withTimezone: true }),
  createdAt:        timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  updatedAt:        timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
});

export const workflowStages = pgTable(
  'workflow_stage',
  {
    id:           uuid('id').primaryKey().defaultRandom(),
    workflowId:   uuid('workflow_id').notNull().references(() => productWorkflows.id, { onDelete: 'cascade' }),
    stageName:    varchar('stage_name', { length: 48 }).notNull(),
    sequence:     integer('sequence').notNull(),
    status:       stageStatusEnum('status').notNull().default('queued'),
    workerName:   varchar('worker_name', { length: 64 }),
    jobId:        varchar('job_id', { length: 128 }),
    retryCount:   integer('retry_count').notNull().default(0),
    durationMs:   integer('duration_ms'),
    errorMessage: text('error_message'),
    metadata:     jsonb('metadata'),
    startedAt:    timestamp('started_at', { withTimezone: true }),
    finishedAt:   timestamp('finished_at', { withTimezone: true }),
  },
  (t) => ({ wfIdx: index('workflow_stage_wf_idx').on(t.workflowId, t.sequence) }),
);

export const workflowEvents = pgTable(
  'workflow_event',
  {
    id:         uuid('id').primaryKey().defaultRandom(),
    workflowId: uuid('workflow_id').notNull().references(() => productWorkflows.id, { onDelete: 'cascade' }),
    type:       varchar('type', { length: 48 }).notNull(),
    stageName:  varchar('stage_name', { length: 48 }),
    message:    text('message'),
    metadata:   jsonb('metadata'),
    createdAt:  timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => ({ evIdx: index('workflow_event_wf_idx').on(t.workflowId, t.createdAt) }),
);

export type ProductWorkflow = typeof productWorkflows.$inferSelect;
export type WorkflowStage = typeof workflowStages.$inferSelect;
export type WorkflowEvent = typeof workflowEvents.$inferSelect;
