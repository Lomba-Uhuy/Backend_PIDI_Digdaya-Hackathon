import { Module } from '@nestjs/common';
import { QueueModule } from '../queue/queue.module.js';
import { UmkmModule } from '../umkm/umkm.module.js';
import { ProductController } from './product.controller.js';
import { ProductService } from './product.service.js';

@Module({
  imports: [QueueModule, UmkmModule],
  controllers: [ProductController],
  providers: [ProductService],
})
export class ProductModule {}