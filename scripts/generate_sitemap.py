#!/usr/bin/env python3
"""Generate sitemap.xml from the current set of public .html pages.

Walks the repo recursively. Skips:
  - _components/* (internal references, not user-facing)
  - 404.html, 500.html (error pages; flagged via robots.txt Disallow too)
  - .git, node_modules, .vercel, hidden directories

Priority + changefreq heuristic by path:
  /                                             1.0 weekly
  /comply, /healthcare, /pricing, /developers,  0.9 weekly
  /platform, /research, /startups, /security
  /docs, /docs/*                                0.8 monthly  (0.9 for index)
  /blog, /blog/*                                0.7 monthly  (0.9 for index)
  /standard, /standard/*                        0.6 monthly
  /integrations, /integrations/*                0.6 monthly
  everything else                               0.5 monthly

Output: site-wide sitemap.xml at the repo root, conformant to
https://www.sitemaps.org/schemas/sitemap/0.9 .

Run:
  python3 scripts/generate_sitemap.py        # write sitemap.xml
  python3 scripts/generate_sitemap.py --dry  # print to stdout only
"""
from __future__ import annotations

import datetime
import fnmatch
import os
import sys

BASE_URL = "https://sgraal.com"
SKIP_DIRS = {"node_modules", "_components", ".git", ".github", ".vercel"}
SKIP_FILES = {"404.html", "500.html"}


# Priority + changefreq scoring rules — first match wins
SCORING = [
    # (path-glob, priority, changefreq)
    ("",                                                "1.0", "weekly"),   # root (index)
    ("comply",                                          "0.9", "weekly"),
    ("healthcare",                                      "0.9", "weekly"),
    ("pricing",                                         "0.9", "weekly"),
    ("developers",                                      "0.9", "weekly"),
    ("platform",                                        "0.9", "weekly"),
    ("research",                                        "0.9", "weekly"),
    ("startups",                                        "0.9", "weekly"),
    ("security",                                        "0.9", "weekly"),
    ("docs",                                            "0.9", "weekly"),
    ("docs/quickstart",                                 "0.9", "monthly"),
    ("docs/*",                                          "0.8", "monthly"),
    ("blog",                                            "0.9", "weekly"),
    ("blog/*",                                          "0.7", "monthly"),
    ("standard",                                        "0.7", "monthly"),
    ("standard/*",                                      "0.6", "monthly"),
    ("integrations",                                    "0.7", "monthly"),
    ("integrations/*",                                  "0.6", "monthly"),
]


def slug(path: str) -> str:
    """Convert a relative .html path to the URL slug.

    pricing.html        → pricing
    docs/quickstart.html → docs/quickstart
    index.html          → "" (root)
    """
    s = path.removesuffix(".html")
    if s == "index":
        return ""
    return s


def score(slug_str: str) -> tuple[str, str]:
    for pattern, prio, freq in SCORING:
        if pattern == "" and slug_str == "":
            return prio, freq
        if pattern and fnmatch.fnmatch(slug_str, pattern):
            return prio, freq
    return "0.5", "monthly"


def discover() -> list[str]:
    out: list[str] = []
    for d, dirs, files in os.walk("."):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith(".")]
        for f in fnmatch.filter(files, "*.html"):
            if f in SKIP_FILES:
                continue
            rel = os.path.relpath(os.path.join(d, f), ".")
            out.append(rel.replace(os.sep, "/"))
    return sorted(out)


def render(pages: list[str]) -> str:
    today = datetime.date.today().isoformat()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for p in pages:
        s = slug(p)
        prio, freq = score(s)
        url = f"{BASE_URL}/{s}" if s else f"{BASE_URL}/"
        lines.append(
            f"  <url><loc>{url}</loc>"
            f"<lastmod>{today}</lastmod>"
            f"<priority>{prio}</priority>"
            f"<changefreq>{freq}</changefreq></url>"
        )
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main() -> int:
    pages = discover()
    xml = render(pages)
    if "--dry" in sys.argv:
        sys.stdout.write(xml)
    else:
        with open("sitemap.xml", "w", encoding="utf-8") as f:
            f.write(xml)
    print(f"sitemap.xml: {len(pages)} entries written", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
