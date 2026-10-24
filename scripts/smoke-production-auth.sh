#!/usr/bin/env bash
# Post-deploy smoke test. Usage:
#   BASE=https://your-app.vercel.app EMAIL=... PASSWORD=... ./scripts/smoke-production-auth.sh
set -euo pipefail

BASE="${BASE:?Set BASE to your Vercel URL (same origin as NEXT_PUBLIC_API_URL)}"
EMAIL="${EMAIL:?Set EMAIL}"
PASSWORD="${PASSWORD:?Set PASSWORD}"
API_DIRECT="${API_DIRECT:-}"

COOKIES="$(mktemp)"
trap 'rm -f "$COOKIES"' EXIT

if [[ -n "$API_DIRECT" ]]; then
  echo "Checking Render health at $API_DIRECT/health ..."
  curl -sf "$API_DIRECT/health" | grep -q '"status":"ok"' || { echo "Render health failed"; exit 1; }
fi

echo "Login via $BASE ..."
curl -sf -c "$COOKIES" -X POST "$BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" >/dev/null

echo "Refresh session ..."
REFRESH_BODY="$(curl -sf -b "$COOKIES" -c "$COOKIES" -X POST "$BASE/api/v1/auth/refresh")"

TOKEN="$(printf '%s' "$REFRESH_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")"

echo "Admin dashboard ..."
curl -sf -H "Authorization: Bearer $TOKEN" "$BASE/api/v1/admin/dashboard" >/dev/null

echo "OK — login, refresh, and admin dashboard succeeded."
