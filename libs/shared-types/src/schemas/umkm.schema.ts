import { z } from 'zod';

export const createUmkmSchema = z.object({
  legalName: z.string().min(1).max(255),
  nib: z.string().regex(/^\d{13}$/, 'NIB must be exactly 13 digits'),
  description: z.string().max(2000).optional(),
});

export type CreateUmkmInput = z.infer<typeof createUmkmSchema>;