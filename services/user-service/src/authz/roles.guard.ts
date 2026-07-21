import { CanActivate, ExecutionContext, ForbiddenException, Injectable, UnauthorizedException } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { ROLES_KEY } from './authz.decorators.js';
import type { Role } from './plan-config.js';

/**
 * Enforces @Roles(...). The caller's role arrives as the `x-user-role` header,
 * injected by the gateway from the validated JWT (internal services trust the
 * gateway). No metadata → route is open to any authenticated user.
 */
@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private readonly reflector: Reflector) {}

  canActivate(ctx: ExecutionContext): boolean {
    const required = this.reflector.getAllAndOverride<Role[] | undefined>(ROLES_KEY, [
      ctx.getHandler(),
      ctx.getClass(),
    ]);
    if (!required || required.length === 0) return true;

    const req = ctx.switchToHttp().getRequest<{ headers: Record<string, unknown> }>();
    const userId = req.headers['x-user-id'] as string | undefined;
    if (!userId) throw new UnauthorizedException('Missing authenticated user');
    const role = ((req.headers['x-user-role'] as string) ?? 'umkm') as Role;
    if (!required.includes(role)) {
      throw new ForbiddenException(`Requires role: ${required.join(' | ')}`);
    }
    return true;
  }
}
