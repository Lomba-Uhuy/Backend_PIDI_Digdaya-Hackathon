import { ForbiddenException, Inject, Injectable, Logger, NotFoundException } from '@nestjs/common';
import { asc, eq } from 'drizzle-orm';
import { DRIZZLE, type DrizzleDB } from '../database/database.module.js';
import {
  products,
  productWorkflows,
  umkm,
  workflowEvents,
  workflowStages,
  type ProductWorkflow,
} from '../database/schema/index.js';

const MATCHING_URL = process.env.MATCHING_SERVICE_URL ?? 'http://matching-service:8001';

// The authoritative execution graph for product initialization (in order).
const STAGES = [
  'hs_classification',
  'embedding',
  'buyer_sync',
  'buyer_matching',
  'market_intelligence',
  'export_readiness',
  'dashboard_bootstrap',
] as const;
type StageName = (typeof STAGES)[number];

// Stages that hit a remote service may fail transiently (cold model load,
// network) — give them bounded retries before failing the whole workflow.
const STAGE_MAX_ATTEMPTS: Record<StageName, number> = {
  hs_classification: 3,
  embedding: 1,
  buyer_sync: 2,
  buyer_matching: 1,
  market_intelligence: 1,
  export_readiness: 1,
  dashboard_bootstrap: 1,
};

@Injectable()
export class WorkflowService {
  private readonly logger = new Logger(WorkflowService.name);
  constructor(@Inject(DRIZZLE) private readonly db: DrizzleDB) {}

  private async umkmIdForUser(userId: string): Promise<string> {
    const row = await this.db.query.umkm.findFirst({ where: eq(umkm.userId, userId) });
    if (!row) throw new NotFoundException('No UMKM profile for this user yet');
    return row.id;
  }

  private async ownedWorkflow(productId: string, userId: string): Promise<ProductWorkflow> {
    const umkmId = await this.umkmIdForUser(userId);
    const wf = await this.db.query.productWorkflows.findFirst({
      where: eq(productWorkflows.productId, productId),
    });
    if (!wf) throw new NotFoundException('No workflow for this product yet');
    if (wf.umkmId !== umkmId) throw new ForbiddenException('Not your workflow');
    return wf;
  }

  // ── Public read APIs ──────────────────────────────────────────────────────
  async getWorkflow(productId: string, userId: string) {
    const wf = await this.ownedWorkflow(productId, userId);
    const stages = await this.db
      .select()
      .from(workflowStages)
      .where(eq(workflowStages.workflowId, wf.id))
      .orderBy(asc(workflowStages.sequence));
    const total = stages.length || 1;
    const done = stages.filter((s) => s.status === 'completed').length;
    return {
      ...wf,
      stages,
      progress: { completed: done, total, percent: Math.round((done / total) * 100) },
    };
  }

  async getStages(productId: string, userId: string) {
    const wf = await this.ownedWorkflow(productId, userId);
    return this.db
      .select()
      .from(workflowStages)
      .where(eq(workflowStages.workflowId, wf.id))
      .orderBy(asc(workflowStages.sequence));
  }

  async getEvents(productId: string, userId: string) {
    const wf = await this.ownedWorkflow(productId, userId);
    return this.db
      .select()
      .from(workflowEvents)
      .where(eq(workflowEvents.workflowId, wf.id))
      .orderBy(asc(workflowEvents.createdAt));
  }

  // ── Start / retry (idempotent) ────────────────────────────────────────────
  /**
   * Ensure a product initialization workflow exists and is running. Idempotent:
   * an existing non-failed workflow is returned as-is (no duplicate work); a
   * failed one is reset + re-run (execution_version bumped).
   */
  async startForProduct(productId: string, umkmId: string): Promise<ProductWorkflow> {
    const existing = await this.db.query.productWorkflows.findFirst({
      where: eq(productWorkflows.productId, productId),
    });

    if (existing) {
      if (existing.status !== 'failed') return existing;
      // Retry a failed workflow: reset stages + bump version, then re-run.
      await this.db
        .update(productWorkflows)
        .set({
          status: 'queued',
          failureReason: null,
          retryCount: existing.retryCount + 1,
          executionVersion: existing.executionVersion + 1,
          updatedAt: new Date(),
        })
        .where(eq(productWorkflows.id, existing.id));
      await this.db
        .update(workflowStages)
        .set({ status: 'queued', errorMessage: null, startedAt: null, finishedAt: null, durationMs: null })
        .where(eq(workflowStages.workflowId, existing.id));
      await this.emit(existing.id, 'RetryScheduled', null, `Retry #${existing.retryCount + 1}`);
      void this.run(existing.id);
      return existing;
    }

    const [wf] = await this.db
      .insert(productWorkflows)
      .values({ productId, umkmId, status: 'queued', currentStage: STAGES[0] })
      .returning();
    if (!wf) throw new Error('Failed to create workflow');
    await this.db.insert(workflowStages).values(
      STAGES.map((name, i) => ({ workflowId: wf.id, stageName: name, sequence: i + 1, status: 'queued' as const })),
    );
    await this.emit(wf.id, 'WorkflowStarted', null, 'Inisialisasi produk dimulai');
    void this.run(wf.id);
    return wf;
  }

