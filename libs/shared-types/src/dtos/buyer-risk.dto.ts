export type BuyerRiskLevel = "LOW" | "MEDIUM" | "HIGH";

export interface BuyerProfile {
  companyName?: string;
  country?: string;
  countryCode?: string;
  requestedSampleBeforeContract?: boolean;
  requestedPaymentOutsidePlatform?: boolean;
}

export interface BuyerCommunicationEntry {
  sender?: "buyer" | "seller" | "agent" | "other";
  message: string;
  sentAt?: string;
  channel?: string;
}

export interface BuyerRedFlagRequest {
  buyerProfile: BuyerProfile;
  communicationHistory: BuyerCommunicationEntry[];
}

export interface BuyerRedFlagFinding {
  id: string;
  description: string;
  category: "SAMPLE" | "JURISDICTION" | "COMMUNICATION" | "PAYMENT";
  severity: BuyerRiskLevel;
  evidence: string;
}

export interface BuyerRedFlagResult {
  riskLevel: BuyerRiskLevel;
  flags: BuyerRedFlagFinding[];
  recommendation: string;
}
