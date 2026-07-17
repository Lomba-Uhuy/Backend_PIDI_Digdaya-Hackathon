import { Module } from '@nestjs/common';
import { DealController } from './deal.controller.js';
import { DealService } from './deal.service.js';

@Module({
  controllers: [DealController],
  providers: [DealService],
})
export class DealModule {}
