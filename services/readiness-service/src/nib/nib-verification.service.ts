import { Injectable, Logger } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";

const NIB_API_BASE = "https://www.badanperizinan.co.id/api/v1/public";
const INSW_API_BASE = "https://api.insw.go.id/api/cms";
const OSS_PUBLIC_NIB_URL = "https://api-prd.oss.go.id/v1/reg/public/nib";

const SANDBOX_PROFILES = [
  {
    business_name: "CV Karya Rotan Nusantara",
    npwp: "73.456.781.3-429.000",
    kbli: "16291",
    kbli_description:
      "Industri barang dari anyaman rotan, bambu, dan sejenisnya",
    business_scale: "KECIL",
    registered_date: "2021-03-10",
    certifications: ["SNI"],
  },
  {
    business_name: "PT Sumber Makmur Ekspor",
    npwp: "01.234.567.8-543.000",
    kbli: "46339",
    kbli_description: "Perdagangan besar barang keperluan rumah tangga lainnya",
    business_scale: "MENENGAH",
    registered_date: "2019-07-22",
    certifications: ["ISO 9001"],
  },
  {
    business_name: "UD Mitra Dagang Sejati",
    npwp: "62.345.678.2-117.000",
    kbli: "46909",
    kbli_description: "Perdagangan besar berbagai macam barang",
    business_scale: "KECIL",
    registered_date: "2020-11-05",
    certifications: [],
  },
  {
    business_name: "CV Indah Kerajinan Indonesia",
    npwp: "84.567.890.4-321.000",
    kbli: "32901",
    kbli_description:
      "Industri kerajinan yang tidak diklasifikasikan di tempat lain",
    business_scale: "KECIL",
    registered_date: "2022-01-15",
    certifications: ["HALAL"],
  },
  {
    business_name: "PT Batik Nusantara Lestari",
    npwp: "52.678.901.6-789.000",
    kbli: "13131",
    kbli_description: "Industri batik",
    business_scale: "MENENGAH",
    registered_date: "2018-04-30",
    certifications: ["SNI", "ISO 9001"],
  },
  {
    business_name: "CV Agro Ekspor Mandiri",
    npwp: "31.890.123.5-654.000",
    kbli: "01611",
    kbli_description: "Jasa pertanian dan perkebunan",
    business_scale: "KECIL",
    registered_date: "2023-02-18",
    certifications: [],
  },
  {
    business_name: "UD Furnitur Jepara Jaya",
    npwp: "91.234.560.7-012.000",
    kbli: "31001",
    kbli_description: "Industri furnitur dari kayu",
    business_scale: "KECIL",
    registered_date: "2020-08-14",
    certifications: ["SNI"],
  },
  {
    business_name: "PT Global Rempah Indonesia",
    npwp: "45.123.456.9-876.000",
    kbli: "10300",
    kbli_description:
      "Industri pengolahan dan pengawetan buah-buahan dan sayuran",
    business_scale: "MENENGAH",
    registered_date: "2017-12-01",
    certifications: ["HALAL", "ISO 22000"],
  },
  {
    business_name: "CV Citra Tekstil Nusantara",
    npwp: "29.876.543.1-234.000",
    kbli: "14201",
    kbli_description: "Industri pakaian jadi dari tekstil",
    business_scale: "KECIL",
    registered_date: "2021-09-03",
    certifications: [],
  },
  {
    business_name: "PT Mebel Ekspor Makmur",
    npwp: "68.901.234.0-567.000",
    kbli: "31009",
    kbli_description: "Industri furnitur lainnya",
    business_scale: "MENENGAH",
    registered_date: "2019-05-20",
    certifications: ["ISO 9001"],
  },
] satisfies Array<{
  business_name: string;
  npwp: string;
  kbli: string;
  kbli_description: string;
  business_scale: string;
  registered_date: string;
  certifications: string[];
}>;

export interface InswHistoryEntry {
  status: string;
  keterangan: string;
  waktu_oss: string;
}

export interface NibVerificationResult {
  nib: string;
  is_valid: boolean;
  business_name: string;
  npwp: string;
  kbli: string;
  kbli_description: string;
  business_scale: string;
  oss_status_aktif: string;
  oss_status_migrasi: string;
  oss_status_penanaman_modal: string;
  compliance_status: string;
  registered_date: string;
  certifications: string[];
  /** Data dari INSW (Indonesia National Single Window) */
  insw_verified: boolean;
  insw_kategori: string;
  insw_history: InswHistoryEntry[];
  /** true apabila endpoint public OSS RBA berhasil mengembalikan data */
  oss_public_verified: boolean;
  /** Raw response ringkas dari public OSS RBA untuk audit/debug UI */
  oss_public_data: Record<string, unknown>;
  /** Sumber data yang berhasil dipakai untuk membentuk hasil final */
  verification_sources: string[];
  /** true apabila badanperizinan.co.id tidak tersedia — data berasal dari sandbox mock */
  sandbox_mode: boolean;
}

