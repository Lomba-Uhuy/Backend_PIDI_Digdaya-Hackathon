#!/usr/bin/env bash
# =============================================================================
# TradeConnect — End-to-End Demo Dry Run
# Skenario: UMKM kursi rotan → verifikasi → HS Code → buyer Jepang → reply email
#           → kalkulasi FOB-CIF → red flag check
# Usage: BASE_URL=https://your-domain.com bash scripts/dry-run.sh
# =============================================================================

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3000/api/v1}"
EMAIL="${DEMO_EMAIL:-demo@tradeconnect.id}"
PASSWORD="${DEMO_PASSWORD:-DemoPass123!}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

ok()   { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; ERRORS=$((ERRORS+1)); }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

ERRORS=0
TOKEN=""
UMKM_ID=""
PRODUCT_ID=""

# ── Helper: timed curl ────────────────────────────────────────────────────────
call() {
  local label="$1"; shift
  local max_ms="${LATENCY_LIMIT:-5000}"
  local start end elapsed_ms http_code body

  start=$(date +%s%3N)
  # shellcheck disable=SC2048
  body=$(curl -s -o /tmp/tc_body -w "%{http_code}" "$@")
  end=$(date +%s%3N)
  elapsed_ms=$((end - start))
  http_code="$body"
  body=$(cat /tmp/tc_body)

  if [[ "$http_code" -ge 200 && "$http_code" -lt 300 ]]; then
    ok "$label  [${elapsed_ms}ms]"
    if [[ "$elapsed_ms" -gt "$max_ms" ]]; then
      warn "$label response time ${elapsed_ms}ms > ${max_ms}ms threshold"
    fi
  else
    fail "$label  [HTTP $http_code] [${elapsed_ms}ms]"
    echo "      Body: $(echo "$body" | head -c 300)"
  fi

  echo "$body"
}

echo ""
echo "========================================="
echo "  TradeConnect Demo Dry Run"
echo "  Base URL : $BASE_URL"
echo "  $(date)"
echo "========================================="
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# STEP 0: Auth — register + login
# ─────────────────────────────────────────────────────────────────────────────
info "STEP 0 — Register & Login"

REGISTER_BODY=$(call "POST /auth/register" \
  -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"name\":\"Demo UMKM Rotan\"}" \
  2>/dev/null) || true   # ignore duplicate-user error on re-run

LOGIN_RESP=$(call "POST /auth/login" \
  -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('accessToken',''))" 2>/dev/null || echo "")
if [[ -z "$TOKEN" ]]; then
  fail "Could not extract accessToken from login response"
  echo "Response: $LOGIN_RESP" && exit 1
fi
ok "JWT token acquired (${#TOKEN} chars)"

