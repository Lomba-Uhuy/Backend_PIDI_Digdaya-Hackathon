import {
  pgTable, uuid, varchar, text, timestamp,
  integer, decimal, index,
} from 'drizzle-orm/pg-core';
import { umkm } from './umkm.schema.js';

export const products = pgTable(
  'product',
  {
    id:               uuid('id').primaryKey().defaultRandom(),
    umkmId:           uuid('umkm_id').notNull().references(() => umkm.id, { onDelete: 'cascade' }),
    name:             varchar('name', { length: 255 }).notNull(),
    description:      text('description').notNull(),
    hsCode:           varchar('hs_code', { length: 10 }),
    hsConfidence:     decimal('hs_confidence', { precision: 5, scale: 4 }),
    moq:              integer('moq').notNull().default(1),
    monthlyCapacity:  integer('monthly_capacity').notNull().default(0),
    priceMin:         decimal('price_min', { precision: 18, scale: 4 }).notNull(),
    priceMax:         decimal('price_max', { precision: 18, scale: 4 }).notNull(),
    // hpp is SENSITIVE — never returned in API responses, never sent to LLM
    hpp:              decimal('hpp', { precision: 18, scale: 4 }).notNull(),
    photoUrls:        text('photo_urls').array().notNull().default([]),
    createdAt:        timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    updatedAt:        timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => ({
    umkmIdx:    index('product_umkm_idx').on(t.umkmId),
    hsCodeIdx:  index('product_hs_code_idx').on(t.hsCode),
  }),
);

export type Product = typeof products.$inferSelect;
export type NewProduct = typeof products.$inferInsert;