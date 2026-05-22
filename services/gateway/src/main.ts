import 'reflect-metadata';
import helmet from '@fastify/helmet';
import { ValidationPipe } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { NestFactory } from '@nestjs/core';
import {
  FastifyAdapter,
  type NestFastifyApplication,
} from '@nestjs/platform-fastify';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { Logger } from 'nestjs-pino';

import { AppModule } from './app.module.js';

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create<NestFastifyApplication>(
    AppModule,
    new FastifyAdapter({
      logger: false,        // we own logging via nestjs-pino
      trustProxy: true,
      bodyLimit: 10 * 1024 * 1024,
    }),
    { bufferLogs: true },
  );

  app.useLogger(app.get(Logger));

  await app.register(helmet, {
    contentSecurityPolicy: false,    // off for /docs in dev
  });

  app.useGlobalPipes(
    new ValidationPipe({
      transform: true,
      whitelist: true,
      forbidNonWhitelisted: true,
      transformOptions: { enableImplicitConversion: true },
    }),
  );

  const config = app.get(ConfigService);
  const corsOrigins = (config.get<string>('CORS_ORIGINS') ?? '').split(',').filter(Boolean);
  app.enableCors({
    origin: corsOrigins.length > 0 ? corsOrigins : true,
    credentials: true,
  });

  app.setGlobalPrefix('api/v1', {
    exclude: ['health', 'docs', 'admin/queues'],
  });

  // OpenAPI / Swagger
  const swaggerConfig = new DocumentBuilder()
    .setTitle('TradeConnect Gateway')
    .setDescription('AI-Powered Export Execution Infrastructure — Gateway')
    .setVersion('0.1.0')
    .addBearerAuth()
    .build();
  const document = SwaggerModule.createDocument(app, swaggerConfig);
  SwaggerModule.setup('docs', app, document);

  const port = config.get<number>('PORT') ?? 3000;
  await app.listen(port, '0.0.0.0');

  // biome-ignore lint/suspicious/noConsole: bootstrap log only
  console.log(`Gateway listening on http://0.0.0.0:${port}`);
  // biome-ignore lint/suspicious/noConsole: bootstrap log only
  console.log(`OpenAPI:    http://0.0.0.0:${port}/docs`);
  // biome-ignore lint/suspicious/noConsole: bootstrap log only
  console.log(`Bull Board: http://0.0.0.0:${port}/admin/queues`);
}

bootstrap().catch((err) => {
  // biome-ignore lint/suspicious/noConsole: fatal bootstrap error
  console.error('Gateway failed to start:', err);
  process.exit(1);
});