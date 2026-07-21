import { SetMetadata } from '@nestjs/common';
import type { Feature, Role } from './plan-config.js';

export const ROLES_KEY = 'authz:roles';
export const FEATURE_KEY = 'authz:feature';

/** Restrict a route/controller to one or more roles. Empty = any authenticated. */
export const Roles = (...roles: Role[]) => SetMetadata(ROLES_KEY, roles);

/** Require the caller's subscription to unlock a feature flag. */
export const RequireFeature = (feature: Feature) => SetMetadata(FEATURE_KEY, feature);
