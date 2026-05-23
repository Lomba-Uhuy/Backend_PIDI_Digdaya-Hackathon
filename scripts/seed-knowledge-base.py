#!/usr/bin/env python3
"""Export Knowledge Base seeder for TradeConnect RAG pipeline.

Populates export_knowledge_base with ~50 authoritative entries covering:
  - Incoterms 2020
  - Payment terms and risk management
  - Negotiation strategies for UMKM exporters
  - Fraud red flag indicators
  - Export document requirements
  - Indonesian export regulations
  - Logistics and shipping
  - Market intelligence

Optionally generates 1024-dim embeddings using intfloat/multilingual-e5-large
(same model as matching-service) if sentence-transformers is available.

Usage:
    python scripts/seed-knowledge-base.py
    python scripts/seed-knowledge-base.py --with-embeddings
    python scripts/seed-knowledge-base.py --clear --with-embeddings
    python scripts/seed-knowledge-base.py --dsn postgresql+psycopg://tc_user:tc_pass_dev@localhost:5432/tradeconnect

Requirements (standalone):
    uv pip install sqlalchemy "psycopg[binary]" pgvector
    # For embeddings:
    uv pip install "sentence-transformers>=3.3" "torch>=2.0"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from uuid import uuid4

try:
    from sqlalchemy import create_engine, text
except ImportError as exc:
    raise SystemExit("Install sqlalchemy: uv pip install sqlalchemy 'psycopg[binary]'") from exc

# ─────────────────────────────────────────────────────────────────────────────
# Knowledge Base Entries
# category choices: incoterms | payment_terms | negotiation | fraud_indicators
#                   documents | regulations | logistics | market_intelligence
# ─────────────────────────────────────────────────────────────────────────────

KB_ENTRIES: list[dict] = [

    # ══════════════════════ INCOTERMS ══════════════════════

    {
        "title": "FOB – Free On Board: Panduan Lengkap untuk Eksportir Indonesia",
        "category": "incoterms",
        "source": "Incoterms 2020, ICC Publication No. 723",
        "content": """FOB (Free On Board) adalah salah satu Incoterms paling umum digunakan dalam ekspor Indonesia.
Artinya: Penjual (eksportir) bertanggung jawab atas barang hingga barang dimuat ke atas kapal di pelabuhan keberangkatan yang disepakati.

TANGGUNG JAWAB PENJUAL (EKSPORTIR):
- Mengemas barang sesuai standar ekspor
- Mengurus bea cukai ekspor, perizinan, dan PEB
- Mengirimkan barang ke pelabuhan keberangkatan
- Memuat barang ke atas kapal
- Biaya dan risiko sampai barang berada di atas kapal

TANGGUNG JAWAB PEMBELI (IMPORTIR):
- Menyewa kapal dan membayar biaya pengiriman (ocean freight)
- Membayar asuransi kargo
- Mengurus bea cukai impor di negara tujuan
- Menanggung semua risiko setelah barang dimuat ke kapal

KAPAN RISIKO BERALIH: Tepat saat barang dimuat ke atas kapal (on board) di pelabuhan keberangkatan.

KEUNTUNGAN FOB UNTUK UMKM:
- Harga penawaran lebih mudah dihitung (tidak perlu menghitung freight + asuransi)
- Pembeli biasanya sudah punya kontrak shipping yang lebih murah
- Umum digunakan, pembeli internasional sangat familiar

CONTOH PENULISAN: FOB Tanjung Priok, Jakarta
Artinya: Risiko beralih saat barang dimuat di Pelabuhan Tanjung Priok.

PERHATIAN: Untuk kontainer, gunakan FCA (Free Carrier) bukan FOB, karena risiko sebenarnya beralih saat penyerahan ke forwarder/terminal, bukan saat dimuat ke kapal.""",
    },

    {
        "title": "CIF – Cost, Insurance, Freight: Ketika Eksportir Menanggung Lebih Banyak",
        "category": "incoterms",
        "source": "Incoterms 2020, ICC Publication No. 723",
        "content": """CIF (Cost, Insurance, Freight) berarti eksportir membayar biaya pengiriman DAN asuransi kargo hingga pelabuhan tujuan.

TANGGUNG JAWAB PENJUAL (EKSPORTIR):
- Semua tanggung jawab FOB, DITAMBAH:
- Menyewa kapal dan membayar ocean freight
- Membeli asuransi minimum (Institute Cargo Clauses C) untuk kepentingan pembeli
- Mengurus semua dokumen pengiriman

TANGGUNG JAWAB PEMBELI:
- Bea cukai impor di negara tujuan
- Biaya port handling di pelabuhan tujuan
- Asuransi tambahan jika merasa minimum coverage tidak cukup

KAPAN RISIKO BERALIH: Saat barang dimuat ke atas kapal di pelabuhan keberangkatan
(SAMA seperti FOB – bukan di pelabuhan tujuan!)

PENTING: Walaupun penjual membayar freight dan asuransi, risiko tetap beralih ke pembeli begitu barang naik kapal. Jika kapal tenggelam setelah meninggalkan pelabuhan, itu masalah pembeli – bukan penjual.

CARA MENGHITUNG HARGA CIF:
CIF = HPP + Biaya Produksi + Keuntungan + Biaya Ekspor + Ocean Freight + Premi Asuransi

KEUNTUNGAN CIF UNTUK UMKM:
- Harga terlihat lebih tinggi (mencakup freight)
- Pembeli lebih mudah membandingkan total landed cost
- Cocok untuk pembeli yang belum berpengalaman dengan logistik ekspor

KELEMAHAN: Eksportir harus punya pengetahuan tentang biaya pengiriman ke berbagai negara.""",
    },

    {
        "title": "CFR – Cost and Freight: Penjual Bayar Freight, Pembeli Bayar Asuransi",
        "category": "incoterms",
        "source": "Incoterms 2020, ICC Publication No. 723",
        "content": """CFR (Cost and Freight) mirip CIF, tetapi penjual TIDAK membayar asuransi.

TANGGUNG JAWAB PENJUAL:
- Semua tanggung jawab FOB, DITAMBAH:
- Membayar ocean freight ke pelabuhan tujuan
- Tidak perlu membeli asuransi

TANGGUNG JAWAB PEMBELI:
- Membeli asuransi sendiri
- Bea cukai impor

RISIKO BERALIH: Sama seperti FOB dan CIF – saat barang dimuat ke kapal.

KAPAN GUNAKAN CFR: Ketika pembeli ingin memilih asuransi sendiri (karena punya polis group coverage yang lebih baik), tapi tetap ingin penjual mengurus pengiriman.

PERBANDINGAN FOB, CFR, CIF:
- FOB: Penjual bayar sampai muat kapal. Pembeli urus freight + asuransi.
- CFR: Penjual bayar freight. Pembeli urus asuransi.
- CIF: Penjual bayar freight + asuransi (minimum).

TIPS UNTUK UMKM: Jika pembeli meminta CIF tapi kamu tidak yakin dengan biaya freight, minta mereka pilih CFR atau FOB agar tidak rugi karena salah estimasi freight.""",
    },

    {
        "title": "EXW – Ex Works: Tanggung Jawab Paling Sedikit untuk Eksportir",
        "category": "incoterms",
        "source": "Incoterms 2020, ICC Publication No. 723",
        "content": """EXW (Ex Works) adalah incoterm di mana eksportir punya tanggung jawab PALING SEDIKIT.

TANGGUNG JAWAB PENJUAL:
- Hanya menyediakan barang di lokasi produksi/gudang
- Mengemas sesuai permintaan
- TIDAK mengurus bea cukai ekspor
- TIDAK memuat ke truk

TANGGUNG JAWAB PEMBELI:
- Segala sesuatu mulai dari pabrik penjual
- Memuat barang ke kendaraan
- Mengurus bea cukai ekspor Indonesia
- Membayar semua biaya pengiriman, asuransi
- Mengurus bea cukai impor

RISIKO BERALIH: Saat barang tersedia di lokasi penjual.

CONTOH: EXW Pabrik Cirebon, Jawa Barat

PERINGATAN UNTUK EKSPORTIR INDONESIA:
EXW terlihat mudah tapi sebenarnya BERBAHAYA untuk eksportir Indonesia karena:
1. Eksportir tetap bertanggung jawab atas PEB (dokumen ekspor Indonesia) yang harus diurus pembeli asing
2. Jika ada masalah bea cukai, akan sulit diselesaikan karena pihak asing yang mengurus
3. Lebih baik gunakan FCA yang memberikan proteksi lebih baik

REKOMENDASI: Untuk UMKM, hindari EXW kecuali pembeli sangat berpengalaman dan punya agen lokal di Indonesia.""",
    },

    {
        "title": "DAP – Delivered at Place: Eksportir Menanggung Semua Biaya ke Tujuan",
        "category": "incoterms",
        "source": "Incoterms 2020, ICC Publication No. 723",
        "content": """DAP (Delivered at Place) berarti penjual menanggung hampir semua biaya dan risiko hingga lokasi tujuan pembeli.

TANGGUNG JAWAB PENJUAL:
- Semua biaya ekspor, freight, dan asuransi
- Pengiriman hingga tempat tujuan yang disepakati
- Bea cukai EKSPOR (di Indonesia)
- Tidak menanggung bea cukai impor di negara tujuan

TANGGUNG JAWAB PEMBELI:
- Bea cukai impor
- Pajak impor
- Biaya bongkar muat di lokasi tujuan

RISIKO BERALIH: Saat barang tiba di tempat tujuan dan siap untuk dibongkar.

KAPAN GUNAKAN DAP:
- Pembeli baru yang tidak berpengalaman dengan logistik
- Ketika kamu punya mitra freight forwarder yang handal
- Ketika kamu bisa menghitung biaya door-to-door dengan akurat

PERHATIAN: DAP memerlukan pengetahuan mendalam tentang biaya pengiriman ke negara tujuan. Kalkulasikan secara detail sebelum menawarkan harga DAP karena kamu menanggung SEMUA biaya hingga pintu pembeli.""",
    },

    {
        "title": "FCA – Free Carrier: Pengganti Modern untuk FOB dalam Pengiriman Kontainer",
        "category": "incoterms",
        "source": "Incoterms 2020, ICC Publication No. 723",
        "content": """FCA (Free Carrier) adalah incoterm yang DIREKOMENDASIKAN untuk pengiriman kontainer, menggantikan FOB.

MENGAPA FCA LEBIH BAIK DARI FOB UNTUK KONTAINER?
Dalam pengiriman kontainer modern:
- Penjual menyerahkan barang ke terminal kontainer (CY - Container Yard)
- Barang dimuat ke kontainer di terminal, BUKAN langsung ke kapal
- Dengan FOB, risiko belum beralih saat penyerahan ke terminal
- Dengan FCA, risiko beralih saat penyerahan ke carrier/terminal

TANGGUNG JAWAB PENJUAL DENGAN FCA:
- Mengurus bea cukai ekspor
- Menyerahkan barang ke freight carrier/terminal yang ditunjuk pembeli
- Di lokasi yang disepakati (bisa gudang penjual atau terminal)

TANGGUNG JAWAB PEMBELI:
- Menyewa kapal, membayar freight
- Membeli asuransi
- Bea cukai impor

RISIKO BERALIH: Saat penyerahan ke carrier di lokasi yang disepakati.

PEMBARUAN INCOTERMS 2020: FCA sekarang bisa mensyaratkan pembeli meminta Bill of Lading yang sudah dicap "on board" untuk kepentingan LC, mengatasi masalah lama dengan bank.

REKOMENDASI UMKM: Untuk ekspor menggunakan kontainer dari pelabuhan Indonesia, gunakan FCA [Terminal Kontainer] daripada FOB.""",
    },

    # ══════════════════════ PAYMENT TERMS ══════════════════════

    {
        "title": "Letter of Credit (L/C): Instrumen Pembayaran Paling Aman untuk Eksportir",
        "category": "payment_terms",
        "source": "UCP 600, ICC; Bank Indonesia Regulation",
        "content": """Letter of Credit (L/C) atau Surat Kredit Berdokumen adalah instrumen pembayaran yang PALING AMAN untuk eksportir karena pembayaran dijamin oleh bank.

CARA KERJA L/C:
1. Importir meminta bank-nya (Issuing Bank) membuka L/C
2. Bank importir mengirim L/C ke bank koresponden/advising bank di Indonesia
3. Eksportir menerima L/C dan memeriksa syarat-syaratnya
4. Eksportir mengirimkan barang sesuai syarat L/C
5. Eksportir menyerahkan dokumen ke bank lokal (Nominated Bank)
6. Bank memeriksa dokumen – jika compliant, pembayaran dilakukan
7. Bank lokal meneruskan dokumen ke bank importir
8. Bank importir mendebet rekening importir

JENIS-JENIS L/C:
- Sight L/C (L/C Atas Unjuk): Pembayaran segera setelah dokumen diperiksa dan disetujui. PALING DIREKOMENDASIKAN untuk UMKM.
- Usance/Deferred L/C: Pembayaran pada tanggal jatuh tempo (misal 30, 60, 90 hari setelah pengapalan). Ada risiko karena pembayaran tertunda.
- Irrevocable L/C: Tidak bisa dibatalkan tanpa persetujuan semua pihak. WAJIB diminta.
- Confirmed L/C: Bank lokal juga ikut menjamin pembayaran. Lebih aman jika bank importir tidak dikenal.

