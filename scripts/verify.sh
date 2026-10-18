#!/usr/bin/env bash
# Smoke-test a running ThreatGlobe stack (make demo / docker compose up).
#
#   scripts/verify.sh                 # frontend :8080, backend :8000
#   FRONTEND_URL=http://localhost:5173 scripts/verify.sh
#   scripts/verify.sh --e2e           # also run the Playwright browser suite
set -uo pipefail

FRONTEND_URL="${FRONTEND_URL:-http://localhost:8080}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0
FAIL=0

ok() { echo "  PASS  $1"; PASS=$((PASS + 1)); }
bad() { echo "  FAIL  $1"; FAIL=$((FAIL + 1)); }
check() { if eval "$2" >/dev/null 2>&1; then ok "$1"; else bad "$1"; fi; }
json() { curl -fsS --max-time 10 "$1"; }

echo "ThreatGlobe verification · frontend=$FRONTEND_URL backend=$BACKEND_URL"

echo "[1] waiting for services"
for _ in $(seq 1 60); do curl -fsS "$BACKEND_URL/health" >/dev/null 2>&1 && break; sleep 1; done
check "backend /health" "json $BACKEND_URL/health | grep -q '\"ok\"'"
check "frontend serves the app" "curl -fsS $FRONTEND_URL/ | grep -q '<div id=\"root\">'"

echo "[2] REST API (via the frontend proxy, same origin as the browser)"
for path in /health /api/status /api/stats "/api/events?limit=5" /api/countries /api/ports /api/honeypots /api/timeline; do
  check "GET $path -> 200" "curl -fsS -o /dev/null $FRONTEND_URL$path"
done
STATUS="$(json "$FRONTEND_URL/api/status")"
check "status reports DEMO source" "echo '$STATUS' | grep -q '\"mode\":\"demo\"'"
check "PUBLIC_MODE is on" "echo '$STATUS' | grep -q '\"public_mode\":true'"
check "status exposes no Elasticsearch settings/secrets" "! echo '$STATUS' | grep -qiE 'elasticsearch|password|secret'"
FIRST_ID="$(json "$FRONTEND_URL/api/events?limit=1" | python3 -c 'import json,sys; print(json.load(sys.stdin)["events"][0]["id"])')"
check "GET /api/events/{id} -> 200" "curl -fsS -o /dev/null $FRONTEND_URL/api/events/$FIRST_ID"
check "GET /api/events/<unknown> -> 404" "[ \"\$(curl -s -o /dev/null -w '%{http_code}' $FRONTEND_URL/api/events/nope)\" = 404 ]"
check "invalid query -> 422" "[ \"\$(curl -s -o /dev/null -w '%{http_code}' '$FRONTEND_URL/api/events?limit=0')\" = 422 ]"

echo "[3] privacy (PUBLIC_MODE)"
EVENTS="$(json "$FRONTEND_URL/api/events?limit=2000")"
check "no unmasked source IPs" "echo '$EVENTS' | python3 -c 'import json,sys; ev=json.load(sys.stdin)[\"events\"]; sys.exit(0 if ev and all(e[\"source_ip\"] is None or e[\"source_ip\"].endswith(\".*.*\") for e in ev) else 1)'"
check "passwords masked, destination IP and raw withheld" "echo '$EVENTS' | python3 -c 'import json,sys; ev=json.load(sys.stdin)[\"events\"]; sys.exit(0 if all((e[\"password\"] is None or e[\"password\"][1:]==\"••••••\") and e[\"destination_ip\"] is None and e[\"raw\"] is None for e in ev) else 1)'"
check "replay data is chronological" "json '$FRONTEND_URL/api/events?limit=2000&order=asc' | python3 -c 'import json,sys; t=[e[\"timestamp\"] for e in json.load(sys.stdin)[\"events\"]]; sys.exit(0 if t==sorted(t) and len(t)>1 else 1)'"

echo "[4] live streaming"
N1="$(json "$BACKEND_URL/api/status" | python3 -c 'import json,sys; print(json.load(sys.stdin)["events_ingested"])')"
WS_URL="$(echo "$FRONTEND_URL" | sed 's#^http#ws#')/ws/attacks"
WS="$(python3 "$ROOT/scripts/ws_probe.py" "$WS_URL" 6 2>&1)"
echo "        ws: $WS"
check "WebSocket hello received" "echo '$WS' | grep -q '\"hello\": 1'"
check "WebSocket attacks streamed" "echo '$WS' | python3 -c 'import json,sys; sys.exit(0 if json.load(sys.stdin)[\"counts\"].get(\"attack\",0)>=2 else 1)'"
check "WebSocket stats snapshot received" "echo '$WS' | grep -q '\"snapshot\"'"
check "streamed attacks chronological and masked" "echo '$WS' | grep -q '\"chronological\": true, \"masked\": true'"
N2="$(json "$BACKEND_URL/api/status" | python3 -c 'import json,sys; print(json.load(sys.stdin)["events_ingested"])')"
check "event counter increased ($N1 -> $N2)" "[ $N2 -gt $N1 ]"

echo "[5] security headers"
HEADERS="$(curl -fsSI "$FRONTEND_URL/")"
for h in Content-Security-Policy X-Content-Type-Options X-Frame-Options Referrer-Policy; do
  check "header $h" "echo '$HEADERS' | grep -qi '^$h:'"
done

if [ "${1:-}" = "--e2e" ]; then
  echo "[6] browser end-to-end (Playwright)"
  if (cd "$ROOT/frontend" && E2E_BASE_URL="$FRONTEND_URL" npx playwright test); then ok "Playwright e2e"; else bad "Playwright e2e"; fi
fi

echo
echo "Result: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