interface BadanPerizinanResponse {
  success: boolean;
  status?: boolean;
  data?: { fields: Array<{ label: string; value: string }> };
}

interface InswResponse {
  code: string;
  message: string;
  data?: {
    data_header: Array<{
      nib: string;
      npwp: string;
      nama_perusahaan: string;
      kategori: string;
    }>;
    data_history: Array<{
      status: string;
      ket: string;
      waktu_oss: string;
    }>;
  };
}

interface OssPublicResponse {
  [key: string]: unknown;
}

type PartialNibResult = Partial<
  Omit<NibVerificationResult, "nib" | "is_valid" | "sandbox_mode">
> & {
  nib: string;
  is_valid: boolean;
  source: string;
};

@Injectable()
export class NibVerificationService {
  private readonly logger = new Logger(NibVerificationService.name);

  private readonly inswToken: string | undefined;
  private readonly ossPublicUserKey: string | undefined;
  private readonly ossPublicRecaptcha: string | undefined;
  private readonly ossPublicCookie: string | undefined;
  private readonly ossPublicUrl: string;

  constructor(cfg: ConfigService) {
    this.inswToken = cfg.get<string>("INSW_TOKEN") || undefined;
    this.ossPublicUserKey = cfg.get<string>("OSS_PUBLIC_USER_KEY") || undefined;
    this.ossPublicRecaptcha =
      cfg.get<string>("OSS_PUBLIC_RECAPTCHA_RESPONSE") || undefined;
    this.ossPublicCookie = cfg.get<string>("OSS_PUBLIC_COOKIE") || undefined;
    this.ossPublicUrl =
      cfg.get<string>("OSS_PUBLIC_NIB_URL") || OSS_PUBLIC_NIB_URL;
  }

  async verify(nib: string): Promise<NibVerificationResult> {
    if (nib.length < 13) {
      this.logger.warn("nib.demo_placeholder nib=%s → sandbox", nib);
      return this.sandboxResult(nib);
    }

    // Step 1 + 2: badanperizinan.co.id dan public OSS RBA.
    // Hasil keduanya digabung supaya field yang kosong di satu sumber dapat
    // dilengkapi sumber lain.
    const [badanPerizinan, ossPublic] = await Promise.all([
      this.fetchBadanPerizinan(nib),
      this.fetchOssPublic(nib),
    ]);

    let combined = this.mergeNibSources(badanPerizinan, ossPublic);

    if (!combined.is_valid) return combined;

    // INSW dinonaktifkan: verifikasi cukup dari badanperizinan saja.
    // // Step 2: INSW — double-check + status bea cukai (butuh NPWP dari step 1)
    // if (!this.inswToken) {
    //   this.logger.warn("insw.skip nib=%s reason=no_token", nib);
    //   return combined;
    // }
    //
    // combined = await this.mergeWithInsw(combined, this.inswToken);
    return combined;
  }

  // ── Step 1 ──────────────────────────────────────────────────────────────────

  private async fetchBadanPerizinan(
    nib: string,
  ): Promise<NibVerificationResult> {
    try {
      const resp = await fetch(`${NIB_API_BASE}/nib/${nib}`, {
        headers: {
          Accept: "application/json",
          "User-Agent": "TradeConnect/1.0",
        },
        signal: AbortSignal.timeout(10_000),
      });
      const body = (await resp.json()) as BadanPerizinanResponse;

      if (!resp.ok || !body.success) {
        this.logger.warn("nib.not_found nib=%s", nib);
        return this.invalidResult(nib);
      }

      const get = (label: string) =>
        body.data?.fields.find((f) => f.label === label)?.value ?? "";
      return {
        nib,
        is_valid: true,
        business_name: get("Nama Perusahaan"),
        npwp: get("NPWP"),
        kbli: "",
        kbli_description: "",
        business_scale: "",
        oss_status_aktif: "",
        oss_status_migrasi: "",
        oss_status_penanaman_modal: "",
        compliance_status: "COMPLIANT",
        registered_date: get("Waktu Penerbitan OSS"),
        certifications: [],
        insw_verified: false,
        insw_kategori: "",
        insw_history: [],
        oss_public_verified: false,
        oss_public_data: {},
        verification_sources: ["badanperizinan"],
        sandbox_mode: false,
      };
    } catch (err: unknown) {
      const reason = err instanceof Error ? err.message : String(err);
      this.logger.warn("nib.api_down nib=%s reason=%s → sandbox", nib, reason);
      return this.sandboxResult(nib);
    }
  }