DOKUMEN YANG BIASANYA DIMINTA L/C:
- Commercial Invoice (2-3 rangkap)
- Packing List
- Bill of Lading atau Airway Bill
- Certificate of Origin
- Insurance Certificate (jika CIF)
- Inspection Certificate (jika diminta)

TIPS KRITIS: Periksa SETIAP detail L/C sebelum mengirimkan barang:
- Nama dan alamat eksportir harus PERSIS SAMA
- Deskripsi barang harus cocok
- Tanggal expired harus cukup
- Tanggal pengapalan terakhir harus masuk akal
- Port of loading harus benar

KESALAHAN FATAL: Perbedaan sekecil apapun dalam dokumen bisa menyebabkan DISCREPANCY dan bank menolak pembayaran.""",
    },

    {
        "title": "Telegraphic Transfer (T/T): Pembayaran Kawat untuk Ekspor",
        "category": "payment_terms",
        "source": "SWIFT International; Bank Indonesia",
        "content": """Telegraphic Transfer (T/T) atau Wire Transfer adalah pembayaran langsung dari rekening pembeli ke rekening eksportir melalui sistem SWIFT.

JENIS T/T BERDASARKAN TIMING:
1. T/T Advance (Pembayaran di Muka): Pembeli bayar 100% sebelum ekspor. PALING AMAN untuk eksportir, tapi sering ditolak pembeli baru.
2. T/T 30/70: Pembeli bayar 30% DP, 70% setelah dokumen pengapalan diterima. Umum dan seimbang.
3. T/T After Shipment: Pembeli bayar setelah menerima dokumen atau barang. BERISIKO untuk eksportir.
4. T/T Against Documents: Pembayaran dilakukan saat dokumen diserahkan ke bank pembeli.

STRUKTUR T/T YANG DIREKOMENDASIKAN UNTUK UMKM:
- 30% DP saat konfirmasi order
- 70% setelah copy Bill of Lading dikirimkan via email
- Original dokumen dikirim via DHL setelah pembayaran penuh

RISIKO T/T UNTUK EKSPORTIR:
- Tidak ada bank guarantor – jika pembeli tidak bayar, sulit menagih
- Khusus pembeli baru, JANGAN pernah kirim barang sebelum ada pembayaran yang masuk
- Waspada terhadap bukti pembayaran palsu (payment confirmation palsu)

CARA VERIFIKASI T/T:
- Konfirmasi langsung ke bank kamu (jangan percaya screenshot dari pembeli)
- Tunggu dana BENAR-BENAR masuk ke rekening, bukan hanya notifikasi
- Khusus untuk jumlah besar (>$10,000), minta konfirmasi dari bank

BIAYA T/T: Biasanya USD 15-50 per transaksi, dibagi antara kedua pihak. Tentukan siapa yang menanggung biaya wire transfer.""",
    },

    {
        "title": "D/P dan D/A: Documentary Collection untuk Ekspor",
        "category": "payment_terms",
        "source": "URC 522, ICC; Bank BNI, Bank Mandiri Trade Finance",
        "content": """Documentary Collection adalah metode pembayaran melalui bank, lebih murah dari L/C tapi kurang aman.

D/P – DOCUMENTS AGAINST PAYMENT (Pembayaran Atas Dokumen):
- Eksportir menyerahkan dokumen ke bank Indonesia
- Bank Indonesia mengirim dokumen ke bank pembeli
- Pembeli HARUS BAYAR terlebih dahulu untuk mendapatkan dokumen
- Dokumen diperlukan untuk mengambil barang dari pelabuhan
- Pembayaran biasanya 5-10 hari kerja setelah pengapalan

KEUNGGULAN D/P:
- Lebih murah dari L/C (biaya bank lebih rendah)
- Pembeli tidak bisa ambil barang tanpa bayar
- Dokumen dikendalikan bank, bukan langsung dikirim ke pembeli

RISIKO D/P:
- Jika pembeli menolak bayar, barang tertahan di pelabuhan tujuan
- Biaya warehousing/demurrage bisa mahal
- Bisa dipaksa jual murah atau re-ekspor barang

D/A – DOCUMENTS AGAINST ACCEPTANCE (Dokumen Atas Akseptasi):
- Pembeli cukup "menerima" (menandatangani) wesel jangka waktu untuk mendapatkan dokumen
- Pembayaran dilakukan pada tanggal jatuh tempo (30, 60, 90 hari)
- LEBIH BERISIKO karena pembeli sudah pegang barang sebelum bayar

KAPAN GUNAKAN D/P: Untuk pembeli yang sudah dikenal, reputasi bagus, tapi belum cukup percaya untuk T/T after shipment.
HINDARI D/A: Untuk pembeli baru karena terlalu berisiko.

REKOMENDASI URUTAN KEAMANAN PEMBAYARAN (dari paling aman):
1. T/T 100% Advance
2. Sight L/C (Confirmed)
3. Sight L/C (Unconfirmed)
4. T/T with 30-50% DP
5. D/P Sight
6. Usance L/C
7. D/A
8. Open Account (PALING BERISIKO)""",
    },

    {
        "title": "Open Account: Risiko Tertinggi, Hanya untuk Buyer Terpercaya",
        "category": "payment_terms",
        "source": "International Trade Centre (ITC); OECD Trade Finance",
        "content": """Open Account adalah ketika eksportir mengirimkan barang TERLEBIH DAHULU, dan pembeli membayar belakangan sesuai termin yang disepakati (net 30, net 60, dll).

CARA KERJA:
- Barang dikirim dan dokumen langsung diberikan ke pembeli
- Invoice diterbitkan dengan tanggal jatuh tempo
- Pembeli bayar pada atau sebelum tanggal jatuh tempo
- Tidak ada keterlibatan bank sebagai garantor

RISIKO SANGAT TINGGI UNTUK UMKM:
- Tidak ada jaminan pembayaran
- Jika pembeli bangkrut, uang hilang
- Sulit menagih secara internasional
- Butuh modal kerja besar karena cash flow tertunda

KAPAN OPEN ACCOUNT BISA DITERIMA:
- Pembeli sudah berbisnis dengan kamu minimal 2-3 tahun
- Track record pembayaran impeccable
- Nominal kecil (tidak lebih dari 10% total outstanding credit)
- Ada asuransi piutang ekspor (export credit insurance)

ASURANSI PIUTANG EKSPOR:
Indonesia Eximbank (LPEI) menyediakan asuransi piutang ekspor. Dengan asuransi ini, jika pembeli tidak bayar, LPEI akan mengganti rugi hingga 90% dari nilai invoice. Pertimbangkan ini jika dipaksa menggunakan Open Account.

TANDA PERINGATAN: Jika pembeli baru LANGSUNG meminta Open Account, ini adalah RED FLAG. Pembeli serius tidak keberatan membayar advance atau membuka L/C.""",
    },

    # ══════════════════════ NEGOTIATION ══════════════════════

    {
        "title": "Price Anchoring: Strategi Tetapkan Harga Pertama yang Menguntungkan",
        "category": "negotiation",
        "source": "Harvard Negotiation Project; Getting to Yes, Fisher & Ury",
        "content": """Price Anchoring adalah teknik negosiasi di mana pihak yang menyebutkan angka PERTAMA memiliki keunggulan psikologis besar.

PRINSIP DASAR:
Angka pertama yang disebut dalam negosiasi menjadi "jangkar" psikologis. Semua diskusi selanjutnya akan berputar di sekitar angka ini. Pembeli yang menyebut harga rendah akan menarik negosiasi ke bawah; penjual yang menyebut harga tinggi akan menahan negosiasi tetap tinggi.

CARA MENERAPKAN UNTUK UMKM EKSPORTIR:

1. SELALU TAWARKAN HARGA LEBIH TINGGI DARI TARGET:
   - Target kamu USD 5 per unit? Tawarkan USD 6.50-7.00
   - Ini memberi ruang untuk negosiasi tanpa mengorbankan margin
   - Pembeli akan menawar, dan kamu bisa "mengalah" sambil tetap profitable

2. JANGAN PERNAH MENYEBUT FLOOR PRICE (Harga Minimum):
   - JANGAN bilang: "Minimum kami USD 4.50 per unit"
   - KATAKAN: "Untuk kuantitas ini, harga terbaik kami USD 6.50. Berapa kebutuhan bulanan Anda?"

3. ANCHOR DENGAN REFERENSI EKSTERNAL:
   - "Harga ekspor pasar saat ini untuk produk sejenis USD 7-8. Kami menawarkan USD 6.50 karena kami sangat tertarik membangun hubungan jangka panjang."
   - Gunakan data UN Comtrade Export Unit Value sebagai referensi

4. ANCHOR DENGAN VOLUME:
   - Tawarkan harga berbeda berdasarkan volume untuk "memancing" pembeli naik kuantitas
   - "500 unit: USD 6.50, 1000 unit: USD 6.00, 2000 unit+: USD 5.50"

5. HINDARI TERLALU CEPAT KONTRA-PENAWARAN:
   - Ketika pembeli menawar, jangan langsung turunkan harga
   - Tanyakan dulu: "Bisakah Anda bantu saya memahami kenapa harga tersebut tidak cocok?"
   - Informasi ini berguna untuk counter-offer yang tepat sasaran""",
    },

    {
        "title": "Menangani Tawaran Harga Terlalu Rendah: Taktik untuk UMKM Eksportir",
        "category": "negotiation",
        "source": "International Trade Centre (ITC); Export Strategy Guide",
        "content": """Ketika pembeli berkata "hargamu terlalu mahal" atau menawar sangat rendah, ini adalah respons yang tepat.

JANGAN PANIK DAN LANGSUNG TURUNKAN HARGA.
Penurunan harga langsung mengirimkan sinyal bahwa harga awal kamu tidak serius.

LANGKAH 1 – VALIDASI TANPA MENYERAHKAN POSISI:
"Terima kasih atas feedback-nya. Bisakah Anda membantu saya memahami target harga Anda berdasarkan apa? Apakah ada supplier lain yang memberikan penawaran untuk produk dengan spesifikasi yang sama?"

LANGKAH 2 – CARI TAHU APAKAH MEREKA SERIUS:
Banyak pembeli menawar rendah sebagai refleks, bukan karena mereka benar-benar mendapat penawaran lebih murah. Tanyakan: "Jika kita bisa mencapai harga yang cocok, apakah Anda siap konfirmasi order minggu ini?"

LANGKAH 3 – TAWARKAN ALTERNATIF (BUKAN DISKON):
Sebelum turunkan harga, tawarkan trade-off:
- "Saya bisa kurangi harga USD 0.30 jika pembayaran T/T 100% di muka"
- "Untuk order 2x lipat, saya bisa berikan harga yang lebih kompetitif"
- "Kita bisa sesuaikan packaging menjadi lebih sederhana untuk menurunkan biaya"

LANGKAH 4 – TURUNKAN HARGA SECARA BERTAHAP DAN KECIL:
Jika harus turunkan harga:
- Penurunan pertama: maksimal 5-8% dari harga awal
- Setiap penurunan harus diiringi sesuatu yang diminta dari pembeli
- Jangan pernah langsung ke harga minimum

KALIMAT PENTING: "Saya sangat ingin kita bisa bekerja sama. Boleh saya tanya, apa yang paling penting untuk Anda: harga, kualitas, lead time, atau syarat pembayaran? Mari kita cari solusi yang menguntungkan kedua pihak."

KAPAN BERHENTI BERNEGOSIASI:
Jika pembeli meminta harga di bawah floor price kamu, lebih baik tolak dengan sopan: "Saya sangat menghargai minat Anda, namun sayangnya pada harga tersebut saya tidak dapat memastikan kualitas yang Anda inginkan. Saya harap kita bisa mencoba lagi di kesempatan lain."
""",
    },

    {
        "title": "BATNA: Senjata Rahasia dalam Negosiasi Ekspor",
        "category": "negotiation",
        "source": "Harvard Negotiation Project; Getting to Yes, Fisher & Ury",
        "content": """BATNA (Best Alternative to a Negotiated Agreement) adalah opsi terbaik yang kamu miliki jika negosiasi GAGAL. Ini adalah kekuatan terbesar dalam negosiasi.

MENGAPA BATNA PENTING:
- Eksportir tanpa BATNA mudah panik dan terlalu cepat menyerahkan posisi
- Eksportir dengan BATNA yang kuat bisa bernegosiasi dengan percaya diri
- BATNA menentukan seberapa jauh kamu mau "mengalah"

CONTOH BATNA UMKM EKSPORTIR:
- "Jika deal dengan pembeli Jerman ini gagal, saya punya buyer dari Dubai yang sudah offer USD 5.20 dan menunggu konfirmasi."
- "Jika harga tidak tercapai, saya bisa jual ke pasar domestik premium di harga lebih tinggi."
- "Ada pameran Sial Interfood bulan depan di mana saya bisa cari 3-5 pembeli baru."

CARA MEMPERKUAT BATNA SEBELUM NEGOSIASI:
1. Selalu negosiasi dengan BEBERAPA calon pembeli secara bersamaan
2. Daftarkan produk di platform B2B: Alibaba, Global Sources, TradeKey
3. Ikuti pameran dagang: SIAL, Gulfood, Foodex Japan
4. Bangun database calon pembeli dari ITC TradeMap, UN Comtrade

