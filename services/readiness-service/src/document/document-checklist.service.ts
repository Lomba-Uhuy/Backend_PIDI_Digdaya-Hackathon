import { Injectable } from '@nestjs/common';

export interface ChecklistItem {
  id: string;
  label: string;
  description: string;
  required: boolean;
}

@Injectable()
export class DocumentChecklistService {
  /**
   * Standard Indonesian export document checklist.
   * Source: Kementerian Perdagangan, INATRADE portal.
   */
  baseChecklist(): ChecklistItem[] {
    return [
      { id: 'NIB',     label: 'NIB',                      description: 'Nomor Induk Berusaha, dari OSS RBA',     required: true  },
      { id: 'APE',     label: 'Angka Pengenal Ekspor',    description: 'Diperlukan untuk ekspor komersial',       required: true  },
      { id: 'PEB',     label: 'Pemberitahuan Ekspor Barang', description: 'Dokumen pabean ekspor',               required: true  },
      { id: 'COO',     label: 'Certificate of Origin',     description: 'Surat keterangan asal barang',           required: true  },
      { id: 'PL',      label: 'Packing List',              description: 'Daftar isi packing',                      required: true  },
      { id: 'CINV',    label: 'Commercial Invoice',        description: 'Invoice perdagangan',                     required: true  },
      { id: 'BL',      label: 'Bill of Lading / AWB',      description: 'Dokumen pengangkutan',                    required: true  },
      { id: 'INS',     label: 'Insurance Certificate',     description: 'Dibutuhkan untuk CIF/CIP',                required: false },
      { id: 'PHYTO',   label: 'Phytosanitary Certificate', description: 'Untuk produk pertanian/agro',            required: false },
      { id: 'HALAL',   label: 'Sertifikat Halal',          description: 'Untuk pasar yang mensyaratkan',          required: false },
      { id: 'COA',     label: 'Certificate of Analysis',   description: 'Untuk produk kimia/farmasi/makanan',     required: false },
    ];
  }
}