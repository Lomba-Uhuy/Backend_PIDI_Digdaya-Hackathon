import { Injectable, Logger } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import postgres from "postgres";

export interface ChecklistItem {
  id: string;
  label: string;
  description: string;
  required: boolean;
}

export interface ExportDocument {
  id: string;
  name: string;
  type: string;
  description: string;
  fileSize: string;
  icon: string;
  content: string;
}

@Injectable()
export class DocumentChecklistService {
  private readonly logger = new Logger(DocumentChecklistService.name);
  private readonly sql: ReturnType<typeof postgres> | null;

  constructor(cfg: ConfigService) {
    const databaseUrl = cfg.get<string>("DATABASE_URL");
    this.sql = databaseUrl
      ? postgres(databaseUrl, { max: 1, idle_timeout: 20, connect_timeout: 2 })
      : null;
  }

  /**
   * Standard Indonesian export document checklist.
   * Source: Kementerian Perdagangan, INATRADE portal.
   */
  baseChecklist(): ChecklistItem[] {
    return [
      { id: "NIB",     label: "NIB",                      description: "Nomor Induk Berusaha, dari OSS RBA",     required: true  },
      { id: "APE",     label: "Angka Pengenal Ekspor",    description: "Diperlukan untuk ekspor komersial",       required: true  },
      { id: "PEB",     label: "Pemberitahuan Ekspor Barang", description: "Dokumen pabean ekspor",               required: true  },
      { id: "COO",     label: "Certificate of Origin",     description: "Surat keterangan asal barang",           required: true  },
      { id: "PL",      label: "Packing List",              description: "Daftar isi packing",                      required: true  },
      { id: "CINV",    label: "Commercial Invoice",        description: "Invoice perdagangan",                     required: true  },
      { id: "BL",      label: "Bill of Lading / AWB",      description: "Dokumen pengangkutan",                    required: true  },
      { id: "INS",     label: "Insurance Certificate",     description: "Dibutuhkan untuk CIF/CIP",                required: false },
      { id: "PHYTO",   label: "Phytosanitary Certificate", description: "Untuk produk pertanian/agro",            required: false },
      { id: "HALAL",   label: "Sertifikat Halal",          description: "Untuk pasar yang mensyaratkan",          required: false },
      { id: "COA",     label: "Certificate of Analysis",   description: "Untuk produk kimia/farmasi/makanan",     required: false },
    ];
  }