ATURAN EMAS: JANGAN PERNAH UNGKAPKAN BATNA KEPADA PEMBELI
- JANGAN: "Kalau tidak jadi order kamu, saya punya buyer lain yang mau bayar lebih tinggi."
- Mengungkapkan BATNA mengurangi kekuatannya dan bisa menyinggung pembeli

CARA MEMANFAATKAN BATNA TANPA MENGUNGKAPKANNYA:
- "Saya perlu konfirmasi dari Anda sebelum akhir minggu karena saya perlu mengalokasikan kapasitas produksi kami."
- "Kuartal ini kapasitas kami sudah hampir penuh. Jika Anda bisa konfirmasi sekarang, saya bisa prioritaskan order Anda."
- Ketenangan dan tidak terburu-buru dalam negosiasi adalah sinyal implisit bahwa kamu punya alternatif.""",
    },

    {
        "title": "Strategi Counter-Offer yang Efektif dalam Negosiasi Ekspor",
        "category": "negotiation",
        "source": "International Chamber of Commerce (ICC); Export Development Canada",
        "content": """Counter-offer yang efektif membutuhkan strategi, bukan sekadar angka.

PRINSIP COUNTER-OFFER:
1. Selalu berikan alasan untuk setiap perubahan harga
2. Minta sesuatu sebagai imbalan setiap kali kamu mengalah
3. Jangan pernah langsung ke harga final

FORMULA COUNTER-OFFER:

CONTOH: Pembeli minta USD 4.50, harga kamu USD 6.50, target USD 5.50

PUTARAN 1 – Beri sedikit, minta banyak:
"Saya sangat menghargai ketertarikan Anda. Untuk order pertama, saya bisa berikan USD 6.00 (turun 50 sen dari harga awal). Sebagai imbalannya, bisakah Anda mempertimbangkan T/T 50% advance dan konfirmasi order sebelum akhir bulan?"

PUTARAN 2 – Jika masih ditawar:
"Saya mengerti kekhawatiran Anda tentang harga. Saya bisa turun sedikit lagi ke USD 5.75 tetapi hanya jika minimal order ditingkatkan dari 500 ke 800 unit, dan pembayaran 30% DP."

PUTARAN 3 – Mendekati target:
"Ini penawaran terbaik yang saya bisa berikan: USD 5.50 untuk 1000 unit dengan T/T 30% DP, 70% setelah copy BL. Harga ini sudah mencakup standard export packaging dan Certificate of Origin."

TEKNIK "NIBBLE" (Minta sedikit lebih di akhir):
Setelah deal hampir tercapai, minta sedikit tambahan:
"Deal, saya setuju USD 5.50. Oh, satu hal kecil – bisakah Anda minta freight forwarder Anda punya office di Surabaya? Ini akan memudahkan koordinasi pengiriman."

JANGAN LAKUKAN:
- Jangan counter dengan perbedaan yang terlalu besar sekaligus
- Jangan katakan "Ini harga final saya" jika kamu belum benar-benar di sana
- Jangan beri counter-offer tanpa alasan""",
    },

    {
        "title": "Negosiasi Volume dan Kemitraan Jangka Panjang",
        "category": "negotiation",
        "source": "Export Strategy Guide; ITC Geneva",
        "content": """Pembeli yang berkomitmen volume besar dan jangka panjang layak mendapat diskon – tapi pastikan komitmen itu nyata.

MENGAPA FOKUS PADA LONG-TERM PARTNERSHIP:
- Biaya akuisisi buyer baru jauh lebih mahal dari mempertahankan yang lama
- Buyer rutin memungkinkan perencanaan produksi lebih baik
- Hubungan panjang sering berujung pada referral buyer baru

STRUKTUR DISKON VOLUME:
Berikan diskon berjenjang berdasarkan commitment:
- 1 kali order: harga standard
- Kontrak 6 bulan (2 shipment): 3% discount
- Kontrak 12 bulan (4 shipment): 5% discount
- Kontrak 24 bulan exclusive: 7-8% discount

CARA MENDAPATKAN KOMITMEN YANG NYATA:
- Minta Purchase Order atau Letter of Intent tertulis, bukan hanya "janji verbal"
- Tentukan minimum quantity per shipment dalam kontrak
- Tentukan konsekuensi jika tidak mencapai volume (misal harga revert ke harga standard)

KALIMAT NEGOSIASI EFEKTIF:
"Saya sangat tertarik membangun kemitraan jangka panjang dengan perusahaan Anda. Jika Anda bisa berkomitmen minimal 1 kontainer per kuartal selama setahun, saya siap memberikan harga khusus USD 5.20 (vs USD 5.50 untuk one-time order). Bagaimana menurut Anda?"

PERHATIKAN TANDA-TANDA KOMITMEN PALSU:
- Pembeli yang hanya mau "coba dulu" tanpa komitmen volume
- Janji volume besar tapi minta harga rendah SEKARANG tanpa jaminan apapun
- Tidak mau menandatangani Letter of Intent""",
    },

    # ══════════════════════ FRAUD INDICATORS ══════════════════════

    {
        "title": "Red Flag: 10 Tanda Pembeli Internasional Tidak Dapat Dipercaya",
        "category": "fraud_indicators",
        "source": "FinCEN Advisory; UN CTED; Ditjen Bea dan Cukai RI",
        "content": """Kejahatan perdagangan internasional (Trade-Based Financial Crime) adalah ancaman nyata. Kenali tanda-tandanya.

RED FLAG #1 – HARGA TERLALU JAUH DI BAWAH PASAR:
Jika pembeli menawarkan harga jauh di atas pasar atau barang sangat mudah terjual, ini mungkin scam untuk memancing pengiriman barang.

RED FLAG #2 – PERMINTAAN PEMBAYARAN TUNAI KE REKENING OFFSHORE:
"Tolong transfer biaya administrasi USD 500 ke rekening pribadi kami di Hong Kong sebelum kami proses order." Ini PENIPUAN. Tidak ada transaksi ekspor yang memerlukan pembayaran ke rekening pribadi.

RED FLAG #3 – DOKUMEN PERUSAHAAN TIDAK BISA DIVERIFIKASI:
- Website tidak ada atau dibuat baru-baru ini
- Alamat di Google Maps menunjukkan rumah atau lahan kosong
- Nomor telepon tidak aktif atau nomor pribadi
- Tidak ada jejak di LinkedIn, Dun & Bradstreet, atau direktori bisnis

RED FLAG #4 – TEKANAN WAKTU TIDAK WAJAR:
"Order ini harus dikirim minggu depan karena ada deadline dari client kami." Penipu sering menciptakan urgensi palsu agar korban tidak sempat verifikasi.

RED FLAG #5 – PERMINTAAN MODIFIKASI RUTE PENGIRIMAN ANEH:
"Tolong kirim ke Singapura dulu, nanti kami urus re-ekspor ke tujuan akhir." Rute tidak wajar bisa indikasi pencucian uang atau penghindaran sanksi.

RED FLAG #6 – OVERPAYMENT SCAM:
Pembeli mengirim lebih dari jumlah invoice dan meminta kembalian. Cek asli palsu, tapi permintaan kembalian nyata.

RED FLAG #7 – EMAIL DOMAIN TIDAK PROFESIONAL:
Email dari gmail/yahoo untuk perusahaan besar adalah red flag. Cek apakah domain email cocok dengan website perusahaan.

RED FLAG #8 – TIDAK MAU MELAKUKAN VIDEO CALL:
Penipu biasanya menghindari video call karena takut identitas terbongkar.

RED FLAG #9 – L/C DARI BANK YANG TIDAK DIKENAL:
Bank tidak terkenal, terutama dari yurisdiksi berisiko tinggi (Belize, Vanuatu, dll). Verifikasi bank melalui SWIFT BIC code.

RED FLAG #10 – MEMINTA DATA RAHASIA AWAL:
"Sebelum kami proses order, mohon kirimkan full product costing dan supplier information." Informasi ini bisa dijual ke kompetitor.""",
    },

    {
        "title": "Cara Verifikasi Identitas Pembeli Internasional Sebelum Ekspor",
        "category": "fraud_indicators",
        "source": "ITC TradeMap; Dun & Bradstreet; ICC Commercial Crime Services",
        "content": """Verifikasi pembeli adalah investasi 30 menit yang bisa menyelamatkan ratusan juta rupiah.

LANGKAH VERIFIKASI (GRATIS):

1. CEK WEBSITE:
- Buka web browser, cek domain website pembeli
- Gunakan WHOIS (whois.net) untuk cek kapan domain dibuat – domain <1 tahun CURIGAI
- Cek apakah ada review negatif dengan Google: "[nama perusahaan] + scam/fraud/complaint"

2. VERIFIKASI ALAMAT:
- Buka Google Maps, masukkan alamat perusahaan
- Apakah terlihat seperti kantor? Atau rumah/lahan kosong?
- Street view untuk konfirmasi

3. LINKEDIN VERIFICATION:
- Cari nama perusahaan di LinkedIn
- Berapa karyawan? Sudah berapa lama berdiri?
- Cari kontak yang menghubungi kamu di LinkedIn

4. VERIFIKASI REGISTRASI PERUSAHAAN:
Tiap negara punya database perusahaan:
- US: SEC EDGAR, state corporation databases
- EU: EuroPages, national company registries
- UK: Companies House (free)
- Australia: ASIC
- Singapore: ACRA (fee minimal)
- Jepang: Commercial Registry

5. CREDIT CHECK:
- Dun & Bradstreet (D&B): tersedia versi berbayar
- Creditsafe: laporan kredit internasional
- Coface: khusus eksportir

6. REFERENSI DARI SUPPLIER LAIN:
Tanya: "Apakah ada supplier Indonesia lain yang sudah pernah berbisnis dengan perusahaan ini yang bisa saya hubungi?"

7. KONFIRMASI VIA VIDEO CALL:
Minta video call sebelum tanda tangan kontrak. Perusahaan legit tidak keberatan.

LAYANAN BERBAYAR:
- LPEI (Indonesia Eximbank) menyediakan layanan credit check untuk buyer
- Kamar Dagang setempat bisa bantu verifikasi""",
    },

    {
        "title": "Trade Finance Scam dan Penipuan L/C Palsu",
        "category": "fraud_indicators",
        "source": "FinCEN Advisory FIN-2014-A005; ICC Commercial Crime Services",
        "content": """Penipuan L/C palsu dan trade finance fraud merugikan eksportir Indonesia jutaan dolar setiap tahun.

MODUS 1 – L/C DARI BANK PALSU:
- Penipu membuat L/C yang terlihat asli dari "bank" yang tidak ada
- Cara verifikasi: Masukkan SWIFT BIC code di swift.com/bic-registrations
- Jika BIC tidak ada di database SWIFT resmi = PENIPUAN

MODUS 2 – L/C DISCREPANCY YANG DISENGAJA:
- Penipu sengaja membuat syarat L/C yang hampir tidak mungkin dipenuhi
- Ketika ada discrepancy, mereka menolak waiver dan barang tertahan
- Kemudian minta "settlement fee" untuk melepaskan barang
Pencegahan: Baca L/C dengan sangat teliti SEBELUM mengirimkan barang. Konsultasikan dengan trade finance specialist bank kamu.

MODUS 3 – SWIFT MESSAGE PALSU:
- Penipu membuat pesan SWIFT palsu yang terlihat seperti konfirmasi transfer
- Cara verifikasi: Hubungi bank kamu LANGSUNG (bukan melalui email yang dikirim penipu)

MODUS 4 – MIDDLEMAN FRAUD:
- Ada "agen" yang mengaku bisa menghubungkan ke banyak buyer premium
- Minta biaya "registrasi" atau "membership" terlebih dahulu
- Setelah bayar, mereka menghilang atau terus minta biaya tambahan

MODUS 5 – INVOICE FINANCING SCAM:
- Perusahaan menawarkan "invoice financing" dengan bunga rendah
- Minta dokumen sensitif terlebih dahulu
- Gunakan dokumen untuk fraud, bukan memberikan pinjaman

PROTOKOL KEAMANAN:
1. Jangan pernah bayar biaya apapun sebelum menerima PO
2. Semua pembayaran MASUK DULU ke rekening kamu, baru kirim barang
3. Verifikasi semua L/C dengan bank kamu, bukan dengan email dari penipu
4. Jika terlalu bagus untuk menjadi kenyataan, kemungkinan besar PENIPUAN""",
    },

    # ══════════════════════ DOCUMENTS ══════════════════════

    {
        "title": "Commercial Invoice: Dokumen Ekspor Paling Penting",
        "category": "documents",
        "source": "Ditjen Bea Cukai RI; UCP 600 ICC; Incoterms 2020",
        "content": """Commercial Invoice adalah faktur komersial yang menjadi dasar semua transaksi ekspor.

INFORMASI WAJIB DALAM COMMERCIAL INVOICE:

1. DATA EKSPORTIR:
   - Nama lengkap perusahaan
   - Alamat lengkap, kota, negara, kode pos
   - Nomor telepon, email, website
   - NIB/NPWP

2. DATA IMPORTIR (CONSIGNEE):
   - Nama lengkap perusahaan atau nama penerima
   - Alamat lengkap sesuai L/C atau instruksi pembeli
   - Harus PERSIS SAMA dengan yang tertulis di L/C (jika menggunakan L/C)

