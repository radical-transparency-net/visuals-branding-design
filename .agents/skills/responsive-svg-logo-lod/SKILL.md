---
name: responsive-svg-logo-lod
description: Single-file responsive SVG logo architecture using internal @media (max-width: ...) Level-of-Detail layers, centered transform scaling, dark-mode SVG favicons, and LOD-matched static exports.
---

# Responsive SVG Logo Level-of-Detail (LOD)

Use this skill when designing, tuning, or exporting scalable SVG brand marks that must stay crisp from 512px hero displays down to 16x16px favicons.

## 1. Four-Tier `@media` LOD Architecture

When an SVG is loaded via `<img>`, `<object>`, or CSS `background-image`, internal `@media (max-width: ...)` rules evaluate against the **rendered image element box**, behaving like native container queries:

| Tier | Breakpoint | Optical Behavior |
| :--- | :--- | :--- |
| **XL (Hero)** | Default (`> 160px`) | Full lace detail: perforated *linnenslag* `RT`, *spinnen*, fine ribbon weft weave, outward *picots*, full 60-degree *tullegrond* mesh. |
| **M (Header)** | `@media (max-width: 160px)` | Fine perforations, spiders, and inner ribbon cross-weave hide; `RT` becomes 100% solid (`scale(1.12)`); double ribbon rails + outer *picot* beads + boosted mesh remain crisp. |
| **S (Icon)** | `@media (max-width: 72px)` | Complex mesh hides; `RT` scales to `1.36x`; a bold simplified scalloped contour (`2.8px`) + 10 symmetric *traliën* anchors to `1.36x RT` + crest beads remain clear. |
| **XS (Favicon)** | `@media (max-width: 34px)` | Border/mesh hides completely; `RT` scales to `1.82x` with widened horizontal separation (`±2.2px` between `R` and `T`) so `16x16px` and `32x32px` tabs stay razor-sharp. |

## 2. Implementation Guardrails

- **Origin-Centered Scaling:** Wrap the foreground monogram in `<g transform="translate(128, 128)"><g class="rt-scale">...</g></g>` centered around `(0, 0)`. CSS `transform: scale(...)` then scales symmetrically around the canvas center without `transform-origin` browser inconsistencies.
- **Keep `.lod-s` Hidden by Default:** `.lod-s` must be `display: none` in default CSS, enabled only inside `@media (max-width: 72px)`, and disabled again inside `@media (max-width: 34px)`.
- **Clearance Around Scaled `RT`:** When `RT` scales by `1.36x` at `S`, any `.lod-s` ring outside `.rt-scale` must clear `1.36x RT`, and `.lod-s` anchor endpoints hitting `RT` must be multiplied by `1.36` so they join flush.
- **Avoid `prefers-color-scheme` in Master Swatch SVGs:** Master `rt-logo.svg` (`#000000`) and `rt-logo-inverse.svg` (`#ffffff`) must NOT contain `@media (prefers-color-scheme: dark)`, otherwise preview pages on dark-mode OSes turn black-on-white swatches invisible. Put `@media (prefers-color-scheme: dark)` exclusively inside `favicon.svg` using a CSS custom property (`--ink`) on `.ink`/`.line` (never inside `<mask>`).
- **Inline SVG Caveat:** If embedding inline `<svg>` in HTML/React, `@media` reads the viewport instead of the component container. Prefer `<img src="...">` or wrap inline SVG in a CSS `@container` rule.
- **LOD-Matched Static Exports:** Rasterizers (`rsvg-convert`, ImageMagick) evaluate default CSS (`> 160px`). Always emit fixed-LOD static SVGs (`xl`, `m`, `s`, `xs`) and render `128px` PNGs from `m`, `64px` from `s`, and `32px`/`16px` from `xs`.
