import { Module } from '@nestjs/common';
import { DealController } from './deal.controller.js';
import { DealService } from './deal.service.js';
import { MessageController } from './message.controller.js';
import { MessageService } from './message.service.js';
import { PurchaseOrderController } from './purchase-order.controller.js';
import { PurchaseOrderService } from './purchase-order.service.js';
import { ComplianceController } from './compliance.controller.js';
import { ComplianceService } from './compliance.service.js';

@Module({
  controllers: [DealController, MessageController, PurchaseOrderController, ComplianceController],
  providers: [DealService, MessageService, PurchaseOrderService, ComplianceService],
})
export class DealModule {}
