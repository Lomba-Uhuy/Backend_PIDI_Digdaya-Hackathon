import { z } from 'zod';

export const fraudScanSchema = z.object({
  buyerId:      z.string().uuid(),
  termsText:    z.string().min(1).max(20000),
  contractText: z.string().max(50000).optional(),
});

export type FraudScanInput = z.infer<typeof fraudScanSchema>;