# TradeConnect — Demo Cheat Sheet

## Service URLs

| Service | Internal | Exposed Port |
|---------|----------|--------------|
| Gateway (semua request masuk sini) | `http://gateway:3000` | **3000** |
| User Service | `http://user-service:3001` | 3001 |
| Readiness Service | `http://readiness-service:3002` | 3002 |
| Matching Service | `http://matching-service:8001` | 8001 |
| Comms Service | `http://comms-service:8002` | 8002 |
| Flower (Celery monitor) | — | 5555 |

**Base API:** `http://localhost:3000/api/v1`
**Swagger UI:** `http://localhost:3000/docs`

---

## Kredensial Demo

```
Email   : demo@tradeconnect.id
Password: DemoPass123!
NIB     : 1234567890  (10 digit → sandbox mode)
```

---

## Semua Endpoint Aktif

### Auth (Public)
```bash
# Register
curl -X POST http://localhost:3000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@tradeconnect.id","password":"DemoPass123!","name":"Demo UMKM"}'

# Login → ambil accessToken
curl -X POST http://localhost:3000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@tradeconnect.id","password":"DemoPass123!"}'
```

**Semua endpoint di bawah butuh header:** `Authorization: Bearer <accessToken>`

---

### NIB Verification
```bash
curl -X POST http://localhost:3000/api/v1/verify-nib \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"nib":"1234567890"}'
```
- NIB < 13 digit → sandbox mode (`sandbox_mode: true`)
- Response time target: **< 5 detik**

---

### HS Code Classifier
```bash
curl -X POST http://localhost:3000/api/v1/matching/classify-hs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description":"kursi rotan anyaman ekspor premium untuk pasar internasional","top_k":3}'
```
- Produk rotan → HS Code ~4602 atau 9401.61
- Response time target: **< 5 detik**

---

### Buyer Matching
```bash
# By product_id (setelah buat produk)
curl -X POST http://localhost:3000/api/v1/matching/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"product_id":"<PRODUCT_ID>","top_k":5,"country_filter":["JP"]}'
```
- Response time target: **< 3 detik**
- Pastikan buyer sudah di-seed (jalankan `buyer-seeding` task di Celery)

---

### Generate Email Reply
```bash
curl -X POST http://localhost:3000/api/v1/negotiations/generate-reply \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "importer_email": "Please send price list, MOQ, and lead time for 500 rattan chairs to Osaka.",
    "product_id": "<PRODUCT_ID>"
  }'
```
- Response time target: **< 10 detik**
- Butuh `ANTHROPIC_API_KEY` di `.env`

---

### Kalkulasi FOB–CIF
```bash
curl -X POST http://localhost:3000/api/v1/calculate-price \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hpp": 3.50,
    "originCharges": 0.50,
    "qty": 500,
    "oceanFreight": 350,
    "insuranceAmount": 25,
    "exportDuty": 0,
    "profitMarginPct": 20,
    "hsCode": "4602",
    "exchangeRate": 16000
  }'
```
- Formula: FOB = HPP + margin + biaya domestik → CFR = FOB + freight → CIF = CFR + asuransi
- `pricingWarning` muncul jika CIF >30% dari BPS benchmark

---

### Red Flag Check
```bash
# Skenario buyer AMAN (ekspektasi: LOW)
curl -X POST http://localhost:3000/api/v1/check-red-flag \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "buyerProfile": {
      "companyName": "Osaka Craft Imports Co. Ltd.",
      "countryCode": "JP",
      "requestedSampleBeforeContract": false,
      "requestedPaymentOutsidePlatform": false
    },
    "communicationHistory": [
      {"sender":"buyer","message":"Please send product catalog.","sentAt":"2026-05-28T09:00:00Z","channel":"email"}
    ]
  }'

# Skenario buyer BERISIKO (ekspektasi: HIGH)
curl -X POST http://localhost:3000/api/v1/check-red-flag \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "buyerProfile": {
      "companyName": "Mystery Trader LLC",
      "countryCode": "AE",
      "requestedSampleBeforeContract": true,
      "requestedPaymentOutsidePlatform": false
    },
    "communicationHistory": [
      {"sender":"buyer","message":"Send sample first before we sign any contract.","sentAt":"2026-05-29T08:00:00Z","channel":"whatsapp"},
      {"sender":"buyer","message":"This is urgent! Reply within 24 hours!","sentAt":"2026-05-29T10:00:00Z","channel":"whatsapp"},
      {"sender":"buyer","message":"Pay agent commission via bitcoin.","sentAt":"2026-05-29T11:00:00Z","channel":"whatsapp"}
    ]
  }'
```
- Flag yang dicek: negara high-risk, sampel sebelum kontrak, komunikasi terburu-buru, bayar di luar platform

