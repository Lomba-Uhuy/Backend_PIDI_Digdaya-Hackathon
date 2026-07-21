import { HttpService } from "@nestjs/axios";
import { Controller, Get, HttpCode, Param, Post, Req, UseGuards } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import { ApiBearerAuth, ApiOperation, ApiTags } from "@nestjs/swagger";
import { firstValueFrom } from "rxjs";
import { JwtAuthGuard } from "../auth/guards/jwt-auth.guard.js";
import { buildForwardHeaders, translateAxiosError } from "./proxy.helper.js";

@ApiTags("Product Workflow")
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller("products/:productId/workflow")
export class WorkflowProxyController {
  private readonly upstream: string;
  constructor(
    private readonly http: HttpService,
    cfg: ConfigService,
  ) {
    this.upstream = cfg.getOrThrow<string>("USER_SERVICE_URL");
  }

  private async forwardGet(suffix: string, productId: string, req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/products/${productId}/workflow${suffix}`, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Get()
  @ApiOperation({ summary: "Product initialization workflow (status + stages + progress)" })
  get(@Param("productId") productId: string, @Req() req: any) {
    return this.forwardGet("", productId, req);
  }

  @Get("stages")
  @ApiOperation({ summary: "Workflow stages" })
  stages(@Param("productId") productId: string, @Req() req: any) {
    return this.forwardGet("/stages", productId, req);
  }

  @Get("events")
  @ApiOperation({ summary: "Workflow event log" })
  events(@Param("productId") productId: string, @Req() req: any) {
    return this.forwardGet("/events", productId, req);
  }

  @Post()
  @HttpCode(202)
  @ApiOperation({ summary: "Start / retry the initialization workflow (idempotent)" })
  async start(@Param("productId") productId: string, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/products/${productId}/workflow`, {}, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }
}
