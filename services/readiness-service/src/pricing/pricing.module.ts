import { Module } from "@nestjs/common";
import { PricingBenchmarkService } from "./pricing-benchmark.service.js";
import { PricingCalculatorService } from "./pricing.service.js";
import { PricingController } from "./pricing.controller.js";

@Module({
  controllers: [PricingController],
  providers: [PricingCalculatorService, PricingBenchmarkService],
  exports: [PricingCalculatorService],
})
export class PricingModule {}
