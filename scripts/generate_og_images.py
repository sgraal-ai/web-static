#!/usr/bin/env python3
"""Generate 8 brand-consistent 1200×630 og:image PNGs for social sharing.

Logo: Sgraal V6.1 "Erős pecsét" — outer ring + inner amber dot. Two
concentric circles, no SVG dependency (pure Pillow + ImageDraw).

Fonts: DejaVu Sans Bold (headline) + DejaVu Sans Regular (subtitle),
bundled with matplotlib. Same font family the Convergence Proof PDF
uses, so the repo has exactly one font choice.

Output: web-static/og/og-<slug>.png (×8)
Dimensions: 1200×630 (the standard og:image canonical size)

Re-run: python3 scripts/generate_og_images.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Brand tokens (V6.1 pergamen palette)
# ---------------------------------------------------------------------------
BG_CREAM       = (239, 234, 224)   # #efeae0
INK_DARK       = (31, 29, 26)      # #1f1d1a  — logo outer ring, headline
INK_MUTED      = (87, 83, 78)      # #57534e  — subtitle, brand URL
AMBER          = (245, 158, 11)    # #F59E0B  — logo inner dot, accent

# ---------------------------------------------------------------------------
# Canvas spec
# ---------------------------------------------------------------------------
W, H = 1200, 630
LEFT_MARGIN = 80
LOGO_SIZE = 96     # logo box edge length
LOGO_TOP  = 80
BRAND_TEXT_Y = LOGO_TOP + LOGO_SIZE + 14   # just below the logo
ACCENT_RADIUS = 250   # bottom-right decorative ring

HEADLINE_PT = 64
SUBTITLE_PT = 24
BRAND_PT    = 18

# ---------------------------------------------------------------------------
# Font discovery (DejaVu via matplotlib bundle — same as Convergence Proof PDF)
# ---------------------------------------------------------------------------
def _font_path(name: str) -> str:
    import matplotlib
    base = Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf"
    p = base / name
    if not p.exists():
        raise FileNotFoundError(f"font missing: {p}")
    return str(p)


def _load_fonts():
    return (
        ImageFont.truetype(_font_path("DejaVuSans-Bold.ttf"), HEADLINE_PT),
        ImageFont.truetype(_font_path("DejaVuSans.ttf"), SUBTITLE_PT),
        ImageFont.truetype(_font_path("DejaVuSans.ttf"), BRAND_PT),
    )


# ---------------------------------------------------------------------------
# Logo: 2 concentric circles (V6.1 spec: outer r=20 stroke-w=4, inner r=7 fill)
# Scaled to 96×96: outer r=40 stroke-w=8, inner r=14
# ---------------------------------------------------------------------------
def draw_logo(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    """Draw the Sgraal mark at top-left of an LOGO_SIZE box anchored (x, y)."""
    cx = x + LOGO_SIZE // 2
    cy = y + LOGO_SIZE // 2
    # Outer ring — stroke-only circle, width 8
    outer_r = 40
    draw.ellipse(
        (cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r),
        outline=INK_DARK,
        width=8,
    )
    # Inner dot — amber fill
    inner_r = 14
    draw.ellipse(
        (cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r),
        fill=AMBER,
    )


# ---------------------------------------------------------------------------
# Bottom-right decorative accent (subtle gold ring, 15% opacity)
# ---------------------------------------------------------------------------
def draw_accent(img: Image.Image) -> None:
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    od = ImageDraw.Draw(overlay)
    cx, cy = W + 50, H + 30  # mostly off-canvas, only top-left arc visible
    r = ACCENT_RADIUS
    od.ellipse(
        (cx - r, cy - r, cx + r, cy + r),
        outline=(245, 158, 11, 38),  # ~15% alpha
        width=18,
    )
    img.alpha_composite(overlay)


# ---------------------------------------------------------------------------
# Headline wrapping (word-wrap by approximate pixel width)
# ---------------------------------------------------------------------------
def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        trial = " ".join(cur + [w])
        # Pillow ≥ 9.2: textbbox returns (x0,y0,x1,y1)
        bbox = font.getbbox(trial)
        width = bbox[2] - bbox[0]
        if width <= max_width or not cur:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


# ---------------------------------------------------------------------------
# Render one og:image
# ---------------------------------------------------------------------------
def render(headline: str, subtitle: str, out_path: Path) -> None:
    img = Image.new("RGBA", (W, H), BG_CREAM + (255,))
    draw = ImageDraw.Draw(img)
    fh, fs, fb = _load_fonts()

    # Bottom-right decorative accent (drawn first so text overlays cleanly)
    draw_accent(img)

    # Top-left logo
    draw_logo(draw, LEFT_MARGIN, LOGO_TOP)

    # Brand URL line below the logo
    draw.text((LEFT_MARGIN, BRAND_TEXT_Y), "sgraal.com", font=fb, fill=INK_MUTED)

    # Headline — wrap to fit within 70% of canvas width
    max_text_width = int(W * 0.78) - LEFT_MARGIN
    headline_lines = wrap_text(headline, fh, max_text_width)
    headline_line_h = HEADLINE_PT + 10
    headline_block_h = headline_line_h * len(headline_lines)

    # Subtitle — also wrap if long
    subtitle_lines = wrap_text(subtitle, fs, max_text_width)
    subtitle_line_h = SUBTITLE_PT + 8
    subtitle_block_h = subtitle_line_h * len(subtitle_lines)

    # Vertical positioning — center the headline+subtitle block in the lower 2/3
    total_h = headline_block_h + 18 + subtitle_block_h
    top_y = (H - total_h) // 2 + 40  # slight downward bias to balance the logo
    y = top_y
    for line in headline_lines:
        draw.text((LEFT_MARGIN, y), line, font=fh, fill=INK_DARK)
        y += headline_line_h
    y += 18  # gap between headline and subtitle
    for line in subtitle_lines:
        draw.text((LEFT_MARGIN, y), line, font=fs, fill=INK_MUTED)
        y += subtitle_line_h

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out_path, "PNG", optimize=True)


# ---------------------------------------------------------------------------
# 8 og:images per task spec
# ---------------------------------------------------------------------------
IMAGES = [
    ("og-default",   "The immune system for AI agent memory",
                     "USE_MEMORY · WARN · ASK_USER · BLOCK — on every memory access"),
    ("og-pricing",   "Pricing — Free to Enterprise",
                     "Free tier · Pro $99 · Team $499 · Enterprise — pay only for production verdicts"),
    ("og-comply",    "GDPR Article 5(1)(c) — cryptographically proved",
                     "W3C Verifiable Credentials for AI agent memory minimization"),
    ("og-healthcare","FDA-style Lyapunov proofs for clinical AI",
                     "POST /v1/proofs/convergence — agent stability, mathematically certified"),
    ("og-developers","Sgraal in 5 lines of code",
                     "pip install sgraal · drop-in Mem0/Zep proxy · open source SDK"),
    ("og-research",  "Memory governance — first principles",
                     "25 mathematical disciplines · 86 scoring modules · production-validated"),
    ("og-quickstart","Your first memory verdict in 60 seconds",
                     "5-line quickstart · live demo key · zero signup required"),
    ("og-failures",  "How Sgraal catches what others miss",
                     "8 documented failure modes · honest disclosure · no overclaim"),
]


def main() -> int:
    out_dir = Path("og")
    out_dir.mkdir(exist_ok=True)
    for slug, headline, subtitle in IMAGES:
        out = out_dir / f"{slug}.png"
        render(headline, subtitle, out)
        size = out.stat().st_size
        print(f"  {out}: {W}×{H}, {size:,} B")
    print(f"\nGenerated {len(IMAGES)} og:image PNGs into og/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
