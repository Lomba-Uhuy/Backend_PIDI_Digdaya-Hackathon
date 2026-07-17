# TradeConnect Backend Run Guide

Panduan ini menjelaskan cara menjalankan semua service di repo ini, alur penggunaan,
endpoint penting, serta contoh request JSON yang sesuai dengan key backend sebenarnya.

## 1) Ringkasan service

| Service | Port | Tipe | Fungsi utama | Docs |
|---|---:|---|---|---|
| Gateway | 3000 | NestJS | Auth, proxy, rate limit | `/docs` |
| User Service | 3001 | NestJS | Register/login, UMKM, product | `/docs` |
| Readiness Service | 3002 | NestJS | Pricing & fraud scan | `/docs` |
| Matching Service | 8001 | FastAPI | HS classify, buyer matching | `/docs` |
| Comms Service | 8002 | FastAPI | Draft negosiasi RAG | `/docs` |
| ETL Worker | - | Celery | Ingest data & verification | - |
| Embedding Worker | - | Celery | Generate embedding product | - |
| Verification Worker | - | Celery | Verifikasi eksternal | - |
| Flower | 5555 | Monitoring | Monitor Celery queue | `/` |

## 2) Prasyarat

- Node.js 22+
- pnpm 9+
- Python 3.12+
- Docker Desktop
- `uv` untuk service Python

## 3) Environment

Copy file contoh lalu isi nilainya:

```powershell
Copy-Item .env.example .env
```

Yang paling penting:

- `JWT_SECRET`
- `DATABASE_URL`
- `BULL_REDIS_URL`
- `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` untuk Comms
- `OSS_RBA_API_KEY`, `INATRADE_API_KEY`, `UN_COMTRADE_API_KEY`, `BPS_API_KEY` bila fitur eksternal dipakai

## 4) Cara menjalankan

### Opsi A — Full stack via Docker

Paling mudah untuk semua service sekaligus:

```powershell
docker compose --profile full --profile workers --profile obs up -d --build
```

Lalu buka:

- Gateway docs: `http://localhost:3000/docs`
- User Service docs: `http://localhost:3001/docs`
- Readiness Service docs: `http://localhost:3002/docs`
- Matching Service docs: `http://localhost:8001/docs`
- Comms Service docs: `http://localhost:8002/docs`
- Bull Board: `http://localhost:3000/admin/queues`
- Flower: `http://localhost:5555`

### Opsi B — Development manual

#### 1. Nyalakan infra

```powershell
pnpm docker:infra
```

#### 2. Install dependency Node

```powershell
pnpm install
```

#### 3. Sync dependency Python

```powershell
cd services\matching-service
uv sync
cd ..\comms-service
uv sync
cd ..\etl-worker
uv sync
cd ..\..
```

#### 4. Jalankan migration

User Service:

```powershell
cd services\user-service
pnpm db:migrate
cd ..\..
```

Matching Service:

```powershell
cd services\matching-service
uv run alembic upgrade head
cd ..\..
```

#### 5. Jalankan service

Node services:

```powershell
pnpm --dir services/gateway dev
pnpm --dir services/user-service dev
pnpm --dir services/readiness-service dev
```

Python services:

```powershell
cd services\matching-service
uv run uvicorn matching_service.main:app --reload --port 8001

cd ..\comms-service
uv run uvicorn comms_service.main:app --reload --port 8002
```

Workers:

```powershell
cd services\matching-service
uv run celery -A matching_service.infrastructure.workers.celery_app worker -Q ai -l info --concurrency=2

cd ..\etl-worker
uv run celery -A etl_worker.celery_app worker -Q external -l info --concurrency=4
uv run celery -A etl_worker.celery_app worker -Q ingest -l info --concurrency=2
```

## 5) Penting: pola akses API

- **Gateway** dipakai untuk request publik.
- **User Service** menerima `x-user-id` dari gateway pada endpoint UMKM/product.
- **Readiness Service** punya route langsung di service, lalu gateway mem-forward ke sana.
- **Matching Service** dan **Comms Service** pakai body snake_case.

## 6) Auth flow

### Register user

Langsung ke User Service:

`POST http://localhost:3001/auth/register`

```json
{
  "email": "owner@kopigayo.id",
  "password": "KopiGayo!2026"
}
```

### Login

Via Gateway:

`POST http://localhost:3000/auth/login`

```json
{
  "email": "owner@kopigayo.id",
  "password": "KopiGayo!2026"
}
```

Response berisi:

- `accessToken`
- `refreshToken`
- `user.id`
- `user.email`
- `user.tier`

## 7) User Service

Docs:

- `http://localhost:3001/docs`

### 7.1 Create UMKM

Gateway:

`POST http://localhost:3000/umkm`

Body:

