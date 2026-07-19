import 'reflect-metadata';
import path from 'node:path';
import helmet from '@fastify/helmet';
import { ValidationPipe } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { NestFactory } from '@nestjs/core';
import { FastifyAdapter, type NestFastifyApplication } from '@nestjs/platform-fastify';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { drizzle } from 'drizzle-orm/postgres-js';
import { migrate } from 'drizzle-orm/postgres-js/migrator';
import { Logger } from 'nestjs-pino';
import postgres from 'postgres';

import { AppModule } from './app.module.js';

async function runMigrations(): Promise<void> {
  const databaseUrl =
    process.env.DATABASE_URL ?? 'postgres://tc_user:tc_pass_dev@localhost:5432/tradeconnect';
  // dist/main.js → ../migrations (copied by Dockerfile to /repo/services/user-service/migrations)
  const migrationsFolder = path.join(__dirname, '..', 'migrations');
  const sql = postgres(databaseUrl, { max: 1, idle_timeout: 10 });
  try {
    const db = drizzle(sql);
    await migrate(db, { migrationsFolder });
    // biome-ignore lint/suspicious/noConsole: startup migration log
    console.log('Database migrations applied successfully.');
  } finally {
    await sql.end();
  }
}

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create<NestFastifyApplication>(
    AppModule,
    new FastifyAdapter({ logger: false, trustProxy: true }),
    { bufferLogs: true },
  );
  app.useLogger(app.get(Logger));
  await app.register(helmet, { contentSecurityPolicy: false });

  app.useGlobalPipes(
    new ValidationPipe({
      transform: true,
      whitelist: true,
      forbidNonWhitelisted: true,
      transformOptions: { enableImplicitConversion: true },
    }),
  );

  const swaggerConfig = new DocumentBuilder()
    .setTitle('TradeConnect User Service')
    .setDescription('UMKM onboarding, products, JWT issuance')
    .setVersion('0.1.0')
    .addBearerAuth()
    .build();
  SwaggerModule.setup('docs', app, SwaggerModule.createDocument(app, swaggerConfig));

  const port = app.get(ConfigService).get<number>('PORT') ?? 3001;
  await app.listen(port, '0.0.0.0');
  // biome-ignore lint/suspicious/noConsole: bootstrap log only
  console.log(`User Service listening on http://0.0.0.0:${port}`);
}

runMigrations()
  .then(() => bootstrap())
  .catch((err) => {
    // biome-ignore lint/suspicious/noConsole: fatal startup error
    console.error('User Service failed to start:', err);
    process.exit(1);
  });