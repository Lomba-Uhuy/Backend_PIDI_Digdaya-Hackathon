import { Body, Controller, Post } from "@nestjs/common";
import { ApiBody, ApiOkResponse, ApiOperation, ApiTags } from "@nestjs/swagger";
import { PricingInputDto } from "./dto/pricing-input.dto.js";
import { PricingCalculatorService } from "./pricing.service.js";

const pricingExample = {
  hpp: 3.5,
  originCharges: 0.5,
  qty: 500,
  oceanFreight: 0.3,
  insuranceAmount: 4.4,
  exportDuty: 0.1,
  profitMarginPct: 20,
  hsCode: "0901",
  exchangeRate: 16000,
};

const pricingResponseExample = {
  fobUnit: "4.80",
  fobTotal: "2400.00",
  cfrTotal: "2400.30",
  insuranceAmount: "4.40",
  cifTotal: "2404.70",
  perUnitCIF: "4.8094",
  idr: {
    fobUnit: "76800",
    fobTotal: "38400000",
    cfrTotal: "38404800",
    cifTotal: "38475200",
    perUnitCIF: "76950",
  },
  benchmarkUnitValue: "4.7500",
  pricingWarning: null,
  marginEstimate: "20.00%",
  exchangeRate: 16000,
};

@ApiTags("Pricing")
@Controller("pricing")
export class PricingController {
  constructor(private readonly pricing: PricingCalculatorService) {}

  @Post("calculate-price")
  @ApiOperation({ summary: "Calculate FOB / CFR / CIF export price" })
  @ApiBody({
    type: PricingInputDto,
    examples: { default: { value: pricingExample } },
  })
  @ApiOkResponse({ schema: { example: pricingResponseExample } })
  calculatePrice(@Body() dto: PricingInputDto) {
    return this.pricing.calculate(dto);
  }

  @Post("calculate")
  @ApiOperation({
    summary: "Calculate FOB / CFR / CIF export price",
    deprecated: true,
  })
  @ApiBody({
    type: PricingInputDto,
    examples: { default: { value: pricingExample } },
  })
  @ApiOkResponse({ schema: { example: pricingResponseExample } })
  calculateLegacy(@Body() dto: PricingInputDto) {
    return this.pricing.calculate(dto);
  }
}
