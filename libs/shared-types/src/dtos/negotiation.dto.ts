export interface NegotiationDraftRequest {
  inquiryText: string;
  productId: string;
  buyerId?: string;
}

export interface NegotiationDraftResponse {
  draftEn: string;
  strategyId: string;
  rationaleId: string;
  warnings: string[];
  confidence: number;
}