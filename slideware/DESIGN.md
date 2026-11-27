# Radical Transparency Slideware — Design Specification

**Generator Source:** [`generate_slideware.py`](generate_slideware.py) (backed by [`../lace_core.py`](../lace_core.py) and [`../lace_font.py`](../lace_font.py))  
**Interactive Workbench:** [`preview.html`](preview.html)

---

## 1. Overview & Transparency Standard

All slideware assets follow the same craft rules as the canonical logo:

- **Monochrome Transparent Masters:** Light-surface masters use `#000000` ink on transparent; dark-surface (`-inverse`) masters use `#ffffff` ink on transparent so slide decks can apply custom background tints (`#f8f9ff`, `#eff4ff`, `#0b1c30`, `#000000`) and watermark opacity in PowerPoint, Google Slides, Keynote, or Reveal.js.
- **Mask Invariance:** Cloth-stitch (*linnenslag*) perforations inside `rt-wordmark-cartouche` use explicit SVG `<mask>` cutouts (`#ffffff` visible, `#000000` transparent) rather than opaque background fills.
- **Zero External Font Dependencies:** All uppercase letterforms (`A–Z`, `' '`, `'-'`, `'.'`) are defined procedurally in Python (`lace_font.py`) with synchronized SVG `<path>` outlines and continuous polygon SDFs.

---

## 2. Asset Specifications

### 2.1 Seamless 16:9 Hex-Mesh + Spiders (`rt-mesh-bg-1920x1080`)
- **Canvas:** `1920 × 1080` (`viewBox="0 0 1920 1080"`), clipped strictly to `[0, 1920] × [0, 1080]`.
- **Periodic Lattice:** `62` columns × `40` staggered rows (`dx = 1920 / 62 ≈ 30.968px`, `dy = 1080 / 40 = 27.0px`, `R ≈ 18.0px`, isotropic aspect error `0.67%`).
- **Seamless Invariants:**
  - `n_cols % 2 == 0` ensures horizontal tile edges wrap identically.
  - `n_rows % 2 == 0` ensures staggered row parity matches across top/bottom edges.
  - `n_rows % SPIDER_MOD == 0` (`40 % 4 == 0`) ensures the 6-legged *spinnen* cadence `((r + 2*c) % 4 == 0)` wraps cleanly across both horizontal and vertical tile boundaries.

### 2.2 Letterless Lace Medallion (`rt-lace-medallion`)
- **Canvas:** `256 × 256` (`viewBox="0 0 256 256"`), PNG export at `1024 × 1024`.
- **Construction:** Identical 8-arch *Brugse Schelprand* outer *lintkant* ribbon and continuous 60° *tullegrond* lattice + *spinnen* as the XL logo, without the `RT` monogram—intended for draping over slide corners, headers, and section borders.

### 2.3 Extended Lace Cartouche (`rt-wordmark-cartouche`)
- **Canvas:** `viewBox="0 0 972 392"`, PNG export at `1920 × 774`.
- **Hex-Grid Fixed-Width Lace Font (`lace_font.py`):**
  - Locked to `HEX_RADIUS = 8.6` (`DX = sqrt(3)*8.6 ≈ 14.90`, `DY = 1.5*8.6 = 12.90`).
  - Each glyph occupies a `3 × 5` hex cell (`44.69 × 64.50`), separated by `1` hex column horizontally (`pitch = 4*DX ≈ 59.58`) and `2` hex rows vertically (`25.80`).
  - Because any `k`-letter line has width `(4k - 1)·DX`, both `RADICAL` (27 columns) and `TRANSPARENCY` (47 columns) center on the exact same hex-column phase, allowing uninterrupted *tullegrond* anchoring through every 1-hex inter-letter column, every open letter bay (`L, T, Y, C, E, S`), and the 2-hex horizontal band between the two words—with only closed counters (`R, A, D, P`, etc.) kept open.
- **Border & Weave:**
  - 4-way symmetric superellipse *lintkant* border (`half_w = 442`, `half_h = 152`, `exponent = 0.66`, `lobe_count = 24`, `scallop_amp = 13.5`) resampled uniformly by arc length (`864` samples, `216` outward *picots*).
  - Cloth-stitch *linnenslag* `<mask>` micro-perforations (`step = 2.85`, `hole_r = 0.52`, `rim_pad = 2.10`).

---

## 3. Asset Inventory

| Asset | SVG (`slideware/svg/`) | PNG (`slideware/png/`) | Variants |
| :--- | :--- | :--- | :--- |
| Seamless 16:9 Mesh + Spiders | `rt-mesh-bg-1920x1080.svg` | `rt-mesh-bg-1920x1080.png` (`1920×1080`) | light (`#000000`) & `-inverse` (`#ffffff`) |
| Letterless Lace Medallion | `rt-lace-medallion.svg` | `rt-lace-medallion-1024.png` (`1024×1024`) | light (`#000000`) & `-inverse` (`#ffffff`) |
| Extended Lace Cartouche | `rt-wordmark-cartouche.svg` | `rt-wordmark-cartouche-1920.png` (`1920×774`) | light (`#000000`) & `-inverse` (`#ffffff`) |

---

## 4. Regeneration

```bash
python3 slideware/generate_slideware.py
```

Use `--svg-only` to regenerate only the vector SVGs without rasterizing PNGs.
