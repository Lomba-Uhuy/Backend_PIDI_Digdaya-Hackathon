import { HttpService } from '@nestjs/axios';
import { Body, Controller, Post, Req, UseGuards } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { ApiBearerAuth, ApiTags } from '@nestjs/swagger';
import { firstValueFrom } from 'rxjs';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard.js';
import { buildForwardHeaders, translateAxiosError } from './proxy.helper.js';

@ApiTags('AI Buyer Discovery')
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller('matching')
export class MatchingProxyController {
  private readonly upstream: string;
  constructor(private readonly http: HttpService, cfg: ConfigService) {
    this.upstream = cfg.getOrThrow<string>('MATCHING_SERVICE_URL');
  }

  @Post('search')
  async search(@Body() body: unknown, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/api/v1/match`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) { translateAxiosError(e); }
  }

  @Post('classify-hs')
  async classifyHs(@Body() body: unknown, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/api/v1/hs-classifier/classify`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) { translateAxiosError(e); }
  }
}