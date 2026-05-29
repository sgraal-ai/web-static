#!/usr/bin/env python3
"""
check_navbar_footer_drift.py — site-wide footer + top-navbar drift gate.

Locks in the byte-identical state achieved by:
  - Phase 8a (#89) homepage footer cleanup
  - Phase 8b (#90) site-wide footer harmonization (44/44 e53145718d76)
  - Phase 8c-audit (Phase 8d PR) header verified 44/44 (395430f8631b)

For each web-static *.html page (root + standard/ subdirectory), extract the
top <nav>...</nav> block and the <footer>...</footer> block, compute md5,
compare to the canonical hashes in scripts/canonical_hashes.json.

Exit 0 on PASS (all 44 pages match both canonical hashes).
Exit 1 on FAIL (any page's footer or top-navbar md5 differs from canonical).

When the drift gate fails, the actionable message tells the contributor to:
  (a) revert the unintentional change, OR
  (b) if the change is intentional, update scripts/canonical_hashes.json
      with the new canonical_md5 in the SAME PR and reference the change
      in the PR description.

Modeled on the existing IP-leak STRICT gate (scripts/check_ip_leak.py) and
endpoint-count drift gate (scripts/check_endpoint_count_drift.sh).

Usage:
  python3 scripts/check_navbar_footer_drift.py            # full scan
  python3 scripts/check_navbar_footer_drift.py --verbose  # per-page details
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = REPO_ROOT / "scripts" / "canonical_hashes.json"


def load_policy() -> dict:
    if not POLICY_PATH.is_file():
        print(f"ERROR: policy file not found: {POLICY_PATH}", file=sys.stderr)
        sys.exit(2)
    with open(POLICY_PATH) as f:
        return json.load(f)


def enumerate_pages() -> list[Path]:
    """All *.html pages under the web-static root (root + standard/)."""
    roots = [REPO_ROOT, REPO_ROOT / "standard"]
    pages: list[Path] = []
    for root in roots:
        if root.is_dir():
            for p in sorted(root.glob("*.html")):
                pages.append(p)
    return pages


def extract_block(text: str, regex: str) -> str | None:
    m = re.search(regex, text, re.S)
    return m.group(0) if m else None


def main() -> int:
    verbose = "--verbose" in sys.argv

    policy = load_policy()
    footer_cfg = policy["footer_block"]
    header_cfg = policy["header_navbar_block"]

    pages = enumerate_pages()
    if not pages:
        print("ERROR: no .html pages found", file=sys.stderr)
        return 2

    drifts: list[tuple[str, str, str, str]] = []  # (page, kind, expected, got)
    missing: list[tuple[str, str]] = []          # (page, kind)

    for page in pages:
        rel = str(page.relative_to(REPO_ROOT))
        try:
            text = page.read_text(encoding="utf-8")
        except Exception as e:
            print(f"ERROR: cannot read {rel}: {e}", file=sys.stderr)
            return 2

        for kind, cfg in (("footer", footer_cfg), ("header_navbar", header_cfg)):
            block = extract_block(text, cfg["extraction_regex"])
            if block is None:
                missing.append((rel, kind))
                continue
            actual = hashlib.md5(block.encode("utf-8")).hexdigest()
            expected = cfg["canonical_md5"]
            if verbose:
                mark = "OK" if actual == expected else "DRIFT"
                print(f"  [{mark}] {rel} {kind} md5={actual[:12]} len={len(block)}")
            if actual != expected:
                drifts.append((rel, kind, expected, actual))

    print()
    print(f"Scanned {len(pages)} pages.")
    print(f"  footer canonical md5  : {footer_cfg['canonical_md5'][:12]}")
    print(f"  header canonical md5  : {header_cfg['canonical_md5'][:12]}")

    if missing:
        print()
        print(f"FAIL: {len(missing)} pages missing a required block:")
        for rel, kind in missing:
            print(f"  {rel}: no {kind} block matched")

    if drifts:
        print()
        print(f"FAIL: {len(drifts)} drift(s) detected.")
        for rel, kind, expected, actual in drifts:
            print(f"  {rel}  {kind}:")
            print(f"    expected md5: {expected}")
            print(f"    actual   md5: {actual}")

        print()
        print("ACTION required. Either:")
        print("  (a) Revert the unintentional change in this PR, OR")
        print("  (b) If the change is INTENTIONAL, update")
        print("      scripts/canonical_hashes.json with the new canonical_md5")
        print("      in the SAME PR, and add to the PR description:")
        for kind in sorted({d[1] for d in drifts}):
            cfg = footer_cfg if kind == "footer" else header_cfg
            short_kind = "footer" if kind == "footer" else "header"
            print(f"        '{short_kind} canonical hash changed {cfg['canonical_md5'][:12]} -> <new12>'")
        return 1

    if missing:
        return 1

    print()
    print(f"PASS: all {len(pages)} pages match both canonical hashes "
          f"(footer + top navbar).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
