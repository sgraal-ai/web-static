#!/usr/bin/env python3
"""
check_ip_leak.py — IP-CI workflow for Sgraal's protected IP categories.

CANONICAL LOCATION: sgraal-ai/core/scripts/check_ip_leak.py
DUPLICATED TO: sgraal-ai/web-static/scripts/check_ip_leak.py
              sgraal-ai/sdks/scripts/check_ip_leak.py

If you edit this file, sync the change to the other two repos. The
duplication is intentional (small script, simpler than cross-repo
checkout in GitHub Actions). Header comment in each duplicate notes
this canonical location.

Background — #1131:
  - IP_DEFENSE_RULES_v2 protects 7 categories of numerical IP:
    β weights, Weibull λ values, domain thresholds, scoring calibration,
    action_type multipliers, detection thresholds, R12 corpus weakness map.
  - The 2026-04-30 audit found 1 leak (protect.html:156); the 2026-05-16
    re-audit (after a 17-day window) found 11 leaks (Batch 7). Root cause
    per INCIDENT_PLAYBOOK §7.18 F5: no CI gate prevents re-introduction.
  - This script is that gate.

Detection rule (Phase A v1):
  - Sliding 5-line window across each in-scope file
  - Match: 3+ decimal-pointed numbers (\\d+\\.\\d+) within the window
  - Context required: at least one IP keyword in the same window
  - Pre-strip noise (CSS classes, JSX prop literals, color values, etc.)
  - Allowlist via inline IP-CI-ALLOW: <reason> comment

Modes:
  - STRICT_MODE=1 (default): exit 1 on any unexempted violation
  - STRICT_MODE=0: exit 0, emit warnings to stdout only

Usage:
  python3 scripts/check_ip_leak.py                # full scan
  python3 scripts/check_ip_leak.py --diff-only   # scan only changed files vs main
  STRICT_MODE=0 python3 scripts/check_ip_leak.py # advisory mode
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Detection rules
# ---------------------------------------------------------------------------

KEYWORDS_RE = re.compile(
    r"\b(omega|omega_mem|USE_MEMORY|WARN|ASK_USER|BLOCK|threshold|"
    r"lambda|weibull|injection|poisoning|replay|tamper|sleeper|drift|"
    # 2026-05-28: closes the PR #81 / IP-WP-1 gap (whitepaper.html exposed
    # `r1 + 0.3×r2 + 0.1×r3 + 0.05×r4` with no keyword from the original
    # set — the attack_surface coefficient family was uncovered).
    # The existing 3+-decimal-in-5-line-window requirement still applies,
    # so qualitative public text ("compound attack-surface score, tier-
    # labelled. Levels: NONE/LOW/...") does NOT fire (no decimals); only
    # actual numeric leaks (β-coefficients, multiplier values, weight
    # tables) trigger.
    r"attack_surface|attack|compound|coefficient|multiplier|surface)\b"
    r"|Ω|λ",
    re.IGNORECASE,
)

DECIMAL_RE = re.compile(r"-?\b\d+\.\d+\b")

ALLOWLIST_RE = re.compile(r"IP-CI-ALLOW:\s*\S")

WINDOW = 5  # lines

# ---------------------------------------------------------------------------
# Noise pre-strip filters — drop signals that match decimal/keyword patterns
# but are clearly not IP (CSS classes, JSX prop literals, color values, etc.)
# ---------------------------------------------------------------------------

# HTML: strip <script>, <style>, <svg> bodies and noisy attributes.
SCRIPT_STYLE_SVG_RE = re.compile(
    r"<(script|style|svg)\b[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE
)
HTML_ATTRS_RE = re.compile(
    r'\b(class|style|href|src|width|height|viewBox|fill|stroke|'
    r"stroke-width|d|aria-[a-z]+|onclick|content|tabindex|id|key|name)="
    r'"[^"]*"',
    re.IGNORECASE,
)

# Tailwind / utility class fragments often appear inline outside class="..."
CSS_UTILITY_RE = re.compile(
    r"\b(text-|bg-|px-|py-|pt-|pb-|pl-|pr-|mb-|mt-|ml-|mr-|m-|p-|"
    r"w-|h-|max-w-|min-w-|gap-|space-y-|space-x-|grid-cols-|"
    r"rounded-|font-|leading-|tracking-|hover:|md:|sm:|lg:|xl:|"
    r"border-|opacity-|z-|top-|right-|left-|bottom-|flex-|items-|"
    r"justify-|self-|inset-|translate-|scale-)\S*",
    re.IGNORECASE,
)

# TS/JS: JSX prop literals like min={0.1} max={5} step={0.1} — UI control
# defaults, not calibration.
JSX_NUMERIC_PROPS_RE = re.compile(
    r"\b(min|max|step|value|width|height|x|y|cx|cy|r|"
    r"strokeDasharray|strokeDashoffset|stroke-dasharray|"
    r"viewBox|tabIndex)=\{[^}]+\}",
    re.IGNORECASE,
)

# Color values (any file type)
RGBA_RE = re.compile(r"rgba?\([^)]+\)", re.IGNORECASE)
HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")

# Skip lines that ARE the regex match — keep window for context
NUMBERED_HEADER_RE = re.compile(r"^\s*(<[^>]+>\s*)*\d+\.\d+\s+[A-Z]")
LEGAL_SECTION_RE = re.compile(r"§\d+\.\d+(\([a-z]\))?")

# ---------------------------------------------------------------------------
# In-scope / out-of-scope paths (per-repo override via env or .ipignore)
# ---------------------------------------------------------------------------

# Repo auto-detection: presence of these dirs identifies the repo
REPO_PROFILES = {
    "web-static": {
        "scope": ["**/*.html"],  # all HTML, recursive (root + blog/ + docs/ etc.)
        "skip_dirs": ["node_modules", "dist", ".next", "build", ".git"],
    },
    "core": {
        "scope": ["dashboard/**/*.ts", "dashboard/**/*.tsx"],
        "skip_dirs": [
            "node_modules", "dist", ".next", "build", ".git",
            # Backend retains numerical precision (real API responses).
            "api", "scoring_engine", "tests", "examples",
        ],
    },
    "sdks": {
        "scope": ["**/*.py", "**/*.ts", "**/*.js", "**/*.md"],
        "skip_dirs": ["node_modules", "dist", ".git", "__pycache__"],
    },
}


def detect_repo(root: Path) -> str:
    """Identify which repo we're in based on directory structure."""
    if (root / "dashboard" / "app" / "lib" / "mock-data.ts").exists():
        return "core"
    if (root / "standard.html").exists() and (root / "decide.html").exists():
        return "web-static"
    # Fallback: assume SDKs (most permissive)
    return "sdks"


