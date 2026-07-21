import { HttpService } from "@nestjs/axios";
import { Body, Controller, Get, Param, Post, Query, Req, UseGuards } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import {
  ApiBearerAuth,
  ApiBody,
  ApiOkResponse,
  ApiOperation,
  ApiTags,
} from "@nestjs/swagger";
import { SkipThrottle } from "@nestjs/throttler";
import { firstValueFrom } from "rxjs";
import { JwtAuthGuard } from "../auth/guards/jwt-auth.guard.js";
import { BuyerSyncDto } from "./dto/buyer-sync.dto.js";
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

  @Get("buyers")
  // Read-only DB directory listing — not an embedding/LLM call. Exclude it from the
  // stricter 'ai-endpoints' budget (20/min) so filter/pagination bursts don't 429;
  // the 'default' throttler (100/min) still applies.
  @SkipThrottle({ "ai-endpoints": true })
  @ApiOperation({
    summary: "List/search buyers from the synchronized DB",
    description:
      "Reads the synchronized production buyer table (real + synthetic). Filters: q, country, hs, source, is_synthetic, min_credibility; sorting + pagination. Never proxies TradeAtlas directly.",
  })
  async listBuyers(@Query() query: Record<string, unknown>, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/api/v1/buyers`, {
          headers: buildForwardHeaders(req),
          params: query,
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Post("buyers/sync")
  @ApiOperation({
    summary: "Trigger a real-buyer sync (enqueues the ETL TradeAtlas sync task)",
    description:
      "Dynamic: pass the product's HS codes + target markets. Enqueues etl.sync_tradeatlas_buyers; returns a task id immediately. Real buyers land in the DB and become matchable via /matching/search.",
  })
  @ApiBody({ type: BuyerSyncDto })
  async syncBuyers(@Body() body: BuyerSyncDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/api/v1/buyers/sync`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Get("buyers/stats")
  @SkipThrottle({ "ai-endpoints": true })
  @ApiOperation({ summary: "Buyer directory statistics (real vs simulated, by source & country)" })
  async buyerStats(@Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/api/v1/buyers/stats`, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Get("buyers/analytics")
  @SkipThrottle({ "ai-endpoints": true })
  @ApiOperation({ summary: "Buyer directory analytics (credibility bands, HS, embeddings, recency)" })
  async buyerAnalytics(@Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/api/v1/buyers/analytics`, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Get("buyers/:id")
  @SkipThrottle({ "ai-endpoints": true })
  @ApiOperation({ summary: "Buyer detail by id (full record + source metadata)" })
  async buyerDetail(@Param("id") id: string, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/api/v1/buyers/${encodeURIComponent(id)}`, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }
}
