import { describe, expect, it } from 'vitest';
import { PricingCalculatorService } from './pricing.service.js';

describe('PricingCalculatorService', () => {
  const svc = new PricingCalculatorService();

  it('computes FOB, CFR, CIF correctly with Incoterms 2020 + 110% insurance', () => {
    const r = svc.calculate({
      hpp: 100_000,
      originCharges: 10_000,
      qty: 100,
      oceanFreight: 500_000,
      insuranceRate: 0.005,
    });
    // FOB = (100_000 + 10_000) × 100 = 11_000_000
    expect(r.fobTotal).toBe('11000000.00');
    // CFR = FOB + ocean = 11_500_000
    expect(r.cfrTotal).toBe('11500000.00');
    // Insurance = 0.005 × 1.10 × 11_500_000 = 63_250
    expect(r.insuranceAmount).toBe('63250.00');
    // CIF = CFR + insurance = 11_563_250
    expect(r.cifTotal).toBe('11563250.00');
  });

  it('avoids float precision errors at high quantities', () => {
    const r = svc.calculate({
      hpp: 0.1, originCharges: 0.2, qty: 3, oceanFreight: 0, insuranceRate: 0,
    });
    // 0.1 + 0.2 in float math = 0.30000000000000004
    // Decimal.js gives us exact 0.30
    expect(r.fobUnit).toBe('0.30');
    expect(r.fobTotal).toBe('0.90');
  });
});