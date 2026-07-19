import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { BullModule } from '@nestjs/bullmq';
import { JwtModule } from '@nestjs/jwt';
import { TerminusModule } from '@nestjs/terminus';
import { LoggerModule } from 'nestjs-pino';

import { configuration } from './config/configuration.js';
import { DatabaseModule } from './database/database.module.js';
import { AuthModule } from './auth/auth.module.js';
import { UmkmModule } from './umkm/umkm.module.js';
import { ProductModule } from './product/product.module.js';
import { DealModule } from './deal/deal.module.js';
import { ReminderModule } from './reminder/reminder.module.js';
import { MarketModule } from './market/market.module.js';
import { QueueModule } from './queue/queue.module.js';
import { HealthController } from './common/health.controller.js';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true, load: [configuration], cache: true }),

    LoggerModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (cfg: ConfigService) => ({
        pinoHttp: {
          level: cfg.get<string>('LOG_LEVEL') ?? 'info',
          transport:
            cfg.get<string>('NODE_ENV') === 'development'
              ? { target: 'pino-pretty', options: { colorize: true, singleLine: true } }
              : undefined,
          customProps: () => ({ service: 'user-service' }),
        },
      }),
    }),

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
          defaultJobOptions: {
            removeOnComplete: { age: 86_400 },
            removeOnFail: { age: 604_800 },
          },
        };
      },
    }),

    JwtModule.registerAsync({
      global: true,
      inject: [ConfigService],
      useFactory: (cfg: ConfigService) => ({
        secret: cfg.getOrThrow<string>('JWT_SECRET'),
        signOptions: {
          expiresIn: cfg.get<string>('JWT_ACCESS_TOKEN_EXPIRES') ?? '30m',
          algorithm: 'HS256',
        },
      }),
    }),

    TerminusModule,
    DatabaseModule,
    AuthModule,
    QueueModule,
    UmkmModule,
    ProductModule,
    DealModule,
    ReminderModule,
    MarketModule,
  ],
  controllers: [HealthController],
})
export class AppModule {}