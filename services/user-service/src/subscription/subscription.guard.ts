import { CanActivate, ExecutionContext, ForbiddenException, Injectable, UnauthorizedException } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { FEATURE_KEY } from '../authz/authz.decorators.js';
import type { Feature } from '../authz/plan-config.js';
import { SubscriptionService } from './subscription.service.js';

/**
 * Enforces @RequireFeature(...). Loads the caller's LIVE entitlements from the
 * DB (never trusts the token) so upgrades/downgrades take effect immediately.
 */
@Injectable()
export class SubscriptionGuard implements CanActivate {
  constructor(
    private readonly reflector: Reflector,
    private readonly subscriptions: SubscriptionService,
  ) {}

  async canActivate(ctx: ExecutionContext): Promise<boolean> {
    const feature = this.reflector.getAllAndOverride<Feature | undefined>(FEATURE_KEY, [
      ctx.getHandler(),
      ctx.getClass(),
    ]);
    if (!feature) return true;

    const req = ctx.switchToHttp().getRequest<{ headers: Record<string, unknown> }>();
    const userId = req.headers['x-user-id'] as string | undefined;
    if (!userId) throw new UnauthorizedException('Missing authenticated user');

    const ent = await this.subscriptions.entitlementsFor(userId);
    if (!ent.flags[feature]) {
      throw new ForbiddenException({
        message: `Fitur '${feature}' memerlukan paket berbayar`,
        code: 'feature_locked',
        feature,
        plan: ent.plan,
      });
    }
    return true;
  }
}
