#!/usr/bin/env bash
# check_endpoint_count_drift.sh — fail if hardcoded endpoint counts in public
# HTML copy drift from the live api.sgraal.com OpenAPI spec.
#
# Background: see web-static#4 (Phase 1.5 fix-step) and research#17 (Direction
# 2 latent capability audit). Multiple pages historically claimed
# inconsistent counts ("366+", "356", "255+") while the source-of-truth
# count from openapi.json was 355. This check prevents that drift class from
# re-shipping.
#
# Source of truth: https://api.sgraal.com/openapi.json (live).
# Pages scanned: index.html, decide.html, protect.html, scale.html,
# whitepaper.html, comply.html, docs.html, docs/api.html, benchmark.html,
# pricing.html, latency.html.
#
# Behavior:
#   STRICT_MODE=1 → exit 1 on any drift (used on push to main)
#   STRICT_MODE=0 (default) → exit 0 with warnings (used on pull_request)
#
# Usage:
#   STRICT_MODE=1 ./scripts/check_endpoint_count_drift.sh

set -uo pipefail

OPENAPI_URL="${OPENAPI_URL:-https://api.sgraal.com/openapi.json}"
STRICT_MODE="${STRICT_MODE:-0}"

cd "$(dirname "$0")/.."

# 1. Fetch live count
LIVE_COUNT=$(curl -sf --max-time 30 "$OPENAPI_URL" \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d['paths']))")

if [[ -z "$LIVE_COUNT" || ! "$LIVE_COUNT" =~ ^[0-9]+$ ]]; then
  echo "ERROR: could not fetch endpoint count from $OPENAPI_URL"
  echo "       This is likely transient; retry the workflow."
  exit 2
fi

echo "Live endpoint count (source of truth): $LIVE_COUNT"
echo "Strict mode: $STRICT_MODE"
echo

# 2. Scan public HTML files for hardcoded counts
# Pattern: <num>[+]? endpoints? (case-insensitive). Also matches "<num> API endpoints".
# We search for any 3-digit count followed by " endpoint" or " API endpoint"
# variant that doesn't match LIVE_COUNT.

PAGES=(
  "index.html"
  "decide.html"
  "protect.html"
  "scale.html"
  "comply.html"
  "docs.html"
  "docs/api.html"
  "docs/quickstart.html"
  "whitepaper.html"
  "benchmark.html"
  "pricing.html"
  "latency.html"
)

DRIFT_COUNT=0
FOUND_COUNT=0

for page in "${PAGES[@]}"; do
  if [[ ! -f "$page" ]]; then
    continue
  fi
  # Match patterns like:
  #   355 endpoints
  #   355+ endpoints
  #   355 API endpoints
  #   API Reference (355 endpoints)
  while IFS= read -r line; do
    # Extract the number
    num=$(echo "$line" | grep -oE "[0-9]{2,4}\+? *(API )?endpoints?" \
          | grep -oE "[0-9]{2,4}" | head -1)
    if [[ -z "$num" ]]; then
      continue
    fi
    FOUND_COUNT=$((FOUND_COUNT + 1))
    if [[ "$num" != "$LIVE_COUNT" ]]; then
      DRIFT_COUNT=$((DRIFT_COUNT + 1))
      echo "DRIFT: $page claims $num endpoints (live: $LIVE_COUNT)"
      echo "  → $(echo "$line" | tr -s ' ' | cut -c1-160)"
    fi
  done < <(grep -niE "[0-9]{2,4}\+? *(API )?endpoints?" "$page" 2>/dev/null || true)
done

echo
echo "Summary: $FOUND_COUNT endpoint-count claims found across public HTML, $DRIFT_COUNT drifted from live $LIVE_COUNT"

if [[ "$DRIFT_COUNT" -gt 0 ]]; then
  if [[ "$STRICT_MODE" == "1" ]]; then
    echo
    echo "FAIL: endpoint-count drift detected. Update the listed pages to match $LIVE_COUNT,"
    echo "      or, if the live count itself was bumped, run this check after deploy completes."
    echo
    echo "      Background: web-static#4 (#1054 Phase 1.5 fix-step), research#17 §6 Direction 2 audit."
    exit 1
  else
    echo
    echo "WARN: drift detected but STRICT_MODE=0 — not failing the build."
    echo "      To fix: update each listed page's hardcoded count to $LIVE_COUNT."
    exit 0
  fi
fi

echo "PASS: all hardcoded endpoint-count claims match live $LIVE_COUNT."
exit 0
