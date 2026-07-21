import { Inject, Injectable, Logger } from '@nestjs/common';
import { desc, sql } from 'drizzle-orm';
import { DRIZZLE, type DrizzleDB } from '../database/database.module.js';
import { adminAuditLog } from '../database/schema/index.js';

export interface AuditActor {
  userId: string;
  email?: string;
  ip?: string;
}

export interface AuditInput {
  action: string;
  resourceType?: string;
  resourceId?: string;
  before?: unknown;
  after?: unknown;
}

/** Records administrative actions to an immutable audit log. Never throws into the caller. */
@Injectable()
export class AuditService {
  private readonly logger = new Logger(AuditService.name);
  constructor(@Inject(DRIZZLE) private readonly db: DrizzleDB) {}

  async record(actor: AuditActor, input: AuditInput): Promise<void> {
    try {
      await this.db.insert(adminAuditLog).values({
        actorUserId: actor.userId,
        actorEmail: actor.email ?? null,
        action: input.action,
        resourceType: input.resourceType ?? null,
        resourceId: input.resourceId ?? null,
        before: (input.before ?? null) as never,
        after: (input.after ?? null) as never,
        ip: actor.ip ?? null,
      });
    } catch (e) {
      // Audit must never break the primary action, but a failure is notable.
      this.logger.error(`audit record failed for ${input.action}: ${String(e)}`);
    }
  }

  async list(opts: { limit?: number; offset?: number; action?: string } = {}) {
    const limit = Math.min(Math.max(opts.limit ?? 50, 1), 200);
    const offset = Math.max(opts.offset ?? 0, 0);
    const where = opts.action ? sql`WHERE action = ${opts.action}` : sql``;
    const rows = await this.db
      .select()
      .from(adminAuditLog)
      .orderBy(desc(adminAuditLog.createdAt))
      .limit(limit)
      .offset(offset);
    const countRows = (await this.db.execute(
      sql`SELECT count(*)::int AS count FROM admin_audit_log ${where}`,
    )) as unknown as Array<{ count: number }>;
    return { items: rows, total: countRows[0]?.count ?? rows.length, limit, offset };
  }
}
