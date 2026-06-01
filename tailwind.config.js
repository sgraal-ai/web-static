/** @type {import('tailwindcss').Config} */
// Tailwind v3 build config for the CDN→built-CSS migration.
// theme.extend below is index.html's inline "Variant B" Play-CDN config, verbatim,
// so the built stylesheet reproduces the homepage's custom tokens exactly.
// content scans ALL site HTML (excluding deps) so the output is complete and
// reusable for the later site-wide rollout — not just index.html.
module.exports = {
  darkMode: "class",
  content: ["./**/*.html", "!./node_modules/**"],
  // JS-toggled classes from the scope inventory (applied via classList at runtime).
  safelist: ["text-gold", "border-gold", "text-on-surface-variant", "text-slate-400"],
  theme: {
    extend: {
      colors: {
        "surface": "#ffffff",
        "background": "#ffffff",
        "obsidian": "#0B0F14",
        "gold": "#c9a962",
        "gold-dark": "#745b1c",
        "primary": "#c9a962",
        "on-surface": "#0B0F14",
        "on-surface-variant": "#6b7280",
        "outline-variant": "rgba(0,0,0,0.06)",
        "surface-container": "#f5f4f0",
        "surface-container-low": "#faf9f6",
        "code-bg": "#f0efe9",
      },
      fontFamily: {
        "headline": ["Manrope", "sans-serif"],
        "body": ["Inter", "sans-serif"],
        "label": ["Inter", "sans-serif"],
      },
      borderRadius: {
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
