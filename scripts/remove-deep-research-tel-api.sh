#!/usr/bin/env bash
# Remove /tel-api from piren-deep-research funnel and restore deep-research routes only.
set -euo pipefail

TS="${TAILSCALE_BIN:-/home/piren/.local/tailscale/tailscale}"
SOCK="${TAILSCALE_SOCKET:-/home/piren/.local/tailscale/tailscaled.sock}"

ts() { "$TS" --socket="$SOCK" "$@"; }

ts funnel reset
ts funnel --yes --bg 3000
ts funnel --yes --bg --set-path=/app http://127.0.0.1:3001

echo "[funnel] piren-deep-research restored (no /tel-api):"
ts funnel status
