import {
  pgTable, uuid, varchar, text, timestamp, decimal, pgEnum, index,
} from 'drizzle-orm/pg-core';
import { umkm } from './umkm.schema';
import { products } from './product.schema';

export const dealStatusEnum = pgEnum('deal_status', [
  'contacted',
  'negotiating',
  'compliance',
  'po_sent',
  'po_signed',
  'closed',
]);

export const deals = pgTable(
  'deal',
  {
    id:            uuid('id').primaryKey().defaultRandom(),
    umkmId:        uuid('umkm_id').notNull().references(() => umkm.id, { onDelete: 'cascade' }),
    productId:     uuid('product_id').references(() => products.id, { onDelete: 'set null' }),
    // Buyer may be a synthetic/demo buyer not present in the buyer table, so we
    // denormalize name/country and keep buyer_id nullable (no FK).
    buyerId:       uuid('buyer_id'),
    buyerName:     varchar('buyer_name', { length: 255 }),
    buyerCountry:  varchar('buyer_country', { length: 64 }),
    status:        dealStatusEnum('status').notNull().default('contacted'),
    agreedPrice:   decimal('agreed_price', { precision: 12, scale: 4 }),
    lastMessage:   text('last_message'),
    createdAt:     timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    updatedAt:     timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => ({
    umkmStatusIdx: index('deal_umkm_status_idx').on(t.umkmId, t.status),
  }),
);

export type Deal = typeof deals.$inferSelect;
export type NewDeal = typeof deals.$inferInsert;
