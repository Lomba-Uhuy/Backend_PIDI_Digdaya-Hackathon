import { Injectable, Logger } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import postgres from "postgres";

type TradeFlowRow = {
  partner_iso?: string | null;
  partner_name?: string | null;
  reporter_iso?: string | null;
  reporter_name?: string | null;
  period?: number | string | null;
  trade_value_usd?: number | string | null;
  net_weight_kg?: number | string | null;
};

type PeriodRow = { max_period?: number | string | null };

export interface RegionData {
  countryCode: string;
  countryName: string;
  tradeValueUsd: number;
  netWeightKg: number;
  period: number;
  unitValueUsd: number;
}

export interface MarketIntelligenceStats {
  hsCode: string;
  totalValueUsd: number;
  totalWeightKg: number;
  topRegion: string;
  bpsStats: RegionData[];
  comtradeStats: RegionData[];
  insights: {
    analysis: string;
    alerts: Array<{
      type: "opportunity" | "regulatory" | "warning";
      title: string;
      description: string;
    }>;
  };
}

// HS Code prefix → human-readable category label (Indonesian)
const HS_CATEGORY_MAP: Array<{ prefix: string; label: string }> = [
  { prefix: "0901", label: "Kopi" },
  { prefix: "0902", label: "Teh" },
  { prefix: "1511", label: "Minyak Sawit (CPO/RPO)" },
  { prefix: "1507", label: "Minyak Kedelai" },
  { prefix: "1513", label: "Minyak Kelapa / Kelapa Sawit Inti" },
  { prefix: "2701", label: "Batu Bara" },
  { prefix: "2711", label: "Gas Alam (LNG/LPG)" },
  { prefix: "2709", label: "Minyak Bumi Mentah" },
  { prefix: "4001", label: "Karet Alam" },
  { prefix: "4002", label: "Karet Sintetis" },
  { prefix: "1801", label: "Biji Kakao" },
  { prefix: "1803", label: "Pasta Kakao" },
  { prefix: "0306", label: "Udang & Krustasea" },
  { prefix: "0302", label: "Ikan Segar" },
  { prefix: "0304", label: "Fillet Ikan" },
  { prefix: "4412", label: "Kayu Lapis (Plywood)" },
  { prefix: "4407", label: "Kayu Gergajian" },
  { prefix: "4703", label: "Pulp Kayu Kimia" },
  { prefix: "6403", label: "Alas Kaki Kulit" },
  { prefix: "6404", label: "Alas Kaki Tekstil" },
  { prefix: "7601", label: "Aluminium Tidak Ditempa" },
  { prefix: "2603", label: "Bijih Tembaga" },
  { prefix: "2602", label: "Bijih Mangan" },
  { prefix: "8703", label: "Kendaraan Bermotor" },
  { prefix: "6204", label: "Pakaian Wanita" },
  { prefix: "6203", label: "Pakaian Pria" },
  { prefix: "0803", label: "Pisang" },
  { prefix: "0804", label: "Nanas & Buah Tropis" },
  { prefix: "0901", label: "Kopi" },
];

// HS prefixes affected by EU Deforestation Regulation (EUDR)
const EUDR_HS_PREFIXES = [
  "0901", "1511", "1201", "4001", "1801",
  "4407", "4408", "4409", "4412", "4413",
  "7203", "2601",
];

// Product-specific certifications
const CERTIFICATION_MAP: Array<{ prefix: string; certs: string }> = [
  { prefix: "0901", certs: "Rainforest Alliance, UTZ, Fairtrade, 4C Association, Specialty Coffee Association (SCA)" },
  { prefix: "1511", certs: "RSPO (Roundtable on Sustainable Palm Oil), ISPO (Indonesian Sustainable Palm Oil)" },
  { prefix: "4001", certs: "FSC (Forest Stewardship Council), PEFC, GlobalG.A.P, SNI ISO 3780" },
  { prefix: "1801", certs: "Rainforest Alliance, UTZ, Fairtrade, Cocoa Horizons" },
  { prefix: "4412", certs: "FSC, SVLK (Sistem Verifikasi Legalitas Kayu), PEFC" },
  { prefix: "4407", certs: "SVLK, FSC, PEFC" },
  { prefix: "0306", certs: "ASC (Aquaculture Stewardship Council), HACCP, MSC, BAP (Best Aquaculture Practices)" },
  { prefix: "0302", certs: "MSC (Marine Stewardship Council), HACCP, ISO 22000" },
  { prefix: "0304", certs: "MSC, HACCP, ISO 22000, halal certification" },
];

