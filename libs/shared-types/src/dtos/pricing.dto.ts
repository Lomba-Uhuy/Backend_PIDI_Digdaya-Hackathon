export interface PricingRequest {
  hpp: number;
  originCharges: number;
  qty: number;
  oceanFreight: number;
  /** Direct insurance amount in USD; preferred for calculate-price */
  insuranceAmount?: number;
  /** Legacy rate-based insurance input retained for backward compatibility */
  insuranceRate?: number;
  /** Export duty / bea ekspor in USD, folded into FOB seller-side costs */
  exportDuty?: number;
  /** Profit margin percentage (default 20%) */
  profitMarginPct?: number;
  /** HS code for benchmark comparison (e.g. '0901' or '09') */
  hsCode?: string;
  /** IDR per 1 USD exchange rate (default 16000) */
  exchangeRate?: number;
}

export interface PricingBreakdown {
  fobUnit: string;
  fobTotal: string;
  cfrTotal: string;
  insuranceAmount: string;
  cifTotal: string;
  perUnitCIF: string;
  /** All values in IDR (converted at the supplied exchange rate) */
  idr: {
    fobUnit: string;
    fobTotal: string;
    cfrTotal: string;
    cifTotal: string;
    perUnitCIF: string;
  };
  /** Average export unit value from BPS/Comtrade for the supplied HS code */
  benchmarkUnitValue: string | null;
  /** Warning if CIF deviates >30% from BPS benchmark */
  pricingWarning: string | null;
  marginEstimate: string;
  exchangeRate: number;
}
