#!/usr/bin/env bash
# check_module_count.sh — fail if hardcoded scoring-module counts in
# public HTML copy reference legacy/intermediate values rather than the
# current source-of-truth (87 modules in core/scoring_engine/*.py — post
# core#32 input_integrity.py addition; bumped from 86 via web-static#1101).
#
# Background: see research#19 C5 finding (Tier-3 drift class), research#31
# §4 (codebase ground truth, baseline 86 modules), core#38 (README sync
# 83→86 that established the prior canonical count), and core#32 +
# web-static#1101 (87 ground truth post input-integrity gate).
#
# Three drift-prevention workflows now exist on web-static:
#   - endpoint-count-drift (STRICT on push:main since web-static#1066)
#   - banned-strings (STRICT on push:main since web-static#13)
#   - module-count (THIS — WARN mode initial, STRICT flip = separate Step 2 PR)
#
# Source-of-truth: `ls ~/core/scoring_engine/*.py | wc -l` = 87 (as of
# 2026-05-15, post-core#32 input_integrity.py). Note: the source-of-truth
# directory lives in the `sgraal-ai/core` repo, NOT in this repo. The check
# is therefore pattern-based (banned-strings style) rather than fetch-based
# (endpoint-count-drift style). Live verification of the source-of-truth is
# manual — bump the SOURCE_OF_TRUTH constant below when scoring_engine/
# module count changes.
#
# 9 patterns detected (anti-drift):
#   "83 module"   / "83-module"   / "83 modules"   (legacy, pre-core#38)
#   "85 module"   / "85-module"   / "85 modules"   (intermediate, deprecated)
#   "86 module"   / "86-module"   / "86 modules"   (intermediate, deprecated
#                                                   post-core#32 / web-static#1101)
#
# Behavior:
#   STRICT_MODE=1 → exit 1 on any drift outside allowlist (used on push:main
#                   once Step 2 flip ships)
#   STRICT_MODE=0 (default) → exit 0 with warnings (used on pull_request
#                   AND initial push:main while in WARN mode)
#
# Allowlist policy (mirrors banned-strings approach): a `<file>:<line>`
# entry exempts a single legitimate historical/disclosure reference. Use
# sparingly. Each entry should have an inline comment explaining the
# legitimate context.
#
# Usage:
#   STRICT_MODE=1 ./scripts/check_module_count.sh

set -uo pipefail
cd "$(dirname "$0")/.."

SOURCE_OF_TRUTH="${SOURCE_OF_TRUTH:-87}"
STRICT_MODE="${STRICT_MODE:-0}"

# Patterns are ERE (extended regex). \b is word-boundary to prevent false
# positives like "883 modules" matching "83 module".
PATTERNS=(
  "\b83 module\b"
  "\b83-module\b"
  "\b83 modules\b"
  "\b85 module\b"
  "\b85-module\b"
  "\b85 modules\b"
  "\b86 module\b"
  "\b86-module\b"
  "\b86 modules\b"
)

# Allowlist: file:line pairs that are OK to contain a banned legacy count.
#
# Format: "<filepath>:<line_number>" — exact match required. To add an entry:
#   1. Identify the legitimate-context line (e.g., a changelog "v1.0 — 83
#      modules" historical reference, or a docs/threat-model.html disclosure
#      block explaining the migration).
#   2. Add the path:line pair below with a comment explaining WHY the
#      legitimate reference is required (this is the discipline that
#      keeps the allowlist from silently growing).
#
# Two policy slots reserved (currently empty — no legitimate references
# exist on web-static today; the canonical count is 86 everywhere):
#
#   Slot 1 (changelog.html historical version-history block):
#     If a future changelog entry says "v1.0: 83 modules → v1.5: 85 modules
#     → v2.0: 86 modules" as legitimate version-history copy, allowlist the
#     specific lines here. Currently empty.
#
#   Slot 2 (docs/threat-model.html-style disclosure block):
#     If a "what changed since the last threat-model snapshot" disclosure
#     legitimately references the prior 83/85 module count, allowlist it.
#     Mirrors the existing banned-strings allowlist pattern for the SOC 2
#     "NOT certified" disclosure block. Currently empty.
ALLOWLIST=(
  # (no entries — canonical count is 87 across all surface as of
  # 2026-05-15 post web-static#1101; no legitimate historical/disclosure
  # references exist)
)

is_allowlisted() {
  local fl="$1"
  for a in "${ALLOWLIST[@]}"; do
    if [[ "$fl" == "$a" ]]; then return 0; fi
  done
  return 1
}

echo "Module-count drift check — STRICT_MODE=$STRICT_MODE"
echo "Source-of-truth: $SOURCE_OF_TRUTH modules (per core#32 + web-static#1101)"
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
echo "Summary: $HITS module-count drift hits outside allowlist (source-of-truth: $SOURCE_OF_TRUTH)"

if [[ "$HITS" -gt 0 ]]; then
  if [[ "$STRICT_MODE" == "1" ]]; then
    echo
    echo "FAIL: $HITS module-count drift hits found."
    echo "      Each hit must be either fixed (update to $SOURCE_OF_TRUTH) or, if"
    echo "      intentional (legitimate historical/disclosure context), added to"
    echo "      the ALLOWLIST array in this script with a comment explaining why."
    echo
    echo "      Background: research#19 C5 (Tier-3 drift class), core#32"
    echo "      (input_integrity.py added — canonical module count 87),"
    echo "      web-static#1101 (SoT bump 86→87)."
    exit 1
  else
    echo
    echo "WARN: drift detected but STRICT_MODE=0 — not failing the build."
    echo "      To fix: update each listed page's hardcoded module count to"
    echo "      $SOURCE_OF_TRUTH OR add the path:line pair to ALLOWLIST with"
    echo "      a comment."
    exit 0
  fi
fi

echo "PASS: 0 module-count drift hits outside allowlist."
exit 0
