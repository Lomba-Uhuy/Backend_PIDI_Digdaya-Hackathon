import { Module } from '@nestjs/common';
import { NibVerificationController } from './nib-verification.controller.js';
import { NibVerificationService } from './nib-verification.service.js';

@Module({
  controllers: [NibVerificationController],
  providers: [NibVerificationService],
})
export class NibModule {}
