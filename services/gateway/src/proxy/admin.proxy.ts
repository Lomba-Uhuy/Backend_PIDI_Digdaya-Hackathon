import { HttpService } from "@nestjs/axios";
import { Body, Controller, Get, Param, Patch, Post, Query, Req, UseGuards } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import { ApiBearerAuth, ApiOperation, ApiTags } from "@nestjs/swagger";
import { firstValueFrom } from "rxjs";
import { JwtAuthGuard } from "../auth/guards/jwt-auth.guard.js";
import { buildForwardHeaders, translateAxiosError } from "./proxy.helper.js";

/**
 * Admin API passthrough. JWT is validated here; the `admin` ROLE is enforced by
 * user-service (RolesGuard on x-user-role) so authorization stays centralized.
 */
@ApiTags("Admin")
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller("admin")
export class AdminProxyController {
  private readonly upstream: string;
  constructor(
    private readonly http: HttpService,
    cfg: ConfigService,
  ) {
    this.upstream = cfg.getOrThrow<string>("USER_SERVICE_URL");
  }

  private async fwd(method: "get" | "post" | "patch", suffix: string, req: any, body?: unknown, params?: Record<string, unknown>) {
    try {
      const cfg = { headers: buildForwardHeaders(req), params };
      const url = `${this.upstream}/admin${suffix}`;
      const { data } =
        method === "get"
          ? await firstValueFrom(this.http.get(url, cfg))
          : method === "post"
            ? await firstValueFrom(this.http.post(url, body ?? {}, cfg))
            : await firstValueFrom(this.http.patch(url, body ?? {}, cfg));
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Get("metrics") @ApiOperation({ summary: "Admin dashboard metrics" })
  metrics(@Req() req: any) { return this.fwd("get", "/metrics", req); }

  @Get("users")
  users(@Req() req: any, @Query() q: Record<string, unknown>) { return this.fwd("get", "/users", req, undefined, q); }

  @Get("users/:id")
  user(@Param("id") id: string, @Req() req: any) { return this.fwd("get", `/users/${id}`, req); }

  @Patch("users/:id/role")
  setRole(@Param("id") id: string, @Body() body: unknown, @Req() req: any) { return this.fwd("patch", `/users/${id}/role`, req, body); }

  @Patch("users/:id/plan")
  setPlan(@Param("id") id: string, @Body() body: unknown, @Req() req: any) { return this.fwd("patch", `/users/${id}/plan`, req, body); }

  @Get("companies")
  companies(@Req() req: any, @Query() q: Record<string, unknown>) { return this.fwd("get", "/companies", req, undefined, q); }

  @Get("products")
  products(@Req() req: any, @Query() q: Record<string, unknown>) { return this.fwd("get", "/products", req, undefined, q); }

  @Get("workflows")
  workflows(@Req() req: any, @Query() q: Record<string, unknown>) { return this.fwd("get", "/workflows", req, undefined, q); }

  @Post("workflows/:productId/retry")
  retry(@Param("productId") productId: string, @Req() req: any) { return this.fwd("post", `/workflows/${productId}/retry`, req); }

  @Get("subscriptions")
  subscriptions(@Req() req: any) { return this.fwd("get", "/subscriptions", req); }

  @Get("providers")
  providers(@Req() req: any) { return this.fwd("get", "/providers", req); }

  @Get("activity")
  activity(@Req() req: any, @Query() q: Record<string, unknown>) { return this.fwd("get", "/activity", req, undefined, q); }

  @Get("audit")
  audit(@Req() req: any, @Query() q: Record<string, unknown>) { return this.fwd("get", "/audit", req, undefined, q); }
}
