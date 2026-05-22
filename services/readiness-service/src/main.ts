import 'reflect-metadata';
import helmet from '@fastify/helmet';
import { ValidationPipe } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { NestFactory } from '@nestjs/core';
import { FastifyAdapter, type NestFastifyApplication } from '@nestjs/platform-fastify';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { Logger } from 'nestjs-pino';
import { AppModule } from './app.module.js';

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create<NestFastifyApplication>(
    AppModule,
    new FastifyAdapter({ logger: false, trustProxy: true }),
    { bufferLogs: true },
  );
  app.useLogger(app.get(Logger));
  await app.register(helmet, { contentSecurityPolicy: false });
  app.useGlobalPipes(new ValidationPipe({ transform: true, whitelist: true, forbidNonWhitelisted: true }));

  const swaggerConfig = new DocumentBuilder()
    .setTitle('TradeConnect Readiness')
    .setDescription('FOB/CIF pricing, fraud detection, document compliance')
    .setVersion('0.1.0')
    .build();
  SwaggerModule.setup('docs', app, SwaggerModule.createDocument(app, swaggerConfig));

  const port = app.get(ConfigService).get<number>('PORT') ?? 3002;
  await app.listen(port, '0.0.0.0');
  // biome-ignore lint/suspicious/noConsole: bootstrap log
  console.log(`Readiness Service listening on http://0.0.0.0:${port}`);
}

bootstrap().catch((err) => {
  // biome-ignore lint/suspicious/noConsole: fatal
  console.error('Readiness Service failed to start:', err);
  process.exit(1);
});