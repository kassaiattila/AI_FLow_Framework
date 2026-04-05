#!/bin/bash
# AIFlow L0 Smoke Test — MANDATORY before and after EVERY development cycle
# Target: <30 seconds, checks health + 4 core endpoints + source=backend
# Usage: ./scripts/smoke_test.sh [port]
# Default port: 8102

set -e

PORT=${1:-8102}
BASE="http://localhost:$PORT"
PASS=0
FAIL=0

echo "=== AIFlow L0 Smoke Test ==="
echo "Target: $BASE"
echo ""

# 1. Get auth token
TOKEN=$(curl -sf -X POST "$BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@bestix.hu","password":"admin"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['token'])" 2>/dev/null) || {
  echo "FAIL: Auth login failed — is the API running on port $PORT?"
  exit 1
}
echo "OK: Auth token acquired"
PASS=$((PASS+1))

# 2. Health check (root-level + /api/v1/health)
curl -sf "$BASE/health" \
  | python -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='ready', f'Health: {d}'" 2>/dev/null && {
  echo "OK: /health"
  PASS=$((PASS+1))
} || {
  echo "FAIL: /health"
  FAIL=$((FAIL+1))
}

# /api/v1/health is not a separate endpoint — health is at /health (root)
# Kept as a note: if v1 health is added later, enable this check

# 3. Core endpoints (source: backend check)
for ep in documents emails rag/collections services/; do
  curl -sf -H "Authorization: Bearer $TOKEN" "$BASE/api/v1/$ep" \
    | python -c "import sys,json; d=json.load(sys.stdin); assert d.get('source')=='backend', f'No source=backend: {list(d.keys())[:5]}'" 2>/dev/null && {
    echo "OK: /api/v1/$ep (source=backend)"
    PASS=$((PASS+1))
  } || {
    echo "FAIL: /api/v1/$ep"
    FAIL=$((FAIL+1))
  }
done

# 4. v1.2.1 endpoints (quality, notifications, pipelines, intent-schemas)
for ep in quality/overview notifications/in-app pipelines/templates/list intent-schemas; do
  curl -sf -H "Authorization: Bearer $TOKEN" "$BASE/api/v1/$ep" \
    | python -c "import sys,json; d=json.load(sys.stdin); assert d.get('source')=='backend', f'No source=backend: {list(d.keys())[:5]}'" 2>/dev/null && {
    echo "OK: /api/v1/$ep (source=backend)"
    PASS=$((PASS+1))
  } || {
    echo "WARN: /api/v1/$ep (may not be deployed yet)"
  }
done

# 4. Summary
echo ""
echo "=== RESULTS ==="
echo "PASS: $PASS | FAIL: $FAIL"

if [ $FAIL -gt 0 ]; then
  echo "SMOKE TEST: FAILED — $FAIL endpoint(s) broken"
  exit 1
fi

echo "SMOKE TEST: ALL PASS"
exit 0