3. DETAIL TRANSAKSI:
   - Nomor dan tanggal invoice
   - Nomor Purchase Order atau kontrak yang direferensikan
   - Tanggal pengapalan (actual atau estimasi)
   - Nomor B/L atau Airway Bill

4. DESKRIPSI BARANG:
   - Nama barang (harus cocok dengan L/C dan PEB)
   - Kode HS (dianjurkan)
   - Kuantitas (unit, kg, liter, dll)
   - Berat bruto dan netto
   - Dimensi atau CBM (jika relevan)

5. HARGA:
   - Harga per unit
   - Total harga per item
   - Total keseluruhan
   - Mata uang (USD, EUR, dll)
   - Incoterms yang berlaku (misal FOB Tanjung Priok)

6. SYARAT PEMBAYARAN:
   - L/C number (jika ada)
   - Due date pembayaran
   - Instruksi rekening bank tujuan

TIPS KRITIS:
- Pastikan angka di invoice KONSISTEN dengan Packing List, B/L, dan dokumen lainnya
- Ketidaksesuaian sekecil apapun bisa menyebabkan diskrepansi L/C
- Simpan semua invoice dengan rapi untuk keperluan perpajakan dan audit""",
    },

    {
        "title": "Packing List: Dokumen Detail Isi Kemasan Ekspor",
        "category": "documents",
        "source": "Ditjen Bea Cukai RI; IATA; FIATA",
        "content": """Packing List adalah daftar detail isi setiap kemasan/kontainer yang diekspor.

INFORMASI WAJIB DALAM PACKING LIST:

1. HEADER (sama seperti commercial invoice):
   - Data eksportir dan importir
   - Referensi invoice dan PO

2. DETAIL KEMASAN:
   - Nomor kemasan/karton (Box 1 of 50, dll)
   - Isi setiap kemasan (nama dan kuantitas per box)
   - Berat netto per kemasan
   - Berat bruto per kemasan
   - Dimensi per kemasan (P x L x T dalam cm)
   - Volume per kemasan (CBM – Cubic Meter)

3. SUMMARY TOTAL:
   - Total jumlah kemasan
   - Total berat netto
   - Total berat bruto
   - Total CBM

4. CONTAINER INFORMATION (jika berlaku):
   - Nomor kontainer
   - Seal number
   - Nomor B/L

MENGHITUNG CBM:
CBM = Panjang (m) × Lebar (m) × Tinggi (m)
Contoh: Karton 60cm x 40cm x 30cm = 0.6 × 0.4 × 0.3 = 0.072 CBM per karton
50 karton = 50 × 0.072 = 3.6 CBM total

MENGAPA CBM PENTING:
- Freight forwarder menghitung biaya berdasarkan berat atau volume (whichever is greater)
- LCL shipment dihitung per CBM
- Penting untuk booking kontainer yang tepat

MARKING DAN LABELING:
Setiap kemasan harus memiliki:
- Nama dan alamat consignee
- Port of destination
- Nomor PO atau referensi
- Gross weight dan net weight
- Country of origin: Made in Indonesia
- Handling instructions jika perlu (Fragile, This Side Up, dll)""",
    },

    {
        "title": "Bill of Lading (B/L): Dokumen Kepemilikan dalam Pengiriman Laut",
        "category": "documents",
        "source": "FIATA; ICC; Hague-Visby Rules",
        "content": """Bill of Lading (B/L) adalah dokumen terpenting dalam pengiriman laut – sekaligus dokumen kepemilikan (title document) atas barang.

JENIS-JENIS BILL OF LADING:

1. ORIGINAL BILL OF LADING (OBL):
   - Dokumen fisik yang menjadi BUKTI KEPEMILIKAN barang
   - Biasanya terbit 3 asli + beberapa salinan
   - Pembeli HARUS menyerahkan OBL untuk mengambil barang
   - Dikirim via kurir (DHL/FedEx) atau via bank (dalam transaksi L/C)

2. SEAWAY BILL / SEA WAYBILL:
   - Bukan title document – tidak perlu OBL untuk ambil barang
   - Lebih cepat dan murah
   - TIDAK aman untuk pembayaran D/P atau L/C karena siapapun bisa ambil barang
   - Gunakan HANYA untuk pembeli sangat terpercaya dengan T/T advance

3. TELEX RELEASE / EXPRESS RELEASE:
   - Eksportir "melepaskan" OBL secara elektronik kepada agen pelayaran di tujuan
   - Pembeli bisa ambil barang tanpa OBL fisik
   - Lebih cepat tapi sama berisikonya dengan Sea Waybill

4. HOUSE B/L vs MASTER B/L:
   - MASTER B/L: diterbitkan shipping line
   - HOUSE B/L: diterbitkan freight forwarder
   - Untuk L/C, biasanya perlu MASTER B/L

INFORMASI PENTING DALAM B/L:
- Shipper (eksportir)
- Consignee (pembeli atau "To Order" untuk B/L negotiable)
- Notify Party (biasanya pembeli atau broker bea cukai pembeli)
- Port of Loading (pelabuhan keberangkatan)
- Port of Discharge (pelabuhan tujuan)
- Description of Goods
- Number and kind of packages, gross weight, CBM
- Vessel name, voyage number
- Date of loading ("On Board" date)
- Freight payment terms (Prepaid atau Collect)

PROTECT YOURSELF: Untuk FOB shipment, pastikan B/L tertulis "To Order" atau "To Order of [Bank]" bukan langsung ke nama pembeli. Ini mencegah pembeli mengambil barang sebelum bayar.""",
    },

    {
        "title": "Certificate of Origin (Surat Keterangan Asal/SKA): Akses Preferential Tariff",
        "category": "documents",
        "source": "Kementerian Perdagangan RI; Ditjen Perundingan Perdagangan Internasional",
        "content": """Certificate of Origin (COO) atau Surat Keterangan Asal (SKA) adalah dokumen yang menyatakan bahwa barang benar-benar diproduksi di Indonesia. Dengan COO yang tepat, pembeli bisa mendapat tarif bea masuk yang lebih rendah.

JENIS-JENIS COO UNTUK EKSPORTIR INDONESIA:

1. FORM D – SKA ASEAN-CEPT (ATIGA):
   - Untuk ekspor ke negara ASEAN (Malaysia, Thailand, Vietnam, Filipina, dll)
   - Memberikan akses ASEAN Free Trade Area (AFTA)
   - Tarif bea masuk hampir 0% di negara ASEAN

2. FORM E – SKA ACFTA (ASEAN-China FTA):
   - Untuk ekspor ke China
   - Tarif preferensial di bawah perjanjian ASEAN-China

3. FORM AJ – SKA ASEAN-Japan CEPA:
   - Untuk ekspor ke Jepang
   - Tarif lebih rendah dari MFN rate

4. FORM AK – SKA ASEAN-Korea FTA:
   - Untuk ekspor ke Korea Selatan

5. SKA FORM B (Non-Preferential):
   - Untuk negara yang tidak punya FTA dengan Indonesia
   - Tidak memberikan tarif preferensial, tapi diperlukan oleh pembeli untuk customs clearance
   - Berlaku untuk ekspor ke AS, EU, Australia, dll

6. FORM IJEPA – Indonesia-Japan EPA:
   - Bilateral FTA Indonesia-Jepang
   - Sering memberikan preferensi lebih baik dari Form AJ

7. RCEP FORM:
   - Regional Comprehensive Economic Partnership
   - Berlaku untuk 15 negara (ASEAN + China, Jepang, Korea, Australia, NZ)
   - Mulai berlaku 2022

CARA MENDAPATKAN COO:
- Ajukan ke Dinas Perdagangan setempat atau Kantor Wilayah Kemendag
- Bisa online melalui INATRADE (inatrade.kemendag.go.id)
- Perlu melampirkan: Invoice, Packing List, B/L, dan bukti origin (biaya produksi/bahan baku dari Indonesia)

DEADLINES: COO harus dimohonkan SEBELUM atau segera SETELAH tanggal pengapalan (biasanya tidak lebih dari 7 hari setelah B/L).""",
    },

    {
        "title": "PEB: Pemberitahuan Ekspor Barang – Prosedur Bea Cukai Indonesia",
        "category": "documents",
        "source": "Peraturan Menteri Keuangan; Ditjen Bea dan Cukai; INSW",
        "content": """PEB (Pemberitahuan Ekspor Barang) adalah dokumen wajib yang diajukan ke Bea Cukai sebelum ekspor barang dari Indonesia.

KAPAN PEB DIAJUKAN:
- Untuk ekspor dengan formalitas penuh (jalur merah atau hijau): SEBELUM barang dimuat
- Melalui sistem CEISA (Customs Excise Information System and Automation) / Portal INSW

SIAPA YANG BISA MENGURUS PEB:
- Eksportir langsung (jika punya akses CEISA)
- PPJK (Pengusaha Pengurusan Jasa Kepabeanan) – customs broker / freight forwarder

DOKUMEN YANG DIPERLUKAN UNTUK PEB:
- Nomor Induk Berusaha (NIB)
- Invoice komersial
- Packing List
- Kontrak atau PO
- Dokumen pendukung (sertifikasi produk jika diperlukan)
- Bukti pembayaran PPN ekspor atau SPB (Surat Persetujuan Bayar) jika ada bea ekspor

JALUR BAJU PEB:
- HIJAU: Langsung persetujuan ekspor, tidak ada pemeriksaan fisik
- MERAH: Ada pemeriksaan fisik barang sebelum ekspor

NPWP DAN REGISTRASI:
- Eksportir WAJIB memiliki NPWP
- Untuk eksportir reguler, disarankan daftar sebagai "Eksportir Terdaftar" untuk kemudahan akses

KODE HS YANG BENAR:
- PEB WAJIB mencantumkan kode HS (Harmonized System) yang benar
- Kode HS menentukan tarif bea ekspor (jika ada) dan larangan/pembatasan
- Konsultasi dengan PPJK atau Bea Cukai jika tidak yakin kode HS produk kamu

BATAS WAKTU:
- PEB harus diajukan sebelum barang memasuki kawasan pabean (Port Area)
- Untuk barang tertentu yang kena Pajak Ekspor, perhitungan pajak menggunakan kurs pajak minggu berjalan""",
    },

    {
        "title": "Phytosanitary Certificate dan Sertifikat Karantina untuk Ekspor Produk Pertanian",
        "category": "documents",
        "source": "Kementerian Pertanian RI; Badan Karantina Pertanian; IPPC",
        "content": """Phytosanitary Certificate diperlukan untuk ekspor tanaman, produk nabati, dan beberapa produk pertanian olahan.

PRODUK YANG MEMERLUKAN PHYTOSANITARY CERTIFICATE:
- Tanaman segar dan bagian tanaman
- Hasil pertanian segar (buah, sayuran)
- Produk olahan pertanian tertentu (tergantung negara tujuan)
- Biji-bijian, rempah-rempah
- Kayu dan produk kayu tertentu
- Produk perikanan ke beberapa negara

CARA MENDAPATKAN PHYTOSANITARY CERTIFICATE:
1. Ajukan permohonan ke UPT (Unit Pelaksana Teknis) Badan Karantina Pertanian terdekat
2. Petugas akan melakukan pemeriksaan fisik barang
3. Jika lulus pemeriksaan, sertifikat diterbitkan
4. Waktu proses: 1-3 hari kerja

KARANTINA HEWAN (untuk produk olahan hewani):
- Ikan dan produk perikanan: Badan Karantina Ikan, Pengendalian Mutu, dan Keamanan Hasil Perikanan (BKIPM) – Kementerian Kelautan dan Perikanan
- Produk ternak olahan: Otoritas Veteriner (Kementan)

FUMIGATION CERTIFICATE:
- Diperlukan untuk kayu, produk kayu, dan kemasan kayu
- ISPM 15: Standard internasional untuk kemasan kayu ekspor
- Kemasan kayu (pallet kayu, kotak kayu) HARUS memenuhi ISPM 15 atau menggunakan alternatif (pallet plastik, karton)
- Fumigasi dilakukan oleh perusahaan fumigasi berlisensi

PENTING UNTUK PASAR EU:
Mulai 2023, EU memberlakukan EUDR (EU Deforestation Regulation) untuk produk tertentu seperti minyak sawit, kopi, kakao, kayu. Eksportir harus bisa membuktikan produk tidak berasal dari lahan yang mengalami deforestasi sejak 2020.""",
    },

    # ══════════════════════ REGULATIONS ══════════════════════

    {
        "title": "NIB dan APE: Dua Izin Wajib untuk Eksportir Indonesia",
        "category": "regulations",
        "source": "OSS RBA; Kementerian Perdagangan RI; PP No.5/2021",
        "content": """Sebelum bisa ekspor, UMKM Indonesia wajib memiliki dua dokumen utama.

NIB – NOMOR INDUK BERUSAHA:
- Diperoleh melalui OSS (Online Single Submission) RBA: oss.go.id
- Menggantikan TDP, SIUP, dan berbagai izin lama
- NIB sekaligus menjadi Angka Pengenal Importir (API) untuk importasi
- Gratis, bisa diurus online
- Prosedur: Daftar di oss.go.id → Isi data usaha → Pilih KBLI → Pernyataan kesanggupan → NIB terbit