---

## Dry Run & Stress Test

```bash
# Dry run end-to-end (semua step)
BASE_URL=http://localhost:3000/api/v1 \
  DEMO_EMAIL=demo@tradeconnect.id \
  DEMO_PASSWORD=DemoPass123! \
  bash scripts/dry-run.sh

# Stress test (10x setiap endpoint)
TOKEN=<accessToken> \
  BASE_URL=http://localhost:3000/api/v1 \
  bash scripts/stress-test.sh
```

---

## Multi-Tenant Isolation Check

UMKM A tidak boleh bisa akses data UMKM B:
```bash
# Login sebagai UMKM A → ambil token A
TOKEN_A=$(curl -s -X POST .../auth/login -d '{"email":"umkm_a@...","password":"..."}' | python3 -c "import sys,json; print(json.load(sys.stdin)['accessToken'])")

# Ambil UMKM ID milik B dulu (misal dari DB)
UMKM_B_ID="<uuid-milik-B>"

# Coba akses produk B dengan token A → harus 403 atau data kosong
curl -X GET http://localhost:3000/api/v1/umkm/$UMKM_B_ID/products \
  -H "Authorization: Bearer $TOKEN_A"
```

---

## Langkah Restart Jika Server Crash

```bash
# Restart semua service
docker compose restart

# Restart satu service saja
docker compose restart gateway
docker compose restart readiness-service
docker compose restart matching-service
docker compose restart comms-service

# Lihat logs realtime
docker compose logs -f gateway
docker compose logs -f readiness-service

# Full restart (rebuild)
docker compose down && docker compose --profile full up -d

# Cek status semua service
docker compose ps
```

---

## Troubleshooting Cepat

| Problem | Solusi |
|---------|--------|
| 401 Unauthorized | Token expired → login ulang |
| Buyer matching return 0 | Jalankan buyer-seeding task di Celery Flower (port 5555) |
| generate-reply timeout | Cek `ANTHROPIC_API_KEY` di `.env`, pastikan tidak kosong |
| NIB verify error | Normal jika OSS RBA down — `sandbox_mode: true` sudah aktif |
| Benchmark `null` | Trade data belum di-seed → jalankan BPS ETL task |
| 500 Internal Server Error | Cek `docker compose logs <service>` |
| Database connection error | `docker compose restart postgres` lalu tunggu healthcheck |

---

## Endpoint Status Check (One-liner)

```bash
TOKEN=$(curl -s -X POST http://localhost:3000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@tradeconnect.id","password":"DemoPass123!"}' | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('accessToken',''))")

for ep in "verify-nib|{\"nib\":\"1234567890\"}" \
          "calculate-price|{\"hpp\":3.5,\"originCharges\":0.5,\"qty\":100,\"oceanFreight\":200}" \
          "check-red-flag|{\"buyerProfile\":{\"companyName\":\"Test\",\"countryCode\":\"JP\"},\"communicationHistory\":[{\"message\":\"Hello\"}]}" \
          "matching/classify-hs|{\"description\":\"kursi rotan ekspor\",\"top_k\":1}" \
          "negotiations/classify-intent|{\"email_text\":\"Please send price list\"}"; do
  IFS='|' read -r path body <<< "$ep"
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "http://localhost:3000/api/v1/$path" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" -d "$body")
  echo "$code  /api/v1/$path"
done
```
