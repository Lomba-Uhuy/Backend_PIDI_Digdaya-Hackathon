import { Controller, Get } from '@nestjs/common';
import { HealthCheck, HealthCheckService } from '@nestjs/terminus';

@Controller('health')
export class HealthController {
  constructor(private readonly health: HealthCheckService) {}

  @Get()
  liveness() { return { status: 'ok' }; }

  @Get('ready')
  @HealthCheck()
  readiness() { return this.health.check([]); }
}