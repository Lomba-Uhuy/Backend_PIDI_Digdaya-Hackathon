import { Inject, Injectable } from '@nestjs/common';
import { sql } from 'drizzle-orm';
import { DRIZZLE, type DrizzleDB } from '../database/database.module.js';

export interface HsOption {
  code: string;
  label: string;
  count: number;
}

export interface RegionOption {
  name: string;
  count: number;
  valueUsd: number;
}

/**
 * Reference data for the Market Intelligence filters, derived from the real
 * ingested BPS trade dataset (no hardcoded lists).
 */
@Injectable()
export class MarketService {
  constructor(@Inject(DRIZZLE) private readonly db: DrizzleDB) {}

  async hsCodes(): Promise<HsOption[]> {
    const rows = (await this.db.execute(sql`
      SELECT commodity_code AS code,
             MIN(commodity_name) AS label,
             COUNT(*)::int AS n
      FROM bps_trade_data
      WHERE commodity_code IS NOT NULL AND commodity_code <> ''
      GROUP BY commodity_code
      ORDER BY n DESC
    `)) as unknown as Array<{ code: string; label: string; n: number }>;
    return rows.map((r) => ({ code: r.code, label: r.label ?? r.code, count: Number(r.n) }));
  }

  /**
   * Top destination countries for an HS chapter, aggregated from the real
   * ingested BPS export dataset. Feeds the Market Intelligence heat map.
   */
  async topMarkets(hs: string, flow: "X" | "M" = "X"): Promise<
    Array<{ partner: string; tradeValueUsd: number; netWeightKg: number; period: number | null }>
  > {
    const code = hs.replace(/[^0-9]/g, "").slice(0, 2) || "09";
    const rows = (await this.db.execute(sql`
      SELECT country_name AS partner,
             COALESCE(SUM(value), 0)::float8 AS value_usd,
             COALESCE(SUM(net_weight_kg), 0)::float8 AS weight_kg,
             MAX(period) AS period
      FROM bps_trade_data
      WHERE commodity_code = ${code}
        AND flow_code = ${flow}
        AND country_name IS NOT NULL AND country_name <> ''
      GROUP BY country_name
      ORDER BY value_usd DESC NULLS LAST
      LIMIT 15
    `)) as unknown as Array<{ partner: string; value_usd: number; weight_kg: number; period: string | null }>;
    return rows.map((r) => ({
      partner: r.partner,
      tradeValueUsd: Number(r.value_usd),
      netWeightKg: Number(r.weight_kg),
      period: r.period != null ? Number(r.period) : null,
    }));
  }

  async regions(): Promise<RegionOption[]> {
    const rows = (await this.db.execute(sql`
      SELECT country_name AS name,
             COUNT(*)::int AS n,
             COALESCE(SUM(value), 0)::float8 AS v
      FROM bps_trade_data
      WHERE country_name IS NOT NULL AND country_name <> ''
      GROUP BY country_name
      ORDER BY v DESC NULLS LAST
      LIMIT 30
    `)) as unknown as Array<{ name: string; n: number; v: number }>;
    return rows.map((r) => ({ name: r.name, count: Number(r.n), valueUsd: Number(r.v) }));
  }
}
