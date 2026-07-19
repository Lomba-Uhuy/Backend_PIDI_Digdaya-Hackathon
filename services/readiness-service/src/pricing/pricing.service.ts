import { Injectable, Logger } from "@nestjs/common";
import type { PricingBreakdown } from "@tradeconnect/shared-types/dtos";
import Decimal from "decimal.js";
import { PricingBenchmarkService } from "./pricing-benchmark.service.js";

export interface PricingInput {
  hpp: number;
  originCharges: number;
  qty: number;
  oceanFreight: number;
  insuranceAmount?: number;
  insuranceRate?: number;
  exportDuty?: number;
  profitMarginPct?: number;
  hsCode?: string;
  exchangeRate?: number;
}

@Injectable()
export class PricingCalculatorService {
  private readonly logger = new Logger(PricingCalculatorService.name);

  constructor(private readonly benchmarkService: PricingBenchmarkService) {}

  /**
   * Incoterms-style pricing waterfall:
   *   FOB unit  = HPP + profit margin + domestic charges + export duty
   *   FOB total = FOB unit × qty
   *   CFR total = FOB total + international freight
   *   CIF total = CFR + insurance
   *
   * Uses Decimal.js throughout — never `number` arithmetic for money.
   */
  async calculate(input: PricingInput): Promise<PricingBreakdown> {
    Decimal.set({ precision: 18, rounding: Decimal.ROUND_HALF_UP });

    const quantity = new Decimal(input.qty);
    const hpp = new Decimal(input.hpp);
    const domesticCharges = new Decimal(input.originCharges);
    const freight = new Decimal(input.oceanFreight);
    const profitMarginPct = new Decimal(input.profitMarginPct ?? 20);
    const exportDuty = new Decimal(input.exportDuty ?? 0);
    const exchangeRate = new Decimal(input.exchangeRate ?? 16_000);

    const profitAmount = hpp.times(profitMarginPct).dividedBy(100);
    const fobUnit = hpp
      .plus(profitAmount)
      .plus(domesticCharges)
      .plus(exportDuty);
    const fobTotal = fobUnit.times(quantity);
    const cfrTotal = fobTotal.plus(freight);

    const insuranceAmount = this.resolveInsuranceAmount(input, cfrTotal);
    const cifTotal = cfrTotal.plus(insuranceAmount);
    const perUnitCIF = cifTotal.dividedBy(quantity);

    const benchmark = await this.benchmarkService.lookupExportUnitValue(
      input.hsCode,
    );
    const benchmarkUnitValue = benchmark
      ? benchmark.unitValueUsd.toFixed(4)
      : null;
    const pricingWarning = benchmark
      ? this.buildPricingWarning(
          perUnitCIF,
          benchmark.unitValueUsd,
          input.hsCode,
          benchmark.sampleCount,
        )
      : null;

    const idrRate = exchangeRate;
    const idr = {
      fobUnit: fobUnit.times(idrRate).toFixed(0),
      fobTotal: fobTotal.times(idrRate).toFixed(0),
      cfrTotal: cfrTotal.times(idrRate).toFixed(0),
      cifTotal: cifTotal.times(idrRate).toFixed(0),
      perUnitCIF: perUnitCIF.times(idrRate).toFixed(0),
    };

    this.logger.log(
      `pricing.calc hs=${input.hsCode ?? "-"} fob=${fobTotal.toFixed(2)} cfr=${cfrTotal.toFixed(2)} cif=${cifTotal.toFixed(2)}`,
    );

    return {
      fobUnit: fobUnit.toFixed(2),
      fobTotal: fobTotal.toFixed(2),
      cfrTotal: cfrTotal.toFixed(2),
      insuranceAmount: insuranceAmount.toFixed(2),
      cifTotal: cifTotal.toFixed(2),
      perUnitCIF: perUnitCIF.toFixed(4),
      idr,
      benchmarkUnitValue,
      pricingWarning,
      marginEstimate: `${profitMarginPct.toFixed(2)}%`,
      exchangeRate: idrRate.toNumber(),
    };
  }

  private resolveInsuranceAmount(
    input: PricingInput,
    cfrTotal: Decimal,
  ): Decimal {
    if (input.insuranceAmount !== undefined) {
      return new Decimal(input.insuranceAmount);
    }

    if (input.insuranceRate !== undefined) {
      return new Decimal(input.insuranceRate).times("1.10").times(cfrTotal);
    }

    return new Decimal(0);
  }

  private buildPricingWarning(
    perUnitCif: Decimal,
    benchmarkUnitValue: number,
    hsCode: string | undefined,
    sampleCount: number,
  ): string | null {
    if (!Number.isFinite(benchmarkUnitValue) || benchmarkUnitValue <= 0) {
      return null;
    }

    const benchmark = new Decimal(benchmarkUnitValue);
    const deviation = perUnitCif.minus(benchmark).abs().dividedBy(benchmark);
    if (deviation.lte(0.3)) {
      return null;
    }

    const direction = perUnitCif.greaterThan(benchmark) ? "above" : "below";
    return `CIF per unit is ${deviation.times(100).toFixed(1)}% ${direction} the BPS export unit value benchmark for HS ${hsCode ?? "unknown"} (n=${sampleCount}).`;
  }
}
