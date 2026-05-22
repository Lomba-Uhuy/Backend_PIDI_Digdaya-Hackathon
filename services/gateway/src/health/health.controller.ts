import { Controller, Get } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import {
  HealthCheck,
  HealthCheckService,
  HttpHealthIndicator,
} from '@nestjs/terminus';

@Controller('health')
export class HealthController {
  constructor(
    private readonly health: HealthCheckService,
    private readonly http: HttpHealthIndicator,
    private readonly config: ConfigService,
  ) {}

  @Get()
  liveness(): { status: 'ok' } {
    return { status: 'ok' };
  }

  @Get('ready')
  @HealthCheck()
  readiness() {
    const userUrl = this.config.get<string>('USER_SERVICE_URL');
    const matchingUrl = this.config.get<string>('MATCHING_SERVICE_URL');
    const commsUrl = this.config.get<string>('COMMS_SERVICE_URL');
    const readinessUrl = this.config.get<string>('READINESS_SERVICE_URL');

    return this.health.check([
      () => this.http.pingCheck('user-service', `${userUrl}/health`),
      () => this.http.pingCheck('readiness-service', `${readinessUrl}/health`),
      () => this.http.pingCheck('matching-service', `${matchingUrl}/health`),
      () => this.http.pingCheck('comms-service', `${commsUrl}/health`),
    ]);
  }
}