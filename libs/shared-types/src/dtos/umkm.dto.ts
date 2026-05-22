export enum VerificationStatus {
  PENDING     = 'PENDING',
  IN_PROGRESS = 'IN_PROGRESS',
  VERIFIED    = 'VERIFIED',
  FAILED      = 'FAILED',
}

export interface UmkmDto {
  id: string;
  legalName: string;
  nib: string;
  description: string | null;
  verificationStatus: VerificationStatus;
  verifiedScore: number;
  certifications: string[];
  userId: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateUmkmDto {
  legalName: string;
  nib: string;            // exactly 13 digits
  description?: string;
}