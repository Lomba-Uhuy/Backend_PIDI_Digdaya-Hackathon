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
  const corsOrigins = (config.get<string>('CORS_ORIGINS') ?? '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  // Always allow localhost, private LAN IPs, and VS Code dev tunnels / GitHub
  // Codespaces — on top of any explicit CORS_ORIGINS allowlist. This lets the app
  // be reached via VS Code "Forward a Port" without editing config.
  const TUNNEL_HOST = /(\.devtunnels\.ms|\.devtunnel\.ms|\.app\.github\.dev)$/i;
  const LAN_ORIGIN =
    /^https?:\/\/(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)(:\d+)?$/i;
  app.enableCors({
    origin: (origin, cb) => {
      if (!origin) return cb(null, true); // same-origin, curl, server-to-server
      if (corsOrigins.includes(origin)) return cb(null, true);
      if (LAN_ORIGIN.test(origin)) return cb(null, true);
      try {
        if (TUNNEL_HOST.test(new URL(origin).hostname)) return cb(null, true);
      } catch {
        /* malformed origin — fall through */
      }
      if (corsOrigins.length === 0) return cb(null, true); // no allowlist → dev-open
      return cb(new Error(`Origin ${origin} not allowed by CORS`), false);
    },
    credentials: true,
  });

  app.setGlobalPrefix('api/v1', {
    exclude: ['health', 'docs', 'admin/queues'],
  });

  // OpenAPI / Swagger
  const swaggerConfig = new DocumentBuilder()
    .setTitle('TradeConnect Gateway')
    .setDescription(
      `AI-Powered Export Execution Infrastructure — Gateway API

## How to authenticate

1. **Register** a new account via \`POST /api/v1/auth/register\` (one-time)
   _or_ **Log in** via \`POST /api/v1/auth/login\` if you already have an account.
2. Copy the \`accessToken\` from the response.
3. Click the **Authorize 🔒** button at the top of this page.
4. In the **bearer (http, Bearer)** field, paste the token and click **Authorize**.
5. All protected endpoints will now send \`Authorization: Bearer <token>\` automatically.

> Access tokens expire according to \`JWT_EXPIRES\` env var (default 1 day).
> Use \`refreshToken\` to obtain a new pair without re-authenticating.`,
    )
    .setVersion('0.1.0')
    .addBearerAuth({
      type: 'http',
      scheme: 'bearer',
      bearerFormat: 'JWT',
      description: 'Paste the accessToken returned by /auth/login or /auth/register',
    })
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