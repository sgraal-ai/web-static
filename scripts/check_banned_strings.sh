#!/usr/bin/env bash
# check_banned_strings.sh — fail if Tier-1 strict-ban strings appear in
# customer-facing HTML.
#
# Background: the #1054 audit established a manual-grep banned-strings
# discipline (SOC 2, MiFID2, Basel4, etc.). research#25 recommended
# codifying it + extending with 6 NEW Tier-1 strict-ban strings.
# This script is the codification.
#
# Tier-1 banned strings (14 total):
#   Compliance certification claims (8 from #1054 audit):
#     SOC 2, SOC2, MiFID2, MiFID II, Basel4, Basel III, ISO 27001, PCI-DSS
#   New Tier-1 (research#25):
#     Proven (standalone, word-boundary)
#     certified by, certified to
#     audited by, audited to
#     approved by
#     100% accuracy
#     Guaranteed (capitalized, word-boundary)
#
# Allowlist (file:line pairs that are OK to contain a banned string):
#   - docs/threat-model.html:296-297 — explicit "NOT certified by SOC 2..."
#     disclosure (the exception that proves the rule)
#   - standard/cvss.html:224 — factual reference: NIST CSF / ISO 27001
#     in CVSS context, not a Sgraal claim
#   - security.html:170 (cross-link line) — references the threat-model page
#     which contains the NOT-certified disclosure
#   - startups.html:253 — procurement-question quote ("What's your SOC 2
#     status?") — these are QUESTIONS enterprise asks, not Sgraal claims
#
# Line number history:
#   - Original entries (pre Sub-Sprint 1a): threat-model:191/192, cvss:114,
#     security:65, startups:N/A
#   - After 1a nav rollout (2026-05-19): threat-model:246/247, cvss:169,
#     security:120, startups:203 (newly added in 1c)
#   - After 1f tier-aware nav rollout (2026-05-21): threat-model:277/278,
#     cvss:200, security:151, startups:234
#   - After 1c cookie-consent catch-up + 1f og:image sub-sprint (2026-05-22):
#     threat-model:290/291 → 296/297, cvss:218 → 225, security:164 → 188,
#     startups:247 → 253 (og:image rollout injected 6 meta tags near top of
#     every GA-instrumented page; standard/ og:url completeness was +1 more
#     on cvss; security canonical/og:url was +2 + Phase 6 JSON-LD was +16).
#   - 2026-05-30 audit (B2 drift audit) — re-verified every entry's cited
#     line still contains a banned pattern. Result: 5/5 allowlist entries
#     CURRENT, 0 drift. Gate output: "PASS: 0 banned-string hits outside
#     allowlist." See PR body for the per-entry audit table.
# Line shifts come from canonical nav expansion (more Tier 2/3 entries added).
#
# Behavior:
#   STRICT_MODE=1 → exit 1 on any hit outside allowlist
#   STRICT_MODE=0 (default) → exit 0 with warning
#
# Usage:
#   STRICT_MODE=1 ./scripts/check_banned_strings.sh

set -uo pipefail
cd "$(dirname "$0")/.."

STRICT_MODE="${STRICT_MODE:-0}"
HITS=0

