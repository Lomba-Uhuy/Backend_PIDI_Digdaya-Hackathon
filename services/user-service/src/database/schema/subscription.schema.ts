import { pgTable, uuid, varchar, timestamp, jsonb } from 'drizzle-orm/pg-core';
import { users } from './user.schema.js';

/**
 * One subscription per user. The `plan` drives capabilities via the central plan
 * config (authz/plan-config.ts) — capabilities are NEVER hardcoded per endpoint.
 * `featureFlags` holds per-user overrides layered on top of the plan defaults.
 * `usage` tracks monthly counters for quota enforcement. Payment fields are
 * future-ready for Midtrans/Xendit/Stripe.
 */
export const subscriptions = pgTable('subscription', {
  id: uuid('id').primaryKey().defaultRandom(),
  userId: uuid('user_id')
    .notNull()
    .references(() => users.id, { onDelete: 'cascade' })
    .unique(),
  plan: varchar('plan', { length: 32 }).notNull().default('free'),
  status: varchar('status', { length: 24 }).notNull().default('active'), // active|expired|canceled|trialing
  billingCycle: varchar('billing_cycle', { length: 16 }).notNull().default('none'), // none|monthly|yearly
  startedAt: timestamp('started_at', { withTimezone: true }).notNull().defaultNow(),
  expiredAt: timestamp('expired_at', { withTimezone: true }),
  paymentStatus: varchar('payment_status', { length: 16 }).notNull().default('none'), // none|pending|paid|failed
  provider: varchar('provider', { length: 24 }), // midtrans|xendit|stripe|null
  usage: jsonb('usage').$type<Record<string, number>>().notNull().default({}),
  featureFlags: jsonb('feature_flags').$type<Record<string, boolean>>().notNull().default({}),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
});

export type Subscription = typeof subscriptions.$inferSelect;
export type NewSubscription = typeof subscriptions.$inferInsert;
