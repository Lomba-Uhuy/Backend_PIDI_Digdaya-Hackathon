import { describe, expect, it } from "vitest";
import type { PricingBenchmarkService } from "./pricing-benchmark.service.js";
import { PricingCalculatorService } from "./pricing.service.js";

describe("PricingCalculatorService", () => {
  const benchmarkService = {
    lookupExportUnitValue: async () => null,
  } as unknown as PricingBenchmarkService;

  const svc = new PricingCalculatorService(benchmarkService);

  it("computes FOB, CFR, CIF correctly with profit margin, export duty, and direct insurance", async () => {
    const r = await svc.calculate({
      hpp: 100,
      originCharges: 10,
      qty: 100,
      oceanFreight: 500,
      insuranceAmount: 50,
      exportDuty: 5,
      profitMarginPct: 20,
      exchangeRate: 16000,
    });
    // FOB = HPP + 20% profit + domestic charges + export duty
    expect(r.fobUnit).toBe("135.00");
    expect(r.fobTotal).toBe("13500.00");
    // CFR = FOB + freight
    expect(r.cfrTotal).toBe("14000.00");
    // CIF = CFR + insurance
    expect(r.insuranceAmount).toBe("50.00");
    expect(r.cifTotal).toBe("14050.00");
    expect(r.idr.fobTotal).toBe("216000000");
    expect(r.exchangeRate).toBe(16000);
  });

  it("avoids float precision errors at high quantities", async () => {
    const r = await svc.calculate({
      hpp: 0.1,
      originCharges: 0.2,
      qty: 3,
      oceanFreight: 0,
      insuranceAmount: 0,
      profitMarginPct: 0,
    });
    // 0.1 + 0.2 in float math = 0.30000000000000004
    // Decimal.js gives us exact 0.30
    expect(r.fobUnit).toBe("0.30");
    expect(r.fobTotal).toBe("0.90");
  });

  it("flags prices that deviate too far from the benchmark", async () => {
    const benchmarkedService = new PricingCalculatorService({
      lookupExportUnitValue: async () => ({
        hsCode: "0901",
        unitValueUsd: 5,
        sampleCount: 12,
        source: "bps.trade_flows",
      }),
    } as unknown as PricingBenchmarkService);

    const result = await benchmarkedService.calculate({
      hpp: 100,
      originCharges: 10,
      qty: 1,
      oceanFreight: 0,
      insuranceAmount: 0,
      profitMarginPct: 20,
      hsCode: "0901",
      exchangeRate: 16000,
    });

    expect(result.benchmarkUnitValue).toBe("5.0000");
    expect(result.pricingWarning).toContain("benchmark for HS 0901");
  });
});
