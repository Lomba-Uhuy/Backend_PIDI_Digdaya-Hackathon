import { Injectable, Logger } from '@nestjs/common';
import Decimal from 'decimal.js';
import type { PricingBreakdown } from '@tradeconnect/shared-types/dtos';

export interface PricingInput {
  hpp: number;
  originCharges: number;
  qty: number;
  oceanFreight: number;
  insuranceRate: number;
}

@Injectable()
export class PricingCalculatorService {
  private readonly logger = new Logger(PricingCalculatorService.name);

  /**
   * Incoterms 2020 pricing waterfall:
   *   FOB unit  = HPP + Origin Charges
   *   FOB total = FOB unit × qty
   *   CFR total = FOB total + Ocean Freight
   *   Insurance = rate × 1.10 × CFR     (industry standard: cover 110% of CFR)
   *   CIF total = CFR + Insurance
   *
   * Uses Decimal.js throughout — never `number` arithmetic for money.
   */
  calculate(input: PricingInput): PricingBreakdown {
    Decimal.set({ precision: 12, rounding: Decimal.ROUND_HALF_UP });

    const fobUnit = new Decimal(input.hpp).plus(input.originCharges);
    const fobTotal = fobUnit.times(input.qty);
    const cfrTotal = fobTotal.plus(input.oceanFreight);

    const insuranceAmount = new Decimal(input.insuranceRate).times('1.10').times(cfrTotal);
    const cifTotal = cfrTotal.plus(insuranceAmount);
    const perUnitCIF = cifTotal.dividedBy(input.qty);

    // Margin estimate = (CIF − FOB) / CIF × 100  — represents trade overhead
    const marginEstimate = cifTotal.minus(fobTotal).dividedBy(cifTotal).times(100);

    this.logger.log(
      `pricing.calc fob=${fobTotal.toFixed(2)} cfr=${cfrTotal.toFixed(2)} cif=${cifTotal.toFixed(2)}`,
    );

    return {
      fobUnit:            fobUnit.toFixed(2),
      fobTotal:           fobTotal.toFixed(2),
      cfrTotal:           cfrTotal.toFixed(2),
      insuranceAmount:    insuranceAmount.toFixed(2),
      cifTotal:           cifTotal.toFixed(2),
      perUnitCIF:         perUnitCIF.toFixed(4),
      benchmarkUnitValue: null, // populated by ETL when UN Comtrade data is available
      pricingWarning:     this.checkPricingAnomaly(perUnitCIF),
      marginEstimate:     `${marginEstimate.toFixed(2)}%`,
    };
  }

  private checkPricingAnomaly(_perUnitCIF: Decimal): string | null {
    // TODO: compare with stored Export Unit Value from UN Comtrade
    // < Q1 historical → underpricing warning
    // > Q3 historical → overpricing warning
    return null;
  }
}