```json
{
  "legalName": "CV Kopi Gayo Nusantara",
  "nib": "1234567890123",
  "description": "Produsen kopi arabika specialty dari Takengon, Aceh Tengah."
}
```

### 7.2 Get UMKM saya

Gateway:

`GET http://localhost:3000/umkm/me`

### 7.3 Create product

Gateway:

`POST http://localhost:3000/umkm/{umkmId}/products`

Body:

```json
{
  "name": "Kopi Arabika Gayo Grade A",
  "description": "Kopi arabika specialty dari Aceh Tengah, proses semi-washed, cocok untuk pasar roastery premium.",
  "moq": 50,
  "monthlyCapacity": 10000,
  "priceMin": 5.5,
  "priceMax": 6.5,
  "hpp": 3.5,
  "photoUrls": [
    "https://storage.tradeconnect.id/products/gayo-grade-a-1.jpg",
    "https://storage.tradeconnect.id/products/gayo-grade-a-2.jpg"
  ]
}
```

Catatan:

- `hpp` diterima dari owner, tidak ditampilkan lagi di response.
- `priceMax` harus `>= priceMin`.

### 7.4 List product per UMKM

Langsung ke User Service:

`GET http://localhost:3001/umkm/{umkmId}/products`

Headers internal:

```http
x-user-id: <user-id>
x-request-id: <request-id>
```

## 8) Readiness Service

Docs:

- `http://localhost:3002/docs`

### 8.1 Pricing calculator

Gateway:

`POST http://localhost:3000/api/v1/readiness/pricing`

Direct service:

`POST http://localhost:3002/pricing/calculate`

Body:

```json
{
  "hpp": 3.5,
  "originCharges": 0.5,
  "qty": 500,
  "oceanFreight": 0.3,
  "insuranceRate": 0.002
}
```

Response key:

- `fobUnit`
- `fobTotal`
- `cfrTotal`
- `insuranceAmount`
- `cifTotal`
- `perUnitCIF`
- `benchmarkUnitValue`
- `pricingWarning`
- `marginEstimate`

### 8.2 Fraud scan

Gateway:

`POST http://localhost:3000/api/v1/readiness/fraud-scan`

Direct service:

`POST http://localhost:3002/fraud/scan`

Body:

```json
{
  "buyerId": "2c2d2c1b-5a7d-4d25-8bc3-e0bf7f2f2d11",
  "termsText": "Payment must be made in full by wire transfer. Please ignore the invoice if the amount is overpaid.",
  "contractText": "Goods will be shipped to a third-party warehouse before bank clearance is completed."
}
```

Response key:

- `riskLevel`
- `riskScore`
- `flags`
- `recommendation`

## 9) Matching Service

Docs:

- `http://localhost:8001/docs`

### 9.1 Buyer search

Gateway:

`POST http://localhost:3000/api/v1/matching/search`

Direct service:

`POST http://localhost:8001/api/v1/match`

Body:

```json
{
  "product_id": "5d9f2d9e-0f0f-4cb0-9d84-1d7a9ef5d8d7",
  "top_k": 5,
  "country_filter": ["DE", "NL", "JP"]
}
```

Response item:

- `buyer_id`
- `name`
- `country`
- `hs_codes`
- `credibility_score`
- `similarity_score`
- `distance`
- `explanation`
- `is_synthetic`

### 9.2 HS classify

Gateway:

`POST http://localhost:3000/api/v1/matching/classify-hs`

Direct service:

`POST http://localhost:8001/api/v1/hs-classifier/classify`

Body:

```json
{
  "description": "Kopi arabika roasted whole bean dari Gayo Aceh. Specialty grade, fermentasi 72 jam, dried natural.",
  "top_k": 3
}
```

Response key:

- `hs_code`
- `description`
- `confidence`
- `top_k`

## 10) Comms Service

Docs:

- `http://localhost:8002/docs`

### 10.1 Draft negosiasi

Gateway:

`POST http://localhost:3000/api/v1/negotiations/draft`

Direct service:

`POST http://localhost:8002/api/v1/negotiations/draft`

Body:

```json
{
  "inquiry_text": "Kami tertarik dengan kopi Gayo Anda. Bisakah Anda memberikan quotation untuk 500kg kopi roasted whole bean?",
  "product_id": "5d9f2d9e-0f0f-4cb0-9d84-1d7a9ef5d8d7",
  "buyer_id": "2c2d2c1b-5a7d-4d25-8bc3-e0bf7f2f2d11"
}
```

Response key:

- `draft_en`
- `strategy_id`
- `rationale_id`
- `warnings`
- `confidence`

## 11) Workers

### Matching embedding worker

Queue: `ai`

```powershell
cd services\matching-service
uv run celery -A matching_service.infrastructure.workers.celery_app worker -Q ai -l info --concurrency=2
```

