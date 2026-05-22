import { BullBoardModule } from '@bull-board/nestjs';
import { FastifyAdapter } from '@bull-board/fastify';
import { HttpModule } from '@nestjs/axios';
import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { APP_GUARD } from '@nestjs/core';
import { BullModule } from '@nestjs/bullmq';
import { JwtModule } from '@nestjs/jwt';
import { TerminusModule } from '@nestjs/terminus';
import { ThrottlerModule } from '@nestjs/throttler';
import { LoggerModule } from 'nestjs-pino';

import { configuration } from './config/configuration.js';
import { AuthModule } from './auth/auth.module.js';
import { CustomThrottlerGuard } from './middleware/custom-throttler.guard.js';
import { ProxyModule } from './proxy/proxy.module.js';
import { HealthController } from './health/health.controller.js';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      load: [configuration],
      cache: true,
    }),

    // Structured JSON logging
    LoggerModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (cfg: ConfigService) => ({
        pinoHttp: {
          level: cfg.get<string>('LOG_LEVEL') ?? 'info',
          transport:
            cfg.get<string>('NODE_ENV') === 'development'
              ? { target: 'pino-pretty', options: { colorize: true, singleLine: true } }
              : undefined,
          autoLogging: true,
          customProps: () => ({ service: 'gateway' }),
          serializers: {
            req: (req) => ({
              id: req.id,
              method: req.method,
              url: req.url,
              headers: { 'x-request-id': req.headers['x-request-id'] },
            }),
          },
          genReqId: (req) =>
            (req.headers['x-request-id'] as string) ?? crypto.randomUUID(),
        },
      }),
    }),

    // BullMQ — Gateway only reads queues for Bull Board UI, doesn't produce
    BullModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (cfg: ConfigService) => {
        const url = new URL(cfg.getOrThrow<string>('BULL_REDIS_URL'));
        return {
          connection: {
            host: url.hostname,
            port: Number(url.port || 6379),
            db: Number((url.pathname || '/0').slice(1)),
          },
        };
      },
    }),
    BullModule.registerQueue({ name: 'verification' }, { name: 'embeddings' }),

    // Bull Board UI at /admin/queues
    BullBoardModule.forRoot({
      route: '/admin/queues',
      adapter: FastifyAdapter,
    }),

    // JWT verification only (issuance happens in User Service)
    JwtModule.registerAsync({
      global: true,
      inject: [ConfigService],
      useFactory: (cfg: ConfigService) => ({
        secret: cfg.getOrThrow<string>('JWT_SECRET'),
      }),
    }),

    // Rate limiting
    ThrottlerModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (cfg: ConfigService) => [
        {
          name: 'default',
          ttl: (cfg.get<number>('RATE_LIMIT_DEFAULT_TTL') ?? 60) * 1000,
          limit: cfg.get<number>('RATE_LIMIT_DEFAULT_LIMIT') ?? 100,
        },
        {
          name: 'ai-endpoints',
          ttl: (cfg.get<number>('RATE_LIMIT_AI_TTL') ?? 60) * 1000,
          limit: cfg.get<number>('RATE_LIMIT_AI_LIMIT') ?? 20,
        },
      ],
    }),

    HttpModule.register({
      timeout: 30_000,
      maxRedirects: 3,
    }),

    TerminusModule,
    AuthModule,
    ProxyModule,
  ],
  controllers: [HealthController],
  providers: [{ provide: APP_GUARD, useClass: CustomThrottlerGuard }],
})
export class AppModule {}