def should_skip_path(path: Path, profile: dict) -> bool:
    """Skip files in out-of-scope directories or test files."""
    parts = path.parts
    for skip_dir in profile["skip_dirs"]:
        if skip_dir in parts:
            return True
    name = path.name
    if name.startswith("test_") or name.endswith("_test.py"):
        return True
    if ".test." in name or ".spec." in name:
        return True
    if "test_corpus" in str(path):  # the test corpus itself is fixture data
        return True
    return False


def in_scope_files(root: Path, diff_only: bool = False) -> Iterable[Path]:
    """Yield in-scope files for the current repo."""
    repo = os.environ.get("IP_CI_REPO") or detect_repo(root)
    profile = REPO_PROFILES.get(repo, REPO_PROFILES["sdks"])

    if diff_only:
        # Use git to find changed files vs origin/main
        try:
            base = os.environ.get("GITHUB_BASE_REF", "main")
            result = subprocess.run(
                ["git", "diff", "--name-only", f"origin/{base}...HEAD"],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            )
            changed = [Path(p) for p in result.stdout.strip().splitlines() if p]
        except subprocess.CalledProcessError:
            # No remote tracking — fall back to full scan
            changed = None

        if changed is not None:
            for p in changed:
                full = root / p
                if not full.exists() or not full.is_file():
                    continue
                if should_skip_path(p, profile):
                    continue
                # Filter by extension match against scope globs
                for pattern in profile["scope"]:
                    ext = pattern.rsplit(".", 1)[-1]
                    if p.suffix == "." + ext:
                        yield full
                        break
            return

    # Full scan
    for pattern in profile["scope"]:
        for p in root.glob(pattern):
            if p.is_file() and not should_skip_path(p.relative_to(root), profile):
                yield p


# ---------------------------------------------------------------------------
# Scrub + scan
# ---------------------------------------------------------------------------

def _preserve_lines_sub(pattern: re.Pattern, text: str) -> str:
    """Replace pattern matches with the same number of newlines so line
    numbers in violation reports stay aligned with the raw source file."""
    def repl(m: re.Match) -> str:
        return "\n" * m.group(0).count("\n")
    return pattern.sub(repl, text)


def scrub_html(text: str) -> str:
    # Multi-line blocks: preserve line count to keep violation line numbers
    # aligned with the raw source file.
    text = _preserve_lines_sub(SCRIPT_STYLE_SVG_RE, text)
    # Single-line strips: safe to replace with empty string.
    text = HTML_ATTRS_RE.sub("", text)
    text = CSS_UTILITY_RE.sub("", text)
    text = RGBA_RE.sub("", text)
    text = HEX_COLOR_RE.sub("", text)
    return text


def scrub_ts(text: str) -> str:
    text = JSX_NUMERIC_PROPS_RE.sub("", text)
    text = RGBA_RE.sub("", text)
    text = HEX_COLOR_RE.sub("", text)
    return text


def scrub_md_py(text: str) -> str:
    text = RGBA_RE.sub("", text)
    text = HEX_COLOR_RE.sub("", text)
    return text


