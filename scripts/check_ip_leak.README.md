# IP-CI workflow — `check_ip_leak.py`

Detects numerical IP leaks (calibration values, decision-band thresholds, Weibull λ tables, domain thresholds) in public-facing files before they ship. Companion to `IP_DEFENSE_RULES_v2` and INCIDENT_PLAYBOOK §7.18 F5.

## Why

The 2026-04-30 IP audit found 1 leak; the 2026-05-16 re-audit (Batch 7) found 11. Ad-hoc audits don't hold the rule against ongoing PR work. This script is the structural fix: every PR is automatically scanned, and any unexempted numerical-cluster pattern near IP-relevant keywords blocks merge.

## What gets flagged

A line range triggers if **all three** conditions hold within a 5-line sliding window:

1. **At least 3 decimal-pointed numbers** (e.g., `0.15`, `78.4`, `1.5`) — bare integers like `30` or `100` do NOT count, only decimals
2. **At least one IP keyword** in the same window: `omega`, `omega_mem`, `USE_MEMORY`, `WARN`, `ASK_USER`, `BLOCK`, `threshold`, `lambda`, `weibull`, `injection`, `poisoning`, `replay`, `tamper`, `sleeper`, `drift`, `Ω`, `λ`
3. **No `IP-CI-ALLOW:` annotation** in the same window

## What is automatically excluded

Before scanning, the script strips known-noise patterns:

| Pattern | File types |
|---|---|
| `<script>`, `<style>`, `<svg>` block bodies | HTML |
| HTML attributes: `class=`, `style=`, `href=`, `width=`, `viewBox=`, etc. | HTML |
| Tailwind utility class prefixes (`text-`, `bg-`, `px-`, `py-`, `mb-`, etc.) | HTML |
| JSX prop literals: `min={0.1}`, `step={0.1}`, `cy={50}`, etc. | TS / TSX / JS |
| `rgba(...)`, `rgb(...)`, `#hex` color values | All |
| Numbered section headers like `2.3 Section Title` | All |
| Legal section references like `§164.312(c)` (alone, without IP keyword) | All |

In-scope file types per repo (auto-detected by repo profile):

| Repo | In-scope | Out-of-scope |
|---|---|---|
| `web-static` | All `*.html` recursive | `node_modules/`, `dist/`, `.next/`, `.git/` |
| `core` | `dashboard/**/*.{ts,tsx}` | `api/`, `scoring_engine/`, `tests/`, `examples/` — backend retains numerical precision |
| `sdks` | `**/*.{py,ts,js,md}` | `node_modules/`, `dist/`, `__pycache__/` |

Test files (`test_*.py`, `*_test.py`, `*.test.ts`, `*.spec.*`) and the script's own `test_corpus/` are always excluded.

## Allowlist syntax — `IP-CI-ALLOW: <reason>`

When a flagged line is **legitimately** allowed (action_type multipliers per 2026-04-05, benchmark stats like F1 scores, centralized band cutpoints, etc.), annotate it with an `IP-CI-ALLOW:` comment.

### Per-file-type comment markers

| File type | Comment marker |
|---|---|
| HTML / Markdown (HTML comment) | `<!-- IP-CI-ALLOW: <reason> -->` |
| TypeScript / JavaScript / TSX / JSX | `// IP-CI-ALLOW: <reason>` |
| Python | `# IP-CI-ALLOW: <reason>` |
| Shell / YAML | `# IP-CI-ALLOW: <reason>` |

### Scope rules

