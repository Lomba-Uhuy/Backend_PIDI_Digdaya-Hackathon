import { BadRequestException, ConflictException, Inject, Injectable, NotFoundException } from '@nestjs/common';
import * as bcrypt from 'bcrypt';
import { eq, sql } from 'drizzle-orm';
import { DRIZZLE, type DrizzleDB } from '../database/database.module.js';
import { users, subscriptions, productWorkflows } from '../database/schema/index.js';
import { isRole, PLANS, resolveEntitlements } from '../authz/plan-config.js';
import { WorkflowService } from '../workflow/workflow.service.js';
import { AuditService, type AuditActor } from './audit.service.js';

type Row = Record<string, unknown>;
const rows = <T = Row>(r: unknown): T[] => r as unknown as T[];

const MATCHING_URL = process.env.MATCHING_SERVICE_URL ?? 'http://matching-service:8001';
const COMMS_URL = process.env.COMMS_SERVICE_URL ?? 'http://comms-service:8002';
const READINESS_URL = process.env.READINESS_SERVICE_URL ?? 'http://readiness-service:3002';

@Injectable()
export class AdminService {
  constructor(
    @Inject(DRIZZLE) private readonly db: DrizzleDB,
    private readonly workflow: WorkflowService,
    private readonly audit: AuditService,
  ) {}

  // ── Dashboard metrics (all real; OCR reported as unavailable, not faked) ─────
  async metrics() {
    const [counts] = rows<Row>(
      await this.db.execute(sql`
        SELECT
          (SELECT count(*) FROM users)::int AS users_total,
          (SELECT count(*) FROM users WHERE is_active)::int AS users_active,
          (SELECT count(*) FROM users WHERE last_login_at > now() - interval '30 days')::int AS users_active_30d,
          (SELECT count(*) FROM umkm)::int AS companies,
          (SELECT count(*) FROM product)::int AS products,
          (SELECT count(*) FROM deal)::int AS deals`),
    );

    const wf = rows<{ status: string; n: number }>(
      await this.db.execute(sql`SELECT status, count(*)::int AS n FROM product_workflow GROUP BY status`),
    );
    const wfByStatus: Record<string, number> = { queued: 0, running: 0, completed: 0, failed: 0 };
    for (const r of wf) wfByStatus[r.status] = r.n;

    const [dur] = rows<{ avg_ms: number | null }>(
      await this.db.execute(sql`
        SELECT avg(extract(epoch FROM (finished_at - started_at)) * 1000)::int AS avg_ms
        FROM product_workflow WHERE status='completed' AND finished_at IS NOT NULL AND started_at IS NOT NULL`),
    );

    const completed = wfByStatus.completed ?? 0;
    const failed = wfByStatus.failed ?? 0;
    const successRate = completed + failed > 0 ? Math.round((completed / (completed + failed)) * 100) : null;

    const plans = rows<{ plan: string; n: number }>(
      await this.db.execute(sql`SELECT plan, count(*)::int AS n FROM subscription GROUP BY plan`),
    );

    const recentErrors = rows<Row>(
      await this.db.execute(sql`
        SELECT e.id, e.type, e.stage_name, e.message, e.created_at, w.product_id
        FROM workflow_event e JOIN product_workflow w ON w.id = e.workflow_id
        WHERE e.type IN ('StageFailed','WorkflowFailed')
        ORDER BY e.created_at DESC LIMIT 10`),
    );

    return {
      users: { total: counts?.users_total ?? 0, active: counts?.users_active ?? 0, active30d: counts?.users_active_30d ?? 0 },
      companies: counts?.companies ?? 0,
      products: counts?.products ?? 0,
      deals: counts?.deals ?? 0,
      workflows: {
        ...wfByStatus,
        total: (wfByStatus.queued ?? 0) + (wfByStatus.running ?? 0) + completed + failed,
        avgDurationMs: dur?.avg_ms ?? null,
        successRate,
      },
      // OCR module is not deployed yet — report honestly instead of fabricating.
      ocr: { available: false, queued: 0, completed: 0, failed: 0 },
      subscriptionDistribution: plans,
      recentErrors,
    };
  }

