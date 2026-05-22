import { z } from 'zod';

export const createProductSchema = z
  .object({
    name: z.string().min(1).max(255),
    description: z.string().min(10).max(5000),
    moq: z.number().int().positive(),
    monthlyCapacity: z.number().int().positive(),
    priceMin: z.number().positive(),
    priceMax: z.number().positive(),
    hpp: z.number().positive(),
    photoUrls: z.array(z.string().url()).max(10).optional(),
  })
  .refine((data) => data.priceMax >= data.priceMin, {
    message: 'priceMax must be >= priceMin',
    path: ['priceMax'],
  });

export type CreateProductInput = z.infer<typeof createProductSchema>;