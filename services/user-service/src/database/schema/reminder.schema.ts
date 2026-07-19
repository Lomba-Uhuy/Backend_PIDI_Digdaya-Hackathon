import { pgTable, uuid, varchar, timestamp, index } from 'drizzle-orm/pg-core';
import { users } from './user.schema';

export const reminders = pgTable(
  'reminder',
  {
    id:        uuid('id').primaryKey().defaultRandom(),
    userId:    uuid('user_id').notNull().references(() => users.id, { onDelete: 'cascade' }),
    title:     varchar('title', { length: 255 }).notNull(),
    remindAt:  timestamp('remind_at', { withTimezone: true }).notNull(),
    type:      varchar('type', { length: 64 }).notNull().default('general'),
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => ({
    userIdx: index('reminder_user_idx').on(t.userId, t.remindAt),
  }),
);

export type Reminder = typeof reminders.$inferSelect;
export type NewReminder = typeof reminders.$inferInsert;
