import { pgTable, uuid, varchar, timestamp, boolean } from 'drizzle-orm/pg-core';

export const users = pgTable('users', {
  id:            uuid('id').primaryKey().defaultRandom(),
  email:         varchar('email', { length: 255 }).notNull().unique(),
  passwordHash:  varchar('password_hash', { length: 255 }).notNull(),
  tenantId:      uuid('tenant_id'),
  tier:          varchar('tier', { length: 16 }).notNull().default('free'),
  // RBAC role — free-form varchar (not a DB enum) so roles stay extensible
  // without a migration. Valid values are defined in authz/plan-config.ts.
  role:          varchar('role', { length: 32 }).notNull().default('umkm'),
  isActive:      boolean('is_active').notNull().default(true),
  lastLoginAt:   timestamp('last_login_at', { withTimezone: true }),
  createdAt:     timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  updatedAt:     timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
});

export type User = typeof users.$inferSelect;
export type NewUser = typeof users.$inferInsert;