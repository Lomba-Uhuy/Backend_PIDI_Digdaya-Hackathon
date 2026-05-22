import { Module } from '@nestjs/common';
import { QueueModule } from '../queue/queue.module.js';
import { UmkmController } from './umkm.controller.js';
import { UmkmService } from './umkm.service.js';

@Module({
  imports: [QueueModule],
  controllers: [UmkmController],
  providers: [UmkmService],
  exports: [UmkmService],
})
export class UmkmModule {}