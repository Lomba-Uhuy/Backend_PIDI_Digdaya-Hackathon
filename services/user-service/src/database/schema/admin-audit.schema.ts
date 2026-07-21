import { pgTable, uuid, varchar, timestamp, jsonb, index } from 'drizzle-orm/pg-core';

/** Immutable log of administrative actions (actor, action, resource, before/after). */
export const adminAuditLog = pgTable(
  'admin_audit_log',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    actorUserId: uuid('actor_user_id'),
    actorEmail: varchar('actor_email', { length: 255 }),
    action: varchar('action', { length: 64 }).notNull(),
    resourceType: varchar('resource_type', { length: 64 }),
    resourceId: varchar('resource_id', { length: 128 }),
    before: jsonb('before'),
    after: jsonb('after'),
    ip: varchar('ip', { length: 64 }),
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => ({
    createdIdx: index('admin_audit_created_idx').on(t.createdAt),
    actionIdx: index('admin_audit_action_idx').on(t.action, t.createdAt),
  }),
);

export type AdminAuditEntry = typeof adminAuditLog.$inferSelect;
