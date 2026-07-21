import { ForbiddenException, Inject, Injectable, NotFoundException } from '@nestjs/common';
import { and, count, desc, eq, sql } from 'drizzle-orm';
import { DRIZZLE, type DrizzleDB } from '../database/database.module.js';
import { deals, umkm, type Deal } from '../database/schema/index.js';
import type { CreateDealDto } from './dto/create-deal.dto.js';
import type { UpdateDealDto } from './dto/update-deal.dto.js';

export interface DealListResult {
  items: Deal[];
  total: number;
  page: number;
  pageSize: number;
}

export interface DealAnalytics {
  total: number;
  open: number;
  closed: number;
  conversionRate: number; // closed / total, 0..1
  avgCloseDays: number | null;
  avgAgreedPrice: number | null;
  byStatus: { status: string; count: number }[];
  byCountry: { country: string; count: number }[];
}

@Injectable()
export class DealService {
  constructor(@Inject(DRIZZLE) private readonly db: DrizzleDB) {}

  /** Resolve the caller's UMKM id (deals are scoped to it). */
  private async umkmIdForUser(userId: string): Promise<string> {
    const row = await this.db.query.umkm.findFirst({ where: eq(umkm.userId, userId) });
    if (!row) throw new NotFoundException('No UMKM profile for this user yet');
    return row.id;
  }

  async create(dto: CreateDealDto, userId: string): Promise<Deal> {
    const umkmId = await this.umkmIdForUser(userId);
    const [created] = await this.db
      .insert(deals)
      .values({
        umkmId,
        productId: dto.productId,
        buyerId: dto.buyerId,
        buyerName: dto.buyerName,
        buyerCountry: dto.buyerCountry,
        status: dto.status ?? 'contacted',
        agreedPrice: dto.agreedPrice != null ? String(dto.agreedPrice) : undefined,
        lastMessage: dto.lastMessage,
      })
      .returning();
    if (!created) throw new Error('Failed to create deal');
    return created;
  }

  async list(
    userId: string,
    opts: { status?: string; page: number; pageSize: number },
  ): Promise<DealListResult> {
    const umkmId = await this.umkmIdForUser(userId);
    const where = opts.status
      ? and(eq(deals.umkmId, umkmId), eq(deals.status, opts.status as Deal['status']))
      : eq(deals.umkmId, umkmId);

    const totalRows = await this.db
      .select({ value: count() })
      .from(deals)
      .where(where);
    const total = Number(totalRows[0]?.value ?? 0);

    const items = await this.db
      .select()
      .from(deals)
      .where(where)
      .orderBy(desc(deals.updatedAt))
      .limit(opts.pageSize)
      .offset((opts.page - 1) * opts.pageSize);

    return { items, total: Number(total), page: opts.page, pageSize: opts.pageSize };
  }

  async findById(id: string, userId: string): Promise<Deal> {
    const umkmId = await this.umkmIdForUser(userId);
    const row = await this.db.query.deals.findFirst({ where: eq(deals.id, id) });
    if (!row) throw new NotFoundException(`Deal ${id} not found`);
    if (row.umkmId !== umkmId) throw new ForbiddenException('Not your deal');
    return row;
  }

  async update(id: string, dto: UpdateDealDto, userId: string): Promise<Deal> {
    await this.findById(id, userId); // ownership check
    const [updated] = await this.db
      .update(deals)
      .set({
        ...(dto.status !== undefined ? { status: dto.status } : {}),
        ...(dto.agreedPrice !== undefined ? { agreedPrice: String(dto.agreedPrice) } : {}),
        ...(dto.lastMessage !== undefined ? { lastMessage: dto.lastMessage } : {}),
        updatedAt: new Date(),
      })
      .where(eq(deals.id, id))
      .returning();
    if (!updated) throw new NotFoundException(`Deal ${id} not found`);
    return updated;
  }

  /** Negotiation analytics aggregated from the caller's real deal records. */
  async analytics(userId: string): Promise<DealAnalytics> {
    const umkmId = await this.umkmIdForUser(userId);

    const totalsRows = (await this.db.execute(sql`
      SELECT
        COUNT(*)::int AS total,
        COUNT(*) FILTER (WHERE status IN ('contacted','negotiating','compliance','po_sent'))::int AS open,
        COUNT(*) FILTER (WHERE status = 'po_signed')::int AS closed,
        AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) FILTER (WHERE status = 'po_signed') AS avg_close_seconds,
        AVG(agreed_price::numeric) FILTER (WHERE agreed_price IS NOT NULL) AS avg_price
      FROM deal WHERE umkm_id = ${umkmId}
    `)) as unknown as Array<Record<string, unknown>>;

    const statusRows = (await this.db.execute(sql`
      SELECT status::text AS status, COUNT(*)::int AS count
      FROM deal WHERE umkm_id = ${umkmId} GROUP BY status ORDER BY count DESC
    `)) as unknown as Array<{ status: string; count: number }>;

    const countryRows = (await this.db.execute(sql`
      SELECT buyer_country AS country, COUNT(*)::int AS count
      FROM deal WHERE umkm_id = ${umkmId} AND buyer_country IS NOT NULL AND buyer_country <> ''
      GROUP BY buyer_country ORDER BY count DESC LIMIT 8
    `)) as unknown as Array<{ country: string; count: number }>;

    const t = totalsRows[0] ?? {};
    const total = Number(t.total ?? 0);
    const closed = Number(t.closed ?? 0);
    const avgCloseSeconds = t.avg_close_seconds != null ? Number(t.avg_close_seconds) : null;
    const avgPrice = t.avg_price != null ? Number(t.avg_price) : null;

    return {
      total,
      open: Number(t.open ?? 0),
      closed,
      conversionRate: total > 0 ? closed / total : 0,
      avgCloseDays: avgCloseSeconds != null ? Number((avgCloseSeconds / 86400).toFixed(2)) : null,
      avgAgreedPrice: avgPrice != null ? Number(avgPrice.toFixed(2)) : null,
      byStatus: statusRows.map((r) => ({ status: r.status, count: Number(r.count) })),
      byCountry: countryRows.map((r) => ({ country: r.country, count: Number(r.count) })),
    };
  }
}