# Allowlist: file:line pairs that are OK to contain banned strings.
# Format: "<filepath>:<line_number>"
ALLOWLIST=(
  # The "Sgraal is NOT certified by SOC 2..." disclosure block on the
  # threat-model page is THE exception that proves the rule. Two lines
  # contain banned strings: the main disclaimer (277) — which trips
  # SOC 2 + ISO 27001 + PCI-DSS + certified by simultaneously — and the
  # follow-up SOC 2 Type II procurement-contact paragraph (278).
  # This is an explicit honest non-certification disclosure, the OPPOSITE
  # of overclaim. Required by procurement-process transparency.
  # Line numbers updated 2026-05-22 og:image sub-sprint
  # (was 290/291 in cookie-consent catch-up, 277/278 in Sub-Sprint 1f,
  # 246/247 in 1c-era). The og:image rollout injected 6 meta tags
  # (og:image, og:image:width/height/alt, twitter:card, twitter:image)
  # near the top of every GA-instrumented page, shifting downstream by +6.
  "docs/threat-model.html:296"
  "docs/threat-model.html:297"
  # NIST CSF / ISO 27001 in CVSS scoring context — factual reference to
  # an external framework's reliance on CVSS, not a Sgraal certification
  # claim. The sentence reads "Frameworks like NIST CSF and ISO 27001
  # already reference CVSS for risk assessment" — ISO 27001 is the
  # subject of the framework, not a Sgraal capability.
  # Line number updated 2026-05-22 og:image sub-sprint (+6 from catch-up's 218).
  # Updated 2026-05-23 standard/ og:url completeness sub-sprint: +1 (og:url injected after <title>).
  "standard/cvss.html:225"
  # The "See also: Threat Model" cross-link on the security page links
  # to the threat-model page and explicitly quotes its NOT-certified
  # disclosure verbatim. Trips SOC 2 + certified by patterns. The line
  # exists precisely to redirect customers to the honest disclosure,
  # not to claim certification.
  # Line number updated 2026-05-22 og:image sub-sprint (+6 from cookie-banner's 164,
  # was 151 pre-banner, 120 in 1c-era). Updated 2026-05-23 canonical/og:url
  # completeness sub-sprint: +2 (canonical + og:url injected after <title>).
  # Updated 2026-05-28 Phase 6 JSON-LD sub-sprint: +16 (JSON-LD block inserted
  # before </head>; was 172).
  "security.html:188"
  # The /startups page documents the three procurement blockers AI
  # startups hit when selling to enterprise. Blocker #3 quotes the
  # questions enterprise procurement actually asks: "What's your SOC 2
  # status? EU AI Act mapping? FDA pathway?" — these are the QUESTIONS
  # the customer asks, not claims Sgraal makes. The page's actual
  # response is to point at MVMem certificate + W3C VCs + conformity
  # declaration — explicitly NOT a claim to hold SOC 2 itself.
  # Line number updated 2026-05-22 og:image sub-sprint (+6 from cookie-banner's 247,
  # was 234 pre-banner, 203 in 1c-era).
  "startups.html:253"
  # Negated "guaranteed" — claim-honesty disclaimer ("not ... guaranteed"),
  # added in claim-honesty cleanup (roi #122). The word is disclaimed, not
  # asserted; \bGuaranteed\b cannot distinguish negated vs asserted use.
  "index.html:1079"
  # Negated "guaranteed" — claim-honesty disclaimer ("not ... guaranteed"),
  # added in claim-honesty cleanup (roi #122). The word is disclaimed, not
  # asserted; \bGuaranteed\b cannot distinguish negated vs asserted use.
  "roi.html:258"
  # Negated "guaranteed" — claim-honesty disclaimer ("not ... guaranteed"),
  # added in claim-honesty cleanup (roi #122). The word is disclaimed, not
  # asserted; \bGuaranteed\b cannot distinguish negated vs asserted use.
  "signup.html:425"
)

is_allowlisted() {
  local fl="$1"
  for a in "${ALLOWLIST[@]}"; do
    if [[ "$fl" == "$a" ]]; then return 0; fi
  done
  return 1
}

# Patterns are ERE (extended regex) format. Word-boundary checks use \b
# to avoid matching compound words (e.g., "Proven" should not match
# "Provenance" — that's why we anchor with \b).
BANNED_PATTERNS=(
  "SOC 2"
  "SOC2"
  "MiFID2"
  "MiFID II"
  "Basel4"
  "Basel III"
  "ISO 27001"
  "PCI-DSS"
  "\bProven\b"
  "certified by"
  "certified to"
  "audited by"
  "audited to"
  "approved by"
  "100% accuracy"
  "\bGuaranteed\b"
)

echo "Banned-strings check — STRICT_MODE=$STRICT_MODE"
echo "Patterns: ${#BANNED_PATTERNS[@]} | Allowlist entries: ${#ALLOWLIST[@]}"
echo

for pattern in "${BANNED_PATTERNS[@]}"; do
  while IFS= read -r match; do
    [[ -z "$match" ]] && continue
    file=$(echo "$match" | cut -d: -f1)
    line=$(echo "$match" | cut -d: -f2)
    if is_allowlisted "$file:$line"; then
      continue
    fi
    HITS=$((HITS + 1))
    # Truncate long matches for readability
    snippet=$(echo "$match" | cut -c1-200)
    echo "BANNED: $file:$line matches /$pattern/"
    echo "  → $snippet"
  done < <(grep -rniE "$pattern" \
              *.html docs/*.html standard/*.html integrations/*.html \
              2>/dev/null || true)
done

echo
echo "Summary: $HITS banned-string hits outside allowlist"

if [[ "$HITS" -gt 0 ]]; then
  if [[ "$STRICT_MODE" == "1" ]]; then
    echo
    echo "FAIL: $HITS banned-string hits found."
    echo "      Each hit must be either fixed (preferred) or, if intentional,"
    echo "      added to the ALLOWLIST array in this script with a comment"
    echo "      explaining why it is a legitimate exception."
    echo
    echo "      Background: research#25 (banned-strings extension audit),"
    echo "      research#10 (#1054 audit precedent), web-static#11 (#1068"
    echo "      cross-surface consolidation that pre-cleaned 'Proven' heading)."
    exit 1
  else
    echo
    echo "WARN: drift detected but STRICT_MODE=0 — not failing the build."
    echo "      To fix: clean each banned-string instance OR add to ALLOWLIST."
    exit 0
  fi
fi

echo "PASS: 0 banned-string hits outside allowlist."
exit 0
