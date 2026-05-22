import {
  pgTable, uuid, varchar, text, timestamp, boolean,
  decimal, jsonb, pgEnum, index,
} from 'drizzle-orm/pg-core';
import { users } from './user.schema.js';

export const verificationStatusEnum = pgEnum('verification_status', [
  'PENDING',
  'IN_PROGRESS',
  'VERIFIED',
  'FAILED',
]);

export const umkm = pgTable(
  'umkm',
  {
    id:                  uuid('id').primaryKey().defaultRandom(),
    legalName:           varchar('legal_name', { length: 255 }).notNull(),
    nib:                 varchar('nib', { length: 13 }).notNull().unique(),
    description:         text('description'),
    verificationStatus:  verificationStatusEnum('verification_status').notNull().default('PENDING'),
    verifiedScore:       decimal('verified_score', { precision: 5, scale: 4 }).notNull().default('0'),
    ossRbaData:          jsonb('oss_rba_data').notNull().default({}),
    inatradeData:        jsonb('inatrade_data').notNull().default({}),
    certifications:      text('certifications').array().notNull().default([]),
    userId:              uuid('user_id').notNull().references(() => users.id, { onDelete: 'cascade' }),
    isActive:            boolean('is_active').notNull().default(true),
    createdAt:           timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    updatedAt:           timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => ({
    nibIdx:    index('umkm_nib_idx').on(t.nib),
    userIdx:   index('umkm_user_id_idx').on(t.userId),
    statusIdx: index('umkm_verification_status_idx').on(t.verificationStatus),
  }),
);

export type Umkm = typeof umkm.$inferSelect;
export type NewUmkm = typeof umkm.$inferInsert;