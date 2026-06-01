/** @type {import('tailwindcss').Config} */
// Tailwind v3 build config for the site-wide CDN→built-CSS migration.
// theme.extend below is the UNION of every page's inline Play-CDN config
// (Variant A minimal + Variant B index/signup + Variant C decide Material
// palette + Variant D protect partial + memory-ecosystem-map amber set),
// so no page loses a token when its inline config is retired.
//
// Conflicting tokens (same name, different value across variants) are resolved
// to Variant B — the homepage/signup values — approved canonical 2026-06-01.
// The page that visually shifts as a result is decide.html (and, slightly,
// protect.html). Each conflict line is commented inline.
//
// content scans ALL site HTML (root + docs/ + blog/ + standard/ +
// integrations/ + _components/) so the output is complete site-wide.
module.exports = {
  darkMode: "class",
  content: ["./**/*.html", "!./node_modules/**"],
  // JS-toggled named tokens applied via classList at runtime (scanner can't
  // always associate them with an element statically).
  safelist: [
    "text-gold",
    "border-gold",
    "text-on-surface-variant",
    "text-slate-400",
  ],
  theme: {
    extend: {
      colors: {
        // --- Variant B canonical core (index/signup) ---
        "surface": "#ffffff",
        "background": "#ffffff",
        "obsidian": "#0B0F14",
        "gold": "#c9a962",
        "gold-dark": "#745b1c",
        "primary": "#c9a962",
        "on-surface": "#0B0F14",
        "on-surface-variant": "#6b7280", // canonical = Variant B (approved 2026-06-01); decide.html shifts (was #4d4639)
        "outline-variant": "rgba(0,0,0,0.06)", // canonical = Variant B (approved 2026-06-01); decide.html + protect.html shift (was #e0e2ea)
        "surface-container": "#f5f4f0", // canonical = Variant B (approved 2026-06-01); decide.html shifts (was #ffffff)
        "surface-container-low": "#faf9f6", // canonical = Variant B (approved 2026-06-01); decide.html + protect.html shift (was #f5f4f0)
        "code-bg": "#f0efe9",

        // --- memory-ecosystem-map.html extras ---
        "amber": "#F59E0B",
        "amber-light": "#FEF3C7",
        "amber-dark": "#B45309",

        // --- decide.html Material-palette extras (non-conflicting; preserved) ---
        "tertiary": "#b9c6fa",
        "tertiary-container": "#9eabdd",
        "tertiary-fixed": "#dce1ff",
        "tertiary-fixed-dim": "#b8c5f8",
        "on-tertiary": "#ffffff",
        "on-tertiary-container": "#323f6a",
        "on-tertiary-fixed": "#091842",
        "on-tertiary-fixed-variant": "#384570",
        "secondary": "#606774",
        "secondary-container": "#e0e2ea",
        "secondary-fixed": "#dce2f3",
        "secondary-fixed-dim": "#c0c7d6",
        "on-secondary": "#2a313d",
        "on-secondary-container": "#404754",
        "on-secondary-fixed": "#151c27",
        "on-secondary-fixed-variant": "#404754",
        "primary-container": "#c9a962",
        "primary-fixed": "#ffdf9b",
        "primary-fixed-dim": "#e4c279",
        "on-primary": "#ffffff",
        "on-primary-container": "#533d00",
        "on-primary-fixed": "#251a00",
        "on-primary-fixed-variant": "#5a4303",
        "error": "#ba1a1a",
        "error-container": "#93000a",
        "on-error": "#690005",
        "on-error-container": "#ffdad6",
        "outline": "#999080",
        "surface-variant": "#f5f4f0",
        "surface-dim": "#f5f4f0",
        "surface-bright": "#ffffff",
        "surface-container-lowest": "#ffffff",
        "surface-container-high": "#e9e8e4",
        "surface-container-highest": "#dcdbd7",
        "surface-tint": "#c9a962",
        "inverse-surface": "#101419",
        "inverse-primary": "#745b1c",
        "inverse-on-surface": "#faf9f6",
        "on-background": "#0B0F14",
      },
      fontFamily: {
        "headline": ["Manrope", "sans-serif"],
        "body": ["Inter", "sans-serif"],
        "label": ["Inter", "sans-serif"],
      },
      borderRadius: {
        // canonical = Variant B (approved 2026-06-01); decide.html shifts (was lg .25 / xl .5 / full .75rem)
        "DEFAULT": "0.125rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "full": "9999px",
      },
    },
  },
  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/container-queries"),
  ],
};
