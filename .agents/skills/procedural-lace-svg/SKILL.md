---
name: procedural-lace-svg
description: Procedural SVG engineering grammar for Bruges bobbin-lace network emblems (continuous SDFs, arc-length-uniform scalloped lintkant ribbons, 60-degree tullegrond meshes, flush dual anchoring, and true mask transparency).
---

# Procedural Lace SVG Engineering

Use this skill when generating or modifying mathematical bobbin-lace SVG logos and network emblems.

## 1. Visual Grammar: Avoiding the "Stained-Glass" Trap

Uniform stroke weights inside a thick closed circle read as stained glass, not lace. Authentic Bruges bobbin lace (*Brugse kant*) relies on a strict **3-tier weight and density hierarchy**:

1. **Dense Motif (*Toilé*):** Central monogram (`RT`) rendered solid or with a fine interior *linnenslag* (cloth-stitch) micro-perforation mask inside a crisp solid outer rim (`~2.3px`).
2. **Translucent Border Tape (*Lintkant*):** A continuous scalloped perimeter ribbon formed by two fine parallel rails (`~1.05px`) filled with alternating diagonal linen cross-weft ticks (`~0.56px`), a subtle center warp (`~0.5px`), and rhythmic outward *picot* teardrop loops (`~0.82px`).
3. **Airy Lattice (*Tullegrond*) & Spiders (*Spinnen*):** A 60-degree hexagonal mesh (`~0.92px`) with pin-dots (`r ≈ 1.22`) at vertices and 6-legged *spinnen* (`~0.62px`, central bead `r ≈ 1.6`) in selected clear pockets. This connects directly to directed-graph bobbin-lace research (GroundForge / Irvine & Ruskey), where pins are graph nodes and threads are edges.

## 2. Core Geometric Rules

- **Continuous, Seam-Free Letter SDFs:**
  - Compile letters to explicit `<path>` geometry (never `<text>`).
  - Match the exact path coordinates with a continuous Signed Distance Field (`sdf_rt(x, y)`).
  - Never guard sub-primitive SDF components with piecewise coordinate cutoffs (e.g., `if x >= -23.0`) that create artificial internal zero-boundaries; let overlapping primitives (`min(box, ellipse)`) merge seamlessly so internal perforation grids never show vertical seams.
  - Keep internal letter counters (such as `R`'s eye) explicitly guarded (`is_in_r_counter`) so background mesh lines never clutter counter legibility.
- **Arc-Length-Uniform Closed Ribbons:**
  - Sample any periodic radial envelope `r(θ)` densely (`N >= 720`), compute cumulative arc length, and resample uniformly to `M` points divisible by the lobe symmetry (e.g., `M = 288` works for both 6-fold and 8-fold symmetry). This prevents weft ticks and *picots* from bunching in valleys or stretching on peaks.
  - Floor sharp scalloped cusps (e.g., `sqrt(cos(4θ)^2 + 0.03)`) so the ribbon curvature radius always exceeds `half_width`, preventing rail self-intersections.
- **Flush Dual Anchoring (`RT ↔ mesh ↔ lintkant`):**
  - Classify candidate 60-degree hex edges into: (a) interior edges, (b) segments crossing `inner_poly`, and (c) segments crossing `RT` (excluding counters).
  - Bisect boundary crossings to `0.00px` (`inner_poly`) or `-0.35px` (`RT`) so every thread terminates flush without gaps or overshoot.
  - Bridge remaining degree-1 cavity stubs to the nearest surface within reach or prune iteratively so **zero dangling stubs** remain.
- **True Transparency via `<mask>`:**
  - Never paint opaque white shapes on top of black ink. Use `<mask>` with `<rect fill="#ffffff"/>` and cutout shapes (`fill="#000000"`).
  - Keep `<mask>` fill colors strictly `#ffffff`/`#000000` regardless of whether the foreground ink is `#000000`, `#ffffff`, or `var(--ink)`.
