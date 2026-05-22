export const configuration = () => ({
  NODE_ENV: process.env.NODE_ENV ?? 'development',
  PORT: Number.parseInt(process.env.PORT ?? '3000', 10),
  LOG_LEVEL: process.env.LOG_LEVEL ?? 'info',
  CORS_ORIGINS: process.env.CORS_ORIGINS ?? '',

  JWT_SECRET: process.env.JWT_SECRET ?? 'change-me',

  USER_SERVICE_URL: process.env.USER_SERVICE_URL ?? 'http://localhost:3001',
  READINESS_SERVICE_URL: process.env.READINESS_SERVICE_URL ?? 'http://localhost:3002',
  MATCHING_SERVICE_URL: process.env.MATCHING_SERVICE_URL ?? 'http://localhost:8001',
  COMMS_SERVICE_URL: process.env.COMMS_SERVICE_URL ?? 'http://localhost:8002',

  BULL_REDIS_URL: process.env.BULL_REDIS_URL ?? 'redis://localhost:6379/2',

  RATE_LIMIT_DEFAULT_TTL: Number.parseInt(process.env.RATE_LIMIT_DEFAULT_TTL ?? '60', 10),
  RATE_LIMIT_DEFAULT_LIMIT: Number.parseInt(process.env.RATE_LIMIT_DEFAULT_LIMIT ?? '100', 10),
  RATE_LIMIT_AI_TTL: Number.parseInt(process.env.RATE_LIMIT_AI_TTL ?? '60', 10),
  RATE_LIMIT_AI_LIMIT: Number.parseInt(process.env.RATE_LIMIT_AI_LIMIT ?? '20', 10),
});