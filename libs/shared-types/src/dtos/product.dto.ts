export interface ProductDto {
  id: string;
  umkmId: string;
  name: string;
  description: string;
  hsCode: string | null;
  hsConfidence: number | null;
  moq: number;
  monthlyCapacity: number;
  priceMin: string;       // Decimal string to avoid float precision issues
  priceMax: string;
  // hpp is sensitive — never exposed in this DTO
  photoUrls: string[];
  createdAt: string;
  updatedAt: string;
}

export interface CreateProductDto {
  name: string;
  description: string;
  moq: number;
  monthlyCapacity: number;
  priceMin: number;
  priceMax: number;
  hpp: number;            // accepted from owner only, never returned to others
  photoUrls?: string[];
}