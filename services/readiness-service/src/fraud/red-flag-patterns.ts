import type { FlagSeverity, FlagCategory } from '@tradeconnect/shared-types/dtos';

export interface RedFlagPattern {
  id: string;
  description: string;
  regex: RegExp;
  severity: FlagSeverity;
  category: FlagCategory;
  referenceStandard: string;
}

/**
 * Trade-fraud red flag catalogue.
 * References: FinCEN advisories, BIS export red flags, FATF TBML risk indicators.
 * Source: BAGIAN 4 of the v2 architecture spec.
 */
export const RED_FLAG_PATTERNS: RedFlagPattern[] = [
  {
    id: 'OFFSHORE_PAYMENT',
    description: 'Tekanan pembayaran ke rekening offshore',
    regex: /offshore.{0,40}(payment|transfer|account)|cash.{0,20}(wallet|offshore)/i,
    severity: 'CRITICAL',
    category: 'PAYMENT',
    referenceStandard: 'FinCEN FIN-2010-A001',
  },
  {
    id: 'THIRD_PARTY_CONSIGNEE',
    description: 'Konsignee bukan entitas bisnis akhir (potensi penghindaran sanksi)',
    regex: /third.{0,10}party.{0,20}consign|freight forwarder as consignee/i,
    severity: 'HIGH',
    category: 'LOGISTICS',
    referenceStandard: 'BIS Export Red Flags',
  },
  {
    id: 'CIRCUITOUS_ROUTING',
    description: 'Rute pengiriman tidak efisien atau menyimpang',
    regex: /(reroute|circuitous|unusual route|transit through).{0,50}(sanctioned|embargoed)/i,
    severity: 'HIGH',
    category: 'LOGISTICS',
    referenceStandard: 'FATF TBML Risk Indicators',
  },
  {
    id: 'INVOICE_MANIPULATION',
    description: 'Permintaan manipulasi nilai invoice',
    regex: /(under.invoice|over.invoice|adjust.{0,20}value|reduce.{0,30}customs)/i,
    severity: 'CRITICAL',
    category: 'INVOICE',
    referenceStandard: 'FATF TBML Risk Indicators',
  },
  {
    id: 'KBLI_MISMATCH',
    description: 'Produk tidak sesuai bidang usaha pembeli',
    regex: /urgent|immediately ship|no inspection|waive quality/i,
    severity: 'MEDIUM',
    category: 'ENTITY',
    referenceStandard: 'OSS RBA KBLI Verification',
  },
  {
    id: 'CRYPTO_PAYMENT',
    description: 'Permintaan pembayaran via kripto tanpa justifikasi',
    regex: /(bitcoin|cryptocurrency|usdt|stablecoin).{0,40}(payment|transfer)/i,
    severity: 'HIGH',
    category: 'PAYMENT',
    referenceStandard: 'FinCEN Advisory 2022',
  },
];