import { Inject, Injectable } from '@nestjs/common';
import { asc, eq } from 'drizzle-orm';
import { DRIZZLE, type DrizzleDB } from '../database/database.module.js';
import { dealMessages, deals, type DealMessage } from '../database/schema/index.js';
import { DealService } from './deal.service.js';

export interface CreateMessageInput {
  text: string;
  sender?: 'umkm' | 'buyer' | 'system';
  intent?: string;
  meta?: Record<string, unknown>;
}

@Injectable()
export class MessageService {
  constructor(
    @Inject(DRIZZLE) private readonly db: DrizzleDB,
    private readonly dealService: DealService,
  ) {}

  /** All messages for a deal, oldest first. Enforces deal ownership. */
  async list(dealId: string, userId: string): Promise<{ items: DealMessage[] }> {
    await this.dealService.findById(dealId, userId); // ownership + existence
    const items = await this.db
      .select()
      .from(dealMessages)
      .where(eq(dealMessages.dealId, dealId))
      .orderBy(asc(dealMessages.createdAt));
    return { items };
  }

  /** Append a message to a deal and mirror it onto deal.lastMessage. */
  async create(dealId: string, input: CreateMessageInput, userId: string): Promise<DealMessage> {
    await this.dealService.findById(dealId, userId); // ownership + existence

    const [created] = await this.db
      .insert(dealMessages)
      .values({
        dealId,
        sender: input.sender ?? 'umkm',
        text: input.text,
        intent: input.intent,
        meta: input.meta,
      })
      .returning();
    if (!created) throw new Error('Failed to create message');

    await this.db
      .update(deals)
      .set({ lastMessage: input.text, updatedAt: new Date() })
      .where(eq(deals.id, dealId));

    return created;
  }
}
