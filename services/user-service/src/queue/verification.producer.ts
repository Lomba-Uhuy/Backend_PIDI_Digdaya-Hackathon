import { Injectable } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';
import type {
  VerificationJobData,
  EmbeddingJobData,
} from '@tradeconnect/shared-types/events';

export const VERIFICATION_QUEUE = 'verification';
export const EMBEDDING_QUEUE = 'embeddings';

@Injectable()
export class VerificationProducer {
  constructor(
    @InjectQueue(VERIFICATION_QUEUE) private readonly verificationQueue: Queue,
    @InjectQueue(EMBEDDING_QUEUE) private readonly embeddingQueue: Queue,
  ) {}

  async dispatchVerification(data: VerificationJobData): Promise<void> {
    await this.verificationQueue.add('verify-nib', data, {
      attempts: 5,
      backoff: { type: 'exponential', delay: 3000 },
      removeOnComplete: { age: 86_400 },
      removeOnFail:     { age: 604_800 },
    });
  }

  async dispatchEmbeddingGeneration(data: EmbeddingJobData): Promise<void> {
    await this.embeddingQueue.add('generate-product-embedding', data, {
      attempts: 3,
      backoff: { type: 'fixed', delay: 5000 },
      priority: 2,
    });
  }
}