KBLI YANG TEPAT:
- Pilih KBLI (Klasifikasi Baku Lapangan Usaha Indonesia) yang sesuai dengan bidang usaha
- KBLI yang salah bisa menyebabkan kendala izin

APE – ANGKA PENGENAL EKSPORTIR:
- Diperlukan untuk ekspor produk tertentu (terutama komoditi dan produk unggulan)
- Diterbitkan oleh Kementerian Perdagangan
- Proses: SIINAS (Sistem Informasi Industri Nasional) atau INATRADE
- Produk yang WAJIB APE: Kopi, kakao, produk kayu, rempah-rempah, karet, dan komoditi lainnya
- Produk manufaktur umum biasanya TIDAK perlu APE

LARTAS (LARANGAN DAN PEMBATASAN EKSPOR):
Beberapa produk memiliki larangan atau pembatasan ekspor:
- DILARANG EKSPOR: Ikan tertentu (napoleon, arwana), flora fauna dilindungi, mineral tertentu dalam bentuk mentah
- DIBATASI: Produk kayu (perlu SVLK), hasil tambang (perlu izin khusus), kopi (standar minimum)
- KENA BEA EKSPOR: Minyak sawit mentah (CPO), rotan, kayu, kulit

SVLK – SISTEM VERIFIKASI LEGALITAS KAYU:
Semua produk kayu yang diekspor WAJIB memiliki SVLK. Diperoleh melalui lembaga penilai & verifikasi independen (LVLK).

CEK LARTAS ONLINE:
Website INSW (insw.go.id) → menu Lartas → masukkan HS code""",
    },

    {
        "title": "INSW dan Prosedur Ekspor Melalui Portal Nasional",
        "category": "regulations",
        "source": "INSW; Ditjen Bea Cukai; Peraturan Menteri Keuangan",
        "content": """INSW (Indonesia National Single Window) adalah portal resmi pemerintah untuk pengurusan ekspor-impor secara elektronik.

LAYANAN UTAMA INSW:
1. Portal PEB (Pemberitahuan Ekspor Barang)
2. Pengecekan tarif dan Lartas
3. Tracking status pengajuan dokumen
4. Integrasi dengan berbagai kementerian

CEISA (Customs Excise Information System and Automation):
Sistem Bea Cukai yang terintegrasi dengan INSW untuk:
- Pengajuan PEB
- Tracking nomor PIB/PEB
- Status pemeriksaan fisik

PROSEDUR EKSPOR RINGKASAN:
1. Dapatkan NIB & izin yang diperlukan (APE, SVLK, dll)
2. Buat Commercial Invoice, Packing List
3. Ajukan PEB melalui CEISA / PPJK
4. Bayar PPN Ekspor (0%) atau Bea Ekspor jika ada
5. Dapatkan Nota Persetujuan Ekspor (NPE) dari Bea Cukai
6. Muat barang ke kontainer / kapal
7. Dapatkan Bill of Lading dari pelayaran
8. Urus Certificate of Origin jika diperlukan
9. Kirim dokumen ke bank (untuk L/C) atau langsung ke pembeli

KODE HS: Basis Semua Transaksi Ekspor
- Kode HS 6 digit berlaku secara internasional (WCO)
- Indonesia menggunakan 8-10 digit (BTKI – Buku Tarif Kepabeanan Indonesia)
- Cek HS code produk: insw.go.id → Tarif → BTKI

EXPORT DUTY (Bea Ekspor):
Beberapa komoditi dikenakan bea ekspor progresif:
- CPO (Crude Palm Oil): tarif bervariasi berdasarkan harga referensi
- Konsentrat tembaga dan nikel: bea ekspor tinggi untuk mendorong pengolahan dalam negeri
- Kayu olahan: bervariasi berdasarkan jenis""",
    },

    {
        "title": "Persyaratan BPOM untuk Ekspor Produk Pangan dan Kosmetik Indonesia",
        "category": "regulations",
        "source": "BPOM RI; Peraturan BPOM No. 27/2023",
        "content": """Produk pangan olahan dan kosmetik yang diekspor mungkin memerlukan izin atau sertifikasi BPOM.

PRODUK PANGAN OLAHAN:
Untuk ekspor pangan olahan, umumnya TIDAK diperlukan izin BPOM khusus untuk ekspor.
NAMUN, banyak negara importir mensyaratkan:
- Health Certificate dari BPOM untuk membuktikan produk aman dan layak konsumsi
- Certificate of Free Sale: Surat dari BPOM yang menyatakan produk boleh dijual bebas di Indonesia
- GMP (Good Manufacturing Practice) Certificate

CARA MENDAPATKAN HEALTH CERTIFICATE:
1. Ajukan permohonan ke Balai/Loka POM setempat atau melalui e-registrasi BPOM
2. Lampirkan: Izin Edar produk (SPP-IRT atau MD), hasil uji laboratorium, deskripsi produk
3. Waktu proses: 5-10 hari kerja
4. Biaya: berdasarkan PNBP

SPP-IRT vs MD:
- SPP-IRT (Sertifikat Produksi Pangan Industri Rumah Tangga): Untuk produk dengan risiko rendah, skala kecil. Dikeluarkan Dinas Kesehatan.
- MD (Makanan Dalam): Nomor izin edar BPOM untuk produk pangan yang diproduksi dalam negeri. Wajib untuk produk dengan kategori risiko sedang-tinggi.

Untuk ekspor ke pasar premium (EU, US, Jepang, Australia), MD lebih diakui daripada SPP-IRT.

PRODUK KOSMETIK:
- Wajib memiliki nomor notifikasi BPOM untuk dijual di Indonesia
- Untuk ekspor: Certificate of Free Sale dari BPOM
- Halal Certificate dari MUI jika target pasar adalah negara Muslim (Timur Tengah, Malaysia)

SERTIFIKASI HALAL MUI:
Sangat penting untuk ekspor ke:
- Negara-negara Timur Tengah (wajib)
- Malaysia (sangat disarankan)
- Brunei, Pakistan, Bangladesh
- Komunitas Muslim di EU dan AS
Proses: Melalui BPJPH (Badan Penyelenggara Jaminan Produk Halal), menggunakan LP3H yang terakreditasi""",
    },

    {
        "title": "Ekspor ke Uni Eropa: EUDR, CBAM, dan Persyaratan Ketat",
        "category": "regulations",
        "source": "European Commission; Regulation EU 2023/1115; CBAM EU 2023/956",
        "content": """Uni Eropa memiliki regulasi paling ketat di dunia. Ketahui persyaratannya sebelum ekspor ke EU.

EUDR – EU DEFORESTATION REGULATION (Berlaku mulai 2024-2025):
Produk yang masuk ke EU harus membuktikan tidak berasal dari lahan yang mengalami deforestasi atau degradasi hutan sejak 31 Desember 2020.

PRODUK YANG TERDAMPAK EUDR:
- Minyak sawit (CPO, palm kernel oil)
- Kopi
- Kakao/cokelat
- Kedelai
- Kayu dan produk kayu
- Karet alam
- Ternak (daging sapi)
- Produk turunan dari semua komoditi di atas

KEWAJIBAN UNTUK EKSPORTIR:
1. Due Diligence Statement: Menyatakan bahwa produk bebas dari deforestasi
2. Geolocation data: Koordinat GPS lokasi produksi
3. Supply chain traceability: Rantai pasokan yang dapat dilacak hingga ke tingkat petani/hutan

IMPLIKASI: Eksportir kopi, kakao, dan sawit Indonesia WAJIB mulai mempersiapkan sistem traceability sekarang.

CBAM – CARBON BORDER ADJUSTMENT MECHANISM:
Mulai 2026, produk tertentu yang diimpor EU akan dikenakan biaya karbon setara dengan biaya yang dibayar produsen EU.
Produk terdampak CBAM: Besi/baja, semen, aluminium, pupuk, listrik, hidrogen.
Dampak untuk Indonesia: Eksportir produk tersebut perlu melaporkan emisi karbon produksi.

FOOD SAFETY REGULATIONS:
- RASFF (Rapid Alert System for Food and Feed): Indonesia sering mendapat notifikasi karena residu pestisida di produk pertanian
- Batas residu pestisida EU jauh lebih ketat dari Codex Alimentarius
- Aflatoksin di kacang-kacangan: batas sangat ketat
- Logam berat: batas ketat untuk seafood, rempah-rempah

REACH & RoHS:
Untuk produk kimia, kosmetik, elektronik – harus comply dengan REACH dan RoHS.""",
    },

    # ══════════════════════ LOGISTICS ══════════════════════

    {
        "title": "FCL vs LCL: Panduan Memilih Metode Pengiriman Ekspor yang Tepat",
        "category": "logistics",
        "source": "FIATA; Maersk Line; Freight Forwarder Association Indonesia",
        "content": """Pilihan antara FCL dan LCL berdampak besar pada biaya dan keamanan pengiriman.

FCL – FULL CONTAINER LOAD:
Kamu menyewa SATU kontainer PENUH untuk barangmu sendiri.

Tipe kontainer standar:
- 20ft DC (Dry Container): Kapasitas 25-28 CBM, muatan ~22 ton
- 40ft DC: Kapasitas 55-58 CBM, muatan ~26 ton
- 40ft HC (High Cube): Kapasitas 68 CBM, muatan ~26 ton
- 20ft/40ft Reefer (Refrigerated): Untuk produk yang membutuhkan suhu dingin
- 20ft Open Top: Untuk kargo yang tinggi
- 20ft Flat Rack: Untuk kargo yang sangat besar

KAPAN PILIH FCL:
- Volume barang ≥ 15-20 CBM (mengisi minimal setengah kontainer)
- Barang sensitif yang tidak ingin tercampur dengan kargo orang lain
- Pengiriman rutin dengan volume konsisten

LCL – LESS THAN CONTAINER LOAD:
Barangmu digabung dengan kargo dari eksportir lain dalam satu kontainer.

KAPAN PILIH LCL:
- Volume barang < 10-15 CBM
- Pengiriman pertama / uji coba
- Barang tidak terlalu sensitif terhadap kerusakan akibat konsolidasi

PERBANDINGAN BIAYA:
- FCL: Biaya per kontainer flat, lebih murah per CBM untuk volume besar
- LCL: Biaya per CBM atau per ton (tergantung mana lebih besar = W/M)

KEUNTUNGAN FCL vs LCL:
FCL: Lebih aman (tidak ada pencampuran kargo), lebih cepat di pelabuhan tujuan, lebih murah untuk volume besar
LCL: Lebih fleksibel untuk volume kecil, tidak perlu menunggu sampai punya cukup kargo untuk isi kontainer penuh

TIPS PRAKTIS:
- Untuk trial shipment pertama ke buyer baru: LCL
- Setelah relationship terbukti dan volume konsisten: negosiasi FCL untuk hemat biaya""",
    },

    {
        "title": "Lead Time Ekspor: Panduan Perencanaan Waktu dari Order hingga Delivery",
        "category": "logistics",
        "source": "Freight Forwarder Association Indonesia; Pelindo; Pelayaran Nasional",
        "content": """Lead time ekspor dari Indonesia ke berbagai tujuan dan cara menghitungnya.

KOMPONEN LEAD TIME EKSPOR:

1. PRODUCTION LEAD TIME: Waktu produksi setelah terima order
   - Untuk produk made-to-order: 14-30 hari
   - Untuk produk stock: 1-3 hari packing

2. DOMESTIC TRANSPORT: Kirim ke pelabuhan
   - Sumatera/Jawa: 1-3 hari
   - Kalimantan, Sulawesi, Papua ke Tanjung Priok: 3-7 hari

3. PORT CLEARANCE: Pengurusan di pelabuhan
   - Booking kontainer: 5-7 hari sebelum ETD
   - Stuffing kontainer: 1-2 hari sebelum cutoff
   - Cutoff (batas akhir barang masuk ke port): 24-48 jam sebelum kapal berangkat

4. OCEAN TRANSIT TIME (dari pelabuhan Indonesia):
   - Malaysia/Singapore: 1-3 hari
   - China: 7-14 hari
   - Jepang/Korea: 10-18 hari
   - Australia: 14-21 hari
   - Timur Tengah: 20-28 hari
   - Eropa: 28-35 hari (via Terusan Suez)
   - US West Coast: 21-28 hari
   - US East Coast: 35-45 hari

5. CUSTOMS CLEARANCE DI TUJUAN: 3-7 hari bisnis
   - Bervariasi berdasarkan negara dan penilaian risiko

TOTAL LEAD TIME ESTIMASI (dari order hingga received buyer):
- Malaysia/Singapore: 3-4 minggu
- China/Japan/Korea: 4-6 minggu
- Australia: 5-7 minggu
- Middle East: 6-8 minggu
- Europe: 7-10 minggu
- US: 8-10 minggu

TIPS KOMUNIKASI DENGAN BUYER:
Selalu berikan lead time dengan buffer 10-20% lebih panjang dari estimasi. Lebih baik sampai lebih cepat dari janji daripada terlambat.""",
    },

    {
        "title": "Freight Forwarder: Mitra Logistik Ekspor yang Tidak Bisa Diabaikan",
        "category": "logistics",
        "source": "FIATA; Asosiasi Perusahaan Jasa Pengiriman Ekspres, Pos, dan Logistik Indonesia (Asperindo)",
        "content": """Freight Forwarder adalah agen logistik yang mengurus semua aspek pengiriman ekspor. Memilih FF yang tepat sangat krusial.

