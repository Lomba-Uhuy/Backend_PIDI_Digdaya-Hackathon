#!/usr/bin/env bash
# Wait until every TradeConnect service responds on /health.
set -euo pipefail

ENDPOINTS=(
  "http://localhost:3000/health"   # gateway
  "http://localhost:3001/health"   # user-service
  "http://localhost:3002/health"   # readiness-service
  "http://localhost:8001/health"   # matching-service
  "http://localhost:8002/health"   # comms-service
)
DEADLINE=$(( $(date +%s) + 120 ))

for url in "${ENDPOINTS[@]}"; do
  echo -n "Checking $url ... "
  while true; do
    if curl -fsS --max-time 2 "$url" > /dev/null 2>&1; then
      echo "OK"
      break
    fi
    if [ "$(date +%s)" -gt "$DEADLINE" ]; then
      echo "TIMEOUT"
      exit 1
    fi
    sleep 2
  done
done

echo "All services healthy."