  // ── Users (list + detail), cross-tenant ──────────────────────────────────────
  async listUsers(opts: { search?: string; page?: number; limit?: number; role?: string; status?: string }) {
    const limit = Math.min(Math.max(opts.limit ?? 20, 1), 100);
    const page = Math.max(opts.page ?? 1, 1);
    const offset = (page - 1) * limit;
    const search = opts.search ? `%${opts.search.toLowerCase()}%` : null;

    const conds = [sql`TRUE`];
    if (search) conds.push(sql`(lower(u.email) LIKE ${search} OR lower(coalesce(m.legal_name,'')) LIKE ${search})`);
    if (opts.role) conds.push(sql`u.role = ${opts.role}`);
    if (opts.status === 'active') conds.push(sql`u.is_active = true`);
    if (opts.status === 'inactive') conds.push(sql`u.is_active = false`);
    const where = sql.join(conds, sql` AND `);

    const items = rows<Row>(
      await this.db.execute(sql`
        SELECT u.id, u.email, u.role, u.is_active, u.last_login_at, u.created_at,
               coalesce(s.plan,'free') AS plan, coalesce(s.status,'active') AS sub_status,
               m.id AS umkm_id, m.legal_name, m.nib,
               (SELECT count(*)::int FROM product p WHERE p.umkm_id = m.id) AS products,
               (SELECT status FROM product_workflow w JOIN product p ON p.id=w.product_id WHERE p.umkm_id=m.id ORDER BY w.updated_at DESC LIMIT 1) AS workflow_status
        FROM users u
        LEFT JOIN subscription s ON s.user_id = u.id
        LEFT JOIN umkm m ON m.user_id = u.id
        WHERE ${where}
        ORDER BY u.created_at DESC
        LIMIT ${limit} OFFSET ${offset}`),
    );
    const countRows = rows<{ count: number }>(
      await this.db.execute(sql`SELECT count(*)::int AS count FROM users u LEFT JOIN umkm m ON m.user_id = u.id WHERE ${where}`),
    );
    return { items, total: countRows[0]?.count ?? items.length, page, limit };
  }

  async getUser(id: string) {
    const [user] = rows<Row>(
      await this.db.execute(sql`
        SELECT u.id, u.email, u.role, u.tier, u.is_active, u.last_login_at, u.created_at,
               s.plan, s.status AS sub_status, s.payment_status, s.usage, s.feature_flags, s.started_at, s.expired_at
        FROM users u LEFT JOIN subscription s ON s.user_id = u.id WHERE u.id = ${id}`),
    );
    if (!user) throw new NotFoundException('User not found');
    const [company] = rows<Row>(
      await this.db.execute(sql`SELECT id, legal_name, nib, verification_status, verified_score, created_at FROM umkm WHERE user_id = ${id}`),
    );
    const products = company
      ? rows<Row>(
          await this.db.execute(sql`
            SELECT p.id, p.name, p.hs_code, p.hs_confidence, p.created_at,
                   w.status AS workflow_status, w.current_stage, w.retry_count, w.execution_version
            FROM product p LEFT JOIN product_workflow w ON w.product_id = p.id
            WHERE p.umkm_id = ${company.id as string} ORDER BY p.created_at DESC`),
        )
      : [];
    const activities = company
      ? rows<Row>(
          await this.db.execute(sql`
            SELECT id, status, buyer_name, buyer_country, last_message, updated_at
            FROM deal WHERE umkm_id = ${company.id as string} ORDER BY updated_at DESC LIMIT 20`),
        )
      : [];
    const plan = (user.plan as string) ?? 'free';
    return {
      user,
      company: company ?? null,
      products,
      deals: activities,
      entitlements: resolveEntitlements(plan, (user.feature_flags as Record<string, boolean>) ?? {}),
    };
  }

  // ── Companies / Products ─────────────────────────────────────────────────────
  async listCompanies(opts: { page?: number; limit?: number } = {}) {
    const limit = Math.min(Math.max(opts.limit ?? 20, 1), 100);
    const page = Math.max(opts.page ?? 1, 1);
    const offset = (page - 1) * limit;
    const items = rows<Row>(
      await this.db.execute(sql`
        SELECT m.id, m.legal_name, m.nib, m.verification_status, m.created_at,
               u.email AS owner_email, coalesce(s.plan,'free') AS plan,
               (SELECT count(*)::int FROM product p WHERE p.umkm_id=m.id) AS products,
               (SELECT count(*)::int FROM deal d WHERE d.umkm_id=m.id) AS deals
        FROM umkm m LEFT JOIN users u ON u.id=m.user_id LEFT JOIN subscription s ON s.user_id=m.user_id
        ORDER BY m.created_at DESC LIMIT ${limit} OFFSET ${offset}`),
    );
    const countRows = rows<{ count: number }>(await this.db.execute(sql`SELECT count(*)::int AS count FROM umkm`));
    return { items, total: countRows[0]?.count ?? items.length, page, limit };
  }