- **Same line as the violation**: exempts that line only
- **Preceding line (within 10 lines above the violation window's start)**: exempts the violation

In practice: place the comment **on the line immediately above the numerical cluster** to exempt the whole block. The 10-line lookback is generous enough to cover a single allowlist for a multi-row table (e.g., the 7-row Weibull λ table or a benchmark F1 table).

### Reason validation

- The `<reason>` text must be **non-empty** (≥1 non-whitespace character after the colon)
- Bare `IP-CI-ALLOW:` with no text → CI red (forces authors to document why)
- Recommended format: `IP-CI-ALLOW: <category> per <date> <decision-ref>`

### Examples

#### HTML — action_type multiplier (allowed per 2026-04-05)

```html
<!-- IP-CI-ALLOW: action_type multiplier per 2026-04-05 decision -->
<p>Action multiplier: informational 0.5× · irreversible 1.5× · destructive 2.5×</p>
```

#### TypeScript — centralized band cutpoints

```typescript
// IP-CI-ALLOW: centralized band cutpoints, single source of truth per Batch 7 + 2026-05-16
const BAND_CUTPOINTS = {
  use_memory: 25, warn: 50, ask_user: 75,
} as const;
```

#### Markdown — benchmark F1 stats

```markdown
<!-- IP-CI-ALLOW: benchmark F1 stats per 2026-05-13 dual-stack analysis -->
| Round | Test cases | F1 (Sgraal) | F1 (Grok) |
| 5 | 45 | 1.000 | 1.000 |
```

#### Python — internal test data

```python
# IP-CI-ALLOW: test fixture for omega-band boundary scoring
EDGE_CASES = [(0.05, "very_low"), (0.5, "medium"), (0.85, "critical")]
```

## Modes

| Mode | When | Behavior |
|---|---|---|
| `STRICT_MODE=1` (default) | `push:main` | Exit 1 on any unexempted violation. CI red, merge blocked. |
| `STRICT_MODE=0` | Step-1 PR rollout, manual debugging | Exit 0 with violations printed. Advisory only. |

## Usage

### Local — full scan

```bash
python3 scripts/check_ip_leak.py
```

### Local — diff-only (faster, matches CI behavior)

```bash
python3 scripts/check_ip_leak.py --diff-only
```

### Local — non-blocking (for debugging false positives)

```bash
STRICT_MODE=0 python3 scripts/check_ip_leak.py
```

### CI — GitHub Actions

The workflow (`.github/workflows/ip-leak-check.yml`) runs automatically on every PR + push to main. Annotations are emitted on flagged lines via `::error` syntax.

## When the regex flags a false positive

Three options, in order of preference:

1. **Refactor the code to remove the cluster** (e.g., use `omega-band.ts` helper instead of inline cutpoints — Batch 7 DB-3 pattern)
2. **Add an `IP-CI-ALLOW: <reason>` annotation** if the cluster is legitimately allowed (action_type multipliers, benchmark stats, centralized band cutpoints, etc.)
3. **File a regex refinement ticket** if the script is over-triggering on a pattern not covered by the noise-strip filters — do NOT add allowlist annotations as a workaround for script bugs

## Script + workflow location

| Repo | Canonical | Status |
|---|---|---|
| `sgraal-ai/core` | ✅ canonical | Single source of truth — edit here first |
| `sgraal-ai/web-static` | Duplicate | Sync from core when script updates |
| `sgraal-ai/sdks` | Duplicate | Sync from core when script updates |

The duplication is intentional: ~250 LOC script, simpler than cross-repo GitHub Actions checkout. When updating, edit in core first, then copy to web-static and sdks. The header comment in each duplicate documents this.

## Test corpus

Lives in `scripts/check_ip_leak.test_corpus/` with `positive/` (should-trigger fixtures) and `negative/` (should-pass fixtures). Run `python3 scripts/check_ip_leak_test.py` to verify the script behaves correctly against both.

Test fixtures include real Batch 7 history examples:

- `positive/standard_band_table.html` — pre-Batch-7 4-tier band table
- `positive/weibull_lambda_table.html` — pre-Batch-7 7-tier λ table
- `positive/domain_threshold.html` — pre-Batch-7 fintech/medical domain threshold
- `negative/action_type_multiplier.html` — action_type multiplier with IP-CI-ALLOW
- `negative/centralized_band.ts` — omega-band.ts cutpoints with IP-CI-ALLOW
- `negative/latency_metrics.html` — p50/p95/p99 latency (no IP keyword in proximity)

## Cross-references

- `IP_DEFENSE_RULES_v2` — the 7 protected categories
- INCIDENT_PLAYBOOK §7.18 F5 — the systemic gap this script closes
- Master list ticket #1131 — IP-CI workflow scope
- Batch 7 PRs (`sgraal-ai/web-static#31`, `sgraal-ai/core#45`) — the IP-cleanup work that established the baseline this gate protects
