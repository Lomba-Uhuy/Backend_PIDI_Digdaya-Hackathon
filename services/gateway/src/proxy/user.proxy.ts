import { HttpService } from '@nestjs/axios';
import {
  Body, Controller, Get, Param, Post, Req, UseGuards,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { ApiBearerAuth, ApiTags } from '@nestjs/swagger';
import { firstValueFrom } from 'rxjs';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard.js';
import { buildForwardHeaders, translateAxiosError } from './proxy.helper.js';

@ApiTags('UMKM & Products')
@ApiBearerAuth()
@Controller()
export class UserProxyController {
  private readonly upstream: string;

  constructor(http: HttpService, cfg: ConfigService) {
    this.http = http;
    this.upstream = cfg.getOrThrow<string>('USER_SERVICE_URL');
  }
  private readonly http: HttpService;

  // ---- Public auth routes (no guard) ----
  @Post('auth/login')
  async login(@Body() body: unknown, @Req() req: { headers: Record<string, unknown> }) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/auth/login`, body, {
          headers: { 'x-request-id': (req.headers['x-request-id'] as string) ?? crypto.randomUUID() },
        }),
      );
      return data;
    } catch (e) { translateAxiosError(e); }
  }

  // ---- Authenticated routes ----
  @UseGuards(JwtAuthGuard)
  @Post('umkm')
  async createUmkm(@Body() body: unknown, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/umkm`, body, { headers: buildForwardHeaders(req) }),
      );
      return data;
    } catch (e) { translateAxiosError(e); }
  }

  @UseGuards(JwtAuthGuard)
  @Get('umkm/me')
  async getMyUmkm(@Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/umkm/me`, { headers: buildForwardHeaders(req) }),
      );
      return data;
    } catch (e) { translateAxiosError(e); }
  }

  @UseGuards(JwtAuthGuard)
  @Post('umkm/:umkmId/products')
  async createProduct(
    @Param('umkmId') umkmId: string,
    @Body() body: unknown,
    @Req() req: any,
  ) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/umkm/${umkmId}/products`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) { translateAxiosError(e); }
  }
}