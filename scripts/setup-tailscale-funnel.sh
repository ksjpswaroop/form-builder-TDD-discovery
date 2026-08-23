#!/usr/bin/env bash
# Configure Tailscale Funnel for the discovery form on its dedicated node hostname.
#
# Prerequisites:
#   - discovery-form.service running on 127.0.0.1:8000
#   - tdd-discovery-tailscale.service (separate tailscaled) authenticated as tdd-discovery-form
#
# Usage on piren:
#   ./scripts/setup-tailscale-funnel.sh

set -euo pipefail

TS="${TAILSCALE_BIN:-/home/piren/.local/tailscale/tailscale}"
SOCK="${TAILSCALE_SOCKET:-/home/piren/.local/tailscale-tdd-discovery/tailscaled.sock}"
TARGET="${DISCOVERY_TARGET:-http://127.0.0.1:8000}"

ts() { "$TS" --socket="$SOCK" "$@"; }

echo "[funnel] waiting for tdd-discovery-form tailscale…"
for _ in $(seq 1 60); do
  if ts status --json 2>/dev/null | grep -q '"BackendState": "Running"'; then
    break
  fi
  sleep 1
done

if ! ts status --json 2>/dev/null | grep -q '"BackendState": "Running"'; then
  echo "[funnel] ERROR: tdd-discovery-form not logged in. Run: ts status"
  exit 1
fi

DNS=$(ts status --json | python3 -c "import sys,json; print(json.load(sys.stdin)['Self']['DNSName'].rstrip('.'))")

ts funnel reset 2>/dev/null || true
ts funnel --yes --bg "$TARGET"

echo
echo "========== TDD Discovery Funnel =========="
echo "Public URL: https://${DNS}/"
ts funnel status || true
echo "=========================================="
