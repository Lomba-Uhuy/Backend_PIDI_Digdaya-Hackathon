import { Body, Controller, Get, Post, UseGuards } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { CurrentUser, type InternalUser } from '../common/current-user.decorator.js';
import { RequireFeature, Roles } from '../authz/authz.decorators.js';
import { RolesGuard } from '../authz/roles.guard.js';
import { planCatalogue } from '../authz/plan-config.js';
import { SubscriptionGuard } from './subscription.guard.js';
import { SubscriptionService } from './subscription.service.js';

@ApiTags('Subscription')
@Controller('subscription')
export class SubscriptionController {
  constructor(private readonly subscriptions: SubscriptionService) {}

  @Get('me')
  @ApiOperation({ summary: "Caller's subscription: plan, status, entitlements, usage" })
  me(@CurrentUser() user: InternalUser) {
    return this.subscriptions.me(user.userId);
  }

  @Get('plans')
  @ApiOperation({ summary: 'Public plan catalogue (labels, quotas, feature flags)' })
  plans() {
    return { plans: planCatalogue() };
  }

  @Post('change')
  @ApiOperation({ summary: 'Change the caller plan (self-service; payment simulated for now)' })
  change(@CurrentUser() user: InternalUser, @Body() body: { plan: string }) {
    return this.subscriptions.changePlan(user.userId, body.plan);
  }

  // ── Enforcement demonstrations (prove the central mechanism works) ───────────
  @Get('feature/advanced-analytics')
  @UseGuards(SubscriptionGuard)
  @RequireFeature('advanced_analytics')
  @ApiOperation({ summary: 'Feature-gated probe (403 on free, 200 on premium)' })
  advancedAnalyticsProbe() {
    return { ok: true, feature: 'advanced_analytics' };
  }

  @Get('admin/ping')
  @UseGuards(RolesGuard)
  @Roles('admin')
  @ApiOperation({ summary: 'Admin-only probe (403 for umkm role)' })
  adminPing() {
    return { ok: true, role: 'admin' };
  }
}
