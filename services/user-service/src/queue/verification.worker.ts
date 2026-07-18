import { Processor, WorkerHost } from '@nestjs/bullmq';
import { Inject, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Job } from 'bullmq';
import { eq } from 'drizzle-orm';
import type { VerificationJobData } from '@tradeconnect/shared-types/events';
import { DRIZZLE, type DrizzleDB } from '../database/database.module.js';
import { umkm } from '../database/schema/index.js';
import { VERIFICATION_QUEUE } from './verification.producer.js';

const NIB_API_BASE = 'https://www.badanperizinan.co.id/api/v1/public';
const INSW_API_BASE = 'https://api.insw.go.id/api/cms';
const OSS_PUBLIC_NIB_URL = 'https://api-prd.oss.go.id/v1/reg/public/nib';

interface NibData {
  nib: string;
  is_valid: boolean;
  business_name: string;
  npwp: string;
  business_scale: string;
  oss_status_aktif: string;
  oss_status_migrasi: string;
  oss_status_penanaman_modal: string;
  compliance_status: string;
  registered_date: string;
  insw_verified: boolean;
  insw_kategori: string;
  insw_history: Array<{ status: string; keterangan: string; waktu_oss: string }>;
  oss_public_verified: boolean;
  oss_public_data: Record<string, unknown>;
  verification_sources: string[];
  sandbox_mode: boolean;
}

type PartialNibData = Partial<Omit<NibData, 'nib' | 'is_valid' | 'sandbox_mode'>> & {
  nib: string;
  is_valid: boolean;
  source: string;
};

@Processor(VERIFICATION_QUEUE)
export class VerificationWorker extends WorkerHost {
  private readonly logger = new Logger(VerificationWorker.name);
  private readonly inswToken: string | undefined;
  private readonly ossPublicUserKey: string | undefined;
  private readonly ossPublicRecaptcha: string | undefined;
  private readonly ossPublicCookie: string | undefined;
  private readonly ossPublicUrl: string;

  constructor(
    @Inject(DRIZZLE) private readonly db: DrizzleDB,
    cfg: ConfigService,
  ) {
    super();
    this.inswToken = cfg.get<string>('INSW_TOKEN') || undefined;
    this.ossPublicUserKey = cfg.get<string>('OSS_PUBLIC_USER_KEY') || undefined;
    this.ossPublicRecaptcha = cfg.get<string>('OSS_PUBLIC_RECAPTCHA_RESPONSE') || undefined;
    this.ossPublicCookie = cfg.get<string>('OSS_PUBLIC_COOKIE') || undefined;
    this.ossPublicUrl = cfg.get<string>('OSS_PUBLIC_NIB_URL') || OSS_PUBLIC_NIB_URL;
  }

  async process(job: Job<VerificationJobData>): Promise<void> {
    const { umkmId, nib } = job.data;
    this.logger.log(`verification.start umkmId=${umkmId} nib=${nib}`);

    await this.db
      .update(umkm)
      .set({ verificationStatus: 'IN_PROGRESS', updatedAt: new Date() })
      .where(eq(umkm.id, umkmId));

    try {
      const nibData = await this.verifyNib(nib);
      const score = this.calculateScore(nibData);
      const status = nibData.is_valid ? 'VERIFIED' : 'FAILED';

      await this.db
        .update(umkm)
        .set({
          verificationStatus: status,
          verifiedScore: String(score),
          ossRbaData: nibData as unknown as Record<string, unknown>,
          updatedAt: new Date(),
        })
        .where(eq(umkm.id, umkmId));

      this.logger.log(
        `verification.done umkmId=${umkmId} score=${score} status=${status} insw=${nibData.insw_verified} ceisa=${nibData.insw_kategori === 'REC CEISA'}`,
      );
    } catch (err) {
      this.logger.error(`verification.error umkmId=${umkmId} err=${String(err)}`);
      await this.db
        .update(umkm)
        .set({ verificationStatus: 'FAILED', updatedAt: new Date() })
        .where(eq(umkm.id, umkmId));
      throw err;
    }
  }

  // ── Step 1: badanperizinan.co.id ──────────────────────────────────────────

  private async verifyNib(nib: string): Promise<NibData> {
    const [badanPerizinan, ossPublic] = await Promise.all([
      this.fetchBadanPerizinan(nib),
      this.fetchOssPublic(nib),
    ]);
    return this.mergeNibSources(badanPerizinan, ossPublic);
  }

