import { Inject, Injectable, NotFoundException } from '@nestjs/common';
import { eq, sql } from 'drizzle-orm';
import { DRIZZLE, type DrizzleDB } from '../database/database.module.js';
import { umkm } from '../database/schema/index.js';

export interface ActivityEvent {
  id: string;
  category: string;
  type: string;
  severity: 'info' | 'success' | 'warning' | 'error';
  title: string;
  description: string;
  entity: string;
  entityId: string;
  actor: string;
  status: string;
  timestamp: string;
  link: string;
}

export interface ActivityListResult {
  items: ActivityEvent[];
  limit: number;
  offset: number;
}

export interface SyncStatus {
  provider: string;
  status: string;
  buyersUpserted: number;
  error: string | null;
  finishedAt: string | null;
  startedAt: string | null;
}

export interface ActivityStatistics {
  total: number;
  byCategory: { category: string; count: number }[];
  lastSync: SyncStatus | null;
}

const CATEGORIES = ['negotiation', 'purchase_order', 'sync', 'product'] as const;

@Injectable()
export class ActivityService {
  constructor(@Inject(DRIZZLE) private readonly db: DrizzleDB) {}

  private async umkmIdForUser(userId: string): Promise<string> {
    const row = await this.db.query.umkm.findFirst({ where: eq(umkm.userId, userId) });
    if (!row) throw new NotFoundException('No UMKM profile for this user yet');
    return row.id;
  }

  /**
   * A unified, time-ordered activity feed built ENTIRELY from persisted rows
   * (deals, purchase orders, buyer sync runs, products). Every event maps 1:1 to
   * a real DB record — nothing is fabricated. `buyer_sync_run` is a system-wide
   * source; the rest are scoped to the caller's UMKM.
   */
  async recent(
    userId: string,
    opts: { limit: number; offset: number; category?: string },
  ): Promise<ActivityListResult> {
    const umkmId = await this.umkmIdForUser(userId);
    const { limit, offset } = opts;
    const category = opts.category && CATEGORIES.includes(opts.category as (typeof CATEGORIES)[number])
      ? opts.category
      : undefined;

    const union = sql`
      SELECT 'deal:' || d.id AS id, 'negotiation' AS category,
        CASE WHEN d.status = 'po_signed' THEN 'negotiation_closed' ELSE d.status::text END AS type,
        CASE WHEN d.status = 'po_signed' THEN 'success' WHEN d.status = 'po_sent' THEN 'warning' ELSE 'info' END AS severity,
        'Negosiasi — ' || COALESCE(d.buyer_name, 'Pembeli') AS title,
        COALESCE(NULLIF(d.last_message, ''), 'Status: ' || d.status) AS description,
        'deal' AS entity, d.id::text AS entity_id, 'Anda' AS actor, d.status::text AS status,
        d.updated_at AS ts, '/negotiation' AS link
      FROM deal d WHERE d.umkm_id = ${umkmId}
      UNION ALL
      SELECT 'po:' || po.id, 'purchase_order', 'po_' || po.status,
        CASE WHEN po.status = 'signed' THEN 'success' ELSE 'info' END,
        'Purchase Order ' || po.po_number,
        'Status: ' || po.status || COALESCE(' • ' || po.buyer_name, ''),
        'purchase_order', po.deal_id::text, 'Anda', po.status::text,
        po.updated_at, '/purchase-order'
      FROM purchase_order po JOIN deal d2 ON d2.id = po.deal_id WHERE d2.umkm_id = ${umkmId}
      UNION ALL
      SELECT 'sync:' || s.id, 'sync', 'buyer_sync',
        CASE WHEN s.status = 'error' THEN 'error' WHEN s.status = 'completed' THEN 'success' ELSE 'info' END,
        'Sinkronisasi ' || s.provider,
        COALESCE(s.buyers_upserted::text || ' pembeli diperbarui', 'Sinkronisasi berjalan') || COALESCE(' • ' || s.error, ''),
        'buyer_sync_run', s.id::text, 'Sistem', s.status,
        COALESCE(s.finished_at, s.started_at), '/buyer-discovery'
      FROM buyer_sync_run s
      UNION ALL
      SELECT 'product:' || p.id, 'product',
        CASE WHEN p.created_at = p.updated_at THEN 'product_created' ELSE 'product_updated' END,
        'info', 'Produk — ' || p.name,
        COALESCE('HS ' || p.hs_code, 'Analisis produk'), 'product', p.id::text, 'Anda', 'active',
        p.updated_at, '/verification'
      FROM product p WHERE p.umkm_id = ${umkmId}
    `;

    const rows = (await this.db.execute(sql`
      SELECT id, category, type, severity, title, description, entity, entity_id, actor, status, ts, link
      FROM ( ${union} ) evt
      ${category ? sql`WHERE category = ${category}` : sql``}
      ORDER BY ts DESC
      LIMIT ${limit} OFFSET ${offset}
    `)) as unknown as Array<Record<string, unknown>>;

    return {
      items: rows.map((r) => ({
        id: String(r.id),
        category: String(r.category),
        type: String(r.type),
        severity: r.severity as ActivityEvent['severity'],
        title: String(r.title),
        description: String(r.description ?? ''),
        entity: String(r.entity),
        entityId: String(r.entity_id),
        actor: String(r.actor),
        status: String(r.status),
        timestamp: r.ts instanceof Date ? r.ts.toISOString() : String(r.ts),
        link: String(r.link),
      })),
      limit,
      offset,
    };
  }

  async statistics(userId: string): Promise<ActivityStatistics> {
    const umkmId = await this.umkmIdForUser(userId);

    const counts = (await this.db.execute(sql`
      SELECT 'negotiation' AS category, COUNT(*)::int AS count FROM deal WHERE umkm_id = ${umkmId}
      UNION ALL
      SELECT 'purchase_order', COUNT(*)::int FROM purchase_order po JOIN deal d ON d.id = po.deal_id WHERE d.umkm_id = ${umkmId}
      UNION ALL
      SELECT 'sync', COUNT(*)::int FROM buyer_sync_run
      UNION ALL
      SELECT 'product', COUNT(*)::int FROM product WHERE umkm_id = ${umkmId}
    `)) as unknown as Array<{ category: string; count: number }>;

    const syncRows = (await this.db.execute(sql`
      SELECT provider, status, buyers_upserted, error, finished_at, started_at
      FROM buyer_sync_run
      ORDER BY COALESCE(finished_at, started_at) DESC NULLS LAST
      LIMIT 1
    `)) as unknown as Array<Record<string, unknown>>;

    const byCategory = counts.map((c) => ({ category: c.category, count: Number(c.count) }));
    const total = byCategory.reduce((sum, c) => sum + c.count, 0);
    const s = syncRows[0];
    const lastSync: SyncStatus | null = s
      ? {
          provider: String(s.provider),
          status: String(s.status),
          buyersUpserted: Number(s.buyers_upserted ?? 0),
          error: s.error ? String(s.error) : null,
          finishedAt: s.finished_at instanceof Date ? s.finished_at.toISOString() : (s.finished_at ? String(s.finished_at) : null),
          startedAt: s.started_at instanceof Date ? s.started_at.toISOString() : (s.started_at ? String(s.started_at) : null),
        }
      : null;

    return { total, byCategory, lastSync };
  }
}