@Injectable()
export class MarketIntelligenceService {
  private readonly logger = new Logger(MarketIntelligenceService.name);
  private readonly sql: ReturnType<typeof postgres> | null;

  constructor(cfg: ConfigService) {
    const databaseUrl = cfg.get<string>("DATABASE_URL");
    this.sql = databaseUrl
      ? postgres(databaseUrl, { max: 1, idle_timeout: 20, connect_timeout: 2 })
      : null;
  }

  async getStats(hsCode?: string, userId?: string): Promise<MarketIntelligenceStats> {
    if (!this.sql) {
      throw new Error("Database connection not configured");
    }

    let activeHsCode = hsCode;

    console.log("=== DEBUG MARKET INT ===", { activeHsCode, userId });

    if (!activeHsCode && userId) {
      try {
        const productRows = await this.sql<Array<{ hs_code: string }>>`
          SELECT p.hs_code 
          FROM product p
          JOIN umkm u ON p.umkm_id = u.id
          WHERE u.user_id = ${userId}::uuid 
            AND p.hs_code IS NOT NULL 
            AND p.hs_code != ''
          ORDER BY p.hs_confidence DESC
          LIMIT 1
        `;
        const recommendedHs = productRows[0]?.hs_code;
        if (recommendedHs) {
          activeHsCode = recommendedHs;
          this.logger.log(`Using AI-recommended HS Code from database: ${activeHsCode} for user ${userId}`);
        }
      } catch (dbError) {
        this.logger.warn(`Failed to retrieve AI HS code from database: ${String(dbError)}. Using default.`);
      }
    }

    const normalizedHs = this.normalizeHsCode(activeHsCode ?? "0901");

    try {
      // ── 1. Resolve latest period for BPS ────────────────────────────
      const bpsPeriodRows = await this.sql<PeriodRow[]>`
        SELECT MAX(period) AS max_period
        FROM trade_flows
        WHERE source = 'bps'
          AND flow_code = 'X'
          AND hs_code LIKE ${`${normalizedHs}%`}
      `;
      const bpsLatestPeriod: number = Number(bpsPeriodRows[0]?.max_period ?? 0);

      // ── 2. BPS: Indonesia exports to partner countries (latest year) ─
      const bpsRows: TradeFlowRow[] = bpsLatestPeriod > 0
        ? await this.sql<TradeFlowRow[]>`
            SELECT
              partner_iso   AS partner_iso,
              partner_name  AS partner_name,
              period        AS period,
              SUM(trade_value_usd)::numeric AS trade_value_usd,
              SUM(net_weight_kg)::numeric   AS net_weight_kg
            FROM trade_flows
            WHERE source = 'bps'
              AND flow_code = 'X'
              AND hs_code LIKE ${`${normalizedHs}%`}
              AND period = ${bpsLatestPeriod}
            GROUP BY partner_iso, partner_name, period
            ORDER BY trade_value_usd DESC
            LIMIT 30
          `
        : [];

      // ── 3. Resolve latest period for UN Comtrade ──────────────────────
      const comtradePeriodRows = await this.sql<PeriodRow[]>`
        SELECT MAX(period) AS max_period
        FROM trade_flows
        WHERE source = 'un_comtrade'
          AND flow_code = 'M'
          AND hs_code LIKE ${`${normalizedHs}%`}
      `;
      const comtradeLatestPeriod: number = Number(comtradePeriodRows[0]?.max_period ?? 0);

      // ── 4. UN Comtrade: countries importing from Indonesia (latest year) ──
      const comtradeRows: TradeFlowRow[] = comtradeLatestPeriod > 0
        ? await this.sql<TradeFlowRow[]>`
            SELECT
              reporter_iso  AS reporter_iso,
              reporter_name AS reporter_name,
              period        AS period,
              SUM(trade_value_usd)::numeric AS trade_value_usd,
              SUM(net_weight_kg)::numeric   AS net_weight_kg
            FROM trade_flows
            WHERE source = 'un_comtrade'
              AND flow_code = 'M'
              AND hs_code LIKE ${`${normalizedHs}%`}
              AND period = ${comtradeLatestPeriod}
            GROUP BY reporter_iso, reporter_name, period
            ORDER BY trade_value_usd DESC
            LIMIT 30
          `
        : [];

      // ── 5. Map rows to RegionData ─────────────────────────────────────
      const mapBpsRows = (rows: TradeFlowRow[], fallbackPeriod: number): RegionData[] =>
        rows
          .filter((r) => r.partner_iso && r.partner_iso !== "WLD" && r.partner_iso !== "0")
          .map((r) => {
            const val = Number(r.trade_value_usd ?? 0);
            const wt  = Number(r.net_weight_kg  ?? 0);
            return {
              countryCode:   String(r.partner_iso  ?? "XX"),
              countryName:   String(r.partner_name ?? "Unknown"),
              tradeValueUsd: val,
              netWeightKg:   wt,
              period:        Number(r.period ?? fallbackPeriod),
              unitValueUsd:  wt > 0 ? Number((val / wt).toFixed(4)) : 0,
            };
          });

      const mapComtradeRows = (rows: TradeFlowRow[], fallbackPeriod: number): RegionData[] =>
        rows
          .filter((r) => r.reporter_iso && r.reporter_iso !== "WLD" && r.reporter_iso !== "0")
          .map((r) => {
            const val = Number(r.trade_value_usd ?? 0);
            const wt  = Number(r.net_weight_kg  ?? 0);
            return {
              countryCode:   String(r.reporter_iso  ?? "XX"),
              countryName:   String(r.reporter_name ?? "Unknown"),
              tradeValueUsd: val,
              netWeightKg:   wt,
              period:        Number(r.period ?? fallbackPeriod),
              unitValueUsd:  wt > 0 ? Number((val / wt).toFixed(4)) : 0,
            };
          });

      const bpsStats      = mapBpsRows(bpsRows,         bpsLatestPeriod);
      const comtradeStats = mapComtradeRows(comtradeRows, comtradeLatestPeriod);

      // ── 6. Aggregates ─────────────────────────────────────────────────
      const referenceStats = bpsStats.length > 0 ? bpsStats : comtradeStats;
      const totalValueUsd  = referenceStats.reduce((a, r) => a + r.tradeValueUsd, 0);
      const totalWeightKg  = referenceStats.reduce((a, r) => a + r.netWeightKg,  0);
      const topRegion      = referenceStats[0]?.countryName ?? "N/A";

      // ── 7. Dynamic AI Insights (generik, tidak hardcode produk) ──────
      const fmtUsd = (v: number) =>
        new Intl.NumberFormat("id-ID", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(v);

      const categoryName = this.getHsCategory(normalizedHs);
      const dataPeriod   = bpsLatestPeriod || comtradeLatestPeriod;
      const periodLabel  = dataPeriod > 0 ? ` (${dataPeriod})` : "";

      const analysis = referenceStats.length > 0
        ? `Analisis ${categoryName} HS ${normalizedHs}${periodLabel}: total ekspor Indonesia tercatat sebesar ${fmtUsd(totalValueUsd)} dengan volume ${new Intl.NumberFormat("id-ID").format(Math.round(totalWeightKg))} kg. ${topRegion} memimpin sebagai pasar tujuan utama dari ${referenceStats.length} negara mitra aktif.`
        : `Tidak ditemukan data ekspor untuk HS ${normalizedHs}${periodLabel}. Pastikan ETL worker sudah berhasil mengambil data dari BPS dan UN Comtrade untuk kode HS ini.`;

      const alerts: Array<{ type: "opportunity" | "regulatory" | "warning"; title: string; description: string }> = [];

      // Alert #1 — pasar utama
      if (referenceStats.length > 0 && referenceStats[0]) {
        const top = referenceStats[0];
        const unit = top.unitValueUsd > 0 ? ` dengan harga unit rata-rata $${top.unitValueUsd.toFixed(2)}/kg` : "";
        alerts.push({
          type: "opportunity",
          title: `Pasar Utama: ${top.countryName}`,
          description: `${top.countryName} adalah pasar ekspor terbesar untuk ${categoryName} (HS ${normalizedHs}) senilai ${fmtUsd(top.tradeValueUsd)}${unit}. Prioritaskan negosiasi dengan pembeli dari negara ini.`,
        });
      }

      // Alert #2 — ekspansi ke negara ke-2 & ke-3
      const top3 = referenceStats.slice(1, 3);
      if (top3.length > 0) {
        const t0 = top3[0];
        const t1 = top3[1];
        const names = [t0?.countryName, t1?.countryName].filter(Boolean).join(" dan ");
        const values = [t0 ? fmtUsd(t0.tradeValueUsd) : null, t1 ? fmtUsd(t1.tradeValueUsd) : null].filter(Boolean).join(", ");
        alerts.push({
          type: "opportunity",
          title: `Peluang Ekspansi: ${t0?.countryName ?? ""}${t1 ? " & " + t1.countryName : ""}`,
          description: `${names} menunjukkan permintaan signifikan senilai ${values}. Diversifikasi ke pasar ini dapat meningkatkan resiliensi ekspor ${categoryName} Indonesia.`,
        });
      }

      // Alert #3 — negara dengan unit value tertinggi sebagai pasar premium
      const premiumMarket = referenceStats
        .filter((r) => r.unitValueUsd > 0 && r.tradeValueUsd > 0)
        .sort((a, b) => b.unitValueUsd - a.unitValueUsd)[0];
      if (premiumMarket && premiumMarket.countryCode !== referenceStats[0]?.countryCode) {
        alerts.push({
          type: "opportunity",
          title: `Pasar Premium: ${premiumMarket.countryName}`,
          description: `${premiumMarket.countryName} mencatat harga unit tertinggi sebesar $${premiumMarket.unitValueUsd.toFixed(2)}/kg untuk ${categoryName}. Pasar ini berpotensi menerima harga premium untuk produk berkualitas tinggi dan bersertifikat.`,
        });
      }

      // Alert #4 — EUDR regulatory (hanya jika HS code termasuk komoditas terdampak EUDR)
      const isEudrAffected = this.isEudrAffected(normalizedHs);
      const hasEuTarget = referenceStats.some((r) => {
        const cc = r.countryCode.substring(0, 2).toUpperCase();
        return ["DE", "NL", "FR", "IT", "BE", "ES", "AT", "PL", "SE", "DK", "FI", "NO", "GB"].includes(cc);
      });
      if (isEudrAffected && (hasEuTarget || referenceStats.length === 0)) {
        alerts.push({
          type: "regulatory",
          title: "Regulasi Bebas Deforestasi Uni Eropa (EUDR)",
          description: `Ekspor ${categoryName} (HS ${normalizedHs}) ke pasar Uni Eropa wajib memenuhi EU Deforestation Regulation (EUDR) mulai 30 Desember 2024. Siapkan bukti koordinat GPS lahan, rantai pasok tertelusur, dan dokumen due diligence.`,
        });
      }

      // Alert #5 — regulasi umum pasar ekspor
      if (!isEudrAffected && hasEuTarget) {
        alerts.push({
          type: "regulatory",
          title: "Persyaratan Standar Pasar Eropa",
          description: `Ekspor ke Uni Eropa memerlukan kepatuhan terhadap regulasi REACH, CE marking (jika produk manufaktur), dan standar keamanan produk EU. Pastikan dokumentasi teknis lengkap sebelum pengiriman.`,
        });
      }

      // Alert #6 — sertifikasi (spesifik per produk)
      const certifications = this.getCertifications(normalizedHs);
      alerts.push({
        type: "warning",
        title: "Persyaratan Sertifikasi Pembeli",
        description: `Pembeli di pasar premium (EU, AS, Jepang) umumnya mensyaratkan: ${certifications}. Biaya dan waktu sertifikasi perlu diperhitungkan dalam strategi penetapan harga dan jadwal ekspor.`,
      });

      return {
        hsCode: normalizedHs,
        totalValueUsd,
        totalWeightKg,
        topRegion,
        bpsStats,
        comtradeStats,
        insights: { analysis, alerts },
      };
    } catch (error) {
      this.logger.error(`MarketIntelligence query error: ${String(error)}`);
      throw error;
    }
  }

  /** Normalize HS code: strip non-digits, keep at least 2 digits. */
  private normalizeHsCode(hsCode: string): string {
    const digits = hsCode.replace(/\D/g, "").slice(0, 10);
    return digits.length >= 2 ? digits : "0901";
  }

  /** Return human-readable category label for a given HS prefix. */
  private getHsCategory(hs: string): string {
    for (const entry of HS_CATEGORY_MAP) {
      if (hs.startsWith(entry.prefix)) return entry.label;
    }
    return `Komoditas HS ${hs}`;
  }

  /** Check if HS code is covered by EU Deforestation Regulation (EUDR). */
  private isEudrAffected(hs: string): boolean {
    return EUDR_HS_PREFIXES.some((prefix) => hs.startsWith(prefix));
  }

  /** Return product-specific certification requirements. */
  private getCertifications(hs: string): string {
    for (const entry of CERTIFICATION_MAP) {
      if (hs.startsWith(entry.prefix)) return entry.certs;
    }
    return "ISO 9001, HACCP, sertifikasi keamanan produk standar internasional yang berlaku di negara tujuan";
  }
}
