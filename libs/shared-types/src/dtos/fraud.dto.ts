export type RiskLevel = 'GREEN' | 'YELLOW' | 'RED' | 'CRITICAL';
export type FlagSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type FlagCategory = 'PAYMENT' | 'LOGISTICS' | 'ENTITY' | 'INVOICE';

export interface DetectedFlag {
  id: string;
  description: string;
  severity: FlagSeverity;
  category: FlagCategory;
  referenceStandard: string;
  matchedText: string;
}

export interface FraudScanRequest {
  buyerId: string;
  termsText: string;
  contractText?: string;
}

export interface FraudScanResult {
  riskLevel: RiskLevel;
  riskScore: number;
  flags: DetectedFlag[];
  recommendation: string;
}