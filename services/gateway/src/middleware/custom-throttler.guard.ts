import { type ExecutionContext, Injectable } from '@nestjs/common';
import { ThrottlerGuard } from '@nestjs/throttler';

/**
 * Tier-aware throttler:
 *  - premium user: tracked by user id
 *  - free user / anonymous: tracked by IP
 *  - AI endpoints use the 'ai-endpoints' throttler suffix (lower limit)
 */
@Injectable()
export class CustomThrottlerGuard extends ThrottlerGuard {
  protected override async getTracker(req: Record<string, unknown>): Promise<string> {
    const user = (req as { user?: { sub?: string; tier?: string } }).user;
    if (user?.tier === 'premium' && user?.sub) {
      return `premium:${user.sub}`;
    }
    return `free:${(req as { ip?: string }).ip ?? 'unknown'}`;
  }

  protected override getThrottlerSuffix(context: ExecutionContext): string {
    const req = context.switchToHttp().getRequest<{ url?: string }>();
    const path = req.url ?? '';
    if (path.includes('/matching') || path.includes('/negotiations')) {
      return 'ai-endpoints';
    }
    return 'default';
  }
}