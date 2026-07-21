import { BadRequestException, Inject, Injectable } from '@nestjs/common';
import { eq } from 'drizzle-orm';
import { DRIZZLE, type DrizzleDB } from '../database/database.module.js';
import { subscriptions, type Subscription } from '../database/schema/index.js';
import { PLANS, normalizePlan, resolveEntitlements, type Entitlements } from '../authz/plan-config.js';

@Injectable()
export class SubscriptionService {
  constructor(@Inject(DRIZZLE) private readonly db: DrizzleDB) {}

  /** One subscription per user; lazily creates a default `free` plan. */
  async getOrCreate(userId: string): Promise<Subscription> {
    const existing = await this.db.query.subscriptions.findFirst({
      where: eq(subscriptions.userId, userId),
    });
    if (existing) return existing;
    const [created] = await this.db.insert(subscriptions).values({ userId }).returning();
    if (!created) throw new Error('Failed to create subscription');
    return created;
  }

  /** Effective entitlements (plan defaults + per-user overrides). */
  async entitlementsFor(userId: string): Promise<Entitlements> {
    const sub = await this.getOrCreate(userId);
    return resolveEntitlements(sub.plan, sub.featureFlags ?? {});
  }

  /** Full subscription view for the owner (plan, status, entitlements, usage). */
  async me(userId: string) {
    const sub = await this.getOrCreate(userId);
    return {
      plan: sub.plan,
      status: sub.status,
      billingCycle: sub.billingCycle,
      startedAt: sub.startedAt,
      expiredAt: sub.expiredAt,
      paymentStatus: sub.paymentStatus,
      provider: sub.provider,
      usage: sub.usage ?? {},
      entitlements: resolveEntitlements(sub.plan, sub.featureFlags ?? {}),
    };
  }

  /**
   * Self-service plan change. Real payment integration (Midtrans/Xendit/Stripe)
   * plugs in here later; for now we activate immediately and mark the demo
   * payment as simulated so nothing is faked as a real charge.
   */
  async changePlan(userId: string, plan: string): Promise<Subscription> {
    if (!PLANS[plan]) throw new BadRequestException(`Unknown plan '${plan}'`);
    if (PLANS[plan].comingSoon) throw new BadRequestException(`Plan '${plan}' is not yet available`);
    const sub = await this.getOrCreate(userId);
    const paid = normalizePlan(plan) !== 'free';
    const [updated] = await this.db
      .update(subscriptions)
      .set({
        plan,
        status: 'active',
        billingCycle: paid ? 'monthly' : 'none',
        paymentStatus: paid ? 'paid' : 'none',
        provider: paid ? 'simulated' : null,
        startedAt: new Date(),
        expiredAt: null,
        updatedAt: new Date(),
      })
      .where(eq(subscriptions.userId, userId))
      .returning();
    return updated ?? sub;
  }
}
