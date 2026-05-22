import { z } from 'zod';

export const pricingRequestSchema = z.object({
  hpp:           z.number().positive(),
  originCharges: z.number().nonnegative(),
  qty:           z.number().int().positive(),
  oceanFreight:  z.number().nonnegative(),
  insuranceRate: z.number().min(0).max(1),
});

export type PricingRequestInput = z.infer<typeof pricingRequestSchema>;