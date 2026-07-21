import { HttpService } from "@nestjs/axios";
import { Body, Controller, Get, Post, Req, UseGuards } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import { ApiBearerAuth, ApiOperation, ApiTags } from "@nestjs/swagger";
import { firstValueFrom } from "rxjs";
import { JwtAuthGuard } from "../auth/guards/jwt-auth.guard.js";
import { buildForwardHeaders, translateAxiosError } from "./proxy.helper.js";

@ApiTags("Subscription")
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller("subscription")
export class SubscriptionProxyController {
  private readonly upstream: string;
  constructor(
    private readonly http: HttpService,
    cfg: ConfigService,
  ) {
    this.upstream = cfg.getOrThrow<string>("USER_SERVICE_URL");
  }

  private async get(suffix: string, req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/subscription${suffix}`, { headers: buildForwardHeaders(req) }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Get("me")
  @ApiOperation({ summary: "Caller subscription + entitlements" })
  me(@Req() req: any) {
    return this.get("/me", req);
  }

  // NOTE: GET /subscription/plans is served PUBLICLY by PublicPlansProxyController
  // (the landing page must read the plan catalogue without a session).

  @Get("feature/advanced-analytics")
  @ApiOperation({ summary: "Feature-gate probe" })
  featureProbe(@Req() req: any) {
    return this.get("/feature/advanced-analytics", req);
  }

  @Get("admin/ping")
  @ApiOperation({ summary: "Admin-role probe" })
  adminPing(@Req() req: any) {
    return this.get("/admin/ping", req);
  }

  @Post("change")
  @ApiOperation({ summary: "Change plan (self-service)" })
  async change(@Body() body: unknown, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/subscription/change`, body ?? {}, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }
}
