#!/usr/bin/env python3
"""GDPR GA-consent guard (#sub-sprint cookie-consent + subfolder catch-up).

Walks every .html file site-wide (root + ALL subdirectories) and fails CI if:

  1. Any page contains the auto-loading GA snippet
     `<script async src="https://www.googletagmanager.com/gtag/js?id=G-K7B978E0HF">`
     without going through the deferred `window.sgraalLoadGA` loader.

  2. Any GA-instrumented page (contains the GA measurement ID) is missing
     the cookie consent banner block (`id="sgraal-cookie-banner"`).

Background: PR#45 (cookie banner) shipped a `os.listdir('.')` migration that
silently missed 14 subfolder pages (docs/, blog/, standard/, integrations/).
That was a GDPR self-compliance gap on a site that sells GDPR products.
This guard makes the regression impossible — any future page that auto-loads
GA without the consent gate, or any new GA page that lacks the banner block,
fails CI before merge.

Run locally:
  python3 scripts/check_ga_consent.py
  STRICT_MODE=1 python3 scripts/check_ga_consent.py

Exits 0 on PASS, 1 on any violation.
"""
from __future__ import annotations

import fnmatch
import os
import sys

GA_ID = "G-K7B978E0HF"
AUTOLOAD_PATTERN = (
    '<script async src="https://www.googletagmanager.com/gtag/js?id=G-K7B978E0HF">'
)
BANNER_MARKER = 'id="sgraal-cookie-banner"'
LOADER_MARKER = "window.sgraalLoadGA"

# Directories to skip during walk
SKIP_DIRS = {"node_modules", "_components", ".git", ".github", ".vercel"}


def discover_html_files(root: str = ".") -> list[str]:
    """Walk recursively, return all .html files (excluding skip dirs)."""
    out: list[str] = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith(".")]
        for f in fnmatch.filter(files, "*.html"):
            out.append(os.path.relpath(os.path.join(d, f), root))
    return sorted(out)


def main() -> int:
    files = discover_html_files()
    autoload_leaks: list[str] = []
    ga_pages_without_banner: list[str] = []
    ga_pages_without_loader: list[str] = []
    total_ga_pages = 0

    for path in files:
        try:
            with open(path, encoding="utf-8") as f:
                src = f.read()
        except (OSError, UnicodeDecodeError):
            continue

        has_ga_id = GA_ID in src
        has_autoload = AUTOLOAD_PATTERN in src
        has_banner = BANNER_MARKER in src
        has_loader = LOADER_MARKER in src

        if has_autoload:
            autoload_leaks.append(path)
        if has_ga_id:
            total_ga_pages += 1
            if not has_banner:
                ga_pages_without_banner.append(path)
            if not has_loader:
                ga_pages_without_loader.append(path)

    print(f"check_ga_consent.py: scanned {len(files)} .html files")
    print(f"  GA-instrumented pages: {total_ga_pages}")

    violations = 0
    if autoload_leaks:
        violations += len(autoload_leaks)
        print(f"\nFAIL: {len(autoload_leaks)} page(s) auto-load GA without consent gate:")
        for p in autoload_leaks:
            print(f"  ✗ {p}")
    if ga_pages_without_banner:
        violations += len(ga_pages_without_banner)
        print(f"\nFAIL: {len(ga_pages_without_banner)} GA-instrumented page(s) missing the cookie banner:")
        for p in ga_pages_without_banner:
            print(f"  ✗ {p}")
    if ga_pages_without_loader:
        violations += len(ga_pages_without_loader)
        print(f"\nFAIL: {len(ga_pages_without_loader)} GA-instrumented page(s) missing the deferred GA loader:")
        for p in ga_pages_without_loader:
            print(f"  ✗ {p}")

    if violations == 0:
        print("\nPASS: 0 GDPR consent violations.")
        return 0

    print(
        "\nTo fix: each GA-instrumented page must use the deferred-loader pattern\n"
        "(see _components/cookie-banner.html for the canonical block, and\n"
        "any of pricing.html / index.html / comply.html for an example of the\n"
        "head-region deferred GA loader replacing the original gtag.js autoload).\n"
        "Adding a new GA page? Copy an existing post-banner page's chrome — do\n"
        "NOT paste the old <script async src=...gtag.js> snippet."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