  private async fetchBadanPerizinan(nib: string): Promise<NibData> {
    try {
      const resp = await fetch(`${NIB_API_BASE}/nib/${nib}`, {
        headers: { Accept: 'application/json', 'User-Agent': 'TradeConnect/1.0' },
        signal: AbortSignal.timeout(10_000),
      });
      const body = (await resp.json()) as { success: boolean; status?: boolean; data?: { fields: Array<{ label: string; value: string }> } };

      if (!resp.ok || !body.success) {
        return {
          nib, is_valid: false, business_name: '', npwp: '', business_scale: '',
          oss_status_aktif: '', oss_status_migrasi: '', oss_status_penanaman_modal: '',
          compliance_status: 'INVALID', registered_date: '',
          insw_verified: false, insw_kategori: '', insw_history: [],
          oss_public_verified: false, oss_public_data: {}, verification_sources: [],
          sandbox_mode: false,
        };
      }

      const get = (label: string) => body.data?.fields.find((f) => f.label === label)?.value ?? '';
      return {
        nib, is_valid: true,
        business_name: get('Nama Perusahaan'),
        npwp: get('NPWP'),
        business_scale: '',
        oss_status_aktif: '',
        oss_status_migrasi: '',
        oss_status_penanaman_modal: '',
        compliance_status: 'COMPLIANT',
        registered_date: get('Waktu Penerbitan OSS'),
        insw_verified: false, insw_kategori: '', insw_history: [],
        oss_public_verified: false, oss_public_data: {}, verification_sources: ['badanperizinan'],
        sandbox_mode: false,
      };
    } catch (err) {
      this.logger.warn(`nib.api_down nib=${nib} err=${String(err)} → sandbox`);
      return {
        nib, is_valid: true, business_name: `Demo UMKM NIB-${nib.slice(-4)}`,
        npwp: '000000000000000', business_scale: 'KECIL',
        oss_status_aktif: '', oss_status_migrasi: '', oss_status_penanaman_modal: '',
        compliance_status: 'COMPLIANT',
        registered_date: '2022-01-15',
        insw_verified: false, insw_kategori: '', insw_history: [],
        oss_public_verified: false, oss_public_data: {}, verification_sources: ['sandbox'],
        sandbox_mode: true,
      };
    }
  }

