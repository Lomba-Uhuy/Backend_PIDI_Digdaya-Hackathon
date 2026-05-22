export interface EmbeddingJobData {
  productId: string;
  description: string;
  umkmId: string;
}

export interface EmbeddingJobResult {
  productId: string;
  status: 'success' | 'failed';
  dimensions: number;
}