import { Body, Controller, Post } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { PricingInputDto } from './dto/pricing-input.dto.js';
import { PricingCalculatorService } from './pricing.service.js';

@ApiTags('Pricing')
@Controller('pricing')
export class PricingController {
  constructor(private readonly pricing: PricingCalculatorService) {}

  @Post('calculate')
  calculate(@Body() dto: PricingInputDto) {
    return this.pricing.calculate(dto);
  }
}