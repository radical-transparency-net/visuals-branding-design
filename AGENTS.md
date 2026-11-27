# AI Agent Guidelines & Repository Directives (`AGENTS.md`)

This repository (`radical-transparency-net/visuals-branding-design`) holds the canonical brand assets, procedural asset generators, design specifications, and verification tools for the **Radical Transparency Network**. This file establishes the baseline rules for all AI coding assistants (Antigravity IDE, Claude Code, Gemini CLI, Cursor, Copilot, Codex).

---

## 1. Mandatory Pre-Flight Context Ingestion

Before modifying visual assets, generators, or documentation, read:

1. [`logo/DESIGN.md`](logo/DESIGN.md): Conceptual rationale, Bruges bobbin-lace grammar, responsive LOD specification, and asset inventory.
2. [`slideware/DESIGN.md`](slideware/DESIGN.md): Slideware background tiling invariants, blank lace medallion, and stacked wordmark specifications.
3. [`.agents/rules/00-visual-branding-policy.md`](.agents/rules/00-visual-branding-policy.md): Repository writing style, provenance rules, transparency standards, and verification gates.

---

## 2. Core Principles

- **Code-First Reproducible Masters:** Vector assets are generated deterministically from Python source (`lace_core.py`, `lace_font.py`, `logo/generate_logo.py`, `slideware/generate_slideware.py`) rather than hand-edited in binary exports. Never edit generated `.svg`, `.png`, or `.ico` files directly without updating the generator.
- **Zero Scraped Third-Party Media:** Never commit collected reference photos, stock imagery, or unattributed third-party graphics. Document visual inspiration textually in `DESIGN.md` with clear provenance.
- **True Transparency & Mask Safety:** Knockouts and cloth-stitch perforations must use SVG `<mask>` (`#ffffff` visible, `#000000` cutout), never opaque background-colored fills. Mask fill colors (`#ffffff` / `#000000`) must remain invariant even in `-inverse` or `prefers-color-scheme: dark` SVG outputs.
- **English & Peer Tone:** All committed documentation, skills, rules, HTML previews, and code comments must be written in factual, concise English with zero marketing hyperbole or AI fluff.

---

## 3. Mandatory Verification Before Completion

Whenever `lace_core.py`, `lace_font.py`, `logo/generate_logo.py`, `logo/preview.html`, `slideware/generate_slideware.py`, or `slideware/preview.html` is modified:

1. Regenerate all vector and raster outputs:
   ```bash
   python3 logo/generate_logo.py && python3 slideware/generate_slideware.py
   ```
2. Visually inspect the rendered PNG exports (`logo/png/*.png`, `logo/apple-touch-icon.png`, `slideware/png/*.png`) and headless browser screenshots of `logo/preview.html` and `slideware/preview.html` on both light and dark surfaces.

---

## 4. Shared Skills Toolkit

Domain-specific workflows are codified in [`.agents/skills/`](.agents/skills/):

- **`procedural-lace-svg`**: Geometric grammar for Bruges bobbin-lace SVGs (continuous SDFs, arc-length-uniform scalloped *lintkant* ribbons, 60-degree *tullegrond* meshes, flush dual anchoring, and `<mask>` perforations).
- **`responsive-svg-logo-lod`**: Single-file responsive SVG architecture using `@media (max-width: ...)` optical tiers, centered scaling transforms, dark-mode `favicon.svg`, and fixed-LOD static exports.
- **`visual-asset-verification`**: Multi-scale raster and headless-browser verification protocol for SVG masters, inverse variants, and favicon stacks.