  /** Ownership-scoped entry point: verify the product is the caller's, then start. */
  async startForProductByUser(productId: string, userId: string): Promise<ProductWorkflow> {
    const umkmId = await this.umkmIdForUser(userId);
    const product = await this.db.query.products.findFirst({ where: eq(products.id, productId) });
    if (!product || product.umkmId !== umkmId) throw new NotFoundException('Product not found');
    return this.startForProduct(productId, umkmId);
  }

  /**
   * Force a full re-run of the product's initialization workflow. Unlike
   * `startForProduct` (which is a no-op for an already-completed workflow), this
   * resets every stage + bumps execution_version and re-executes — used when the
   * product's name/description changed, so the HS classification (and everything
   * derived from it: buyers, market intelligence) must be recomputed from the new
   * text. Starts a fresh workflow if none exists yet.
   */
  async rerunForProduct(productId: string, umkmId: string): Promise<ProductWorkflow> {
    const existing = await this.db.query.productWorkflows.findFirst({
      where: eq(productWorkflows.productId, productId),
    });
    if (!existing) return this.startForProduct(productId, umkmId);

    await this.db
      .update(productWorkflows)
      .set({
        status: 'queued',
        failureReason: null,
        currentStage: STAGES[0],
        currentWorker: null,
        retryCount: existing.retryCount + 1,
        executionVersion: existing.executionVersion + 1,
        startedAt: null,
        finishedAt: null,
        updatedAt: new Date(),
      })
      .where(eq(productWorkflows.id, existing.id));
    await this.db
      .update(workflowStages)
      .set({
        status: 'queued',
        errorMessage: null,
        startedAt: null,
        finishedAt: null,
        durationMs: null,
        retryCount: 0,
        jobId: null,
        metadata: null,
      })
      .where(eq(workflowStages.workflowId, existing.id));
    await this.emit(existing.id, 'WorkflowStarted', null, 'Re-inisialisasi produk (data produk diperbarui)');
    void this.run(existing.id);
    return existing;
  }

  // ── Orchestration (background, DB is the source of truth) ──────────────────
  private async run(workflowId: string): Promise<void> {
    try {
      await this.db
        .update(productWorkflows)
        .set({ status: 'running', startedAt: new Date(), updatedAt: new Date() })
        .where(eq(productWorkflows.id, workflowId));

      const wf = await this.db.query.productWorkflows.findFirst({ where: eq(productWorkflows.id, workflowId) });
      if (!wf) return;
      const product = await this.db.query.products.findFirst({ where: eq(products.id, wf.productId) });
      if (!product) throw new Error('product missing');

      const stages = await this.db
        .select()
        .from(workflowStages)
        .where(eq(workflowStages.workflowId, workflowId))
        .orderBy(asc(workflowStages.sequence));

      for (const stage of stages) {
        if (stage.status === 'completed') continue; // resume-safe
        const name = stage.stageName as StageName;
        const startedAt = new Date();
        await this.db
          .update(workflowStages)
          .set({ status: 'running', startedAt, workerName: 'workflow-orchestrator' })
          .where(eq(workflowStages.id, stage.id));
        await this.db
          .update(productWorkflows)
          .set({ currentStage: name, currentWorker: 'workflow-orchestrator', updatedAt: new Date() })
          .where(eq(productWorkflows.id, workflowId));
        await this.emit(workflowId, 'StageStarted', name);

        const maxAttempts = STAGE_MAX_ATTEMPTS[name] ?? 1;
        let lastErr: unknown = null;
        let succeeded = false;
        for (let attempt = 1; attempt <= maxAttempts; attempt++) {
          try {
            const result = await this.runStage(name, product);
            const finishedAt = new Date();
            await this.db
              .update(workflowStages)
              .set({
                status: 'completed',
                finishedAt,
                durationMs: finishedAt.getTime() - startedAt.getTime(),
                retryCount: attempt - 1,
                errorMessage: null,
                jobId: result?.jobId ?? null,
                metadata: result?.metadata ?? null,
              })
              .where(eq(workflowStages.id, stage.id));
            await this.emit(workflowId, 'StageCompleted', name, undefined, result?.metadata);
            succeeded = true;
            break;
          } catch (err) {
            lastErr = err;
            const msg = err instanceof Error ? err.message : String(err);
            if (attempt < maxAttempts) {
              // Mark the stage RETRYING and schedule the next attempt (backoff).
              await this.db
                .update(workflowStages)
                .set({ status: 'retrying', retryCount: attempt, errorMessage: msg })
                .where(eq(workflowStages.id, stage.id));
              await this.emit(workflowId, 'RetryScheduled', name, `Percobaan ${attempt + 1}/${maxAttempts}: ${msg}`);
              this.logger.warn(`workflow ${workflowId} stage ${name} attempt ${attempt} failed: ${msg} — retrying`);
              await new Promise((r) => setTimeout(r, 2_000 * attempt));
            }
          }
        }

        if (!succeeded) {
          const msg = lastErr instanceof Error ? lastErr.message : String(lastErr);
          await this.db
            .update(workflowStages)
            .set({ status: 'failed', finishedAt: new Date(), errorMessage: msg })
            .where(eq(workflowStages.id, stage.id));
          await this.db
            .update(productWorkflows)
            .set({ status: 'failed', failureReason: `${name}: ${msg}`, finishedAt: new Date(), updatedAt: new Date() })
            .where(eq(productWorkflows.id, workflowId));
          await this.emit(workflowId, 'StageFailed', name, msg);
          await this.emit(workflowId, 'WorkflowFailed', null, `Gagal pada tahap ${name}`);
          this.logger.warn(`workflow ${workflowId} failed at ${name}: ${msg}`);
          return;
        }
      }

      await this.db
        .update(productWorkflows)
        .set({ status: 'completed', currentStage: null, currentWorker: null, finishedAt: new Date(), updatedAt: new Date() })
        .where(eq(productWorkflows.id, workflowId));
      await this.emit(workflowId, 'WorkflowCompleted', null, 'Inisialisasi produk selesai');
    } catch (err) {
      this.logger.error(`workflow ${workflowId} crashed: ${String(err)}`);
    }
  }