  async listProducts(opts: { page?: number; limit?: number } = {}) {
    const limit = Math.min(Math.max(opts.limit ?? 20, 1), 100);
    const page = Math.max(opts.page ?? 1, 1);
    const offset = (page - 1) * limit;
    const items = rows<Row>(
      await this.db.execute(sql`
        SELECT p.id, p.name, p.hs_code, p.hs_confidence, p.created_at,
               m.legal_name AS company, u.email AS owner_email,
               w.status AS workflow_status, w.current_stage, w.retry_count,
               (jsonb_array_length(coalesce(p.hs_candidates,'[]'::jsonb)))::int AS hs_candidates
        FROM product p
        LEFT JOIN umkm m ON m.id=p.umkm_id
        LEFT JOIN users u ON u.id=m.user_id
        LEFT JOIN product_workflow w ON w.product_id=p.id
        ORDER BY p.created_at DESC LIMIT ${limit} OFFSET ${offset}`),
    );
    const countRows = rows<{ count: number }>(await this.db.execute(sql`SELECT count(*)::int AS count FROM product`));
    return { items, total: countRows[0]?.count ?? items.length, page, limit };
  }

  // ── Workflow center ──────────────────────────────────────────────────────────
  async listWorkflows(opts: { status?: string; page?: number; limit?: number } = {}) {
    const limit = Math.min(Math.max(opts.limit ?? 20, 1), 100);
    const page = Math.max(opts.page ?? 1, 1);
    const offset = (page - 1) * limit;
    const where = opts.status ? sql`WHERE w.status = ${opts.status}` : sql``;
    const items = rows<Row>(
      await this.db.execute(sql`
        SELECT w.id, w.product_id, w.status, w.current_stage, w.current_worker, w.retry_count,
               w.execution_version, w.failure_reason, w.started_at, w.finished_at, w.updated_at,
               p.name AS product_name, m.legal_name AS company,
               (SELECT count(*)::int FROM workflow_stage s WHERE s.workflow_id=w.id AND s.status='completed') AS stages_done,
               (SELECT count(*)::int FROM workflow_stage s WHERE s.workflow_id=w.id) AS stages_total
        FROM product_workflow w
        LEFT JOIN product p ON p.id=w.product_id
        LEFT JOIN umkm m ON m.id=w.umkm_id
        ${where}
        ORDER BY w.updated_at DESC LIMIT ${limit} OFFSET ${offset}`),
    );
    const countRows = rows<{ count: number }>(
      await this.db.execute(sql`SELECT count(*)::int AS count FROM product_workflow w ${where}`),
    );
    return { items, total: countRows[0]?.count ?? items.length, page, limit };
  }

  async retryWorkflow(productId: string, actor: AuditActor) {
    const wf = await this.db.query.productWorkflows.findFirst({ where: eq(productWorkflows.productId, productId) });
    if (!wf) throw new NotFoundException('Workflow not found');
    const before = { status: wf.status, retryCount: wf.retryCount };
    await this.workflow.startForProduct(productId, wf.umkmId);
    await this.audit.record(actor, {
      action: 'workflow.retried',
      resourceType: 'product_workflow',
      resourceId: wf.id,
      before,
      after: { status: 'queued' },
    });
    return { ok: true, workflowId: wf.id };
  }

  // ── Subscriptions center ─────────────────────────────────────────────────────
  async listSubscriptions() {
    const items = rows<Row>(
      await this.db.execute(sql`
        SELECT s.user_id, u.email, s.plan, s.status, s.billing_cycle, s.payment_status, s.provider,
               s.started_at, s.expired_at, s.usage
        FROM subscription s JOIN users u ON u.id=s.user_id ORDER BY s.updated_at DESC LIMIT 200`),
    );
    const distribution = rows<{ plan: string; n: number }>(
      await this.db.execute(sql`SELECT plan, count(*)::int AS n FROM subscription GROUP BY plan`),
    );
    const catalogue = Object.entries(PLANS).map(([id, p]) => ({ id, label: p.label, comingSoon: !!p.comingSoon }));
    return { items, distribution, catalogue };
  }

  // ── Admin mutations (audited) ────────────────────────────────────────────────
  async createUser(
    input: { email: string; password: string; role?: string; plan?: string },
    actor: AuditActor,
  ) {
    const email = (input.email ?? '').trim().toLowerCase();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) throw new BadRequestException('Invalid email address');
    if (!input.password || input.password.length < 8) {
      throw new BadRequestException('Password must be at least 8 characters');
    }
    const role = input.role ?? 'umkm';
    if (!isRole(role)) throw new BadRequestException(`Unknown role '${role}'`);
    const plan = input.plan ?? 'free';
    if (!PLANS[plan]) throw new BadRequestException(`Unknown plan '${plan}'`);

