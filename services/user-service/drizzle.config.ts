import { defineConfig } from 'drizzle-kit';

export default defineConfig({
  schema: './src/database/schema/index.ts',
  out: './src/database/migrations',
  dialect: 'postgresql',
  dbCredentials: {
    url: process.env.DATABASE_URL ?? 'postgres://tc_user:tc_pass_dev@localhost:5432/tradeconnect',
  },
  verbose: true,
  strict: true,
});