// ── Centralized authorization config ─────────────────────────────────────────
// The single source of truth for roles, subscription plans, feature flags and
// quotas. Endpoints reference FEATURES/QUOTAS by name; plan capabilities live
// ONLY here so nothing is hardcoded per-endpoint or per-plan across the repo.

export const ROLES = ['umkm', 'admin'] as const;
export type Role = (typeof ROLES)[number];
export const isRole = (v: string | undefined | null): v is Role =>
  !!v && (ROLES as readonly string[]).includes(v);

/** Capability flags a plan may unlock. Referenced by @RequireFeature(...). */
export const FEATURES = [
  'bulk_buyer_sync',
  'advanced_analytics',
  'ocr_batch',
  'api_access',
  'team_collaboration',
  'priority_queue',
  'workflow_history_export',
  'advanced_ai_models',
  'workflow_monitoring',
  'data_export',
  'webhook',
  'custom_prompt_library',
  'custom_knowledge_base',
  'provider_diagnostics',
] as const;
export type Feature = (typeof FEATURES)[number];

/** Metered resources. `null` quota = unlimited. */
export const QUOTAS = ['companies', 'products', 'ai_consultations', 'buyer_matches', 'ocr_pages'] as const;
export type Quota = (typeof QUOTAS)[number];

export interface PlanConfig {
  label: string;
  comingSoon?: boolean;
  flags: Partial<Record<Feature, boolean>>;
  quotas: Record<Quota, number | null>; // null = unlimited
}

const ALL_FLAGS_ON = Object.fromEntries(FEATURES.map((f) => [f, true])) as Record<Feature, boolean>;
const UNLIMITED = Object.fromEntries(QUOTAS.map((q) => [q, null])) as Record<Quota, number | null>;

const FREE_PLAN: PlanConfig = {
  label: 'Free',
  // All advanced features off by default (omitted flags resolve to false).
  flags: {},
  quotas: { companies: 1, products: 3, ai_consultations: 50, buyer_matches: 20, ocr_pages: 20 },
};

export const PLANS: Record<string, PlanConfig> = {
  free: FREE_PLAN,
  premium: {
    label: 'Premium',
    flags: ALL_FLAGS_ON,
    quotas: UNLIMITED,
  },
  enterprise: {
    label: 'Enterprise',
    comingSoon: true,
    flags: ALL_FLAGS_ON,
    quotas: UNLIMITED,
  },
};

export const DEFAULT_PLAN = 'free';
export const normalizePlan = (plan: string | null | undefined): string =>
  plan && PLANS[plan] ? plan : DEFAULT_PLAN;

export interface Entitlements {
  plan: string;
  label: string;
  flags: Record<Feature, boolean>;
  quotas: Record<Quota, number | null>;
}

/**
 * Resolve effective entitlements: plan defaults with per-user `overrides` layered
 * on top (a false override can also DISABLE a plan feature).
 */
export function resolveEntitlements(
  plan: string | null | undefined,
  overrides: Record<string, boolean> = {},
): Entitlements {
  const key = normalizePlan(plan);
  const cfg = PLANS[key] ?? FREE_PLAN;
  const flags = {} as Record<Feature, boolean>;
  for (const f of FEATURES) {
    flags[f] = f in overrides ? Boolean(overrides[f]) : cfg.flags[f] ?? false;
  }
  return { plan: key, label: cfg.label, flags, quotas: cfg.quotas };
}

export const hasFeature = (
  plan: string | null | undefined,
  feature: Feature,
  overrides: Record<string, boolean> = {},
): boolean => resolveEntitlements(plan, overrides).flags[feature];

/** Public plan catalogue for pricing UIs (labels + coming-soon flags). */
export function planCatalogue() {
  return Object.entries(PLANS).map(([id, p]) => ({
    id,
    label: p.label,
    comingSoon: Boolean(p.comingSoon),
    quotas: p.quotas,
    flags: resolveEntitlements(id).flags,
  }));
}