def scrub(path: Path, text: str) -> str:
    suffix = path.suffix.lower()
    if suffix in (".html", ".htm"):
        return scrub_html(text)
    if suffix in (".ts", ".tsx", ".js", ".jsx"):
        return scrub_ts(text)
    return scrub_md_py(text)


def line_is_noise(line: str) -> bool:
    """Lines that should never count toward decimal cluster detection."""
    if NUMBERED_HEADER_RE.match(line):
        return True
    if LEGAL_SECTION_RE.search(line) and not KEYWORDS_RE.search(line):
        # Section ref alone is noise; section ref + IP keyword in same line
        # is suspicious — keep it in scan
        return True
    return False


# Allowlist look-back window: when a window triggers a violation, the script
# looks back up to ALLOWLIST_LOOKBACK lines from the violation's start to find
# an `IP-CI-ALLOW:` comment. This gives authors a generous scope to annotate
# block-level allowlists for tables (e.g., a benchmark F1 table with 7 rows
# can be exempted by a single comment placed at the top of the block).
ALLOWLIST_LOOKBACK = 10


def scan_file(path: Path) -> list[dict]:
    try:
        raw = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    scrubbed = scrub(path, raw)
    lines = scrubbed.splitlines()
    violations = []
    seen_starts = set()  # de-dupe overlapping windows on same start line
    for i in range(len(lines)):
        start = max(0, i - WINDOW + 1)
        win = lines[start : i + 1]
        if any(line_is_noise(l) for l in win):
            continue
        decimals = sum(len(DECIMAL_RE.findall(l)) for l in win)
        if decimals < 3:
            continue
        if not any(KEYWORDS_RE.search(l) for l in win):
            continue
        # Allowlist check: look at the window PLUS up to ALLOWLIST_LOOKBACK
        # lines before the window's start. This lets a single allowlist
        # comment exempt a longer block (e.g., 7-row benchmark table).
        allowlist_start = max(0, start - ALLOWLIST_LOOKBACK)
        if any(ALLOWLIST_RE.search(l) for l in lines[allowlist_start : i + 1]):
            continue
        # De-dupe: only emit once per starting line
        if start in seen_starts:
            continue
        seen_starts.add(start)
        violations.append(
            {
                "path": path,
                "start_line": start + 1,
                "end_line": i + 1,
                "decimal_count": decimals,
                "context": "\n".join(win),
            }
        )
    return violations


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def format_violation(v: dict, root: Path) -> str:
    rel = v["path"].relative_to(root)
    return (
        f"VIOLATION: {rel}:{v['start_line']}-{v['end_line']} "
        f"({v['decimal_count']} decimals near IP keyword)\n"
        f"  Context:\n"
        + "\n".join(f"    L{v['start_line'] + i}: {line[:140]}"
                    for i, line in enumerate(v["context"].splitlines()))
        + "\n"
        + "  Fix: redact the numerical cluster OR add a comment like:\n"
        + "    IP-CI-ALLOW: <reason for legitimate exception>\n"
    )


def emit_gha_annotation(v: dict, root: Path) -> None:
    """Emit GitHub Actions ::error annotation."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    rel = v["path"].relative_to(root)
    msg = (
        f"IP leak detected: {v['decimal_count']} decimal-pointed numbers near "
        f"IP keyword within {WINDOW}-line window. Redact the cluster or add "
        f"`IP-CI-ALLOW: <reason>` comment. See scripts/check_ip_leak.README.md"
    )
    print(
        f"::error file={rel},line={v['start_line']},endLine={v['end_line']}"
        f"::{msg}"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--diff-only", action="store_true",
                        help="Scan only files changed vs origin/main")
    parser.add_argument("--root", default=".",
                        help="Repo root (default: cwd)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    strict = os.environ.get("STRICT_MODE", "1") == "1"
    repo = os.environ.get("IP_CI_REPO") or detect_repo(root)

    print(f"IP-CI leak check — STRICT_MODE={int(strict)} repo={repo} "
          f"diff_only={args.diff_only}")

    all_violations = []
    scanned = 0
    for path in in_scope_files(root, diff_only=args.diff_only):
        scanned += 1
        all_violations.extend(scan_file(path))

    print(f"Scanned {scanned} files; found {len(all_violations)} violations.\n")

    for v in all_violations:
        print(format_violation(v, root))
        emit_gha_annotation(v, root)

    if all_violations:
        if strict:
            print(f"\nFAIL: {len(all_violations)} IP-leak violations under "
                  f"STRICT_MODE. Redact the clusters or annotate with "
                  f"IP-CI-ALLOW comments. See scripts/check_ip_leak.README.md.")
            return 1
        else:
            print(f"\nWARN: {len(all_violations)} violations but STRICT_MODE=0 "
                  f"— not failing build.")
            return 0

    print("PASS: 0 IP-leak violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
