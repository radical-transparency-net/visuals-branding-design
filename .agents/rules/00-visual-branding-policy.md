# Visual Branding & Design Repository Policy

**Target:** `radical-transparency-net/visuals-branding-design`  
**Status:** Active Policy

---

## 1. Language, Tone & Privacy

- **Strictly English Repository Artifacts:** All committed documentation, specifications, skill instructions, HTML workbenches, and code comments must be written in clear, factual English. Avoid marketing hyperbole and conversational filler.
- **No Secrets or Local Overrides in Git:** `.agents/local/**` and `.agents/rules/local-*` are git-ignored for personal developer preferences. Never commit credentials, tokens, or internal-only host details.

## 2. Asset Provenance & Licensing

- **Original & Reproducible Assets Only:** Every brand vector and raster asset must originate from deterministic generators in this repository (e.g., `logo/generate_logo.py`) or documented original sources.
- **Zero Scraped Reference Media:** Do not commit collected moodboard images, stock previews, or unattributed external photographs/clipart. Summarize conceptual inspirations and structural principles in `DESIGN.md` instead.

## 3. Technical Craft Standards

- **True Transparency:** Master assets use pure monochrome ink (`#000000` or `#ffffff`) over a genuinely transparent background. Internal perforations must use `<mask>` (`#ffffff` = visible, `#000000` = transparent cutout), never opaque background-colored fills.
- **No External Font Dependencies in SVG Masters:** Letterforms must be compiled to explicit `<path>` geometry so SVGs render identically inside `<img>`, favicons, and offline rasterizers (`rsvg-convert`, Inkscape, browsers).
- **Mandatory Visual Verification:** Do not declare any generator or stylesheet change complete until all outputs are regenerated and visually verified across light and dark backgrounds and across all 4 LOD tiers (`XL`, `M`, `S`, `XS`).
