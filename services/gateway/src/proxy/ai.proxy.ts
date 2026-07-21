import { HttpService } from "@nestjs/axios";
import { Body, Controller, Post, Req, UseGuards } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import { ApiBearerAuth, ApiOperation, ApiTags } from "@nestjs/swagger";
import { firstValueFrom } from "rxjs";
import { JwtAuthGuard } from "../auth/guards/jwt-auth.guard.js";
import { buildForwardHeaders, translateAxiosError } from "./proxy.helper.js";

@ApiTags("AI Consultation")
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller("ai")
export class AiProxyController {
  private readonly upstream: string;
  constructor(
    private readonly http: HttpService,
    cfg: ConfigService,
  ) {
    this.upstream = cfg.getOrThrow<string>("COMMS_SERVICE_URL");
  }

  @Post("chat")
  @ApiOperation({
    summary: "Export-consultation assistant (RAG knowledge base + user business context + LLM)",
  })
  async chat(@Body() body: unknown, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/api/v1/ai/chat`, body, {
          headers: buildForwardHeaders(req),
          timeout: 60_000,
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }
}
