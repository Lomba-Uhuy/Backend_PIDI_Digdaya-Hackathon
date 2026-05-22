export interface PricingRequest {
  hpp: number;
  originCharges: number;
  qty: number;
  oceanFreight: number;
  insuranceRate: number;
}

export interface PricingBreakdown {
  fobUnit: string;
  fobTotal: string;
  cfrTotal: string;
  insuranceAmount: string;
  cifTotal: string;
  perUnitCIF: string;
  benchmarkUnitValue: string | null;
  pricingWarning: string | null;
  marginEstimate: string;
}