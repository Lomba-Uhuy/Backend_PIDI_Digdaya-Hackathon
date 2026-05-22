export const configuration = () => ({
  NODE_ENV: process.env.NODE_ENV ?? 'development',
  PORT: Number.parseInt(process.env.PORT ?? '3001', 10),
  LOG_LEVEL: process.env.LOG_LEVEL ?? 'info',

  DATABASE_URL: process.env.DATABASE_URL ?? 'postgres://tc_user:tc_pass_dev@localhost:5432/tradeconnect',
  BULL_REDIS_URL: process.env.BULL_REDIS_URL ?? 'redis://localhost:6379/2',

  JWT_SECRET: process.env.JWT_SECRET ?? 'change-me',
  JWT_ACCESS_TOKEN_EXPIRES: process.env.JWT_ACCESS_TOKEN_EXPIRES ?? '30m',
  JWT_REFRESH_TOKEN_EXPIRES: process.env.JWT_REFRESH_TOKEN_EXPIRES ?? '14d',
});