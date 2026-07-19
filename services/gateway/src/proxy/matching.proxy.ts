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
import { HsClassifyDto } from "./dto/hs-classify.dto.js";
import { MatchBuyersDto } from "./dto/match-buyers.dto.js";
import { MatchingSearchDto } from "./dto/matching-search.dto.js";
import { HsClassifyResponseDto, MatchResultResponseDto } from "./dto/matching-response.dto.js";
import {
  hsClassifyExample,
  matchBuyersExample,
  matchingSearchExample,
} from "./swagger-examples.js";
import { buildForwardHeaders, translateAxiosError } from "./proxy.helper.js";

@ApiTags("AI Buyer Discovery")
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller("matching")
export class MatchingProxyController {
  private readonly upstream: string;
  constructor(
    private readonly http: HttpService,
    cfg: ConfigService,
  ) {
    this.upstream = cfg.getOrThrow<string>("MATCHING_SERVICE_URL");
  }

  @Post("search")
  @ApiOperation({
    summary: "Find buyers by product ID",
    description: "Loads the pre-computed product embedding from DB then runs pgvector ANN search.",
  })
  @ApiBody({
    type: MatchingSearchDto,
    examples: { default: { value: matchingSearchExample } },
  })
  @ApiOkResponse({ type: [MatchResultResponseDto] })
  async search(@Body() body: MatchingSearchDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/api/v1/match`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Post("match-buyers")
  @ApiOperation({
    summary: "Find buyers by raw embedding vector",
    description:
      "Accepts a 1024-dim embedding vector directly (no DB lookup). Supports optional filters: country, minimum MOQ, HS category prefix.",
  })
  @ApiBody({
    type: MatchBuyersDto,
    examples: { default: { value: matchBuyersExample } },
  })
  @ApiOkResponse({ type: [MatchResultResponseDto] })
  async matchBuyers(@Body() body: MatchBuyersDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/api/v1/match-buyers`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Post("classify-hs")
  @ApiOperation({
    summary: "Classify product description into HS code",
    description: "Uses multilingual-e5-large embeddings to match description against HS code corpus.",
  })
  @ApiBody({
    type: HsClassifyDto,
    examples: { default: { value: hsClassifyExample } },
  })
  @ApiOkResponse({ type: HsClassifyResponseDto })
  async classifyHs(@Body() body: HsClassifyDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/api/v1/hs-classifier/classify`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }
}