### Verification worker

Queue: `external`

```powershell
cd services\etl-worker
uv run celery -A etl_worker.celery_app worker -Q external -l info --concurrency=4
```

### ETL worker

Queue: `ingest`

```powershell
cd services\etl-worker
uv run celery -A etl_worker.celery_app worker -Q ingest -l info --concurrency=2
```

### Flower

```powershell
docker compose up -d flower
```

## 12) Header yang sering dipakai

```http
Authorization: Bearer <accessToken>
x-request-id: <uuid>
x-user-id: <user-id>
x-tenant-id: <tenant-id>
x-user-tier: <free|premium>
```

## 13) Melihat database buyer

Tabel buyer dibuat saat container Postgres pertama kali start lewat
`infra/db/init.sql`. Tabel utama yang biasanya dicek:

- `buyer`: profil buyer/importer
- `buyer_embedding`: embedding buyer untuk fitur matching

### Opsi A — lewat terminal Docker

Pastikan Postgres sudah hidup:

```powershell
pnpm docker:infra
```

Masuk ke database:

```powershell
docker exec -it tc-postgres psql -U tc_user -d tradeconnect
```

Command penting di dalam `psql`:

```sql
\dt
\d buyer
\d buyer_embedding
SELECT COUNT(*) FROM buyer;
SELECT COUNT(*) FROM buyer_embedding;
```

Lihat 20 buyer pertama:

```sql
SELECT
  id,
  name,
  country,
  hs_codes,
  credibility_score,
  min_order_qty,
  is_active,
  is_synthetic,
  created_at
FROM buyer
ORDER BY created_at DESC
LIMIT 20;
```

Cari buyer berdasarkan negara:

```sql
SELECT id, name, country, hs_codes, credibility_score
FROM buyer
WHERE country = 'DE'
ORDER BY credibility_score DESC
LIMIT 20;
```

Cari buyer berdasarkan HS code:

```sql
SELECT id, name, country, hs_codes, credibility_score
FROM buyer
WHERE hs_codes && ARRAY['0901']
ORDER BY credibility_score DESC
LIMIT 20;
```

Lihat buyer synthetic saja:

```sql
SELECT id, name, country, hs_codes, credibility_score
FROM buyer
WHERE is_synthetic = TRUE
ORDER BY created_at DESC
LIMIT 20;
```

Keluar dari `psql`:

```sql
\q
```

### Opsi B — lewat DBeaver / DataGrip / TablePlus

Gunakan koneksi berikut:

```text
Host: localhost
Port: 5432
Database: tradeconnect
User: tc_user
Password: tc_pass_dev
Schema: public
```

Setelah connect, buka:

```text
tradeconnect -> public -> Tables -> buyer
tradeconnect -> public -> Tables -> buyer_embedding
```

### Jika tabel buyer kosong

Seed data synthetic buyer tanpa embedding:

```powershell
python scripts\seed-buyers-with-embeddings.py --count 50 --skip-embeddings
```

Atau seed ulang synthetic buyer dan hapus synthetic lama:

```powershell
python scripts\seed-buyers-with-embeddings.py --clear --count 200 --skip-embeddings
```

Jika ingin embedding juga, pastikan dependency Python ML sudah siap lalu pakai:

```powershell
python scripts\seed-buyers-with-embeddings.py --clear --count 200 --with-embeddings
```

### Kolom penting tabel buyer

- `id`: UUID buyer
- `name`: nama perusahaan/importer buyer
- `country`: kode negara 2 huruf, misalnya `DE`, `US`, `JP`
- `hs_codes`: daftar HS code yang diminati buyer
- `credibility_score`: skor kredibilitas buyer
- `min_order_qty`: minimum order quantity
- `description`: deskripsi kebutuhan/profil buyer
- `is_active`: status aktif
- `is_synthetic`: penanda data synthetic/demo
- `metadata`: data tambahan dalam JSON

## 14) Troubleshooting cepat

- **401/Unauthorized**: token belum dipasang atau `x-user-id` belum dikirim ke endpoint internal.
- **404 di Readiness via gateway**: pakai route gateway yang ada di guide ini atau panggil service langsung.
- **DB error**: pastikan `pnpm docker:infra` atau `docker compose up -d postgres redis` sudah jalan dan migrasi sudah diterapkan.
- **Comms error**: isi minimal `ANTHROPIC_API_KEY` atau `OPENAI_API_KEY`.
- **Matching lambat**: model embedding pertama kali akan butuh waktu download.

## 15) Rute dokumen Swagger

- Gateway: `http://localhost:3000/docs`
- User Service: `http://localhost:3001/docs`
- Readiness Service: `http://localhost:3002/docs`
- Matching Service: `http://localhost:8001/docs`
- Comms Service: `http://localhost:8002/docs`
