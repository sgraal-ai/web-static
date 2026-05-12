#!/usr/bin/env bash
# check_test_count.sh — fail if hardcoded test counts in public HTML
# copy reference legacy/intermediate values rather than the current
# source-of-truth (2,905 test functions in core/tests/test_*.py as of
# 2026-05-12).
#
# Background: this is the 4th drift-prevention workflow on web-static.
# The 3 already-shipped workflows enforce parity of public claims with
# canonical sources:
#   - endpoint-count-drift   STRICT on push:main (live openapi.json = 355)
#   - banned-strings         STRICT on push:main (16 Tier-1 patterns)
#   - module-count           STRICT on push:main (constant SOURCE_OF_TRUTH=86)
#   - test-count             WARN  on push:main (THIS — Step 1, STRICT-flip
#                                                separate Step 2 PR)
#
# Source-of-truth: SOURCE_OF_TRUTH=2905 (verified 2026-05-12 via
#   `grep -hE "def test_" ~/core/tests/test_*.py | wc -l`)
# Bump when test count changes by >50 tests OR when a customer-facing
# page references a specific count that needs to be kept in sync.
#
# Same pattern-based approach as banned-strings + module-count (live
# verification of the source happens manually in the core repo, not
# automatically in CI — the `~/core/` directory is a separate repo not
# accessible from web-static CI workers).
#
# 5 legacy patterns detected (anti-drift):
#   "2,928 tests" / "2928 tests"   (brief-stated current at AFK BATCH 7
#                                    time, but actual was 2,905 —
#                                    flag if any page picks up "2,928"
#                                    as a literal stale value)
#   "2,910 tests" / "2910 tests"   (legacy, pre-fix-assertions sprint)
#   "2,853 tests" / "2853 tests"   (legacy, mid-sprint snapshot)
#   "2,800 tests" / "2800 tests"   (legacy, older sprint)
#   "2,500 tests" / "2500 tests"   (legacy, sprint 70-era)
#
# Behavior:
#   STRICT_MODE=1 → exit 1 on any drift outside allowlist (used on push:main
#                   once Step 2 flip ships)
#   STRICT_MODE=0 (default) → exit 0 with warnings (used on pull_request
#                   AND initial push:main while in WARN mode)
#
# Allowlist policy (mirrors banned-strings + module-count approach):
# a `<file>:<line>` entry exempts a single legitimate historical/
# disclosure reference. Use sparingly. Each entry should have an inline
# comment explaining the legitimate context.
#
# Usage:
#   STRICT_MODE=1 ./scripts/check_test_count.sh

set -uo pipefail
cd "$(dirname "$0")/.."

SOURCE_OF_TRUTH="${SOURCE_OF_TRUTH:-2905}"
STRICT_MODE="${STRICT_MODE:-0}"

# Patterns are ERE (extended regex). \b is word-boundary. Each legacy
# value matches both comma-formatted ("2,928 tests") and plain-integer
# ("2928 tests") forms. Word-boundary on the right of "tests?" prevents
# matching compound words like "testsuite".
PATTERNS=(
  "\b2,?928 tests?\b"
  "\b2,?910 tests?\b"
  "\b2,?853 tests?\b"
  "\b2,?800 tests?\b"
  "\b2,?500 tests?\b"
)

# Allowlist: file:line pairs that are OK to contain a banned legacy count.
#
# Format: "<filepath>:<line_number>" — exact match required. To add an entry:
#   1. Identify the legitimate-context line (e.g., a changelog "v1.0 — 2,500
#      tests" historical reference, or a docs/threat-model.html disclosure
#      block explaining a calibration snapshot).
#   2. Add the path:line pair below with a comment explaining WHY the
#      legitimate reference is required (this is the discipline that
#      keeps the allowlist from silently growing).
#
# Two policy slots reserved (currently empty — no legitimate references
# exist on web-static today; benchmark.html uses "2,900+ test scenarios"
# with a "+" suffix that does NOT match any of the 5 patterns):
#
#   Slot 1 (changelog.html historical version-history block):
#     If a future changelog entry says "v1.0: 2,500 tests → v2.0: 2,800
#     → v3.0: 2,905" as legitimate version-history copy, allowlist the
#     specific lines here. Currently empty.
#
#   Slot 2 (docs/threat-model.html-style disclosure block):
#     If a "what was the test count at calibration snapshot N" disclosure
#     legitimately references a prior count, allowlist it.
#     Mirrors the banned-strings allowlist pattern for the SOC 2
#     "NOT certified" disclosure block. Currently empty.
ALLOWLIST=(
  # (no entries — current web-static surface uses fuzzy "2,900+ test
  # scenarios" framing on benchmark.html which does NOT match any of
  # the 5 specific legacy patterns; clean baseline as of 2026-05-12)
)

is_allowlisted() {
  local fl="$1"
  for a in "${ALLOWLIST[@]}"; do
    if [[ "$fl" == "$a" ]]; then return 0; fi
  done
  return 1
}

echo "Test-count drift check — STRICT_MODE=$STRICT_MODE"
echo "Source-of-truth: $SOURCE_OF_TRUTH tests (verified 2026-05-12)"
echo "Patterns: ${#PATTERNS[@]} | Allowlist entries: ${#ALLOWLIST[@]}"
echo

HITS=0

for pattern in "${PATTERNS[@]}"; do
  while IFS= read -r match; do
    [[ -z "$match" ]] && continue
    file=$(echo "$match" | cut -d: -f1)
    line=$(echo "$match" | cut -d: -f2)
    if is_allowlisted "$file:$line"; then
      continue
    fi
    HITS=$((HITS + 1))
    snippet=$(echo "$match" | cut -c1-200)
    echo "DRIFT: $file:$line matches /$pattern/"
    echo "  → $snippet"
  done < <(grep -rniE "$pattern" \
              *.html docs/*.html standard/*.html integrations/*.html \
              2>/dev/null || true)
done

echo
echo "Summary: $HITS test-count drift hits outside allowlist (source-of-truth: $SOURCE_OF_TRUTH)"

if [[ "$HITS" -gt 0 ]]; then
  if [[ "$STRICT_MODE" == "1" ]]; then
    echo
    echo "FAIL: $HITS test-count drift hits found."
    echo "      Each hit must be either fixed (update to $SOURCE_OF_TRUTH or"
    echo "      remove the specific count in favor of a '+' suffix pattern"
    echo "      like '2,900+ tests' which is fuzzy by design) or, if intentional"
    echo "      (legitimate historical/disclosure context), added to the"
    echo "      ALLOWLIST array in this script with a comment explaining why."
    echo
    echo "      Background: web-static#17/#18 module-count-drift pattern + "
    echo "      AFK BATCH 7 TASK G (test-count drift Step 1)."
    exit 1
  else
    echo
    echo "WARN: drift detected but STRICT_MODE=0 — not failing the build."
    echo "      To fix: update each listed page's hardcoded test count to"
    echo "      $SOURCE_OF_TRUTH (or use '+' suffix for fuzzy commitment)"
    echo "      OR add the path:line pair to ALLOWLIST with a comment."
    exit 0
  fi
fi

echo "PASS: 0 test-count drift hits outside allowlist."
exit 0
