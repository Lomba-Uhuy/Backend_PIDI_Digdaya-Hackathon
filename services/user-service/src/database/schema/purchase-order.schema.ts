import {
  pgTable, uuid, varchar, text, timestamp, decimal, integer, pgEnum, jsonb,
} from 'drizzle-orm/pg-core';
import { deals } from './deal.schema';

export const poStatusEnum = pgEnum('po_status', ['draft', 'sent', 'signed']);

export const purchaseOrders = pgTable('purchase_order', {
  id:           uuid('id').primaryKey().defaultRandom(),
  // One PO per deal.
  dealId:       uuid('deal_id').notNull().unique().references(() => deals.id, { onDelete: 'cascade' }),
  poNumber:     varchar('po_number', { length: 40 }).notNull(),
  productId:    uuid('product_id'),
  productName:  varchar('product_name', { length: 255 }),
  buyerName:    varchar('buyer_name', { length: 255 }),
  buyerCountry: varchar('buyer_country', { length: 64 }),
  incoterm:     varchar('incoterm', { length: 16 }).notNull().default('CIF'),
  unitPrice:    decimal('unit_price', { precision: 18, scale: 4 }).notNull(),
  qty:          integer('qty').notNull().default(1),
  currency:     varchar('currency', { length: 8 }).notNull().default('USD'),
  subtotal:     decimal('subtotal', { precision: 18, scale: 4 }).notNull(),
  paymentTerms: varchar('payment_terms', { length: 255 }).notNull().default('30% DP / 70% L/C'),
  status:       poStatusEnum('status').notNull().default('draft'),
  signedBy:     varchar('signed_by', { length: 255 }),
  signature:    text('signature'),
  signedAt:     timestamp('signed_at', { withTimezone: true }),
  terms:        jsonb('terms'),
  createdAt:    timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  updatedAt:    timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
});

export type PurchaseOrder = typeof purchaseOrders.$inferSelect;
export type NewPurchaseOrder = typeof purchaseOrders.$inferInsert;
