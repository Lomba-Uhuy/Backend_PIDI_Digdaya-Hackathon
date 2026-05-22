import { Module } from '@nestjs/common';
import { FraudController } from './fraud.controller.js';
import { FraudDetectionService } from './fraud-detection.service.js';

@Module({
  controllers: [FraudController],
  providers: [FraudDetectionService],
  exports: [FraudDetectionService],
})
export class FraudModule {}