LAYANAN FREIGHT FORWARDER:
- Booking space di kapal (space booking)
- Stuffing dan sealing kontainer
- Pengurusan dokumen bea cukai (PEB) melalui PPJK
- Pengurusan Certificate of Origin
- Pengiriman dokumen ke bank (untuk L/C)
- Koordinasi dengan agen di negara tujuan
- Asuransi kargo
- Warehousing sementara

JENIS FREIGHT FORWARDER:
1. NVOCC (Non-Vessel Operating Common Carrier): Punya kontrak dengan banyak shipping line, bisa tawarkan harga kompetitif
2. Freight Forwarder Murni: Tidak punya kapal, hanya mengatur pengiriman
3. Ekspedisi Muatan Kapal Laut (EMKL): Khusus laut
4. Integrated Logistics: End-to-end logistics provider

CARA MEMILIH FREIGHT FORWARDER:
✓ Memiliki Surat Izin Usaha Jasa Transportasi (SIUJT)
✓ Terdaftar sebagai PPJK yang resmi di Bea Cukai
✓ Punya pengalaman dengan rute dan jenis produk yang sama
✓ Punya jaringan agen di negara tujuan
✓ Komunikasi responsif dan transparan
✓ Referensi dari eksportir lain

BIAYA FREIGHT FORWARDER:
- Ocean Freight: biaya pokok pengiriman (dibayar ke shipping line)
- THC (Terminal Handling Charge): biaya handling di terminal
- Documentation Fee: biaya pengurusan dokumen
- B/L Fee: biaya penerbitan Bill of Lading
- Customs Clearance Fee (PPJK): biaya pengurusan bea cukai

PASTIKAN: Dapatkan penawaran dari minimal 3 freight forwarder sebelum memilih.""",
    },

    # ══════════════════════ MARKET INTELLIGENCE ══════════════════════

    {
        "title": "Jepang: Pasar Premium dengan Standar Kualitas Tertinggi",
        "category": "market_intelligence",
        "source": "JETRO (Japan External Trade Organization); UN Comtrade; ITC TradeMap",
        "content": """Jepang adalah pasar premium yang sangat menghargai kualitas dan konsistensi. Susah masuk, tapi sangat loyal.

KARAKTERISTIK PEMBELI JEPANG:
- Obsesi terhadap kualitas dan konsistensi (zero defect mentality)
- Sabar, suka relationship jangka panjang, tapi proses keputusan LAMA
- Menghargai profil perusahaan dan track record yang jelas
- Packaging harus premium, bahkan untuk produk B2B
- Dokumen harus sempurna – sedikit kesalahan bisa batalkan deal

PRODUK INDONESIA DIMINATI DI JEPANG:
- Kopi specialty (Toraja, Gayo, Flores, Java Estate)
- Kakao fine/flavor
- Rempah-rempah premium (kayu manis, cengkeh, pala)
- Produk laut (tuna, udang, ikan hias)
- Furnitur kayu berkualitas tinggi
- Kerajinan tangan artistik
- Tekstil tradisional (batik, tenun ikat)

PERSYARATAN KHUSUS JEPANG:
- JAS (Japanese Agricultural Standard): Untuk produk makanan
- Test report dari laboratorium terakreditasi ILAC/JNLA
- Ingredient list dalam bahasa Jepang
- Pelabelan sesuai Food Labeling Act
- Notifikasi impor pangan ke Kementerian Kesehatan Jepang (MHLW)

SALURAN DISTRIBUSI JEPANG:
- Importir spesialis → distributor → retailer (rantai panjang)
- Direct import oleh supermarket besar (AEON, Ito-Yokado)
- Online platform: Amazon Japan, Rakuten (untuk produk yang dikenal)

TIPS EKSPOR KE JEPANG:
1. Kirim sample PERFECT – tidak ada kompromi
2. Siapkan dokumen lab test sejak awal
3. Berikan product specification sheet yang sangat detail
4. Pertimbangkan mengunjungi pameran Foodex Japan (Maret, setiap tahun)""",
    },

    {
        "title": "Timur Tengah (UAE, Saudi Arabia): Pasar Berkembang dengan Sertifikasi Halal",
        "category": "market_intelligence",
        "source": "Dubai Chamber of Commerce; ITC TradeMap; UN Comtrade",
        "content": """UAE (khususnya Dubai) adalah hub perdagangan global yang menjadi pintu masuk ke seluruh Timur Tengah dan Afrika.

KARAKTERISTIK PASAR TIMUR TENGAH:
- Sertifikasi Halal MUI WAJIB untuk hampir semua produk makanan
- Negosiasi adalah budaya – berikan harga yang ada ruang untuk ditawar
- Hubungan personal sangat penting
- Pembayaran melalui L/C lazim, open account untuk mitra lama
- Ramadhan: demand meningkat untuk makanan, berkurang untuk non-makanan

PRODUK INDONESIA POPULER:
- Makanan halal: produk olahan, bumbu, snack
- Minyak kelapa dan turunannya
- Batik dan fashion Muslim (abaya berbahan batik, dll)
- Kerajinan tangan/dekorasi premium
- Kopi robusta dan arabika
- Produk natural beauty (minyak argan lokal kalah dengan minyak kelapa Indonesia)
- Furnitur dan home decor

UAE SEBAGAI HUB:
- Free Trade Zone: Jebel Ali, Dubai Airport Free Zone
- Re-export ke Saudi, Kuwait, Qatar, Oman, Bahrain, Mesir, Afrika Timur
- Dubai International adalah hub transit kargo terbesar di kawasan

SERTIFIKASI YANG DIPERLUKAN UNTUK TIMUR TENGAH:
- Halal Certificate MUI (untuk semua makanan dan kosmetik)
- GCC CoO (Gulf Cooperation Council Certificate of Origin) untuk tarif preferensial
- Emirates Authority for Standardization (ESMA) certificate untuk beberapa kategori produk
- SFDA (Saudi Food and Drug Authority) approval untuk produk ke Saudi Arabia

TIPS NEGOSIASI DENGAN BUYER ARAB:
- Kesabaran adalah kunci – jangan tunjukkan ketergesa-gesaan
- Pertemuan tatap muka / video call sangat dihargai
- Hormati hari dan waktu shalat dalam komunikasi
- Ramadhan: Jangan schedule meeting penting; fokus pada follow-up
- Minta referral: "Siapa lagi yang mungkin tertarik dengan produk kami?" sangat efektif""",
    },

    {
        "title": "Australia dan Selandia Baru: Pasar Premium dengan Biaya Compliance Tinggi",
        "category": "market_intelligence",
        "source": "DFAT Australia; MFAT New Zealand; Australia Border Force",
        "content": """Australia dan Selandia Baru adalah pasar premium yang sangat ketat soal biosecurity.

BIOSECURITY AUSTRALIA:
Regulasi biosecurity Australia adalah PALING KETAT di dunia. Kesalahan pengemasan atau kontaminasi kecil bisa berujung barang dikembalikan atau dimusnahkan.

PRODUK PERTANIAN: Hampir semua produk pertanian segar DILARANG masuk Australia
Produk olahan: Perlu approval dari DAFF (Department of Agriculture, Fisheries and Forestry)

FOOD STANDARDS AUSTRALIA NEW ZEALAND (FSANZ):
- Food Standards Code mengatur semua makanan yang masuk AU/NZ
- Labeling: ingredient list, allergen declaration, nutritional info wajib
- Country of origin labeling wajib untuk makanan

PRODUK INDONESIA YANG BERHASIL DI AUSTRALIA:
- Kopi specialty (ada komunitas Indonesian diaspora yang cukup besar)
- Furniture kayu (teak furniture sangat populer)
- Kerajinan tangan dan home decor
- Tekstil dan pakaian (batik, tenun)
- Produk makanan processed yang sudah dapat FSANZ approval

INDONESIA-AUSTRALIA CEPA (IA-CEPA):
Berlaku mulai 2020, memberikan:
- Tarif 0% untuk banyak produk Indonesia ke Australia
- Kemudahan business visa dan layanan profesional
- Manfaatkan Form IA-CEPA untuk tarif preferensial

TIPS:
- Hubungi KBRI Canberra atau KJRI Sydney/Melbourne untuk business matching
- Ikuti Food & Beverage Show Melbourne
- Gunakan distribusi via Indonesian diaspora networks (banyak Indonesian grocery stores)""",
    },

    {
        "title": "China: Pasar Terbesar dengan Peluang dan Tantangan",
        "category": "market_intelligence",
        "source": "GACC (General Administration of Customs China); ITC TradeMap",
        "content": """China adalah importir terbesar dunia untuk banyak komoditi Indonesia. Namun, masuk ke pasar China membutuhkan persiapan serius.

REGULASI IMPOR CHINA:
- GACC Registration: Eksportir makanan/agri ke China WAJIB terdaftar di GACC
- Inspeksi CIQ (China Inspection and Quarantine): Ketat untuk produk pertanian dan pangan
- E-commerce platform populer: Tmall, JD.com, Taobao (untuk direct consumer)
- B2B marketplace: Alibaba, GlobalSources, made-in-china

PRODUK INDONESIA YANG DICARI CHINA:
- Minyak sawit dan turunannya (China adalah importir CPO terbesar)
- Kopi (pasar kopi China tumbuh 15-20% per tahun)
- Sarang burung walet (swiftlet nest – harga premium, demand sangat tinggi)
- Rumput laut dan produk perikanan
- Furnitur kayu
- Karet alam
- Nikel (ore / produk olahan)
- Produk natural beauty (khusus konsumen muda China)

GACC REGISTRATION PROCESS:
1. Daftar melalui portal GACC: gacc.gov.cn/
2. Diperlukan: Nomor NIB, sertifikasi produksi, izin BPOM/Kementan sesuai produk
3. Dibantu oleh Badan Ketahanan Pangan dan Kementan
4. Waktu proses: Berbulan-bulan – mulai lebih awal!

SARANG BURUNG WALET:
- Komoditi senilai jutaan USD dengan pembeli China yang sangat loyal
- Memerlukan izin khusus dari Kementan dan registrasi GACC
- Harga USD 1,000-3,000/kg – margin sangat tinggi

ACFTA (ASEAN-China FTA):
Gunakan Form E (SKA Form E) untuk mendapat tarif preferensial. Banyak produk Indonesia ke China bisa masuk dengan tarif 0% atau sangat rendah.""",
    },

    {
        "title": "Amerika Serikat: Pasar Besar dengan FDA dan CBP",
        "category": "market_intelligence",
        "source": "US FDA; US CBP; ITC TradeMap; USTR",
        "content": """Amerika Serikat adalah pasar yang sangat besar namun memiliki regulasi ketat yang harus dipahami sejak awal.

REGULASI FDA (Food and Drug Administration):
- Semua makanan, obat, kosmetik, alat kesehatan yang masuk ke AS perlu comply FDA
- FSVP (Foreign Supplier Verification Program): Importir AS WAJIB melakukan verifikasi supplier
- Prior Notice: Pengiriman makanan ke AS harus diberitahukan ke FDA sebelum kedatangan
- Facility Registration: Fasilitas produksi makanan WAJIB terdaftar di FDA
- FSMA (Food Safety Modernization Act): Regulasi keamanan pangan yang ketat

CBP (Customs and Border Protection):
- Semua barang masuk diinspeksi CBP
- AMS (Automated Manifest System): Manifest kargo harus dikirim 24 jam sebelum loading
- ADD/CVD (Anti-Dumping / Countervailing Duty): Beberapa produk kena tarif tambahan

PRODUK INDONESIA POPULER DI AS:
- Furnitur teak dan rattan
- Kopi specialty (Sumatran, Java, Bali)
- Kerajinan tangan dan dekorasi rumah
- Tekstil dan batik
- Produk natural (essential oils, coconut products)
- Seafood (tuna, udang)

US-GSP (Generalized System of Preferences):
Status GSP Indonesia pernah bermasalah. Cek status terkini sebelum ekspor untuk menentukan tarif yang berlaku.

PENTING – LACEY ACT:
Untuk produk kayu dan kertas: WAJIB menyatakan bahwa kayu tidak berasal dari penebangan ilegal. Siapkan dokumentasi chain of custody.

TIPS EKSPOR KE AS:
1. Gunakan importer of record yang berpengalaman
2. Pastikan labeling dalam bahasa Inggris
3. Perhatikan persyaratan pelabelan alergen (Big 9 alergen)
4. Pastikan FDA facility registration aktif""",
    },

    # ══════════════════════ ADDITIONAL ENTRIES ══════════════════════

    {
        "title": "Cara Menghitung Harga Ekspor: Dari HPP hingga CIF",
        "category": "incoterms",
        "source": "Kementerian Perdagangan RI; Export Costing Best Practices",
        "content": """Menghitung harga ekspor yang benar adalah fondasi profitabilitas bisnis ekspor UMKM.

KOMPONEN BIAYA EKSPOR:

1. HPP (Harga Pokok Produksi):
   - Bahan baku
   - Tenaga kerja langsung
   - Overhead pabrik
   Contoh: HPP = Rp 50,000/unit

2. BIAYA PACKAGING EKSPOR:
   - Kemasan primer (bungkus produk)
   - Kemasan sekunder (box)
   - Kemasan tersier (master carton)
   - Seal, strapping, palletisasi
   Contoh: Rp 5,000/unit