    const existing = await this.db.query.users.findFirst({ where: eq(users.email, email) });
    if (existing) throw new ConflictException('Email already registered');

    const passwordHash = await bcrypt.hash(input.password, 12);
    const [created] = await this.db.insert(users).values({ email, passwordHash, role }).returning();
    if (!created) throw new Error('Failed to create user');
    // Provision the subscription so the user shows up consistently across the admin.
    await this.db.insert(subscriptions).values({ userId: created.id, plan }).onConflictDoNothing();

    await this.audit.record(actor, {
      action: 'user.created',
      resourceType: 'user',
      resourceId: created.id,
      after: { email, role, plan },
    });
    return { id: created.id, email: created.email, role: created.role, plan };
  }

  async setUserRole(userId: string, role: string, actor: AuditActor) {
    if (!isRole(role)) throw new BadRequestException(`Unknown role '${role}'`);
    const target = await this.db.query.users.findFirst({ where: eq(users.id, userId) });
    if (!target) throw new NotFoundException('User not found');
    await this.db.update(users).set({ role, updatedAt: new Date() }).where(eq(users.id, userId));
    await this.audit.record(actor, {
      action: 'role.changed',
      resourceType: 'user',
      resourceId: userId,
      before: { role: target.role },
      after: { role },
    });
    return { ok: true, role };
  }

  async setUserPlan(userId: string, plan: string, actor: AuditActor) {
    if (!PLANS[plan]) throw new BadRequestException(`Unknown plan '${plan}'`);
    const existing = await this.db.query.subscriptions.findFirst({ where: eq(subscriptions.userId, userId) });
    const before = existing ? { plan: existing.plan } : null;
    if (existing) {
      await this.db.update(subscriptions).set({ plan, status: 'active', updatedAt: new Date() }).where(eq(subscriptions.userId, userId));
    } else {
      await this.db.insert(subscriptions).values({ userId, plan });
    }
    await this.audit.record(actor, {
      action: 'subscription.changed',
      resourceType: 'subscription',
      resourceId: userId,
      before,
      after: { plan },
    });
    return { ok: true, plan };
  }

  // ── Provider monitoring (honest: real pings; unknown where undeterminable) ────
  async providers() {
    const ping = async (name: string, url: string) => {
      const started = Date.now();
      try {
        const resp = await fetch(url, { signal: AbortSignal.timeout(3000) });
        return { name, status: resp.ok ? 'up' : 'degraded', httpStatus: resp.status, latencyMs: Date.now() - started };
      } catch {
        return { name, status: 'down', httpStatus: null, latencyMs: Date.now() - started };
      }
    };
    const internal = await Promise.all([
      ping('matching-service', `${MATCHING_URL}/health`),
      ping('comms-service (Gemini)', `${COMMS_URL}/health`),
      ping('readiness-service (OSS/INATRADE)', `${READINESS_URL}/api/v1/health/ready`),
    ]);

    // External data providers: derive last-sync/status from persisted sync runs
    // when the table exists; otherwise report 'unknown' honestly.
    let lastSync: Row | null = null;
    try {
      const r = rows<Row>(
        await this.db.execute(sql`SELECT provider, status, buyers_upserted, finished_at, error FROM buyer_sync_run ORDER BY started_at DESC LIMIT 1`),
      );
      lastSync = r[0] ?? null;
    } catch {
      lastSync = null;
    }
    const external = [
      { name: 'TradeAtlas', status: lastSync ? (lastSync.status as string) : 'unknown', lastSync: lastSync?.finished_at ?? null, lastError: lastSync?.error ?? null },
      { name: 'BPS', status: 'unknown', note: 'no persisted health signal' },
      { name: 'UN Comtrade', status: 'unknown', note: 'no persisted health signal' },
    ];
    return { internal, external };
  }

  // ── Global activity (recent workflow events + deals) ─────────────────────────
  async activity(limit = 40) {
    const events = rows<Row>(
      await this.db.execute(sql`
        SELECT e.id, 'workflow' AS source, e.type, e.stage_name, e.message, e.created_at,
               p.name AS product_name, m.legal_name AS company
        FROM workflow_event e
        JOIN product_workflow w ON w.id=e.workflow_id
        LEFT JOIN product p ON p.id=w.product_id
        LEFT JOIN umkm m ON m.id=w.umkm_id
        ORDER BY e.created_at DESC LIMIT ${Math.min(limit, 100)}`),
    );
    return { items: events };
  }
}
