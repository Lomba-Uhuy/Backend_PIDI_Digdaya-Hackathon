export interface BuyerMatchDto {
  buyerId: string;
  name: string;
  country: string;
  hsCodes: string[];
  credibilityScore: number;
  similarityScore: number;
  distance: number;
  explanation: string;
  isSynthetic: boolean;
}

export interface MatchSearchRequest {
  productId: string;
  topK?: number;
  countryFilter?: string[];
}

export interface HSClassifyRequest {
  description: string;
  topK?: number;
}

export interface HSClassifyResult {
  hsCode: string;
  description: string;
  confidence: number;
  topK: Array<{ hsCode: string; description: string; confidence: number }>;
}