  // ── Step 2: OSS public NIB endpoint ────────────────────────────────────────

  private async fetchOssPublic(nib: string): Promise<PartialNibResult | null> {
    if (!this.ossPublicUserKey) {
      this.logger.warn("oss_public.skip nib=%s reason=no_user_key", nib);
      return null;
    }

    try {
      const headers: Record<string, string> = {
        Accept: "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Content-Type": "application/json",
        Origin: "https://oss.go.id",
        Referer: "https://oss.go.id/",
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari",
        user_key: this.ossPublicUserKey,
      };

      if (this.ossPublicRecaptcha) {
        headers["g-recaptcha-response"] = this.ossPublicRecaptcha;
      }
      if (this.ossPublicCookie) {
        headers.Cookie = this.ossPublicCookie;
      }

      const resp = await fetch(this.ossPublicUrl, {
        method: "POST",
        headers,
        body: JSON.stringify({ dataNib: { nib } }),
        signal: AbortSignal.timeout(10_000),
      });

      const raw = (await resp.json()) as OssPublicResponse;
      if (!resp.ok || !this.ossLooksValid(raw)) {
        this.logger.warn("oss_public.not_confirmed nib=%s status=%s", nib, resp.status);
        return null;
      }

      return {
        nib,
        is_valid: true,
        business_name: this.pickString(raw, [
          "nama_perusahaan",
          "namaPerusahaan",
          "nama_perseroan",
          "namaPerseroan",
          "nama_pelaku_usaha",
          "namaPelakuUsaha",
          "nama",
        ]),
        npwp: this.pickString(raw, ["npwp", "npwpPerusahaan", "npwp_perseroan"]),
        kbli: this.pickString(raw, ["kbli", "kode_kbli", "kodeKbli"]),
        kbli_description: this.pickString(raw, [
          "uraian_kbli",
          "uraianKbli",
          "judul_kbli",
          "judulKbli",
          "kbli_description",
        ]),
        business_scale: this.pickString(raw, [
          "skala_usaha",
          "skalaUsaha",
          "uraian_skala_usaha",
          "uraianSkalaUsaha",
        ]),
        oss_status_aktif: this.pickString(raw, [
          "status_aktif",
          "statusAktif",
        ]),
        oss_status_migrasi: this.pickString(raw, [
          "status_migrasi",
          "statusMigrasi",
        ]),
        oss_status_penanaman_modal: this.pickString(raw, [
          "status_penanaman_modal",
          "statusPenanamanModal",
        ]),
        registered_date: this.pickString(raw, [
          "tanggal_terbit_oss",
          "tanggalTerbitOss",
          "tgl_terbit_oss",
          "tglTerbitOss",
          "tgl_pengajuan_nib",
          "tglPengajuanNib",
        ]),
        compliance_status: "COMPLIANT",
        oss_public_verified: true,
        oss_public_data: raw,
        verification_sources: ["oss_public"],
        source: "oss_public",
      };
    } catch (err: unknown) {
      const reason = err instanceof Error ? err.message : String(err);
      this.logger.warn("oss_public.failed nib=%s reason=%s", nib, reason);
      return null;
    }
  }

  // ── Step 2 ──────────────────────────────────────────────────────────────────

  private async mergeWithInsw(
    base: NibVerificationResult,
    token: string,
  ): Promise<NibVerificationResult> {
    try {
      const url = `${INSW_API_BASE}/nib?nib=${base.nib}&npwp=${base.npwp}`;
      const resp = await fetch(url, {
        headers: {
          Accept: "application/json",
          Authorization: `Basic ${token}`,
          "User-Agent": "TradeConnect/1.0",
        },
        signal: AbortSignal.timeout(10_000),
      });

      const body = (await resp.json()) as InswResponse;

      if (!resp.ok || body.code !== "01" || !body.data) {
        this.logger.warn(
          "insw.not_confirmed nib=%s code=%s",
          base.nib,
          body.code,
        );
        return base;
      }

      const header = body.data.data_header[0];
      const history: InswHistoryEntry[] = body.data.data_history.map((h) => ({
        status: h.status,
        keterangan: h.ket,
        waktu_oss: h.waktu_oss,
      }));

      return {
        ...base,
        business_name: header?.nama_perusahaan || base.business_name,
        insw_verified: true,
        insw_kategori: header?.kategori ?? "",
        insw_history: history,
      };
    } catch (err: unknown) {
      const reason = err instanceof Error ? err.message : String(err);
      this.logger.warn("insw.failed nib=%s reason=%s", base.nib, reason);
      return base;
    }
  }

  // ── Helpers ─────────────────────────────────────────────────────────────────