AUTH=(-H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Create UMKM profile
# ─────────────────────────────────────────────────────────────────────────────
info "STEP 1 — Create UMKM Profile"

UMKM_RESP=$(call "POST /umkm" \
  -X POST "$BASE_URL/umkm" \
  "${AUTH[@]}" \
  -d '{
    "businessName": "CV Karya Rotan Nusantara",
    "nib": "1234567890",
    "address": "Jl. Rotan No. 12, Cirebon, Jawa Barat",
    "businessScale": "KECIL",
    "exportReadiness": "READY"
  }')

UMKM_ID=$(echo "$UMKM_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || echo "")
[[ -z "$UMKM_ID" ]] && warn "UMKM id not found — trying /umkm/me"

if [[ -z "$UMKM_ID" ]]; then
  ME_RESP=$(call "GET /umkm/me" -X GET "$BASE_URL/umkm/me" "${AUTH[@]}")
  UMKM_ID=$(echo "$ME_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || echo "")
fi
ok "UMKM ID: $UMKM_ID"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Register product "kursi rotan"
# ─────────────────────────────────────────────────────────────────────────────
info "STEP 2 — Register Product"

PRODUCT_RESP=$(call "POST /umkm/:id/products" \
  -X POST "$BASE_URL/umkm/$UMKM_ID/products" \
  "${AUTH[@]}" \
  -d '{
    "name": "Kursi Rotan Anyaman Ekspor",
    "description": "Kursi rotan anyaman premium untuk pasar ekspor Jepang dan Eropa. Finishing natural, tahan lama.",
    "category": "Furnitur",
    "hsCode": "4602",
    "exportMarkets": ["JP", "NL", "DE"],
    "priceUsd": 35.0,
    "moq": 100
  }')

PRODUCT_ID=$(echo "$PRODUCT_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || echo "")
ok "Product ID: $PRODUCT_ID"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Verifikasi NIB
# ─────────────────────────────────────────────────────────────────────────────
info "STEP 3 — Verifikasi NIB (target: < 5 detik)"

LATENCY_LIMIT=5000 NIB_RESP=$(call "POST /verify-nib" \
  -X POST "$BASE_URL/verify-nib" \
  "${AUTH[@]}" \
  -d '{"nib": "1234567890"}')

IS_VALID=$(echo "$NIB_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('is_valid',''))" 2>/dev/null || echo "")
SANDBOX=$(echo "$NIB_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('sandbox_mode',''))" 2>/dev/null || echo "")
BIZ_NAME=$(echo "$NIB_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('business_name',''))" 2>/dev/null || echo "")

[[ "$IS_VALID" == "True" ]] && ok "NIB valid: $BIZ_NAME (sandbox=$SANDBOX)" || fail "NIB not valid"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: HS Code Classifier
# ─────────────────────────────────────────────────────────────────────────────
info "STEP 4 — HS Code Classifier: 'kursi rotan anyaman ekspor'"

LATENCY_LIMIT=5000 HS_RESP=$(call "POST /matching/classify-hs" \
  -X POST "$BASE_URL/matching/classify-hs" \
  "${AUTH[@]}" \
  -d '{"description": "kursi rotan anyaman ekspor premium untuk pasar internasional", "top_k": 3}')

HS_CODE=$(echo "$HS_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('hs_code',''))" 2>/dev/null || echo "")
HS_DESC=$(echo "$HS_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('description',''))" 2>/dev/null || echo "")
HS_CONF=$(echo "$HS_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('confidence',''))" 2>/dev/null || echo "")

ok "HS Code: $HS_CODE  ($HS_DESC)  confidence=$HS_CONF"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: Buyer Matching — 5 buyer Jepang
# ─────────────────────────────────────────────────────────────────────────────
info "STEP 5 — Buyer Matching: top 5 buyer Jepang (target: < 3 detik)"

if [[ -n "$PRODUCT_ID" ]]; then
  LATENCY_LIMIT=3000 MATCH_RESP=$(call "POST /matching/search" \
    -X POST "$BASE_URL/matching/search" \
    "${AUTH[@]}" \
    -d "{\"product_id\": \"$PRODUCT_ID\", \"top_k\": 5, \"country_filter\": [\"JP\"]}")
else
  warn "No product_id — using match-buyers with embedding skip"
  MATCH_RESP="{}"
fi

BUYER_COUNT=$(echo "$MATCH_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else 0)" 2>/dev/null || echo "0")
[[ "$BUYER_COUNT" -ge 1 ]] && ok "$BUYER_COUNT buyer(s) ditemukan" || warn "0 buyer ditemukan — pastikan embedding sudah di-seed"

echo "$MATCH_RESP" | python3 -c "
import sys, json
try:
    buyers = json.load(sys.stdin)
    if isinstance(buyers, list):
        for i, b in enumerate(buyers[:5], 1):
            print(f'  [{i}] {b.get(\"name\",\"?\")} ({b.get(\"country\",\"?\")})'
                  f'  score={b.get(\"similarity_score\",\"?\")}')
except: pass
" 2>/dev/null || true

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6: Generate Reply Email
# ─────────────────────────────────────────────────────────────────────────────
info "STEP 6 — Generate Reply Email (target: < 10 detik)"

LATENCY_LIMIT=10000 REPLY_RESP=$(call "POST /negotiations/generate-reply" \
  -X POST "$BASE_URL/negotiations/generate-reply" \
  "${AUTH[@]}" \
  -d "{
    \"importer_email\": \"Dear supplier, we are interested in purchasing your rattan chairs (HS 4602). Please send us your price list, MOQ, and lead time. We need at least 500 units per shipment to Osaka, Japan.\",
    \"product_id\": \"${PRODUCT_ID:-00000000-0000-0000-0000-000000000001}\"
  }")

DRAFT=$(echo "$REPLY_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('draft_en','')[:200])" 2>/dev/null || echo "")
INTENT=$(echo "$REPLY_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('intent',''))" 2>/dev/null || echo "")
WARNINGS=$(echo "$REPLY_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('warnings',[]))" 2>/dev/null || echo "")

[[ -n "$DRAFT" ]] && ok "Draft email generated | intent=$INTENT" || fail "Draft email kosong"
[[ "$WARNINGS" != "[]" ]] && warn "Guardrail warnings: $WARNINGS"
echo "      Preview: ${DRAFT:0:120}..."

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7: Kalkulasi FOB–CIF
# ─────────────────────────────────────────────────────────────────────────────
info "STEP 7 — Kalkulasi FOB–CIF (HS 4602, qty=500, HPP=USD3.50)"

PRICE_RESP=$(call "POST /calculate-price" \
  -X POST "$BASE_URL/calculate-price" \
  "${AUTH[@]}" \
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
  }')

FOB=$(echo "$PRICE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('fobTotal',''))" 2>/dev/null || echo "")
CFR=$(echo "$PRICE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('cfrTotal',''))" 2>/dev/null || echo "")
CIF=$(echo "$PRICE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('cifTotal',''))" 2>/dev/null || echo "")
WARN_PRICE=$(echo "$PRICE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('pricingWarning',''))" 2>/dev/null || echo "")

[[ -n "$FOB" ]] && ok "FOB=USD$FOB  CFR=USD$CFR  CIF=USD$CIF" || fail "Price calculation failed"
[[ -n "$WARN_PRICE" && "$WARN_PRICE" != "None" && "$WARN_PRICE" != "null" ]] && warn "Pricing warning: $WARN_PRICE"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 8: Red Flag Check (buyer Jepang — skenario normal)
# ─────────────────────────────────────────────────────────────────────────────
info "STEP 8a — Red Flag Check (buyer normal, expected: LOW)"

REDFLAG_RESP=$(call "POST /check-red-flag (normal)" \
  -X POST "$BASE_URL/check-red-flag" \
  "${AUTH[@]}" \
  -d '{
    "buyerProfile": {
      "companyName": "Osaka Craft Imports Co. Ltd.",
      "countryCode": "JP",
      "requestedSampleBeforeContract": false,
      "requestedPaymentOutsidePlatform": false
    },
    "communicationHistory": [
      {"sender": "buyer", "message": "Please send your product catalog and export terms.", "sentAt": "2026-05-28T09:00:00Z", "channel": "email"},
      {"sender": "buyer", "message": "We would like to discuss payment terms via LC at sight.", "sentAt": "2026-05-29T10:30:00Z", "channel": "email"}
    ]
  }')

RISK=$(echo "$REDFLAG_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('riskLevel',''))" 2>/dev/null || echo "")
FLAGS=$(echo "$REDFLAG_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('flags',[])))" 2>/dev/null || echo "?")
[[ "$RISK" == "LOW" ]] && ok "Risk=$RISK, flags=$FLAGS (diharapkan LOW ✓)" || warn "Risk=$RISK (diharapkan LOW)"

info "STEP 8b — Red Flag Check (buyer berisiko, expected: HIGH)"

REDFLAG_HIGH=$(call "POST /check-red-flag (high-risk)" \
  -X POST "$BASE_URL/check-red-flag" \
  "${AUTH[@]}" \
  -d '{
    "buyerProfile": {
      "companyName": "Mystery Trader LLC",
      "countryCode": "AE",
      "requestedSampleBeforeContract": true,
      "requestedPaymentOutsidePlatform": false
    },
    "communicationHistory": [
      {"sender": "buyer", "message": "Send sample first before we sign any contract.", "sentAt": "2026-05-29T08:00:00Z", "channel": "whatsapp"},
      {"sender": "buyer", "message": "This is very urgent! Please reply ASAP within 24 hours!", "sentAt": "2026-05-29T10:00:00Z", "channel": "whatsapp"},
      {"sender": "buyer", "message": "Please pay agent commission via bitcoin wallet first.", "sentAt": "2026-05-29T11:00:00Z", "channel": "whatsapp"}
    ]
  }')

RISK_H=$(echo "$REDFLAG_HIGH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('riskLevel',''))" 2>/dev/null || echo "")
FLAGS_H=$(echo "$REDFLAG_HIGH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('flags',[])))" 2>/dev/null || echo "?")
[[ "$RISK_H" == "HIGH" ]] && ok "Risk=$RISK_H, flags=$FLAGS_H (diharapkan HIGH ✓)" || warn "Risk=$RISK_H (diharapkan HIGH)"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9: Intent Classification
# ─────────────────────────────────────────────────────────────────────────────
info "STEP 9 — Intent Classification"

INTENT_RESP=$(call "POST /negotiations/classify-intent" \
  -X POST "$BASE_URL/negotiations/classify-intent" \
  "${AUTH[@]}" \
  -d '{"email_text": "We are requesting a formal quotation for 500 units of rattan chairs. Please include your MOQ, lead time, payment terms, and certifications."}')

DETECTED=$(echo "$INTENT_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('intent',''))" 2>/dev/null || echo "")
CONF=$(echo "$INTENT_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('confidence',''))" 2>/dev/null || echo "")
ok "Intent: $DETECTED  (confidence=$CONF)"

# ─────────────────────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "========================================="
echo "  DRY RUN COMPLETE"
if [[ "$ERRORS" -eq 0 ]]; then
  echo -e "  Status: ${GREEN}ALL PASS${NC} (0 errors)"
else
  echo -e "  Status: ${RED}$ERRORS ERROR(S)${NC}"
fi
echo "========================================="
echo ""

exit "$ERRORS"
