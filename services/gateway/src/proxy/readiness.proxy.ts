import { HttpService } from '@nestjs/axios';
import { Body, Controller, Post, Req, UseGuards } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { ApiBearerAuth, ApiTags } from '@nestjs/swagger';
import { firstValueFrom } from 'rxjs';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard.js';
import { buildForwardHeaders, translateAxiosError } from './proxy.helper.js';

@ApiTags('Deal Readiness')
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller('readiness')
export class ReadinessProxyController {
  private readonly upstream: string;
  constructor(private readonly http: HttpService, cfg: ConfigService) {
    this.upstream = cfg.getOrThrow<string>('READINESS_SERVICE_URL');
  }

  @Post('pricing')
  async pricing(@Body() body: unknown, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/api/v1/pricing/calculate`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) { translateAxiosError(e); }
  }

  @Post('fraud-scan')
  async fraudScan(@Body() body: unknown, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/api/v1/fraud/scan`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) { translateAxiosError(e); }
  }
}