# Radical Transparency Logo — Design Specification (`v1.0`)

**Selected Design:** *Brugse Schelprand* (8-arch scalloped Bruges tape-lace frame + 60-degree Flemish *tullegrond* mesh + cloth-stitch `RT` monogram)  
**Generator Source:** [`generate_logo.py`](generate_logo.py)  
**Interactive Workbench:** [`preview.html`](preview.html)

---

## 1. Conceptual Rationale

The Radical Transparency Network logo encodes three interlocking ideas in a pure monochrome mark:

1. **Semantic Linkset Mesh Backdrop:** The 60-degree hexagonal lattice of fine threads and pin-nodes reads as an open knowledge graph / linkset map surrounding the central `RT` identity.
2. **Regional Craft Anchor (Bruges Bobbin Lace):** VLIZ operates near Bruges (*Brugge*), historically renowned for handmade bobbin lace (*kantklossen*). Mathematically, traditional bobbin-lace grounds (*tullegrond*, *traliën*, *spinnen*) are directed graphs on a pin lattice (as formalized in the GroundForge / Tesselace research by Veronika Irvine and Frank Ruskey)—making bobbin lace a literal physical metaphor for linked open-science provenance.
3. **Literal Transparency:** Lace is an open, perforated textile whose structure reveals whatever lies behind it. All knockouts and cloth-stitch perforations in the SVG masters use true `<mask>` transparency rather than opaque white fills.

---

## 2. Structural Evolution (Why This Grammar Works)

An early prototype placed hollow `RT` outlines inside a thick uniform-stroke circular ring, which read as **stained glass** (*glas-in-lood*) rather than lace and lost legibility at small sizes.

The finalized `v1.0` design resolves both issues:

- **Three-Tier Weight Hierarchy:**
  1. **Dense *Toilé* (`RT`):** Bold geometric sans letterforms (`76` units tall, `~13` units stroke) with subtle *linnenslag* (cloth-stitch) micro-perforations inside a crisp solid `2.3px` outer rim at XL, switching to 100% solid fill below `160px`.
  2. **Continuous *Lintkant* Border:** Eight outward Bruges flower-work scalloped arches (`r(θ) = 95.5 + 14.5 * sqrt(cos(4θ)^2 + 0.03)`, `half_width = 4.2`) formed by two fine parallel rails (`1.05px`), rhythmic alternating linen cross-ticks (`0.56px`), a delicate center warp (`0.5px`), and 72 outward teardrop *picots* (`0.82px`) resampled uniformly by arc length (`N = 288`).
  3. **Wall-to-Wall *Tullegrond* & Dual Anchoring:** A 60-degree hexagonal lattice (`hex_a = 8.6`) with 6-legged *spinnen* (spiders) in clear hex pockets, bridged flush into both the `RT` perimeter and the inner ribbon rail (`RT ↔ mesh ↔ lintkant`) with zero dangling stubs, while keeping `R`'s inner counter eye cleanly open.

---

## 3. Technical & Responsive `@media` Specification

- **Canvas:** `viewBox="0 0 256 256"`, centered around `(128, 128)`.
- **No Font Dependency:** `R` and `T` are explicit geometric `<path>` shapes.
- **Mask Invariance:** `<mask id="rt-weave-mask">` strictly uses `#ffffff` (visible) and `#000000` (cutout) regardless of whether foreground ink is `#000000`, `#ffffff`, or `var(--ink)`.

| LOD Tier | Breakpoint | `RT` Scale & Style | Lace Backdrop Behavior |
| :--- | :--- | :--- | :--- |
| **XL (Hero)** | Default (`> 160px`) | `1.00×`, cloth-stitch `<mask>` perforations | Full 60° *tullegrond* + *spinnen* + full woven *lintkant* + 72 *picots* |
| **M (Header)** | `@media (max-width: 160px)` | `1.12×`, 100% solid | Spiders, inner ribbon weave & fine *picots* hidden; double rails + 36 *picot* beads + boosted mesh (`1.25px`) |
| **S (Icon)** | `@media (max-width: 72px)` | `1.36×`, 100% solid | Mesh hidden; simplified bold scalloped contour (`2.8px`) + 16 crest beads + 10 flush *traliën* anchors to `1.36× RT` |
| **XS (Favicon)** | `@media (max-width: 34px)` | `1.82×`, `±2.2px` extra `R`/`T` gap | Backdrop hidden; pure high-contrast monogram for `16px`–`32px` crispness |

### Embedding Notes
- Load `rt-logo.svg` (or `rt-logo-inverse.svg`) via `<img>`, `<object>`, or CSS `background-image` so internal `@media` queries evaluate against the image's rendered box rather than the browser viewport.
- Use `favicon.svg` for browser tabs: it uses `--ink: #0b1c30` by default and switches automatically to `#f8f9ff` under `@media (prefers-color-scheme: dark)`.

---

## 4. Asset Inventory

| Asset | Purpose | Notes |
| :--- | :--- | :--- |
| `rt-logo.svg` | Master responsive SVG | `#000000` on transparent, 4 `@media` LOD tiers |
| `rt-logo-inverse.svg` | Master responsive inverse SVG | `#ffffff` on transparent, 4 `@media` LOD tiers |
| `favicon.svg` | Modern vector favicon | Auto light (`#0b1c30`) / dark (`#f8f9ff`) via `prefers-color-scheme` |
| `favicon.ico` | Legacy/fallback favicon | Multi-size ICO (`16×16` XS, `32×32` XS, `48×48` S) |
| `apple-touch-icon.png` | iOS / PWA home-screen icon | `180×180` (`M`-tier mark centered on solid `#f8f9ff`) |
| `svg/rt-logo-{xl,m,s,xs}.svg` (+ `-inverse`) | Fixed-LOD static SVGs | No `@media`; safe for Office/print/static rasterizers |
| `png/rt-logo-{1024,512,256,128,64,32,16}.png` (+ `-inverse`) | Transparent PNG exports | Each size rendered from its matching fixed-LOD SVG (`xl`→1024/512/256, `m`→128, `s`→64, `xs`→32/16) |

---

## 5. Tuning & Regeneration

All geometric constants live at the top of [`generate_logo.py`](generate_logo.py) (`HEX_RADIUS`, `RIBBON_BASE_R`, `RIBBON_AMP`, `RIBBON_SMOOTH`, `RIBBON_HALF_WIDTH`, `SPIDER_MOD`, `WEAVE_STEP`). Run:

```bash
python3 logo/generate_logo.py
```
