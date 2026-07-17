import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bullmq';
import { VerificationProducer, VERIFICATION_QUEUE, EMBEDDING_QUEUE } from './verification.producer.js';
import { VerificationWorker } from './verification.worker.js';

@Module({
  imports: [
    BullModule.registerQueue(
      { name: VERIFICATION_QUEUE },
      { name: EMBEDDING_QUEUE },
    ),
  ],
  providers: [VerificationProducer, VerificationWorker],
  exports: [VerificationProducer, BullModule],
})
export class QueueModule {}