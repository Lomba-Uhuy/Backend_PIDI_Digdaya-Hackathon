import { Module } from "@nestjs/common";
import { MarketIntelligenceController } from "./market-intelligence.controller.js";
import { MarketIntelligenceService } from "./market-intelligence.service.js";

@Module({
  controllers: [MarketIntelligenceController],
  providers: [MarketIntelligenceService],
  exports: [MarketIntelligenceService],
})
export class MarketIntelligenceModule {}
