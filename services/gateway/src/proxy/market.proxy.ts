import { HttpService } from "@nestjs/axios";
import { Controller, Get, Query, Req, UseGuards } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import { ApiBearerAuth, ApiOperation, ApiTags } from "@nestjs/swagger";
import { firstValueFrom } from "rxjs";
import { JwtAuthGuard } from "../auth/guards/jwt-auth.guard.js";
import { buildForwardHeaders, translateAxiosError } from "./proxy.helper.js";

@ApiTags("Market Reference")
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller("market")
export class MarketProxyController {
  private readonly upstream: string;
  constructor(
    private readonly http: HttpService,
    cfg: ConfigService,
  ) {
    this.upstream = cfg.getOrThrow<string>("USER_SERVICE_URL");
  }

  @Get("hs-codes")
  @ApiOperation({ summary: "HS codes that have real ingested trade data" })
  async hsCodes(@Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/market/hs-codes`, { headers: buildForwardHeaders(req) }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Get("top-markets")
  @ApiOperation({ summary: "Top destination countries for an HS chapter (real BPS data)" })
  async topMarkets(@Req() req: any, @Query("hs") hs?: string, @Query("flow") flow?: string) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/market/top-markets`, {
          headers: buildForwardHeaders(req),
          params: { hs, flow },
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Get("regions")
  @ApiOperation({ summary: "Destination countries present in the trade data" })
  async regions(@Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/market/regions`, { headers: buildForwardHeaders(req) }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }
}
