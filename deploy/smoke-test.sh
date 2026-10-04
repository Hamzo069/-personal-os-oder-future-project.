#!/usr/bin/env sh
# End-to-end check of a running stack through its public entry point:
# register -> upload a receipt -> wait for extraction -> confirm -> dashboard -> refresh cookie.
#
#   BASE_URL=http://localhost:8080 sh deploy/smoke-test.sh
#   BASE_URL=https://localhost CURL_INSECURE=1 sh deploy/smoke-test.sh   # self-signed certificate
#
# Needs curl and python3 (set PYTHON=python where there is no python3, e.g. Git Bash on Windows).
# Exits non-zero on the first failing step.
set -eu

BASE_URL="${BASE_URL:-http://localhost:8080}"
API="$BASE_URL/api/v1"
RECEIPT="${RECEIPT:-$(dirname "$0")/../apps/web/e2e/receipt.png}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
CURL="curl -sS --max-time 20"
[ "${CURL_INSECURE:-0}" = "1" ] && CURL="$CURL -k"

json() { "${PYTHON:-python3}" -c "import json,sys; print(json.load(sys.stdin)$1)"; }
step() { printf '%-28s' "$1"; }

step "web app"
[ "$($CURL -o /dev/null -w '%{http_code}' "$BASE_URL/")" = "200" ] && echo ok

step "register"
EMAIL="smoke-$(date +%s)@example.com"
TOKEN=$($CURL -c "$TMP/cookies" -X POST "$API/auth/register" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"smoke-test-pass-1\",\"name\":\"Smoke\"}" | json "['access_token']")
AUTH="Authorization: Bearer $TOKEN"
echo ok

step "upload receipt"
RID=$($CURL -X POST "$API/receipts" -H "$AUTH" -F "file=@$RECEIPT;type=image/png" | json "['id']")
echo ok

step "extraction"
STATUS=""
for _ in $(seq 1 30); do
  STATUS=$($CURL "$API/receipts/$RID" -H "$AUTH" | json "['status']")
  [ "$STATUS" = "extracted" ] && break
  [ "$STATUS" = "failed" ] && { echo "failed"; exit 1; }
  sleep 1
done
[ "$STATUS" = "extracted" ] || { echo "timed out ($STATUS)"; exit 1; }
echo ok

step "confirm receipt"
CATEGORY=$($CURL "$API/categories" -H "$AUTH" | json "[0]['id']")
$CURL -f -o /dev/null -X POST "$API/receipts/$RID/confirm" -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"date\":\"2026-09-12\",\"merchant\":\"REWE\",\"amount\":\"22.75\",\"currency\":\"EUR\",\"vat_rate\":\"7\",\"category_id\":\"$CATEGORY\"}"
echo ok

step "receipt file"
[ "$($CURL -o /dev/null -w '%{http_code}' "$API/receipts/$RID/file" -H "$AUTH")" = "200" ] && echo ok

step "dashboard"
TOTAL=$($CURL "$API/insights/summary" -H "$AUTH" | json "['total']")
[ "$TOTAL" = "22.75" ] || { echo "unexpected total $TOTAL"; exit 1; }
echo ok

step "refresh cookie"
[ "$($CURL -b "$TMP/cookies" -o /dev/null -w '%{http_code}' -X POST "$API/auth/refresh")" = "200" ] && echo ok

echo "stack smoke test passed for $BASE_URL"
