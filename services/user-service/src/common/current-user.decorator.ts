import { type ExecutionContext, createParamDecorator, UnauthorizedException } from '@nestjs/common';

export interface InternalUser {
  userId: string;
  tenantId?: string;
  tier?: string;
}

/**
 * Extracts user context from headers injected by the gateway:
 *   x-user-id, x-tenant-id, x-user-tier
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
      tenantId: req.headers['x-tenant-id'] as string | undefined,
      tier: req.headers['x-user-tier'] as string | undefined,
    };
  },
);