import { Inject, Injectable } from '@nestjs/common';
import { eq } from 'drizzle-orm';
import { DRIZZLE, type DrizzleDB } from '../database/database.module.js';
import {
  complianceChecks, products, umkm, type ComplianceCheck,
} from '../database/schema/index.js';
import { DealService } from './deal.service.js';

type Status = 'pass' | 'warn' | 'fail';
type Kind = 'nib' | 'fraud_scan' | 'document';
interface CheckDraft { kind: Kind; label: string; status: Status; detail?: Record<string, unknown> }

@Injectable()
export class ComplianceService {
  constructor(
    @Inject(DRIZZLE) private readonly db: DrizzleDB,
    private readonly dealService: DealService,
  ) {}

  async list(dealId: string, userId: string): Promise<{ checks: ComplianceCheck[]; overall: Status }> {
    await this.dealService.findById(dealId, userId);
    const checks = await this.db
      .select()
      .from(complianceChecks)
      .where(eq(complianceChecks.dealId, dealId));
    return { checks, overall: this.overall(checks.map((c) => c.status)) };
  }

  /**
   * Run compliance/readiness checks from REAL owned data (NIB registration, HS
   * classification, agreed price vs floor, production capacity). Re-runnable:
   * replaces the deal's prior checks.
   */
  async run(dealId: string, userId: string): Promise<{ checks: ComplianceCheck[]; overall: Status }> {
    const deal = await this.dealService.findById(dealId, userId);
    const umkmRow = await this.db.query.umkm.findFirst({ where: eq(umkm.userId, userId) });
    const product = deal.productId
      ? await this.db.query.products.findFirst({ where: eq(products.id, deal.productId) })
      : undefined;

    const drafts: CheckDraft[] = [];

    // 1. NIB verified against the combined OSS + Infiniti registry (readiness-service).
    const nib = umkmRow?.nib?.trim();
    drafts.push(await this.verifyNib(nib));

    // 2. HS classification present — required for customs.
    const hs = product?.hsCode?.trim();
    drafts.push({
      kind: 'document',
      label: 'Klasifikasi kode HS produk',
      status: hs ? 'pass' : 'warn',
      detail: { hsCode: hs ?? null },
    });

    // 3. Agreed price vs floor (price_min) — dumping / margin guardrail.
    const agreed = deal.agreedPrice != null ? Number(deal.agreedPrice) : null;
    const floor = product?.priceMin != null ? Number(product.priceMin) : null;
    let priceStatus: Status = 'warn';
    if (agreed != null && floor != null) priceStatus = agreed >= floor ? 'pass' : 'fail';
    drafts.push({
      kind: 'fraud_scan',
      label: 'Harga kesepakatan di atas harga dasar',
      status: priceStatus,
      detail: { agreedPrice: agreed, floorPrice: floor },
    });

    // 4. Production capacity declared — fulfilment readiness.
    const capacity = product?.monthlyCapacity ?? 0;
    drafts.push({
      kind: 'document',
      label: 'Kapasitas produksi bulanan terdeklarasi',
      status: capacity > 0 ? 'pass' : 'warn',
      detail: { monthlyCapacity: capacity },
    });

    // Replace prior checks for this deal (re-runnable).
    await this.db.delete(complianceChecks).where(eq(complianceChecks.dealId, dealId));
    const inserted = await this.db
      .insert(complianceChecks)
      .values(drafts.map((d) => ({ dealId, kind: d.kind, label: d.label, status: d.status, detail: d.detail })))
      .returning();

    return { checks: inserted, overall: this.overall(inserted.map((c) => c.status)) };
  }

  /**
   * Verify the NIB against the combined OSS + Infiniti registry via
   * readiness-service. Falls back to a presence check if that service is
   * unreachable (so compliance never hard-fails on an infra hiccup).
   */
  private async verifyNib(nib: string | undefined): Promise<CheckDraft> {
    const label = 'Verifikasi NIB (OSS + Infiniti)';
    if (!nib) {
      return { kind: 'nib', label, status: 'fail', detail: { nib: null } };
    }
    const base = process.env.READINESS_SERVICE_URL ?? 'http://readiness-service:3002';
    try {
      const resp = await fetch(`${base}/nib/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nib }),
        signal: AbortSignal.timeout(12_000),
      });
      if (resp.ok) {
        const v = (await resp.json()) as {
          is_valid?: boolean;
          business_name?: string;
          verification_sources?: string[];
          sandbox_mode?: boolean;
        };
        return {
          kind: 'nib',
          label,
          status: v.is_valid ? 'pass' : 'fail',
          detail: {
            nib,
            businessName: v.business_name ?? null,
            sources: v.verification_sources ?? [],
            sandbox: v.sandbox_mode ?? false,
          },
        };
      }
    } catch {
      // registry unreachable — degrade to presence check below
    }
    return { kind: 'nib', label, status: 'warn', detail: { nib, note: 'registry unreachable' } };
  }

  private overall(statuses: Status[]): Status {
    if (statuses.includes('fail')) return 'fail';
    if (statuses.includes('warn')) return 'warn';
    return 'pass';
  }
}
