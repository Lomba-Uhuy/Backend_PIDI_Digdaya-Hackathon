import { HttpException } from '@nestjs/common';
import type { AxiosError } from 'axios';

export interface ForwardedContext {
  userId?: string;
  tenantId?: string;
  requestId: string;
  tier?: string;
}

export function buildForwardHeaders(req: {
  user?: { sub?: string; email?: string; tenantId?: string; tier?: string; role?: string };
  headers: Record<string, unknown>;
}): Record<string, string> {
  const headers: Record<string, string> = {
    'x-request-id': (req.headers['x-request-id'] as string) ?? crypto.randomUUID(),
  };
  if (req.user?.sub) headers['x-user-id'] = req.user.sub;
  if (req.user?.email) headers['x-user-email'] = req.user.email;
  if (req.user?.tenantId) headers['x-tenant-id'] = req.user.tenantId;
  if (req.user?.tier) headers['x-user-tier'] = req.user.tier;
  // RBAC role from the validated JWT — internal services enforce on this header.
  headers['x-user-role'] = req.user?.role ?? 'umkm';
  // Best-effort client IP for audit logging.
  const fwd = (req.headers['x-forwarded-for'] as string) ?? '';
  if (fwd) headers['x-forwarded-for'] = fwd;
  return headers;
}

export function translateAxiosError(err: unknown): never {
  const ax = err as AxiosError;
  if (ax.response) {
    throw new HttpException(
      (ax.response.data as Record<string, unknown>) ?? { message: 'Upstream error' },
      ax.response.status,
    );
  }
  throw new HttpException(
    { error: { code: 'upstream_unreachable', message: ax.message } },
    503,
  );
}