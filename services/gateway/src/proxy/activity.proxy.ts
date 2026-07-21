import { HttpService } from "@nestjs/axios";
import { Controller, Get, Query, Req, UseGuards } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import { ApiBearerAuth, ApiOperation, ApiTags } from "@nestjs/swagger";
import { firstValueFrom } from "rxjs";
import { JwtAuthGuard } from "../auth/guards/jwt-auth.guard.js";
import { buildForwardHeaders, translateAxiosError } from "./proxy.helper.js";

@ApiTags("Activity")
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller("activity")
export class ActivityProxyController {
  private readonly upstream: string;
  constructor(
    private readonly http: HttpService,
    cfg: ConfigService,
  ) {
    this.upstream = cfg.getOrThrow<string>("USER_SERVICE_URL");
  }

  @Get("recent")
  @ApiOperation({ summary: "Recent activity feed (persisted events: deals, PO, sync, product)" })
  async recent(
    @Req() req: any,
    @Query("limit") limit?: string,
    @Query("offset") offset?: string,
    @Query("category") category?: string,
  ) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/activity/recent`, {
          headers: buildForwardHeaders(req),
          params: { limit, offset, category },
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Get("statistics")
  @ApiOperation({ summary: "Activity counts by category + last sync status" })
  async statistics(@Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/activity/statistics`, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }
}
