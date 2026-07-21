import {
  pgTable, uuid, varchar, text, timestamp, pgEnum, index, jsonb,
} from 'drizzle-orm/pg-core';
import { deals } from './deal.schema';

// Who authored the message. 'buyer' turns are AI-simulated (no real inbound
// channel exists yet) but persisted + attributed so the thread is auditable.
export const dealMessageSenderEnum = pgEnum('deal_message_sender', [
  'umkm',
  'buyer',
  'system',
]);

export const dealMessages = pgTable(
  'deal_message',
  {
    id:        uuid('id').primaryKey().defaultRandom(),
    dealId:    uuid('deal_id').notNull().references(() => deals.id, { onDelete: 'cascade' }),
    sender:    dealMessageSenderEnum('sender').notNull(),
    text:      text('text').notNull(),
    intent:    varchar('intent', { length: 32 }),
    // { simulated?: boolean, proposedPrice?: number, confidence?: number, ... }
    meta:      jsonb('meta'),
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => ({
    dealCreatedIdx: index('deal_message_deal_created_idx').on(t.dealId, t.createdAt),
  }),
);

export type DealMessage = typeof dealMessages.$inferSelect;
export type NewDealMessage = typeof dealMessages.$inferInsert;
