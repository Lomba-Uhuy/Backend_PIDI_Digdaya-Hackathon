import { HttpService } from "@nestjs/axios";
import { Body, Controller, Post, Req, UseGuards } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import {
  ApiBearerAuth,
  ApiBody,
  ApiOkResponse,
  ApiOperation,
  ApiTags,
} from "@nestjs/swagger";
import { firstValueFrom } from "rxjs";
import { JwtAuthGuard } from "../auth/guards/jwt-auth.guard.js";
import { GenerateReplyDto } from "./dto/generate-reply.dto.js";
import { IntentDto } from "./dto/intent.dto.js";
import { NegotiationDraftDto } from "./dto/negotiation-draft.dto.js";
import {
  GenerateReplyResponseDto,
  IntentResponseDto,
  NegotiationDraftResponseDto,
} from "./dto/comms-response.dto.js";
import {
  generateReplyExample,
  intentExample,
  negotiationDraftExample,
} from "./swagger-examples.js";
import { buildForwardHeaders, translateAxiosError } from "./proxy.helper.js";

@ApiTags("Deal Communication")
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller("negotiations")
export class CommsProxyController {
  private readonly upstream: string;
  constructor(
    private readonly http: HttpService,
    cfg: ConfigService,
  ) {
    this.upstream = cfg.getOrThrow<string>("COMMS_SERVICE_URL");
  }

  @Post("draft")
  @ApiOperation({
    summary: "Draft negotiation reply (legacy — use /generate-reply for new integrations)",
    description: "RAG + LLM pipeline with guardrails. Input is in Bahasa Indonesia or English.",
  })
  @ApiBody({
    type: NegotiationDraftDto,
    examples: { default: { value: negotiationDraftExample } },
  })
  @ApiOkResponse({ type: NegotiationDraftResponseDto })
  async draft(@Body() body: NegotiationDraftDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/api/v1/negotiations/draft`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Post("generate-reply")
  @ApiOperation({
    summary: "Generate English reply to an importer email",
    description:
      "Accepts raw importer email text + product ID. Retrieves relevant export knowledge (Incoterms, regs, templates), generates a professional English draft, and validates it through guardrails (no price below HPP, no desperate language).",
  })
  @ApiBody({
    type: GenerateReplyDto,
    examples: { default: { value: generateReplyExample } },
  })
  @ApiOkResponse({ type: GenerateReplyResponseDto })
  async generateReply(@Body() body: GenerateReplyDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/api/v1/generate-reply`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Post("classify-intent")
  @ApiOperation({
    summary: "Classify importer email intent",
    description:
      "Returns one of: inquiry | negotiation | complaint | spam, with confidence score and per-class scores.",
  })
  @ApiBody({
    type: IntentDto,
    examples: { default: { value: intentExample } },
  })
  @ApiOkResponse({ type: IntentResponseDto })
  async classifyIntent(@Body() body: IntentDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/api/v1/classify-intent`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }
}
