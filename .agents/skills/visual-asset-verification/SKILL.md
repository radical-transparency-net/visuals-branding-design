---
name: visual-asset-verification
description: End-to-end visual verification workflow for generated SVG, PNG, and ICO brand assets across light/dark surfaces and all responsive @media breakpoints.
---

# Visual Asset Verification

Never rely solely on SVG code inspection or exit codes when modifying visual generators. Always verify rendered pixels across scales and backgrounds.

## 1. Regeneration Step

Run the canonical generator from the repository root:

```bash
python3 logo/generate_logo.py
```

Confirm all expected files are produced without errors (`rt-logo.svg`, `rt-logo-inverse.svg`, `favicon.svg`, `favicon.ico`, `apple-touch-icon.png`, `svg/*`, `png/*`).

## 2. Multi-Scale Browser & Raster Verification

1. **Browser `@media` Verification:** Capture a full-page screenshot of `logo/preview.html` with headless Chromium (`google-chrome --headless --disable-gpu --screenshot=... --window-size=1320,2400 file:///.../logo/preview.html`) to confirm that:
   - `<img>` elements at `256px`, `128px`, `64px`, `32px`, and `16px` actually trigger all four `@media` LOD tiers.
   - `rt-logo-inverse.svg` renders pure white `#ffffff` ink on dark `#0b1c30` / `#000000` with transparent cloth-stitch cutouts (no inverted white-blob `<mask>` bugs).
2. **Static Export Inspection:** Inspect rendered PNGs (`rt-logo-512.png`, `rt-logo-128.png`, `rt-logo-64.png`, `rt-logo-32.png`, `apple-touch-icon.png`) directly and verify `file logo/png/*.png logo/apple-touch-icon.png logo/favicon.ico` reports expected dimensions and multi-icon directories.

## 3. Visual Inspection Checklist

- [ ] No internal seam or vertical gap in `R`'s bowl cloth-stitch perforation mask.
- [ ] Zero overlapping or self-intersecting ribbon rails at scalloped pinches.
- [ ] Every mesh edge terminates cleanly at another mesh node, `RT`, or the inner ribbon rail (zero orphan stubs).
- [ ] `R`'s inner counter remains unobstructed and `RT` is immediately legible at every size from `512px` down to `16px`.
- [ ] `apple-touch-icon.png` renders crisp dark ink centered with generous safe-zone padding on `#f8f9ff`.
- [ ] No `__pycache__` or temporary verification images remain committed inside the repository.
