export interface VerificationJobData {
  umkmId: string;
  nib: string;
  userId: string;
  tenantId?: string;
}

export interface VerificationJobResult {
  umkmId: string;
  score: number;
  status: 'VERIFIED' | 'FAILED';
  ossData: Record<string, unknown>;
}