import {
  pgTable, uuid, varchar, timestamp, pgEnum, jsonb, index,
} from 'drizzle-orm/pg-core';
import { deals } from './deal.schema';

export const complianceKindEnum = pgEnum('compliance_kind', ['nib', 'fraud_scan', 'document']);
export const complianceStatusEnum = pgEnum('compliance_status', ['pass', 'warn', 'fail']);

export const complianceChecks = pgTable(
  'compliance_check',
  {
    id:        uuid('id').primaryKey().defaultRandom(),
    dealId:    uuid('deal_id').notNull().references(() => deals.id, { onDelete: 'cascade' }),
    kind:      complianceKindEnum('kind').notNull(),
    label:     varchar('label', { length: 160 }).notNull(),
    status:    complianceStatusEnum('status').notNull(),
    detail:    jsonb('detail'),
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => ({
    dealIdx: index('compliance_check_deal_idx').on(t.dealId, t.createdAt),
  }),
);

export type ComplianceCheck = typeof complianceChecks.$inferSelect;
export type NewComplianceCheck = typeof complianceChecks.$inferInsert;
