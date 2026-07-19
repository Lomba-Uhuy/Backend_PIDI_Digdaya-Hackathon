import { ForbiddenException, Inject, Injectable, NotFoundException } from '@nestjs/common';
import { and, count, desc, eq } from 'drizzle-orm';
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
}
