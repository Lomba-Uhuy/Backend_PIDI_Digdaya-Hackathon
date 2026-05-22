import { HttpService } from '@nestjs/axios';
import { Body, Controller, Post, Req, UseGuards } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { ApiBearerAuth, ApiTags } from '@nestjs/swagger';
import { firstValueFrom } from 'rxjs';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard.js';
import { buildForwardHeaders, translateAxiosError } from './proxy.helper.js';

@ApiTags('Deal Communication')
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller('negotiations')
export class CommsProxyController {
  private readonly upstream: string;
  constructor(private readonly http: HttpService, cfg: ConfigService) {
    this.upstream = cfg.getOrThrow<string>('COMMS_SERVICE_URL');
  }

  @Post('draft')
  async draft(@Body() body: unknown, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/api/v1/negotiations/draft`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) { translateAxiosError(e); }
  }
}