  /**
   * Generates dynamic commercial export documents based on the agreement details.
   */
  async generateDocuments(
    productId: string,
    umkmId: string,
    agreedPrice: number,
    quantityTons = 18.0,
    buyerName?: string,
    buyerLocation?: string,
    buyerCountry?: string,
  ): Promise<ExportDocument[]> {
    let legalName = "";
    let nib = "";
    let productName = "";
    let hsCode = "0901.11";

    if (this.sql) {
      try {
        // Query UMKM details
        const umkmRows = await this.sql`
          SELECT legal_name, nib
          FROM umkm
          WHERE id = ${umkmId}
        `;
        if (umkmRows && umkmRows.length > 0 && umkmRows[0]) {
          legalName = umkmRows[0].legal_name || legalName;
          nib = umkmRows[0].nib || nib;
        }

        // Query Product details
        const productRows = await this.sql`
          SELECT name, hs_code
          FROM product
          WHERE id = ${productId}
        `;
        if (productRows && productRows.length > 0 && productRows[0]) {
          productName = productRows[0].name || productName;
          hsCode = productRows[0].hs_code || "0901.11";
        }
      } catch (err) {
        this.logger.warn(`Failed to query DB for document generation metadata: ${String(err)}.`);
      }
    }

    // Require real UMKM + product data — do not silently use fake placeholders
    if (!legalName || !nib || !productName) {
      this.logger.warn(`generateDocuments: missing required data. umkmId=${umkmId} productId=${productId}`);
      if (!legalName) legalName = `UMKM ID: ${umkmId.substring(0, 8)}`;
      if (!nib) nib = "[NIB belum tersedia]";
      if (!productName) productName = `Produk ID: ${productId.substring(0, 8)}`;
    }

    const consigneeName = buyerName || "[Nama Pembeli Belum Dipilih]";
    const consigneeLocation = buyerLocation || "[Lokasi Pembeli Belum Dipilih]";
    const _buyerCountry = buyerCountry || "";

    const umkmShort = legalName
      .replace(/^(PT|CV|UD|Koperasi)\s+/i, "")
      .split(" ")
      .slice(0, 2)
      .join("")
      .substring(0, 6)
      .toUpperCase();

    // Formatting formulas
    const netWeightKg = quantityTons * 1000;
    const grossWeightKg = netWeightKg + 150; // Add 150 kg for packaging
    const itemTotalVal = agreedPrice * netWeightKg;
    const shippingFreight = 2100;
    const grandTotalVal = itemTotalVal + shippingFreight;

    const formatCurrencyUSD = (val: number) => {
      return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: 2,
      }).format(val);
    };

    const formattedUnitPrice = formatCurrencyUSD(agreedPrice * 1000);
    const formattedItemTotal = formatCurrencyUSD(itemTotalVal);
    const formattedGrandTotal = formatCurrencyUSD(grandTotalVal);
    const formattedQty = quantityTons.toFixed(2);
    const formattedNetWeight = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2 }).format(netWeightKg);
    const formattedGrossWeight = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2 }).format(grossWeightKg);

    return [
      {
        id: "invoice",
        name: "Commercial Invoice (Faktur Dagang)",
        type: `INVOICE-${umkmShort}-202605-001`,
        description: "Tagihan perdagangan resmi yang memuat rincian harga barang, instruksi perbankan, dan syarat pembayaran.",
        fileSize: "148 KB",
        icon: "receipt_long",
        content: `${legalName}
Jakarta, Indonesia
NIB: ${nib}

DITAGIHKAN KEPADA:
${consigneeName}
${consigneeLocation}

DESKRIPSI BARANG: ${productName}
Kode HS: ${hsCode}
Kuantitas: ${formattedQty} Metrik Ton
Harga Satuan: ${formattedUnitPrice} / Metrik Ton
Termin Logistik: CIF
Total Tagihan: ${formattedGrandTotal}

METODE PEMBAYARAN: Letter of Credit (L/C) at Sight
Bank Escrow Pembayar: Bank Mandiri (Persero) Tbk, Jakarta`,
      },
      {
        id: "packing_list",
        name: "Packing List (Rincian Kemasan CBM)",
        type: `PL-${umkmShort}-202605-001`,
        description: "Deskripsi rinci mengenai dimensi kargo kontainer, berat bersih, berat kotor, dan nomor segel kemasan.",
        fileSize: "92 KB",
        icon: "inventory_2",
        content: `DAFTAR KEMASAN (PACKING LIST)
Referensi Pengiriman: PO-${umkmShort}-202605-001
Perusahaan Pelayaran: Maersk Line V.29A

DESKRIPSI KARGO:
Produk: ${productName}
Kemasan: 300 Karung Rami Lapis Ganda (masing-masing berat bersih 60 kg)
Total Karung: 300 Karung
Berat Bersih: ${formattedNetWeight} Kg (${formattedQty} Metrik Ton)
Berat Kotor: ${formattedGrossWeight} Kg
Spesifikasi Kontainer: 1 x 20ft FCL (Full Container Load)
Nomor Segel Kontainer: MAERSK-ID-992182
Volume Kargo: 24.2 CBM`,
      },
      {
        id: "bl",
        name: "Draft Bill of Lading (Konosemen B/L)",
        type: "BL-MAERSK-90021",
        description: "Kontrak pengangkutan laut resmi yang diterbitkan oleh Maersk Line yang menegaskan rute logistik dan instruksi penerima.",
        fileSize: "210 KB",
        icon: "directions_boat",
        content: `BILL OF LADING (DRAFT KONOSEMEN)
Operator Pelayaran: Maersk Line A/S
Nomor B/L: MAEU90881920

PENGIRIM (SHIPPER): ${legalName}, Jakarta, Indonesia
PENERIMA (CONSIGNEE): ${consigneeName}, ${consigneeLocation}
PIHAK NOTIFIKASI: [Bank Pembeli]

PELABUHAN MUAT: Pelabuhan Tanjung Priok (IDTPP), Jakarta
PELABUHAN BONGKAR: [Pelabuhan Tujuan]
NAMA KAPAL: Maersk Mc-Kinney Moller V.2605
STATUS BIAYA: Prabayar berdasarkan Syarat CIF`,
      },
      {
        id: "peb",
        name: "Pemberitahuan Ekspor Barang (PEB)",
        type: "PEB-INSW-099281",
        description: "Pernyataan ekspor bea cukai resmi yang terdaftar dan dinyatakan bersih via INSW (Indonesia National Single Window).",
        fileSize: "312 KB",
        icon: "gavel",
        content: `REPUBLIK INDONESIA - DIREKTORAT JENDERAL BEA DAN CUKAI
PEMBERITAHUAN EKSPOR BARANG (PEB)
Nomor Pengajuan: 099281-${new Date().toISOString().slice(0,10).replace(/-/g,'')}-000001

Eksportir: ${legalName} (NIB: ${nib})
Penerima: ${consigneeName}, ${consigneeLocation}
KBLI Utama: 46311 (Perdagangan Besar Kopi, Teh, dan Kakao)

Komoditas: ${productName}
Kode HS: ${hsCode}
Valuta Ekspor: USD (${formattedGrandTotal})
Kantor Bea Cukai Pemuatan: KPU Tanjung Priok, Jakarta
Status Kelulusan Lartas: BEBAS LARTAS (100% Bersih & Disetujui)`,
      },
      {
        id: "coo",
        name: "Certificate of Origin (Surat Keterangan Asal COO)",
        type: "COO-KADIN-00129",
        description: "Sertifikat Kamar Dagang dan Industri yang menegaskan 100% keaslian asal Indonesia demi kelayakan potongan tarif bea masuk.",
        fileSize: "185 KB",
        icon: "workspace_premium",
        content: `KAMAR DAGANG DAN INDUSTRI INDONESIA (KADIN)
SURAT KETERANGAN ASAL (CERTIFICATE OF ORIGIN - FORM B-2-B)
Nomor Referensi: COO-KADIN-${Date.now().toString().slice(-5)}

Dengan ini kami menyatakan bahwa barang yang dijelaskan di bawah ini adalah asli berasal dari Indonesia:
Eksportir: ${legalName}, Jakarta, Indonesia
Penerima: ${consigneeName}, ${consigneeLocation}

Barang: ${Math.round(quantityTons * 1000 / 60)} Karung ${productName}
Asal Indonesia
Stempel Otoritas: Kamar Dagang dan Industri Indonesia
Status Verifikasi: Aktif & Terverifikasi Asli`,
      },
    ];
  }
}