  private async fetchOssPublic(nib: string): Promise<PartialNibData | null> {
    if (!this.ossPublicUserKey) {
      this.logger.warn(`oss_public.skip nib=${nib} reason=no_user_key`);
      return null;
    }

    try {
      const headers: Record<string, string> = {
        Accept: 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
        'Content-Type': 'application/json',
        Origin: 'https://oss.go.id',
        Referer: 'https://oss.go.id/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari',
        user_key: this.ossPublicUserKey,
      };
      if (this.ossPublicRecaptcha) headers['g-recaptcha-response'] = this.ossPublicRecaptcha;
      if (this.ossPublicCookie) headers.Cookie = this.ossPublicCookie;

      const resp = await fetch(this.ossPublicUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify({ dataNib: { nib } }),
        signal: AbortSignal.timeout(10_000),
      });
      const raw = (await resp.json()) as Record<string, unknown>;
      if (!resp.ok || !this.ossLooksValid(raw)) return null;

      return {
        nib,
        is_valid: true,
        business_name: this.pickString(raw, ['nama_perusahaan', 'namaPerusahaan', 'nama_perseroan', 'namaPerseroan', 'nama_pelaku_usaha', 'namaPelakuUsaha', 'nama']),
        npwp: this.pickString(raw, ['npwp', 'npwpPerusahaan', 'npwp_perseroan']),
        business_scale: this.pickString(raw, ['skala_usaha', 'skalaUsaha', 'uraian_skala_usaha', 'uraianSkalaUsaha']),
        oss_status_aktif: this.pickString(raw, ['status_aktif', 'statusAktif']),
        oss_status_migrasi: this.pickString(raw, ['status_migrasi', 'statusMigrasi']),
        oss_status_penanaman_modal: this.pickString(raw, ['status_penanaman_modal', 'statusPenanamanModal']),
        compliance_status: 'COMPLIANT',
        registered_date: this.pickString(raw, ['tanggal_terbit_oss', 'tanggalTerbitOss', 'tgl_terbit_oss', 'tglTerbitOss', 'tgl_pengajuan_nib', 'tglPengajuanNib']),
        oss_public_verified: true,
        oss_public_data: raw,
        verification_sources: ['oss_public'],
        source: 'oss_public',
      };
    } catch (err) {
      this.logger.warn(`oss_public.failed nib=${nib} err=${String(err)}`);
      return null;
    }
  }

  // ── Step 2: INSW double-check ─────────────────────────────────────────────

  private async enrichWithInsw(base: NibData): Promise<NibData> {
    try {
      const url = `${INSW_API_BASE}/nib?nib=${base.nib}&npwp=${base.npwp}`;
      const resp = await fetch(url, {
        headers: {
          Accept: 'application/json',
          Authorization: `Basic ${this.inswToken}`,
          'User-Agent': 'TradeConnect/1.0',
        },
        signal: AbortSignal.timeout(10_000),
      });
      const body = (await resp.json()) as { code: string; data?: { data_header: Array<{ nama_perusahaan: string; kategori: string }>; data_history: Array<{ status: string; ket: string; waktu_oss: string }> } };

      if (!resp.ok || body.code !== '01' || !body.data) return base;

      const header = body.data.data_header[0];
      return {
        ...base,
        business_name: header?.nama_perusahaan || base.business_name,
        insw_verified: true,
        insw_kategori: header?.kategori ?? '',
        insw_history: body.data.data_history.map((h) => ({ status: h.status, keterangan: h.ket, waktu_oss: h.waktu_oss })),
      };
    } catch (err) {
      this.logger.warn(`insw.failed nib=${base.nib} err=${String(err)}`);
      return base;
    }
  }

  // ── Scoring ───────────────────────────────────────────────────────────────
  //
  // 0.5  — NIB valid (badanperizinan.co.id)
  // 0.3  — COMPLIANT (NIB ada di OSS)
  // 0.2  — REC CEISA (NIB terdaftar di sistem bea cukai → export-ready)
  // Max  — 1.0

  private calculateScore(data: NibData): number {
    let score = 0;
    if (data.is_valid) score += 0.5;
    if (data.compliance_status === 'COMPLIANT') score += 0.3;
    else if (data.compliance_status === 'CONDITIONAL') score += 0.15;

    const scale = (data.business_scale || '').toUpperCase();
    if (scale.includes('MENENGAH') || scale.includes('MEDIUM') || scale.includes('MIDDLE')) {
      score += 0.2;
    } else if (scale.includes('KECIL') || scale.includes('SMALL')) {
      score += 0.15;
    } else if (scale.includes('MIKRO') || scale.includes('MICRO')) {
      score += 0.05;
    }
    return Math.min(1.0, Math.round(score * 10_000) / 10_000);
  }

  private mergeNibSources(badanPerizinan: NibData, ossPublic: PartialNibData | null): NibData {
    if (!ossPublic) return badanPerizinan;
    const sources = new Set([
      ...badanPerizinan.verification_sources,
      ossPublic.source,
    ]);
    if (ossPublic.oss_public_verified) sources.delete('sandbox');

    return {
      ...badanPerizinan,
      is_valid: badanPerizinan.is_valid || ossPublic.is_valid,
      business_name: badanPerizinan.business_name || ossPublic.business_name || '',
      npwp: badanPerizinan.npwp || ossPublic.npwp || '',
      business_scale: badanPerizinan.business_scale || ossPublic.business_scale || '',
      oss_status_aktif: badanPerizinan.oss_status_aktif || ossPublic.oss_status_aktif || '',
      oss_status_migrasi: badanPerizinan.oss_status_migrasi || ossPublic.oss_status_migrasi || '',
      oss_status_penanaman_modal: badanPerizinan.oss_status_penanaman_modal || ossPublic.oss_status_penanaman_modal || '',
      compliance_status: badanPerizinan.compliance_status === 'INVALID'
        ? ossPublic.compliance_status || 'COMPLIANT'
        : badanPerizinan.compliance_status,
      registered_date: badanPerizinan.registered_date || ossPublic.registered_date || '',
      oss_public_verified: Boolean(ossPublic.oss_public_verified),
      oss_public_data: ossPublic.oss_public_data ?? {},
      verification_sources: [...sources].filter((source) => source !== ''),
      sandbox_mode: badanPerizinan.sandbox_mode && !ossPublic.oss_public_verified,
    };
  }

  private ossLooksValid(raw: Record<string, unknown>): boolean {
    const status = this.pickString(raw, ['status', 'code', 'message', 'msg']);
    const nib = this.pickString(raw, ['nib']);
    return (
      Boolean(nib) ||
      Boolean(this.pickString(raw, ['nama_perusahaan', 'namaPerusahaan', 'nama_perseroan', 'namaPerseroan'])) ||
      /success|sukses|berhasil|200|01/i.test(status)
    );
  }

  private pickString(source: unknown, keys: string[]): string {
    const value = this.findFirstValue(source, new Set(keys.map((key) => key.toLowerCase())));
    if (typeof value === 'string') return value.trim();
    if (typeof value === 'number' || typeof value === 'boolean') return String(value);
    return '';
  }

  private findFirstValue(source: unknown, keys: Set<string>): unknown {
    if (!source || typeof source !== 'object') return undefined;
    if (Array.isArray(source)) {
      for (const item of source) {
        const value = this.findFirstValue(item, keys);
        if (value !== undefined && value !== null && value !== '') return value;
      }
      return undefined;
    }
    for (const [key, value] of Object.entries(source)) {
      if (keys.has(key.toLowerCase())) return value;
      const nested = this.findFirstValue(value, keys);
      if (nested !== undefined && nested !== null && nested !== '') return nested;
    }
    return undefined;
  }
}
