import { Injectable, Logger } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import postgres from "postgres";

type BenchmarkRow = {
  sample_count: number | string | null;
  unit_value_usd: number | string | null;
};

export interface ExportUnitBenchmark {
  hsCode: string;
  unitValueUsd: number;
  sampleCount: number;
  source: string;
}

@Injectable()
export class PricingBenchmarkService {
  private readonly logger = new Logger(PricingBenchmarkService.name);
  private readonly sql: ReturnType<typeof postgres> | null;

  constructor(cfg: ConfigService) {
    const databaseUrl = cfg.get<string>("DATABASE_URL");
    this.sql = databaseUrl
      ? postgres(databaseUrl, { max: 1, idle_timeout: 20, connect_timeout: 2 })
      : null;
  }

  async lookupExportUnitValue(
    hsCode?: string,
  ): Promise<ExportUnitBenchmark | null> {
    const normalizedHsCode = this.normalizeHsCode(hsCode);
    if (!normalizedHsCode || !this.sql) {
      return null;
    }

    try {
      const rows = await this.sql<BenchmarkRow[]>`
        SELECT
          COUNT(*)::int AS sample_count,
          SUM(trade_value_usd)::numeric / NULLIF(SUM(net_weight_kg), 0) AS unit_value_usd
        FROM trade_flows
        WHERE source = 'bps'
          AND flow_code = 'X'
          AND hs_code LIKE ${`${normalizedHsCode}%`}
          AND trade_value_usd IS NOT NULL
          AND net_weight_kg IS NOT NULL
          AND net_weight_kg > 0
      `;

      const row = rows[0];
      const unitValueUsd = this.toNumber(row?.unit_value_usd);
      if (unitValueUsd === null) {
        return null;
      }

      return {
        hsCode: normalizedHsCode,
        unitValueUsd,
        sampleCount: this.toInteger(row?.sample_count) ?? 0,
        source: "bps.trade_flows",
      };
    } catch (error) {
      this.logger.warn(
        `pricing.benchmark.unavailable hsCode=${normalizedHsCode} reason=${String(error)}`,
      );
      return null;
    }
  }

  private normalizeHsCode(hsCode?: string): string | null {
    if (!hsCode) {
      return null;
    }

    const digits = hsCode.replace(/\D/g, "");
    return digits.length >= 2 ? digits : null;
  }

  private toNumber(value: number | string | null | undefined): number | null {
    if (value === null || value === undefined || value === "") {
      return null;
    }

    const parsed = typeof value === "number" ? value : Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  private toInteger(value: number | string | null | undefined): number | null {
    const parsed = this.toNumber(value);
    return parsed === null ? null : Math.trunc(parsed);
  }
}
