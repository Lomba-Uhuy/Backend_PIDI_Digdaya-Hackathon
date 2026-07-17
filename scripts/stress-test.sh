#!/usr/bin/env bash
# =============================================================================
# TradeConnect — Stress Test Ringan (10x setiap endpoint)
# Usage: BASE_URL=https://your-domain.com TOKEN=<jwt> bash scripts/stress-test.sh
# =============================================================================

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3000/api/v1}"
TOKEN="${TOKEN:-}"
ITERATIONS=10

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

if [[ -z "$TOKEN" ]]; then
  echo "Usage: TOKEN=<jwt> BASE_URL=<url> bash scripts/stress-test.sh"
  echo "Get token: curl -s -X POST BASE_URL/auth/login -H 'Content-Type: application/json' -d '{...}' | python3 -c \"import sys,json; print(json.load(sys.stdin)['accessToken'])\""
  exit 1
fi

AUTH=(-H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")

pass=0; fail=0

run_n() {
  local label="$1"; local n="$2"; shift 2
  local ok=0; local ko=0; local total_ms=0

  for ((i=1; i<=n; i++)); do
    start=$(date +%s%3N)
    code=$(curl -s -o /dev/null -w "%{http_code}" "$@")
    end=$(date +%s%3N)
    total_ms=$(( total_ms + end - start ))
    if [[ "$code" -ge 200 && "$code" -lt 300 ]]; then ((ok++)); else ((ko++)); fi
  done

  avg=$(( total_ms / n ))
  if [[ "$ko" -eq 0 ]]; then
    echo -e "${GREEN}[PASS]${NC} $label  ${n}/${n} OK  avg=${avg}ms"
    pass=$((pass+1))
  else
    echo -e "${RED}[FAIL]${NC} $label  ${ok}/${n} OK, ${ko} failed  avg=${avg}ms"
    fail=$((fail+1))
  fi
}

echo ""
echo "============================="
echo "  Stress Test ($ITERATIONS iterations per endpoint)"
echo "  Base URL: $BASE_URL"
echo "============================="
echo ""

run_n "POST /verify-nib" $ITERATIONS \
  -X POST "$BASE_URL/verify-nib" "${AUTH[@]}" \
  -d '{"nib":"1234567890"}'

run_n "POST /calculate-price" $ITERATIONS \
  -X POST "$BASE_URL/calculate-price" "${AUTH[@]}" \
  -d '{"hpp":3.5,"originCharges":0.5,"qty":500,"oceanFreight":350,"profitMarginPct":20,"hsCode":"4602"}'

run_n "POST /check-red-flag" $ITERATIONS \
  -X POST "$BASE_URL/check-red-flag" "${AUTH[@]}" \
  -d '{"buyerProfile":{"companyName":"Test Buyer","countryCode":"JP"},"communicationHistory":[{"message":"Please send catalog","sentAt":"2026-05-28T09:00:00Z"}]}'

run_n "POST /negotiations/classify-intent" $ITERATIONS \
  -X POST "$BASE_URL/negotiations/classify-intent" "${AUTH[@]}" \
  -d '{"email_text":"We would like to request a quotation for 500 units with MOQ and lead time."}'

run_n "POST /matching/classify-hs" $ITERATIONS \
  -X POST "$BASE_URL/matching/classify-hs" "${AUTH[@]}" \
  -d '{"description":"kursi rotan anyaman ekspor premium","top_k":3}'

echo ""
echo "============================="
if [[ "$fail" -eq 0 ]]; then
  echo -e "  Result: ${GREEN}ALL PASS${NC} ($pass endpoints)"
else
  echo -e "  Result: ${RED}$fail FAILED${NC}, $pass passed"
fi
echo "============================="
echo ""

exit "$fail"
