# Radical Transparency — Visuals, Branding & Design

Canonical visual identity assets, procedural generators, design specifications, and reusable agent skills for the **Radical Transparency Network** (`radical-transparency.net`).

---

## Repository Structure

```text
visuals-branding-design/
├── AGENTS.md                  # Authoritative AI agent directives
├── CLAUDE.md                  # Pointer to AGENTS.md for Claude Code
├── GEMINI.md                  # Pointer to AGENTS.md for Gemini CLI
├── .agents/
│   ├── rules/                 # Repository-wide branding & verification rules
│   └── skills/                # Reusable skills for procedural SVG & verification
└── logo/
    ├── DESIGN.md              # Conceptual rationale, geometry, and technical specs
    ├── generate_logo.py       # Deterministic procedural SVG + PNG/ICO generator
    ├── preview.html           # Interactive multi-scale & contrast workbench
    ├── rt-logo.svg            # Master responsive monochrome SVG (#000000 on transparent)
    ├── rt-logo-inverse.svg    # Master responsive inverse SVG (#ffffff on transparent)
    ├── favicon.svg            # Auto light/dark SVG favicon (prefers-color-scheme)
    ├── favicon.ico            # Multi-size ICO (16x16, 32x32, 48x48)
    ├── apple-touch-icon.png   # 180x180 iOS touch icon on #f8f9ff surface
    ├── svg/                   # Fixed-LOD static SVGs (xl, m, s, xs + inverse)
    └── png/                   # Transparent PNG exports matched to each LOD tier
```

---

## Quick Usage

### Responsive Logo (`<img>` or CSS `background-image`)
Embed `logo/rt-logo.svg` (or `logo/rt-logo-inverse.svg` on dark surfaces) via `<img>`, `<object>`, or CSS `background-image`. Internal `@media (max-width: ...)` rules evaluate against the rendered image dimensions and automatically switch optical detail tiers (`>160px`, `<=160px`, `<=72px`, `<=34px`).

```html
<img src="/logo/rt-logo.svg" alt="Radical Transparency Network" width="128" height="128" />
```

> **Note on inline `<svg>`:** When inlining SVG markup directly into a DOM document, `@media` queries evaluate against the viewport rather than the element box. Use `<img>` or wrap inline SVG in a CSS `@container` context.

### Modern Favicon Stack
```html
<link rel="icon" type="image/svg+xml" href="/favicon.svg" />
<link rel="alternate icon" href="/favicon.ico" sizes="any" />
<link rel="apple-touch-icon" href="/apple-touch-icon.png" />
```

---

## Regenerating Assets

Requirements: Python 3.9+, `rsvg-convert` (`librsvg2-bin`), and `Pillow` (`PIL`).

```bash
python3 logo/generate_logo.py
```

To regenerate only the SVG masters and fixed-LOD variants without rendering PNG/ICO binaries:

```bash
python3 logo/generate_logo.py --svg-only
```