3. MARGIN KEUNTUNGAN:
   - Target: minimal 20-30% di atas HPP + packaging
   Contoh: 25% margin = Rp 13,750/unit

4. BIAYA EKSPOR LOKAL (Origin Charges):
   - Transport ke pelabuhan
   - THC (Terminal Handling Charge): USD 80-150/kontainer
   - Documentation fees
   - Freight forwarder fee
   - Export duty (jika ada)
   Contoh: USD 0.30/unit (untuk volume 1000 unit)

5. HARGA FOB:
   FOB = HPP + Packaging + Margin + Origin Charges
   = Rp 50,000 + Rp 5,000 + Rp 13,750 + Rp 4,500 ≈ Rp 73,250 → USD 4.60 (kurs 15,900)

6. BIAYA FREIGHT (untuk CFR/CIF):
   - LCL: USD 35-60/CBM ke Malaysia; USD 80-120/CBM ke Eropa
   - FCL: USD 600-900 ke Malaysia; USD 1,800-3,500 ke Eropa per 20ft
   Contoh (CIF Malaysia, LCL, 1 CBM per 100 units): USD 0.50/unit

7. ASURANSI (untuk CIF):
   - Biasanya 0.1-0.3% dari CIF value
   Contoh: 0.2% = USD 0.01/unit

8. HARGA CIF:
   CIF = FOB + Freight + Asuransi = USD 4.60 + USD 0.50 + USD 0.01 = USD 5.11/unit

BENCHMARK:
Bandingkan harga CIF kamu dengan UN Comtrade Export Unit Value (nilai rata-rata ekspor per unit HS code dari Indonesia ke negara tujuan). Jika hargamu jauh di bawah benchmark, kamu mungkin jual terlalu murah.""",
    },

    {
        "title": "Standar Kualitas Internasional yang Diakui Buyer Global",
        "category": "regulations",
        "source": "ISO; IFS; BRC; GlobalGAP; Rainforest Alliance",
        "content": """Sertifikasi kualitas internasional meningkatkan kepercayaan buyer dan membuka akses pasar premium.

UNTUK PRODUK PANGAN:

1. ISO 22000 / FSSC 22000:
   - Standar keamanan pangan internasional
   - Diakui secara global, termasuk GFSI (Global Food Safety Initiative)
   - Diperlukan untuk masuk ke supermarket besar Eropa dan AS

2. BRC (British Retail Consortium):
   - Standar keamanan pangan untuk supplier ke retailer Inggris dan Eropa
   - Diperlukan untuk supply ke Tesco, ASDA, Sainsbury's, dll

3. IFS (International Featured Standards):
   - Serupa BRC, lebih populer di Jerman, Prancis
   - Diperlukan untuk supply ke retailer Jerman (Rewe, Edeka, Lidl)

4. GlobalGAP:
   - Standar untuk produk pertanian segar
   - Diperlukan untuk petani yang mau supply ke supermarket Eropa

5. HACCP (Hazard Analysis Critical Control Points):
   - Sistem manajemen keamanan pangan berbasis risiko
   - Seringkali menjadi prasyarat sebelum audit BRC/IFS/ISO 22000

UNTUK KEBERLANJUTAN (SUSTAINABILITY):

6. Rainforest Alliance:
   - Untuk kopi, kakao, teh, buah-buahan
   - Sangat dicari oleh buyer premium Eropa dan AS

7. UTZ Certified (bergabung dengan Rainforest Alliance sejak 2018):
   - Untuk kopi dan kakao

8. Fairtrade:
   - Menjamin petani mendapat harga adil
   - Popular di Eropa Barat

9. Organic (EU Organic Regulation, USDA NOP):
   - Produk organik bisa harganya 50-200% lebih tinggi dari konvensional

10. RSPO (Roundtable on Sustainable Palm Oil):
    - Wajib untuk ekspor minyak sawit ke Eropa

STRATEGI UNTUK UMKM:
Mulai dengan HACCP dan GMP karena itu fondasi semua sertifikasi. Kemudian pertimbangkan Rainforest Alliance atau Fairtrade jika target pasar Eropa.""",
    },

    {
        "title": "Email Negosiasi: Template dan Frasa Profesional dalam Bahasa Inggris",
        "category": "negotiation",
        "source": "Export Communication Best Practices; Business English for International Trade",
        "content": """Template dan frasa standar untuk komunikasi negosiasi ekspor profesional.

MEMBALAS REQUEST FOR QUOTATION (RFQ):

Subject: RE: Quotation for [Product Name] - [Your Company Name]

Dear Mr./Ms. [Name],

Thank you for your inquiry regarding [product name]. We are pleased to submit our quotation as follows:

Product: [Name]
HS Code: [Code]
Specifications: [Details]
Unit Price: USD [X.XX] FOB Tanjung Priok / CIF [Destination Port]
Minimum Order Quantity: [X] units / [X] kg
Lead Time: [X] working days from order confirmation
Payment Terms: [T/T 30% deposit, 70% against copy B/L / Sight L/C]
Validity: This quotation is valid for 30 days.

We look forward to the opportunity to serve you.

---

MENOLAK TAWARAN HARGA DENGAN SOPAN:

"Thank you for your counter-offer of USD [X]. While I deeply appreciate your interest in our products, I'm afraid the price you've proposed falls below our production costs for the quality standard you require.

However, I'm committed to finding a solution that works for both of us. Would you consider [alternative: higher volume / different payment terms / adjusted specifications]? This would allow us to offer a more competitive price."

---

MEMINTA KOMITMEN TANPA TERLIHAT TERBURU-BURU:

"As we are currently allocating our production capacity for Q3, I would appreciate if you could advise on your decision timeline. This would help us better plan our production schedule to ensure your order receives the priority it deserves."

---

FOLLOW-UP TANPA TERLIHAT PUTUS ASA:

"I hope this message finds you well. I wanted to follow up on the quotation we sent on [date]. We remain very interested in partnering with your company.

If there are any questions or concerns I can address, or if you need any adjustments to our proposal, please don't hesitate to reach out."

---

MERESPONS COMPLAINT:

"Thank you for bringing this matter to our attention. I sincerely apologize for the inconvenience this has caused. Quality is our highest priority, and we are investigating this issue immediately.

Please send us photos/details of the affected goods so we can assess the situation. We are committed to resolving this fairly and will provide our proposed resolution within [X] business days."
""",
    },

    {
        "title": "Asuransi Kargo Ekspor: Melindungi Barang Selama Pengiriman",
        "category": "logistics",
        "source": "ICC Institute of London Underwriters; Indonesia Re; Asuransi Ekspor Indonesia",
        "content": """Asuransi kargo melindungi barang ekspor dari kerusakan atau kehilangan selama perjalanan.

JENIS POLIS ASURANSI KARGO:

1. INSTITUTE CARGO CLAUSES (ICC) A – Comprehensive:
   - Menutup SEMUA risiko kecuali yang dikecualikan
   - Dikecualikan: kerusakan akibat pengemasan buruk, delay, kebangkrutan forwarder
   - DIREKOMENDASIKAN untuk barang berharga atau fragile
   - Premi: 0.3-0.8% dari nilai CIF

2. INSTITUTE CARGO CLAUSES (ICC) B – Named Perils:
   - Hanya menutup risiko yang TERCANTUM dalam polis
   - Termasuk: kebakaran, tenggelamnya kapal, tumpahan, banjir, gempa
   - Tidak menutup: theft, shortage
   - Premi lebih murah dari ICC A

3. INSTITUTE CARGO CLAUSES (ICC) C – Basic:
   - Coverage paling terbatas
   - Hanya: kebakaran, kapal karam, collision
   - Minimum coverage yang dipersyaratkan CIF Incoterms

4. TOTAL LOSS ONLY (TLO):
   - Hanya bayar jika barang hilang TOTAL
   - Sangat murah tapi proteksi sangat terbatas

TIPS KLAIM ASURANSI:
1. Dokumentasikan kondisi barang SEBELUM dikirim (foto/video)
2. Simpan semua dokumen pengiriman
3. Jika ada kerusakan: segera hubungi asuransi, jangan pindah barang tanpa survei
4. Minta surveyors report dari asuransi

ASURANSI KREDIT EKSPOR:
Selain asuransi kargo, ada asuransi KREDIT EKSPOR yang melindungi dari pembeli yang tidak bayar:
- LPEI (Lembaga Pembiayaan Ekspor Indonesia/Indonesia Eximbank)
- Asei (Asuransi Ekspor Indonesia)
- Premi berkisar 0.5-2% dari nilai transaksi""",
    },

    {
        "title": "Pembayaran Down Payment dan Manajemen Risiko Pembeli Baru",
        "category": "payment_terms",
        "source": "Export Credit Best Practices; IFC (International Finance Corporation)",
        "content": """Setiap eksportir pasti menghadapi permintaan dari pembeli baru yang belum terbukti.

FRAMEWORK RISIKO UNTUK PEMBELI BARU:

TIER 1 – SANGAT BERISIKO (order pertama, tidak dikenal):
Syarat minimal: T/T 100% advance atau Sight L/C
Tidak ada kompromi untuk order pertama dari pembeli tidak dikenal.

TIER 2 – RISIKO SEDANG (ada referensi atau verifikasi positif):
Opsi: T/T 30-50% advance, sisanya setelah copy B/L diterima
Atau: D/P Sight melalui bank

TIER 3 – RISIKO RENDAH (track record 3+ order, pembayaran selalu tepat):
Opsi: T/T 30% DP, open account 30-60 hari
Atau: Open account dengan credit insurance

CARA MENYELEKSI PEMBELI BARU:

PERTANYAAN SCREENING WAJIB:
1. "Could you please provide your company registration number and registered address?"
2. "Would it be possible to arrange a brief video call to introduce ourselves?"
3. "Do you have any Indonesian supplier references we could contact?"
4. "What is your typical annual import volume for this category?"

RED FLAGS DALAM RESPONS:
- Tidak mau memberikan informasi perusahaan
- Tidak mau video call
- Minta ekspor dulu, bayar belakangan untuk "membangun kepercayaan"
- Terlalu cepat setuju harga tanpa negotiation (mungkin tidak serius atau scam)

ESCALATION PATH:
Setelah 2-3 order sukses dengan T/T advance:
→ Tawarkan T/T 30% DP + 70% copy BL
→ Setelah 5-6 order: pertimbangkan 60-day open account dengan credit limit
→ Selalu set credit limit (batas maksimal outstanding) per pembeli""",
    },

    {
        "title": "HS Code Indonesia: Panduan Klasifikasi untuk Produk Ekspor Unggulan",
        "category": "regulations",
        "source": "WCO (World Customs Organization); BTKI Kemendag RI",
        "content": """Kode HS (Harmonized System) yang benar sangat penting untuk menentukan tarif bea cukai dan persyaratan dokumen.

HS CODE UTAMA UNTUK EKSPOR INDONESIA:

PERTANIAN DAN PERKEBUNAN:
- 0901: Kopi (roasted: 090121, unroasted: 090111)
- 0902: Teh (hijau 090210, hitam 090230)
- 1801: Biji Kakao (mentah 180100, roasted masuk 180320)
- 0904: Lada (hitam 090411, putih 090412)
- 0908: Pala, kembang pala, kapulaga
- 0910: Kayu Manis (090611), Cengkeh (090700), Jahe (091010)
- 0801: Kelapa segar (080111), kacang mede/cashew (080131)
- 1513: Minyak kelapa (151311), minyak sawit kernel (151321)
- 1511: Minyak sawit CPO (151110), RBD Palm Oil (151190)

KERAJINAN DAN FURNITUR:
- 4601/4602: Produk anyaman (rattan, bambu, enceng gondok)
- 9403: Furnitur (kayu 940360, rattan 940350, bambu 940330)
- 4420: Produk kayu dekoratif, patung kayu, souvenir kayu
- 6304: Barang linen rumah tangga (sarung bantal, taplak)
- 5208/5209: Kain katun (batik, tenun)
- 6302: Bed linen, table linen (batik, tenun ikat)

MAKANAN OLAHAN:
- 2101: Ekstrak kopi, teh, mate
- 2103: Saus, bumbu masak (kecap, sambal)
- 2106: Makanan olahan tidak terklasifikasi lain
- 1704: Gula-gula (tanpa kakao)
- 1806: Cokelat dan produk kakao olahan
- 1901: Produk malt, tepung-terpungan

PERIKANAN:
- 0302/0303: Ikan segar/beku (tuna 030231, kerapu 030227)
- 0306: Krustasea (udang: 030613-030617, kepiting)
- 1604: Produk ikan olahan (tuna kalengan 160414)
- 0307: Moluska (cumi-cumi, kerang mutiara/kulit)

PRODUK NATURAL DAN KOSMETIK:
- 3301: Essential oils (serai wangi, nilam, cengkeh, pala)
- 1404: Produk nabati lain (sabut kelapa/coir 140420)
- 3304: Kosmetik (pelembab, foundation)
- 3305: Produk perawatan rambut
- 3307: Produk perawatan diri

