import { Body, Controller, HttpCode, HttpStatus, Post, Headers } from "@nestjs/common";
import { ApiOkResponse, ApiOperation, ApiTags } from "@nestjs/swagger";
import { MarketIntelligenceQueryDto } from "./dto/market-intelligence-query.dto.js";
import { MarketIntelligenceService, MarketIntelligenceStats } from "./market-intelligence.service.js";

@ApiTags("Market Intelligence")
@Controller("market-intelligence")
export class MarketIntelligenceController {
  constructor(private readonly svc: MarketIntelligenceService) {}

  @Post("stats")
  @HttpCode(HttpStatus.OK)
  @ApiOperation({
    summary: "Get market intelligence stats and AI insights",
    description: "Returns aggregated trade statistics and AI-driven recommendations based on BPS and UN Comtrade records.",
  })
  @ApiOkResponse({
    description: "Successfully retrieved trade stats and insights",
  })
  async getStats(
    @Body() query: MarketIntelligenceQueryDto,
    @Headers("x-user-id") userId?: string,
  ): Promise<MarketIntelligenceStats> {
    return this.svc.getStats(query.hsCode, userId);
  }
}