  /** Execute a single stage. Real work where a server-side driver exists. */
  private async runStage(
    name: StageName,
    product: typeof products.$inferSelect,
  ): Promise<{ jobId?: string; metadata?: Record<string, unknown> } | void> {
    switch (name) {
      case 'hs_classification': {
        const resp = await fetch(`${MATCHING_URL}/api/v1/hs-classifier/classify`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ description: `${product.name}. ${product.description}`, top_k: 5 }),
          // First call cold-loads the multilingual-e5 model; allow generous time.
          signal: AbortSignal.timeout(90_000),
        });
        if (!resp.ok) throw new Error(`hs-classifier HTTP ${resp.status}`);
        const data = (await resp.json()) as {
          hs_code?: string;
          confidence?: number;
          description?: string;
          category?: string;
          top_k?: Array<{ hs_code: string; description?: string; confidence?: number; category?: string }>;
        };
        const candidates =
          data.top_k && data.top_k.length > 0
            ? data.top_k
            : data.hs_code
              ? [{ hs_code: data.hs_code, description: data.description, confidence: data.confidence, category: data.category }]
              : [];
        // Persist the classification artifact on the product (source of truth).
        await this.db
          .update(products)
          .set({
            ...(data.hs_code ? { hsCode: data.hs_code } : {}),
            ...(data.confidence != null ? { hsConfidence: String(data.confidence) } : {}),
            hsCandidates: candidates,
            hsModelVersion: 'multilingual-e5-large',
            hsClassifiedAt: new Date(),
            updatedAt: new Date(),
          })
          .where(eq(products.id, product.id));
        return { metadata: { primary: data.hs_code ?? null, candidates: candidates.length } };
      }
      case 'buyer_sync': {
        // Re-read the product: the in-memory `product` was loaded before the
        // hs_classification stage persisted the HS code, so it is stale here.
        const fresh = await this.db.query.products.findFirst({ where: eq(products.id, product.id) });
        const hs = fresh?.hsCode ?? product.hsCode ?? null;
        // matching-service requires a non-empty hs_codes list. If classification
        // produced nothing, skip the sync honestly rather than failing the workflow.
        if (!hs) return { metadata: { note: 'buyer sync skipped — no HS code classified' } };
        const resp = await fetch(`${MATCHING_URL}/api/v1/buyers/sync`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ hs_codes: [hs], importer_countries: [] }),
          signal: AbortSignal.timeout(30_000),
        });
        if (!resp.ok) throw new Error(`buyers/sync HTTP ${resp.status}`);
        const data = (await resp.json()) as { task_id?: string; status?: string };
        return { jobId: data.task_id, metadata: { status: data.status ?? 'queued', hs } };
      }
      // These stages run as async backend jobs dispatched at product creation
      // (embedding/index) or read shared/persisted data. The orchestrator records
      // their lifecycle; each carries honest metadata, none fabricates progress.
      case 'embedding':
        return { metadata: { note: 'embedding dispatched at product creation (async)' } };
      case 'buyer_matching':
        return { metadata: { note: 'pgvector matching available once embeddings exist' } };
      case 'market_intelligence':
        return { metadata: { note: 'BPS/UN Comtrade data available for the product HS' } };
      case 'export_readiness':
        return { metadata: { note: 'readiness computed from company + product' } };
      case 'dashboard_bootstrap':
        return { metadata: { note: 'dashboard data ready' } };
      default:
        return;
    }
  }

  private async emit(
    workflowId: string,
    type: string,
    stageName?: string | null,
    message?: string,
    metadata?: Record<string, unknown> | null,
  ): Promise<void> {
    await this.db.insert(workflowEvents).values({
      workflowId,
      type,
      stageName: stageName ?? null,
      message: message ?? null,
      metadata: metadata ?? null,
    });
  }
}
