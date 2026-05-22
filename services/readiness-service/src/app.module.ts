import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TerminusModule } from '@nestjs/terminus';
import { LoggerModule } from 'nestjs-pino';

import { PricingModule } from './pricing/pricing.module.js';
import { FraudModule } from './fraud/fraud.module.js';
import { DocumentModule } from './document/document.module.js';
import { HealthController } from './common/health.controller.js';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true, cache: true }),
    LoggerModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (cfg: ConfigService) => ({
        pinoHttp: {
          level: cfg.get<string>('LOG_LEVEL') ?? 'info',
          transport:
            cfg.get<string>('NODE_ENV') === 'development'
              ? { target: 'pino-pretty', options: { colorize: true, singleLine: true } }
              : undefined,
          customProps: () => ({ service: 'readiness-service' }),
        },
      }),
    }),
    TerminusModule,
    PricingModule,
    FraudModule,
    DocumentModule,
  ],
  controllers: [HealthController],
})
export class AppModule {}