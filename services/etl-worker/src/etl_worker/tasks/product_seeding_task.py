"""Synthetic product seeding task.

Menyemai data produk UMKM sintetis beserta embeddingnya untuk demo/dev.

Alur:
  1. Insert synthetic users → umkm → product (etl-worker DB session)
  2. Dispatch task embeddings.generate_product ke queue "ai"
     → embedding-worker akan generate dan simpan ke product_embedding

Semua record ditandai dengan metadata.source = "synthetic_v1".
Idempoten: DELETE synthetic records dulu sebelum re-insert.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import structlog
from sqlalchemy import text

if TYPE_CHECKING:
    from celery import Task

from etl_worker.celery_app import celery_app
from etl_worker.db.session import get_session_factory

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Deterministic helpers (sama dengan buyer_seeding_task)
# ---------------------------------------------------------------------------

def _hash_to_int(seed: int, label: str, index: int, *extra: Any) -> int:
    parts = [str(seed), label, str(index), *[str(v) for v in extra]]
    return int.from_bytes(hashlib.sha256(":".join(parts).encode()).digest()[:8], "big")


def _det_float(seed: int, label: str, index: int, lo: float, hi: float) -> float:
    return lo + (hi - lo) * (_hash_to_int(seed, label, index) / 2**64)


def _det_int(seed: int, label: str, index: int, choices: list[int]) -> int:
    return choices[_hash_to_int(seed, label, index) % len(choices)]


# ---------------------------------------------------------------------------
# Master catalogue — 5 UMKM, masing-masing 10 produk
# ---------------------------------------------------------------------------

UMKM_PROFILES: list[dict[str, Any]] = [
    {
        "key": "rotan",
        "legal_name": "CV Kerajinan Rotan Nusantara",
        "nib_prefix": "1234567890",
        "description": (
            "Produsen kerajinan rotan dan anyaman alami dari Cirebon, Jawa Barat. "
            "Spesialis keranjang, tatakan, dan furnitur rotan untuk pasar Eropa."
        ),
        "certifications": ["SNI 01-2973-2011", "FSC CoC", "Halal MUI"],
        "verified_score": "0.8500",
        "products": [
            {
                "name": "Keranjang Rotan Oval Natural Finish",
                "description": (
                    "Keranjang rotan anyaman tangan diameter 35cm, finishing natural lacquer. "
                    "Cocok untuk penyimpanan buah, roti, atau dekorasi meja. "
                    "Bahan baku rotan grade A dari Kalimantan."
                ),
                "hs_code": "460220",
                "hs_confidence": "0.9200",
                "moq": 50,
                "monthly_capacity": 2000,
                "price_min": "4.50",
                "price_max": "6.50",
                "hpp": "2.80",
            },
            {
                "name": "Tatakan Meja Bundar Anyaman Enceng Gondok",
                "description": (
                    "Tatakan meja oval dari enceng gondok (water hyacinth) diameter 30cm, "
                    "dua lapis, ramah lingkungan. Natural dye. Diameter 30x5cm."
                ),
                "hs_code": "460290",
                "hs_confidence": "0.8800",
                "moq": 100,
                "monthly_capacity": 5000,
                "price_min": "2.20",
                "price_max": "3.50",
                "hpp": "1.30",
            },
            {
                "name": "Kotak Serbaguna Bambu Penutup Geser",
                "description": (
                    "Kotak penyimpanan bambu dengan tutup geser, ukuran 20x15x10cm. "
                    "Cocok untuk alat tulis, perhiasan, atau aksesoris dapur."
                ),
                "hs_code": "460210",
                "hs_confidence": "0.8600",
                "moq": 100,
                "monthly_capacity": 3000,
                "price_min": "3.00",
                "price_max": "4.80",
                "hpp": "1.90",
            },
            {
                "name": "Baki Rotan Persegi Panjang Dekoratif",
                "description": (
                    "Baki rotan 40x25cm motif anyaman diagonal. "
                    "Finishing wax natural, tahan lama, food-safe coating."
                ),
                "hs_code": "460220",
                "hs_confidence": "0.9100",
                "moq": 50,
                "monthly_capacity": 1500,
                "price_min": "5.50",
                "price_max": "8.00",
                "hpp": "3.20",
            },
            {
                "name": "Tempat Tisu Anyaman Pandan Motif Geometris",
                "description": (
                    "Tempat tisu dari anyaman daun pandan motif geometris. "
                    "Natural dye warna bumi. Ukuran 15x8x8cm, kotak standar."
                ),
                "hs_code": "460290",
                "hs_confidence": "0.8400",
                "moq": 200,
                "monthly_capacity": 6000,
                "price_min": "1.80",
                "price_max": "2.80",
                "hpp": "1.00",
            },
            {
                "name": "Set Keranjang Picnic Rotan 3 Ukuran",
                "description": (
                    "Set 3 keranjang picnic rotan nested: S/M/L. "
                    "Dilengkapi engsel kuningan, handle rotan solid. "
                    "Packaging karton export-ready."
                ),
                "hs_code": "460220",
                "hs_confidence": "0.9000",
                "moq": 30,
                "monthly_capacity": 900,
                "price_min": "18.00",
                "price_max": "25.00",
                "hpp": "11.00",
            },
            {
                "name": "Rak Dinding Rotan Minimalis 3 Susun",
                "description": (
                    "Rak dinding rotan 3 susun, rangka kayu jati, finishing natural. "
                    "Ukuran 60x12x50cm. Mudah dipasang, ready for flat-pack shipping."
                ),
                "hs_code": "460220",
                "hs_confidence": "0.8700",
                "moq": 20,
                "monthly_capacity": 400,
                "price_min": "22.00",
                "price_max": "30.00",
                "hpp": "14.00",
            },
            {
                "name": "Pot Tanaman Rotan Cover Medium",
                "description": (
                    "Cover pot tanaman rotan diameter 20cm, cocok untuk pot plastik 15-18cm. "
                    "Finishing natural atau hitam. Tahan kelembaban dengan coating."
                ),
                "hs_code": "460220",
                "hs_confidence": "0.8500",
                "moq": 100,
                "monthly_capacity": 3000,
                "price_min": "3.50",
                "price_max": "5.00",
                "hpp": "2.00",
            },
            {
                "name": "Keranjang Belanja Rotan Handle Kulit",
                "description": (
                    "Keranjang belanja rotan dengan handle kulit sintetis, "
                    "ukuran 35x22x30cm. Tren Skandinavia, diminati pasar Eropa dan Jepang."
                ),
                "hs_code": "460220",
                "hs_confidence": "0.9300",
                "moq": 50,
                "monthly_capacity": 1200,
                "price_min": "12.00",
                "price_max": "18.00",
                "hpp": "7.50",
            },
            {
                "name": "Tikar Anyaman Seagrass Alami 120x180cm",
                "description": (
                    "Tikar lantai dari serat seagrass alami, ukuran 120x180cm. "
                    "Anti-slip backing, sertifikat bebas pewarna berbahaya."
                ),
                "hs_code": "460290",
                "hs_confidence": "0.8600",
                "moq": 30,
                "monthly_capacity": 600,
                "price_min": "28.00",
                "price_max": "38.00",
                "hpp": "17.00",
            },
        ],
    },
    {
        "key": "mebel",
        "legal_name": "PT Mebel Jati Jepara Utama",
        "nib_prefix": "2345678901",
        "description": (
            "Produsen furnitur kayu jati solid dari Jepara, Jawa Tengah. "
            "Spesialis mebel outdoor garden dan indoor living berbahan reclaimed teak."
        ),
        "certifications": ["FSC CoC", "SVLK", "SNI ISO 9001:2015"],
        "verified_score": "0.9000",
        "products": [
            {
                "name": "Meja Makan Jati Solid 6 Kursi Outdoor",
                "description": (
                    "Meja makan kayu jati solid 180x90x76cm dengan 6 kursi. "
                    "Finishing teak oil natural, tahan cuaca, cocok outdoor. "
                    "SVLK certified, FSC CoC."
                ),
                "hs_code": "940360",
                "hs_confidence": "0.9400",
                "moq": 5,
                "monthly_capacity": 80,
                "price_min": "480.00",
                "price_max": "650.00",
                "hpp": "280.00",
            },
            {
                "name": "Kursi Teras Kayu Jati Lipat",
                "description": (
                    "Kursi teras kayu jati lipat klasik, seat canvas canvas abu-abu. "
                    "Mudah dilipat untuk penyimpanan. Finishing teak oil."
                ),
                "hs_code": "940130",
                "hs_confidence": "0.8900",
                "moq": 20,
                "monthly_capacity": 500,
                "price_min": "65.00",
                "price_max": "90.00",
                "hpp": "38.00",
            },
            {
                "name": "Lemari Pakaian Kayu Mahoni 3 Pintu",
                "description": (
                    "Lemari pakaian kayu mahoni solid 3 pintu, ukiran motif Jepara. "
                    "Ukuran 180x55x200cm, finishing rustic brown."
                ),
                "hs_code": "940350",
                "hs_confidence": "0.9200",
                "moq": 3,
                "monthly_capacity": 50,
                "price_min": "320.00",
                "price_max": "450.00",
                "hpp": "190.00",
            },
            {
                "name": "Coffee Table Reclaimed Teak Industrial",
                "description": (
                    "Meja kopi bahan reclaimed teak 100x60x45cm, kaki besi hollow 4cm. "
                    "Finishing wax natural, desain industrial-rustic."
                ),
                "hs_code": "940360",
                "hs_confidence": "0.9000",
                "moq": 10,
                "monthly_capacity": 200,
                "price_min": "120.00",
                "price_max": "165.00",
                "hpp": "72.00",
            },
            {
                "name": "Dipan Platform Kayu Jati Minimalis King",
                "description": (
                    "Dipan platform kayu jati solid ukuran King 180x200cm. "
                    "Desain Skandinavia minimalis, tinggi 25cm. Finishing natural oil."
                ),
                "hs_code": "940350",
                "hs_confidence": "0.9100",
                "moq": 3,
                "monthly_capacity": 60,
                "price_min": "380.00",
                "price_max": "520.00",
                "hpp": "220.00",
            },
            {
                "name": "Rak Buku Kayu Jati 5 Tingkat",
                "description": (
                    "Rak buku kayu jati solid 5 tingkat 90x30x180cm. "
                    "Adjustable shelves, finishing natural teak. "
                    "Flat-pack untuk efisiensi pengiriman."
                ),
                "hs_code": "940360",
                "hs_confidence": "0.8800",
                "moq": 5,
                "monthly_capacity": 120,
                "price_min": "180.00",
                "price_max": "240.00",
                "hpp": "105.00",
            },
            {
                "name": "Garden Bench Jati 2-Seater Klasik",
                "description": (
                    "Bangku taman kayu jati 2 orang, 120x55x88cm. "
                    "Desain klasik dengan sandaran lengkung. Tahan cuaca tanpa perawatan intensif."
                ),
                "hs_code": "940330",
                "hs_confidence": "0.9300",
                "moq": 10,
                "monthly_capacity": 200,
                "price_min": "130.00",
                "price_max": "175.00",
                "hpp": "76.00",
            },
            {
                "name": "Nakas Bedside Table Kayu Jati 1 Laci",
                "description": (
                    "Nakas kayu jati solid 1 laci, ukuran 45x40x55cm. "
                    "Cocok untuk kamar tidur minimalis. Finishing natural oil."
                ),
                "hs_code": "940350",
                "hs_confidence": "0.8900",
                "moq": 10,
                "monthly_capacity": 300,
                "price_min": "75.00",
                "price_max": "100.00",
                "hpp": "44.00",
            },
            {
                "name": "Set Kursi Sofa Rotan Sintetis 3+1+1",
                "description": (
                    "Set sofa teras rotan sintetis 3+1+1 dengan cushion waterproof. "
                    "Rangka aluminium powder coat. Cocok untuk outdoor dan indoor."
                ),
                "hs_code": "940160",
                "hs_confidence": "0.8700",
                "moq": 3,
                "monthly_capacity": 50,
                "price_min": "520.00",
                "price_max": "720.00",
                "hpp": "310.00",
            },
            {
                "name": "Patung Kayu Ukir Kuda Jepara 40cm",
                "description": (
                    "Patung kuda kayu jati ukir tangan, tinggi 40cm. "
                    "Motif ukiran Jepara tradisional, finishing natural polish. "
                    "Cocok sebagai dekorasi dan souvenir premium."
                ),
                "hs_code": "442090",
                "hs_confidence": "0.8800",
                "moq": 20,
                "monthly_capacity": 400,
                "price_min": "35.00",
                "price_max": "55.00",
                "hpp": "20.00",
            },
        ],
    },
    {
        "key": "batik",
        "legal_name": "UD Batik Solo Putri Mandiri",
        "nib_prefix": "3456789012",
        "description": (
            "Usaha batik tulis dan cap dari Laweyan, Solo, Jawa Tengah. "
            "Memproduksi kain batik, sarung, dan linen rumah tangga dengan motif tradisional."
        ),
        "certifications": ["Batik Mark Indonesia", "Halal MUI", "OEKO-TEX Standard 100"],
        "verified_score": "0.8000",
        "products": [
            {
                "name": "Kain Batik Tulis Solo Motif Parang 2.5m",
                "description": (
                    "Kain batik tulis Solo motif parang rusak barong, lebar 115cm panjang 2.5m. "
                    "Bahan cotton prima, pewarna alam indigo dan soga. "
                    "Sertifikat Batik Mark Indonesia."
                ),
                "hs_code": "520811",
                "hs_confidence": "0.9100",
                "moq": 20,
                "monthly_capacity": 400,
                "price_min": "25.00",
                "price_max": "40.00",
                "hpp": "15.00",
            },
            {
                "name": "Kain Batik Cap Pekalongan Motif Mega Mendung",
                "description": (
                    "Kain batik cap motif mega mendung Cirebon, cotton 115x200cm. "
                    "Warna biru klasik multi-gradasi. Cocok untuk bahan baju dan kemeja."
                ),
                "hs_code": "520821",
                "hs_confidence": "0.8800",
                "moq": 50,
                "monthly_capacity": 1500,
                "price_min": "8.00",
                "price_max": "12.00",
                "hpp": "4.80",
            },
            {
                "name": "Sprei Batik King Size 180x200 Set 4pcs",
                "description": (
                    "Set sprei batik king size 180x200cm terdiri dari 1 sprei + 2 sarung bantal + "
                    "1 sarung guling. Motif kawung, organic cotton 200TC."
                ),
                "hs_code": "630291",
                "hs_confidence": "0.9200",
                "moq": 10,
                "monthly_capacity": 200,
                "price_min": "35.00",
                "price_max": "50.00",
                "hpp": "20.00",
            },
            {
                "name": "Sarung Batik Pria Motif Lereng Klasik",
                "description": (
                    "Sarung batik pria motif lereng Solo, cotton prima, "
                    "ukuran 115x200cm. Finishing jahitan serasi, bisa kustom motif."
                ),
                "hs_code": "630291",
                "hs_confidence": "0.8900",
                "moq": 50,
                "monthly_capacity": 2000,
                "price_min": "7.50",
                "price_max": "11.00",
                "hpp": "4.30",
            },
            {
                "name": "Taplak Meja Batik Printing 150x220cm",
                "description": (
                    "Taplak meja batik printing digital motif tropis kontemporer, "
                    "ukuran 150x220cm, cotton heavy 280gsm. Food-safe dye."
                ),
                "hs_code": "630292",
                "hs_confidence": "0.8700",
                "moq": 20,
                "monthly_capacity": 500,
                "price_min": "12.00",
                "price_max": "18.00",
                "hpp": "7.00",
            },
            {
                "name": "Kemeja Batik Tulis Pria Slim Fit",
                "description": (
                    "Kemeja batik tulis pria slim fit, kain cotton prima, "
                    "motif sekar jagad solo. Ukuran S-XXL available, bisa custom."
                ),
                "hs_code": "620520",
                "hs_confidence": "0.8600",
                "moq": 30,
                "monthly_capacity": 600,
                "price_min": "22.00",
                "price_max": "35.00",
                "hpp": "13.00",
            },
            {
                "name": "Kain Lurik Tenun ATBM Tradisional",
                "description": (
                    "Kain lurik ATBM (Alat Tenun Bukan Mesin) tangan, motif garis vertikal, "
                    "warna natural indigo dan coklat soga. Lebar 90cm, per meter."
                ),
                "hs_code": "521142",
                "hs_confidence": "0.8500",
                "moq": 50,
                "monthly_capacity": 800,
                "price_min": "6.00",
                "price_max": "9.00",
                "hpp": "3.50",
            },
            {
                "name": "Selendang Batik Sutra ATBM 50x200cm",
                "description": (
                    "Selendang batik sutra ATBM motif parang, ukuran 50x200cm. "
                    "Bahan sutra ATBM lokal, ringan, cocok untuk fashion dan souvenir premium."
                ),
                "hs_code": "540742",
                "hs_confidence": "0.8400",
                "moq": 10,
                "monthly_capacity": 150,
                "price_min": "45.00",
                "price_max": "70.00",
                "hpp": "27.00",
            },
            {
                "name": "Tas Totebag Batik Canvas Premium",
                "description": (
                    "Tas totebag canvas 350gsm dengan panel batik tulis asli, "
                    "ukuran 40x35cm, handle katun. Cocok corporate gift dan souvenir."
                ),
                "hs_code": "420222",
                "hs_confidence": "0.8300",
                "moq": 50,
                "monthly_capacity": 1000,
                "price_min": "9.00",
                "price_max": "14.00",
                "hpp": "5.50",
            },
            {
                "name": "Keset Batik Handmade 40x60cm",
                "description": (
                    "Keset batik handmade dari perca kain batik, ukuran 40x60cm. "
                    "Anti-slip backing, upcycled fabric. Eco-friendly, setiap item unik."
                ),
                "hs_code": "630790",
                "hs_confidence": "0.8200",
                "moq": 50,
                "monthly_capacity": 1500,
                "price_min": "5.00",
                "price_max": "8.00",
                "hpp": "2.80",
            },
        ],
    },
    {
        "key": "perak",
        "legal_name": "Koperasi Pengrajin Perak Kotagede",
        "nib_prefix": "4567890123",
        "description": (
            "Koperasi pengrajin perak tradisional dari Kotagede, Yogyakarta. "
            "Memproduksi perhiasan perak sterling 925 dengan teknik ukir dan filigree tangan."
        ),
        "certifications": ["SNI Perhiasan", "Produk Unggulan Daerah DIY"],
        "verified_score": "0.7500",
        "products": [
            {
                "name": "Cincin Perak 925 Motif Kawung Ukir Tangan",
                "description": (
                    "Cincin perak sterling 925 motif kawung ukiran tangan pengrajin Kotagede. "
                    "Finishing polish mengkilap. Ukuran 5-12 USA available."
                ),
                "hs_code": "711311",
                "hs_confidence": "0.9500",
                "moq": 10,
                "monthly_capacity": 300,
                "price_min": "12.00",
                "price_max": "20.00",
                "hpp": "7.00",
            },
            {
                "name": "Kalung Filigree Perak 925 Motif Bunga",
                "description": (
                    "Kalung perak filigree teknik sulam kawat halus, motif bunga tropis, "
                    "panjang 45cm+5cm extender. Dikerjakan tangan penuh, tiap item unik."
                ),
                "hs_code": "711311",
                "hs_confidence": "0.9400",
                "moq": 5,
                "monthly_capacity": 100,
                "price_min": "35.00",
                "price_max": "55.00",
                "hpp": "21.00",
            },
            {
                "name": "Gelang Bangle Perak Solid 4mm Ukiran Batik",
                "description": (
                    "Gelang bangle perak 925 solid 4mm, ukiran motif batik parang. "
                    "Diameter 6.5cm (adjustable untuk S-M-L). Finishing matt dan glossy."
                ),
                "hs_code": "711311",
                "hs_confidence": "0.9300",
                "moq": 10,
                "monthly_capacity": 250,
                "price_min": "18.00",
                "price_max": "28.00",
                "hpp": "11.00",
            },
            {
                "name": "Anting Drop Perak 925 Labradorite",
                "description": (
                    "Anting drop perak 925 dengan aksen batu labradorite alami 8mm. "
                    "Panjang 4.5cm, kait sterling silver hypoallergenic."
                ),
                "hs_code": "711311",
                "hs_confidence": "0.9200",
                "moq": 10,
                "monthly_capacity": 200,
                "price_min": "22.00",
                "price_max": "35.00",
                "hpp": "13.00",
            },
            {
                "name": "Brooch Perak Motif Garuda Indonesia",
                "description": (
                    "Bros perak 925 motif Garuda Pancasila, ukiran tangan halus, "
                    "ukuran 4x3cm. Finishing oxidized antik. Souvenir diplomatik premium."
                ),
                "hs_code": "711311",
                "hs_confidence": "0.9100",
                "moq": 20,
                "monthly_capacity": 400,
                "price_min": "15.00",
                "price_max": "25.00",
                "hpp": "9.00",
            },
            {
                "name": "Set Perhiasan Perak Cincin + Kalung Matching",
                "description": (
                    "Set perhiasan perak 925 terdiri dari cincin dan kalung dengan motif wayang "
                    "yang matching. Disajikan dalam gift box kayu. Bisa kustom ukiran nama."
                ),
                "hs_code": "711311",
                "hs_confidence": "0.9300",
                "moq": 5,
                "monthly_capacity": 80,
                "price_min": "55.00",
                "price_max": "85.00",
                "hpp": "33.00",
            },
            {
                "name": "Tempat Kartu Nama Perak 925 Ukir Personalized",
                "description": (
                    "Tempat kartu nama perak 925 dengan ukiran nama atau logo perusahaan. "
                    "Ukuran standar 9.5x6cm. Corporate gift eksklusif."
                ),
                "hs_code": "711311",
                "hs_confidence": "0.8900",
                "moq": 10,
                "monthly_capacity": 200,
                "price_min": "30.00",
                "price_max": "50.00",
                "hpp": "18.00",
            },
            {
                "name": "Keris Miniatur Perak Souvenir Budaya",
                "description": (
                    "Miniatur keris perak 925 panjang 15cm sebagai souvenir budaya premium. "
                    "Sarung kayu ukir, box display. Sertifikat keaslian."
                ),
                "hs_code": "711319",
                "hs_confidence": "0.8700",
                "moq": 5,
                "monthly_capacity": 60,
                "price_min": "65.00",
                "price_max": "95.00",
                "hpp": "38.00",
            },
            {
                "name": "Gelang Charm Perak 925 Seri Nusantara",
                "description": (
                    "Gelang charm perak 925 dengan 5 charm motif budaya Nusantara "
                    "(wayang, batik, keris, Borobudur, Garuda). Panjang 18cm+3cm."
                ),
                "hs_code": "711311",
                "hs_confidence": "0.9200",
                "moq": 10,
                "monthly_capacity": 200,
                "price_min": "45.00",
                "price_max": "65.00",
                "hpp": "27.00",
            },
            {
                "name": "Cincin Perak 925 Batu Akik Bacan",
                "description": (
                    "Cincin perak 925 dengan seting batu akik bacan Halmahera natural "
                    "6x8mm oval. Motif setting prong klasik. Ukuran adjustable."
                ),
                "hs_code": "711620",
                "hs_confidence": "0.9000",
                "moq": 5,
                "monthly_capacity": 100,
                "price_min": "28.00",
                "price_max": "45.00",
                "hpp": "17.00",
            },
        ],
    },
    {
        "key": "rempah",
        "legal_name": "CV Rempah Nusantara Ekspor",
        "nib_prefix": "5678901234",
        "description": (
            "Eksportir rempah-rempah dan kopi specialty dari Malang, Jawa Timur. "
            "Menyuplai lada hitam Bangka, kayu manis Kerinci, kopi arabika Gayo, "
            "dan berbagai rempah pilihan ke pasar Eropa dan Timur Tengah."
        ),
        "certifications": ["Organik Indonesia", "USDA Organic", "Rainforest Alliance"],
        "verified_score": "0.8800",
        "products": [
            {
                "name": "Kopi Arabika Gayo Green Beans Grade 1",
                "description": (
                    "Green coffee beans arabika Gayo Aceh Grade 1, natural process. "
                    "Cupping score 84+. Bag 60kg GrainPro liner. "
                    "Sertifikat Rainforest Alliance dan Organic Indonesia."
                ),
                "hs_code": "090111",
                "hs_confidence": "0.9600",
                "moq": 60,
                "monthly_capacity": 6000,
                "price_min": "4.20",
                "price_max": "5.50",
                "hpp": "2.60",
            },
            {
                "name": "Kopi Robusta Lampung Roasted Medium Dark 250g",
                "description": (
                    "Kopi robusta Lampung roasted medium-dark, specialty grade, "
                    "250g vacuum pack. Body tebal, crema bagus, cocok espresso blend."
                ),
                "hs_code": "090121",
                "hs_confidence": "0.9300",
                "moq": 100,
                "monthly_capacity": 5000,
                "price_min": "3.80",
                "price_max": "5.20",
                "hpp": "2.20",
            },
            {
                "name": "Lada Hitam Bangka Whole Premium 1kg",
                "description": (
                    "Lada hitam Bangka whole pepper 1kg vacuum pack, grade A. "
                    "Moisture ≤12%, piperine ≥5%. Sertifikat organik, bebas pestisida."
                ),
                "hs_code": "090411",
                "hs_confidence": "0.9500",
                "moq": 50,
                "monthly_capacity": 10000,
                "price_min": "5.50",
                "price_max": "7.50",
                "hpp": "3.20",
            },
            {
                "name": "Kayu Manis Kerinci Cassia Sticks Grade A",
                "description": (
                    "Kayu manis Kerinci (cassia) grade A, sticks 10cm, 1kg bulk bag. "
                    "Kadar minyak atsiri ≥1.5%, aroma kuat. USDA Organic certified."
                ),
                "hs_code": "090611",
                "hs_confidence": "0.9400",
                "moq": 25,
                "monthly_capacity": 5000,
                "price_min": "4.00",
                "price_max": "6.00",
                "hpp": "2.30",
            },
            {
                "name": "Cengkeh Whole Maluku Utara Zanzibar Grade",
                "description": (
                    "Cengkeh whole Maluku Utara, Zanzibar grade, 5kg vacuum pack. "
                    "Eugenol content ≥80%, moisture ≤12%, sorted machine & hand."
                ),
                "hs_code": "090700",
                "hs_confidence": "0.9600",
                "moq": 25,
                "monthly_capacity": 5000,
                "price_min": "8.00",
                "price_max": "11.00",
                "hpp": "5.00",
            },
            {
                "name": "Jahe Merah Bubuk Organik 100g",
                "description": (
                    "Jahe merah bubuk organik, spray-dried, 100g aluminium sachet. "
                    "Gingerol content terstandarisasi, bebas irradiasi. USDA Organic."
                ),
                "hs_code": "091010",
                "hs_confidence": "0.9200",
                "moq": 200,
                "monthly_capacity": 20000,
                "price_min": "2.50",
                "price_max": "4.00",
                "hpp": "1.40",
            },
            {
                "name": "Vanilla Planifolia Papua Whole Beans Grade A",
                "description": (
                    "Vanilla planifolia Papua grade A whole beans, length ≥16cm, "
                    "moisture 25-35%, vanillin ≥2%. 100g vacuum pouch. Premium export."
                ),
                "hs_code": "090500",
                "hs_confidence": "0.9500",
                "moq": 10,
                "monthly_capacity": 500,
                "price_min": "95.00",
                "price_max": "130.00",
                "hpp": "62.00",
            },
            {
                "name": "Pala Banda Whole Nutmeg Grade AB",
                "description": (
                    "Pala Banda whole nutmeg grade AB, 25kg carton. "
                    "AFLA free, fumigation-free. Cocok untuk industri makanan dan farmasi."
                ),
                "hs_code": "090811",
                "hs_confidence": "0.9400",
                "moq": 25,
                "monthly_capacity": 5000,
                "price_min": "4.50",
                "price_max": "6.50",
                "hpp": "2.80",
            },
            {
                "name": "Minyak Nilam Patchouli Oil Aceh 100ml",
                "description": (
                    "Minyak nilam (patchouli oil) Aceh, steam distilled, 100ml amber vial. "
                    "Patchouli alcohol ≥30%, specific gravity 0.95-0.975. Export quality."
                ),
                "hs_code": "330119",
                "hs_confidence": "0.9100",
                "moq": 20,
                "monthly_capacity": 2000,
                "price_min": "18.00",
                "price_max": "25.00",
                "hpp": "11.00",
            },
            {
                "name": "Virgin Coconut Oil Cold Pressed Organic 1L",
                "description": (
                    "VCO virgin coconut oil cold pressed, 1L glass bottle. "
                    "FFA ≤0.1%, moisture ≤0.1%, USDA Organic & Kosher certified. "
                    "Cocok food grade dan cosmetic grade."
                ),
                "hs_code": "151311",
                "hs_confidence": "0.9300",
                "moq": 50,
                "monthly_capacity": 10000,
                "price_min": "4.80",
                "price_max": "7.00",
                "hpp": "2.90",
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@celery_app.task(  # type: ignore[untyped-decorator]
    name="seeding.synthetic_products",
    bind=True,
    queue="ingest",
)
def seed_synthetic_products(self: Task, count_per_umkm: int = 10) -> dict[str, Any]:
    """Seed synthetic UMKM + products, then dispatch embedding generation.

    Idempoten: DELETE synthetic records terlebih dahulu sebelum re-insert.
    count_per_umkm: jumlah produk per UMKM (maksimal sesuai catalogue).
    """
    log.info("seeding.products.start", umkm_count=len(UMKM_PROFILES), count_per_umkm=count_per_umkm)
    seed = 42
    inserted_products = 0
    # (product_id, description, name, hs_code, umkm_certifications)
    product_ids_for_embedding: list[tuple[str, str, str, str, list[str]]] = []

    session_factory = get_session_factory()
    with session_factory() as session:
        # ── 1. Hapus data sintetis lama ──────────────────────────────────────
        session.execute(
            text(
                """
                DELETE FROM product_embedding
                WHERE product_id IN (
                    SELECT p.id FROM product p
                    JOIN umkm u ON u.id = p.umkm_id
                    JOIN users usr ON usr.id = u.user_id
                    WHERE usr.email LIKE '%@synthetic.tradeconnect.dev'
                )
                """
            )
        )
        session.execute(
            text(
                """
                DELETE FROM product
                WHERE umkm_id IN (
                    SELECT u.id FROM umkm u
                    JOIN users usr ON usr.id = u.user_id
                    WHERE usr.email LIKE '%@synthetic.tradeconnect.dev'
                )
                """
            )
        )
        session.execute(
            text(
                """
                DELETE FROM umkm
                WHERE user_id IN (
                    SELECT id FROM users
                    WHERE email LIKE '%@synthetic.tradeconnect.dev'
                )
                """
            )
        )
        session.execute(
            text("DELETE FROM users WHERE email LIKE '%@synthetic.tradeconnect.dev'")
        )

        # ── 2. Insert users → umkm → products ───────────────────────────────
        for u_idx, profile in enumerate(UMKM_PROFILES):
            # User
            user_id = str(uuid4())
            session.execute(
                text(
                    """
                    INSERT INTO users (id, email, password_hash, tier, is_active, created_at, updated_at)
                    VALUES (:id, :email, :pw, 'free', TRUE, NOW(), NOW())
                    """
                ),
                {
                    "id": user_id,
                    "email": f"{profile['key']}@synthetic.tradeconnect.dev",
                    "pw": "$2b$10$synthetic_hash_not_real_password_placeholder",
                },
            )

            # UMKM
            umkm_id = str(uuid4())
            nib = f"{profile['nib_prefix']}{u_idx:03d}"
            session.execute(
                text(
                    """
                    INSERT INTO umkm (
                        id, legal_name, nib, description,
                        verification_status, verified_score,
                        oss_rba_data, inatrade_data, certifications,
                        user_id, is_active, created_at, updated_at
                    )
                    VALUES (
                        :id, :legal_name, :nib, :desc,
                        'VERIFIED', :score,
                        CAST(:oss AS JSONB), CAST(:ina AS JSONB), :certs,
                        :user_id, TRUE, NOW(), NOW()
                    )
                    """
                ),
                {
                    "id": umkm_id,
                    "legal_name": profile["legal_name"],
                    "nib": nib,
                    "desc": profile["description"],
                    "score": profile["verified_score"],
                    "oss": json.dumps({"is_mock": True, "source": "synthetic_v1"}),
                    "ina": json.dumps({}),
                    "certs": profile["certifications"],
                    "user_id": user_id,
                },
            )

            # Products — ambil sesuai count_per_umkm
            products_subset = profile["products"][:count_per_umkm]
            for p_idx, prod in enumerate(products_subset):
                product_id = str(uuid4())

                # Variasikan harga sedikit antar instance agar data lebih realistis
                price_factor = 1.0 + _det_float(seed, f"{profile['key']}_price", p_idx, -0.1, 0.1)
                price_min = round(float(prod["price_min"]) * price_factor, 2)
                price_max = round(float(prod["price_max"]) * price_factor, 2)
                hpp = float(prod["hpp"])

                session.execute(
                    text(
                        """
                        INSERT INTO product (
                            id, umkm_id, name, description,
                            hs_code, hs_confidence,
                            moq, monthly_capacity,
                            price_min, price_max, hpp,
                            photo_urls, created_at, updated_at
                        )
                        VALUES (
                            :id, :umkm_id, :name, :desc,
                            :hs_code, :hs_confidence,
                            :moq, :capacity,
                            :price_min, :price_max, :hpp,
                            :photos, NOW(), NOW()
                        )
                        """
                    ),
                    {
                        "id": product_id,
                        "umkm_id": umkm_id,
                        "name": prod["name"],
                        "desc": prod["description"],
                        "hs_code": prod["hs_code"],
                        "hs_confidence": prod["hs_confidence"],
                        "moq": prod["moq"],
                        "capacity": prod["monthly_capacity"],
                        "price_min": str(price_min),
                        "price_max": str(price_max),
                        "hpp": str(hpp),
                        "photos": [],
                    },
                )

                product_ids_for_embedding.append((
                    product_id,
                    prod["description"],
                    prod["name"],
                    prod["hs_code"],
                    profile["certifications"],
                ))
                inserted_products += 1

        session.commit()

    log.info("seeding.products.db_done", inserted=inserted_products)

    # ── 3. Dispatch embedding generation ke embedding-worker ────────────────
    # Embedding-worker (matching-service) mendengarkan queue "ai" di broker
    # yang sama. send_task() tidak butuh task terdaftar lokal.
    # Teks embedding diperkaya: nama + deskripsi + HS code + sertifikasi UMKM
    # agar vektor lebih diskriminatif saat ANN search.
    embedding_dispatched = 0
    for product_id, description, prod_name, hs_code, certs in product_ids_for_embedding:
        cert_str = ", ".join(certs) if certs else ""
        enriched_text = (
            f"{prod_name}. {description}"
            f" Kode HS: {hs_code}."
            + (f" Sertifikasi: {cert_str}." if cert_str else "")
        )
        celery_app.send_task(
            "embeddings.generate_product",
            args=[product_id, enriched_text],
            queue="ai",
            ignore_result=True,
        )
        embedding_dispatched += 1

    log.info(
        "seeding.products.done",
        inserted=inserted_products,
        embedding_tasks_dispatched=embedding_dispatched,
    )
    return {
        "umkm_seeded": len(UMKM_PROFILES),
        "products_inserted": inserted_products,
        "embedding_tasks_dispatched": embedding_dispatched,
    }
