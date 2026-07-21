import { type ExecutionContext, createParamDecorator, UnauthorizedException } from '@nestjs/common';

export interface InternalUser {
  userId: string;
  email?: string;
  tenantId?: string;
  tier?: string;
  role?: string;
  ip?: string;
}

/**
 * Extracts user context from headers injected by the gateway:
 *   x-user-id, x-tenant-id, x-user-tier, x-user-role
 *
 * Internal services trust these headers because only the gateway is
 * publicly reachable and it sets them after JWT validation.
 */
export const CurrentUser = createParamDecorator(
  (_data: unknown, ctx: ExecutionContext): InternalUser => {
    const req = ctx.switchToHttp().getRequest<{ headers: Record<string, unknown> }>();
    const userId = req.headers['x-user-id'] as string | undefined;
    if (!userId) {
      throw new UnauthorizedException('Missing x-user-id header (gateway must inject this)');
    }
    return {
      userId,
      email: req.headers['x-user-email'] as string | undefined,
      tenantId: req.headers['x-tenant-id'] as string | undefined,
      tier: req.headers['x-user-tier'] as string | undefined,
      role: req.headers['x-user-role'] as string | undefined,
      ip: (req.headers['x-forwarded-for'] as string | undefined)?.split(',')[0]?.trim(),
    };
  },
);