CARA CEK HS CODE YANG BENAR:
1. INSW Tariff: insw.go.id → Search HS Code
2. BTKI Online: btki2022.tariffinder.co.id (Tarif Referensi Indonesia)
3. WCO HS Browser: wcoomd.org
4. Konsultasi dengan Bea Cukai atau PPJK jika tidak yakin""",
    },

    {
        "title": "Mempersiapkan Company Profile Ekspor yang Menarik",
        "category": "negotiation",
        "source": "ITC Export Quality Management; SMESCO Export Best Practice",
        "content": """Company Profile yang profesional adalah senjata pertama dalam memenangkan kepercayaan buyer internasional.

KOMPONEN WAJIB COMPANY PROFILE EKSPOR:

1. ABOUT US:
   - Tahun berdiri dan sejarah singkat
   - Jumlah karyawan dan luas fasilitas produksi
   - JANGAN terlalu sombong, JANGAN terlalu merendah

2. PRODUK:
   - Foto produk PROFESIONAL (investasikan dalam fotografi)
   - Deskripsi teknis yang detail
   - Spesifikasi: ukuran, berat, warna tersedia, bahan
   - Kode HS jika memungkinkan

3. KAPASITAS PRODUKSI:
   - Kapasitas bulanan / tahunan yang realistis
   - Jangan overclaim – ini SANGAT berbahaya jika buyer besar menerima

4. SERTIFIKASI DAN KEPATUHAN:
   - Halal (jika ada)
   - ISO/HACCP/GMP (jika ada)
   - NIB dan APE
   - SVLK (untuk produk kayu)
   - Foto sertifikat asli (hanya bagian yang perlu dilihat)

5. FOTO FASILITAS:
   - Foto pabrik/workshop yang bersih dan tertata
   - Foto proses produksi
   - Foto area penyimpanan / warehouse
   - Foto packaging

6. TRACK RECORD:
   - Negara dan jenis pembeli yang pernah dilayani
   - Volume ekspor tahunan (jika bangga)
   - Testimonial buyer (dengan izin)

7. CONTACT INFORMATION:
   - Person yang specifically handle ekspor
   - Email profesional (company domain, bukan gmail)
   - WhatsApp Business yang responsif
   - Website (walaupun sederhana)

TIPS:
- Tulis dalam BAHASA INGGRIS yang baik – gunakan jasa penerjemah profesional jika perlu
- PDF format, maksimal 10-12 halaman
- Versi digital yang bisa di-share via email (< 5MB)""",
    },

    {
        "title": "Kalkulator Bea Masuk: Cara Mengetahui Tarif di Negara Tujuan",
        "category": "market_intelligence",
        "source": "WTO Tariff Database; ITC Market Access Map; EU Trade Helpdesk",
        "content": """Sebelum ekspor, ketahui berapa bea masuk yang harus dibayar buyer di negara tujuan.

MENGAPA BANYAK EKSPORTIR UMKM TIDAK TAHU INI:
Ketidaktahuan bea masuk menyebabkan deal gagal karena landed cost pembeli terlalu tinggi.

SUMBER INFORMASI TARIF GRATIS:

1. WTO TARIFF DATABASE: tariffdata.wto.org
   - Tarif MFN (Most Favoured Nation) semua negara anggota WTO
   - Cari berdasarkan HS code dan negara tujuan

2. ITC MARKET ACCESS MAP: macmap.org
   - Database tarif + preferential rates dari FTA
   - Tarif kumulatif termasuk pajak tambahan
   - Gratis untuk negara berkembang

3. EU TRADE HELPDESK: trade.ec.europa.eu/tradehelp
   - Khusus ekspor ke Uni Eropa
   - Informasi tarif, label, persyaratan produk

4. ASEAN TARIFF FINDER: tariff.miti.gov.my
   - Tarif dalam FTA ASEAN dan FTA ASEAN+
   - Termasuk ATIGA, ACFTA, ASEAN-Korea, ASEAN-Japan

5. JAPAN CUSTOMS: customs.go.jp
   - Official Japan tariff search

CARA MENGGUNAKAN INFORMASI TARIF:

Contoh: Ekspor kopi roasted (HS 0902.10) ke Jerman

MFN Rate (tanpa FTA): 7.5%
GSP Rate (Indonesia eligible): 3.5%
ASEAN FTA Rate: N/A (Jerman bukan ASEAN)

Landed Cost Calculation:
CIF USD 5.00 + Bea Masuk 3.5% (USD 0.18) + EU VAT 7% on CIF+Duty (USD 0.36) = ~USD 5.54 landed cost for buyer

Jika buyer retail price EUR 20 dan landed cost USD 5.54, margin import layer masuk. Deal viable!

TIPS: Share tariff information dengan buyer – ini menunjukkan kamu profesional dan peduli pada bottom line mereka.""",
    },

    {
        "title": "UN Comtrade: Cara Membaca Data Ekspor untuk Strategi Bisnis",
        "category": "market_intelligence",
        "source": "UN Comtrade; ITC TradeMap",
        "content": """UN Comtrade adalah database perdagangan internasional terbesar yang bisa dimanfaatkan UMKM untuk riset pasar gratis.

CARA MENGGUNAKAN UN COMTRADE (comtrade.un.org):

1. CARI NEGARA PEMBELI TERBESAR:
   Query: Reporter = semua negara, Partner = Indonesia, Flow = Import, HS Code = [masukkan HS produk kamu]
   Hasil: Negara mana yang paling banyak impor produk seperti kamu dari Indonesia

2. ANALISIS TREN:
   Bandingkan data 3-5 tahun terakhir untuk melihat:
   - Apakah permintaan naik atau turun?
   - Negara mana yang mulai banyak impor?
   - Musim apa yang demand-nya paling tinggi?

3. BENCHMARKING HARGA:
   Export Unit Value = Total Value (USD) / Total Quantity
   Ini memberikan harga rata-rata ekspor per unit untuk HS code tersebut
   Bandingkan harga tawaranmu dengan benchmark ini

4. KOMPETITOR ANALYSIS:
   Lihat siapa selain Indonesia yang mengekspor ke negara target
   Query: Reporter = Vietnam (atau negara kompetitor), Partner = [negara target], Flow = Export, HS Code = [kode produkmu]

CONTOH INSIGHT UN COMTRADE:
"Ekspor Indonesia untuk HS 0901.21 (kopi roasted) ke Jerman naik 34% dari USD 12 juta ke USD 16 juta dalam 3 tahun terakhir. Export unit value USD 6.2/kg. Ini berarti permintaan Jerman untuk kopi Indonesia roasted sedang booming, dan harga di atas USD 6.50/kg masih dalam range yang wajar."

ITC TRADEMAP (trademap.org):
Lebih mudah digunakan dari UN Comtrade:
- Direktori importir aktif per negara dan HS code
- Tren impor visual
- Gratis untuk negara berkembang (daftar dengan email institusi atau perusahaan)""",
    },

    {
        "title": "Manajemen Sampel Produk: Kunci Mendapatkan Order Pertama",
        "category": "negotiation",
        "source": "Export Promotion Best Practices; TradeIndia; SMESCO",
        "content": """Sampel adalah investasi terpenting untuk mendapatkan buyer pertama.

STRATEGI SAMPEL YANG EFEKTIF:

1. PACKAGING SAMPEL HARUS PREMIUM:
   - Jangan kirim sampel dalam packaging biasa
   - Gunakan packaging yang merepresentasikan brand kamu
   - Include product spec sheet dan company profile
   - Tambahkan business card profesional

2. SYARAT DAN KETENTUAN SAMPEL:
   Ada dua pendekatan:
   a) FREE SAMPLE: Kirim gratis, minta buyer bayar ongkir
      - Cocok untuk buyer serius yang sudah jelas tertarik
      - Batas: maksimal 1-2 sampel per buyer

   b) CHARGED SAMPLE: Buyer bayar harga sampel + ongkir
      - Menyaring buyer yang tidak serius
      - Uang sampel biasanya dikembalikan jika order jadi

3. FOLLOW-UP SETELAH KIRIM SAMPEL:
   Hari 1-3: "Your samples are on the way, tracking number [XXX]"
   Setelah 5-7 hari: "Your samples should have arrived. Any questions?"
   Setelah 14 hari: "We'd love to hear your feedback on our samples."
   Setelah 21 hari: "Are you still considering our products? We have some special pricing this month."

4. INFORMASI YANG HARUS DISERTAKAN DENGAN SAMPEL:
   - Product Specification Sheet (ukuran, berat, bahan, HS code)
   - Price list dengan berbagai opsi volume
   - Company profile singkat
   - Sertifikat relevan (Halal, organic, dsb)
   - Lead time dan MOQ

5. TRACK SAMPEL SECARA SISTEMATIS:
   Buat spreadsheet: nama buyer, tanggal kirim, produk, status, follow-up date
   Jangan sampai ada sampel yang "terlupakan" tanpa follow-up

6. BIAYA SAMPEL SEBAGAI INVESTASI:
   Jangan hitung biaya sampel sebagai "rugi"
   1 order dari buyer premium bisa menutup 50-100 biaya sampel""",
    },

]


# ─────────────────────────────────────────────────────────────────────────────
# Seeding Engine
# ─────────────────────────────────────────────────────────────────────────────

def generate_embeddings(texts: list[str], model_name: str = "intfloat/multilingual-e5-large") -> list[list[float]]:
    """Generate 1024-dim embeddings using sentence-transformers."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("  [SKIP] sentence-transformers not available. Install: uv pip install 'sentence-transformers>=3.3'")
        return []

    print(f"  Loading embedding model '{model_name}'…")
    model = SentenceTransformer(model_name)
    passages = [f"passage: {t}" for t in texts]
    print(f"  Encoding {len(passages)} passages (this may take a minute)…")
    vecs = model.encode(
        passages,
        normalize_embeddings=True,
        batch_size=16,
        show_progress_bar=True,
    )
    return [v.tolist() for v in vecs]


def seed(dsn: str, with_embeddings: bool, clear_first: bool) -> None:
    engine = create_engine(dsn, pool_pre_ping=True)
    print(f"Connected to: {dsn.split('@')[-1]}")

    with engine.begin() as conn:
        if clear_first:
            conn.execute(text("DELETE FROM export_knowledge_base"))
            print("  Cleared existing export_knowledge_base rows.")

        # Optionally generate embeddings
        embeddings: list[list[float]] = []
        if with_embeddings:
            texts = [f"{e['title']}\n{e['content']}" for e in KB_ENTRIES]
            embeddings = generate_embeddings(texts)

        inserted = 0
        for i, entry in enumerate(KB_ENTRIES):
            emb = embeddings[i] if embeddings else None
            conn.execute(
                text("""
                    INSERT INTO export_knowledge_base
                        (id, title, content, category, source, embedding, metadata)
                    VALUES
                        (:id, :title, :content, :category, :source,
                         CAST(:emb AS vector),
                         CAST(:meta AS jsonb))
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id":       str(uuid4()),
                    "title":    entry["title"],
                    "content":  entry["content"],
                    "category": entry["category"],
                    "source":   entry.get("source", ""),
                    "emb":      str(emb) if emb else None,
                    "meta":     json.dumps({"seeded_at": datetime.utcnow().isoformat(), "version": "v1"}),
                },
            )
            inserted += 1

        print(f"\n✅ Inserted {inserted} knowledge base entries.")

        # Count by category
        rows = conn.execute(
            text("SELECT category, COUNT(*) AS n FROM export_knowledge_base GROUP BY category ORDER BY n DESC")
        ).fetchall()
        print("\nEntries by category:")
        for row in rows:
            print(f"  {row[0]:25s}: {row[1]}")

        # Create text search index if not exists
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ekb_tsvector
            ON export_knowledge_base
            USING GIN(to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, '')))
        """))
        print("\n✅ GIN text-search index created (idx_ekb_tsvector).")

        # Create HNSW index if embeddings present
        if with_embeddings and embeddings:
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_ekb_hnsw
                    ON export_knowledge_base
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64)
                """))
                print("✅ HNSW vector index created (idx_ekb_hnsw).")
            except Exception as e:
                print(f"  [WARN] HNSW index creation failed: {e}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Seed TradeConnect export knowledge base for RAG pipeline."
    )
    ap.add_argument(
        "--dsn",
        default=os.environ.get(
            "DATABASE_URL_SYNC",
            "postgresql+psycopg://tc_user:tc_pass_dev@localhost:5432/tradeconnect",
        ),
        help="PostgreSQL DSN (default: tc_user@localhost:5432/tradeconnect)",
    )
    ap.add_argument(
        "--with-embeddings",
        action="store_true",
        help="Generate 1024-dim embeddings using intfloat/multilingual-e5-large",
    )
    ap.add_argument(
        "--clear",
        action="store_true",
        help="Delete existing KB entries before seeding",
    )
    args = ap.parse_args()

    print("=" * 60)
    print("TradeConnect Knowledge Base Seeder")
    print(f"Entries to seed : {len(KB_ENTRIES)}")
    print(f"With embeddings : {args.with_embeddings}")
    print(f"Clear existing  : {args.clear}")
    print("=" * 60)

    if not args.with_embeddings:
        print("\nNote: Running WITHOUT embeddings. Vector search won't work.")
        print("Re-run with --with-embeddings for full RAG functionality.\n")

    seed(args.dsn, args.with_embeddings, args.clear)
    print("\nDone! 🎉")
    print("\nNext step: run scripts/seed-buyers-with-embeddings.py")


if __name__ == "__main__":
    main()