  private invalidResult(nib: string): NibVerificationResult {
    return {
      nib,
      is_valid: false,
      business_name: "",
      npwp: "",
      kbli: "",
      kbli_description: "",
      business_scale: "",
      oss_status_aktif: "",
      oss_status_migrasi: "",
      oss_status_penanaman_modal: "",
      compliance_status: "INVALID",
      registered_date: "",
      certifications: [],
      insw_verified: false,
      insw_kategori: "",
      insw_history: [],
      oss_public_verified: false,
      oss_public_data: {},
      verification_sources: [],
      sandbox_mode: false,
    };
  }

  private sandboxResult(nib: string): NibVerificationResult {
    // modulo always yields valid index — non-null assertion is safe
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    const profile =
      SANDBOX_PROFILES[Number(nib.slice(-1)) % SANDBOX_PROFILES.length]!;
    return {
      nib,
      is_valid: true,
      business_name: profile.business_name,
      npwp: profile.npwp,
      kbli: profile.kbli,
      kbli_description: profile.kbli_description,
      business_scale: profile.business_scale,
      oss_status_aktif: "",
      oss_status_migrasi: "",
      oss_status_penanaman_modal: "",
      compliance_status: "COMPLIANT",
      registered_date: profile.registered_date,
      certifications: profile.certifications,
      insw_verified: false,
      insw_kategori: "",
      insw_history: [],
      oss_public_verified: false,
      oss_public_data: {},
      verification_sources: ["sandbox"],
      sandbox_mode: true,
    };
  }

  private mergeNibSources(
    badanPerizinan: NibVerificationResult,
    ossPublic: PartialNibResult | null,
  ): NibVerificationResult {
    if (!ossPublic) return badanPerizinan;

    const sources = new Set<string>([
      ...badanPerizinan.verification_sources,
      ossPublic.source,
    ]);
    if (ossPublic.oss_public_verified) sources.delete("sandbox");

    return {
      ...badanPerizinan,
      is_valid: badanPerizinan.is_valid || ossPublic.is_valid,
      business_name:
        badanPerizinan.business_name || ossPublic.business_name || "",
      npwp: badanPerizinan.npwp || ossPublic.npwp || "",
      kbli: badanPerizinan.kbli || ossPublic.kbli || "",
      kbli_description:
        badanPerizinan.kbli_description || ossPublic.kbli_description || "",
      business_scale:
        badanPerizinan.business_scale || ossPublic.business_scale || "",
      oss_status_aktif:
        badanPerizinan.oss_status_aktif || ossPublic.oss_status_aktif || "",
      oss_status_migrasi:
        badanPerizinan.oss_status_migrasi || ossPublic.oss_status_migrasi || "",
      oss_status_penanaman_modal:
        badanPerizinan.oss_status_penanaman_modal ||
        ossPublic.oss_status_penanaman_modal ||
        "",
      compliance_status:
        badanPerizinan.compliance_status === "INVALID"
          ? ossPublic.compliance_status || "COMPLIANT"
          : badanPerizinan.compliance_status,
      registered_date:
        badanPerizinan.registered_date || ossPublic.registered_date || "",
      oss_public_verified: Boolean(ossPublic.oss_public_verified),
      oss_public_data: ossPublic.oss_public_data ?? {},
      verification_sources: [...sources].filter((source) => source !== ""),
      sandbox_mode:
        badanPerizinan.sandbox_mode && !ossPublic.oss_public_verified,
    };
  }

  private ossLooksValid(raw: OssPublicResponse): boolean {
    const status = this.pickString(raw, ["status", "code", "message", "msg"]);
    const nib = this.pickString(raw, ["nib"]);
    return (
      Boolean(nib) ||
      Boolean(this.pickString(raw, ["nama_perusahaan", "namaPerusahaan", "nama_perseroan", "namaPerseroan"])) ||
      /success|sukses|berhasil|200|01/i.test(status)
    );
  }

  private pickString(source: unknown, keys: string[]): string {
    const value = this.findFirstValue(source, new Set(keys.map((key) => key.toLowerCase())));
    if (typeof value === "string") return value.trim();
    if (typeof value === "number" || typeof value === "boolean") {
      return String(value);
    }
    return "";
  }

  private findFirstValue(source: unknown, keys: Set<string>): unknown {
    if (!source || typeof source !== "object") return undefined;

    if (Array.isArray(source)) {
      for (const item of source) {
        const value = this.findFirstValue(item, keys);
        if (value !== undefined && value !== null && value !== "") return value;
      }
      return undefined;
    }

    for (const [key, value] of Object.entries(source)) {
      if (keys.has(key.toLowerCase())) return value;
      const nested = this.findFirstValue(value, keys);
      if (nested !== undefined && nested !== null && nested !== "") {
        return nested;
      }
    }

    return undefined;
  }
}
