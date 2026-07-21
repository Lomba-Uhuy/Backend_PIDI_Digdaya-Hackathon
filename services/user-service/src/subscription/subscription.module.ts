import { Module } from '@nestjs/common';
import { SubscriptionController } from './subscription.controller.js';
import { SubscriptionService } from './subscription.service.js';
import { SubscriptionGuard } from './subscription.guard.js';
import { RolesGuard } from '../authz/roles.guard.js';

/**
 * Central authorization + subscription. Exports the service + guards so any
 * feature module can enforce @RequireFeature / @Roles without duplicating logic.
 */
@Module({
  controllers: [SubscriptionController],
  providers: [SubscriptionService, SubscriptionGuard, RolesGuard],
  exports: [SubscriptionService, SubscriptionGuard, RolesGuard],
})
export class SubscriptionModule {}
