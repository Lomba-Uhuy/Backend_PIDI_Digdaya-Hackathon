import { Module } from '@nestjs/common';
import { PricingCalculatorService } from './pricing.service.js';
import { PricingController } from './pricing.controller.js';

@Module({
  controllers: [PricingController],
  providers: [PricingCalculatorService],
  exports: [PricingCalculatorService],
})
export class PricingModule {}