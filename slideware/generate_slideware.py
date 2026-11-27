#!/usr/bin/env python3
"""Deterministic generator for Radical Transparency Network slideware assets.

Builds three monochrome, genuinely transparent slideware assets in both light
(#000000 ink) and dark (-inverse, #ffffff ink) SVG and PNG variants:

  1. rt-mesh-bg-1920x1080     Seamless 16:9 endless hex-mesh + spiders tile
  2. rt-lace-medallion        Letterless Bruges lace medallion (mesh + frame)
  3. rt-wordmark-cartouche    Elongated scalloped lace frame with hex-grid
                              cloth-stitch RADICAL / TRANSPARENCY woven inside
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from lace_core import (  # noqa: E402
    CANVAS_SIZE,
    CENTER,
    HEX_RADIUS,
    SPIDER_MOD,
    build_cartouche_spine,
    build_lintkant_ribbon,
    build_schelprand_spine,
    build_seamless_hex_mesh,
    build_tullegrond_in_ribbon,
    build_weave_holes_in_bbox,
    fmt,
    render_png,
)
from lace_font import layout_lace_wordmark  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
SVG_DIR = OUT_DIR / "svg"
PNG_DIR = OUT_DIR / "png"

CARTOUCHE_W = 972
CARTOUCHE_H = 392


def _base_style(ink: str) -> str:
    return (
        f".ink {{ fill: {ink}; }}\n"
        f"  .line {{ fill: none; stroke: {ink}; stroke-linecap: round; stroke-linejoin: round; }}"
    )


# =============================================================================
# 1. Seamless 16:9 Endless Hex-Mesh + Spiders Background (1920x1080)
# =============================================================================

def render_mesh_bg_svg(mesh_geom: dict[str, str], ink: str = "#000000") -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <style>{_base_style(ink)}</style>
  <defs>
    <clipPath id="slide-clip">
      <rect x="0" y="0" width="1920" height="1080"/>
    </clipPath>
  </defs>
  <g clip-path="url(#slide-clip)">
    <path class="line" stroke-width="1.1" d="{mesh_geom['spider_path']}"/>
    <path class="line" stroke-width="1.65" d="{mesh_geom['mesh_path']}"/>
    <g>{mesh_geom['spider_beads']}{mesh_geom['pin_nodes']}</g>
  </g>
</svg>
'''


# =============================================================================
# 2. Letterless Lace Medallion (Border + Mesh + Spiders)
# =============================================================================

def build_medallion_geometry() -> dict[str, object]:
    spine = build_schelprand_spine()
    ribbon = build_lintkant_ribbon(spine)
    tulle = build_tullegrond_in_ribbon(
        ribbon["inner_pts"],
        hex_radius=HEX_RADIUS,
        spider_mod=SPIDER_MOD,
        motif_sdf=None,
        counter_guard=None,
        r_range=range(-10, 11),
        c_range=range(-10, 11),
        max_radius=120.0,
    )
    return {**ribbon, **tulle}


def render_medallion_svg(geom: dict[str, object], ink: str = "#000000") -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CANVAS_SIZE} {CANVAS_SIZE}">
  <style>{_base_style(ink)}</style>
  <g transform="translate({CENTER}, {CENTER})">
    <g class="line" stroke-width="0.62">{geom['spiders_xl']}</g>
    <path class="line" stroke-width="0.5" opacity="0.65" d="{geom['center_path']}"/>
    <g class="line" stroke-width="0.56">{geom['cross_ticks']}</g>
    <g>{geom['picots_xl']}</g>
    <g class="line" stroke-width="0.92">{geom['mesh_lines']}</g>
    <g>{geom['pin_nodes']}{geom['anchor_beads']}</g>
    <path class="line" stroke-width="1.05" d="{geom['outer_path']}"/>
    <path class="line" stroke-width="1.05" d="{geom['inner_path']}"/>
  </g>
</svg>
'''


# =============================================================================
# 3. Extended Lace Cartouche (RADICAL / TRANSPARENCY woven into hex lattice)
# =============================================================================

def build_cartouche_geometry() -> dict[str, object]:
    wm = layout_lace_wordmark(["RADICAL", "TRANSPARENCY"])
    spine = build_cartouche_spine(
        half_w=442.0,
        half_h=152.0,
        exponent=0.66,
        lobe_count=24,
        scallop_amp=13.5,
        scallop_smooth=0.03,
        n_raw=2048,
        n_samples=864,
    )
    ribbon = build_lintkant_ribbon(spine)
    tulle = build_tullegrond_in_ribbon(
        ribbon["inner_pts"],
        hex_radius=HEX_RADIUS,
        spider_mod=SPIDER_MOD,
        motif_sdf=wm.sdf,
        counter_guard=wm.is_in_counter,
    )
    weave_holes = build_weave_holes_in_bbox(
        wm.sdf,
        wm.bounds,
        step=2.85,
        hole_r=0.52,
        rim_pad=2.10,
    )
    return {
        **ribbon,
        **tulle,
        "wordmark_paths": "".join(
            f'<path class="ink" fill-rule="evenodd" d="{d}"/>' for d in wm.svg_paths
        ),
        "weave_holes": "".join(weave_holes),
        "bounds": wm.bounds,
    }


def render_cartouche_svg(geom: dict[str, object], ink: str = "#000000") -> str:
    x0, y0, x1, y1 = geom["bounds"]
    mx = x0 - 10.0
    my = y0 - 10.0
    mw = (x1 - x0) + 20.0
    mh = (y1 - y0) + 20.0
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CARTOUCHE_W} {CARTOUCHE_H}">
  <style>{_base_style(ink)}</style>
  <defs>
    <mask id="cartouche-weave-mask" maskUnits="userSpaceOnUse" x="{fmt(mx)}" y="{fmt(my)}" width="{fmt(mw)}" height="{fmt(mh)}">
      <rect x="{fmt(mx)}" y="{fmt(my)}" width="{fmt(mw)}" height="{fmt(mh)}" fill="#ffffff"/>
      {geom['weave_holes']}
    </mask>
  </defs>
  <g transform="translate({CARTOUCHE_W // 2}, {CARTOUCHE_H // 2})">
    <g class="line" stroke-width="0.62">{geom['spiders_xl']}</g>
    <path class="line" stroke-width="0.5" opacity="0.65" d="{geom['center_path']}"/>
    <g class="line" stroke-width="0.56">{geom['cross_ticks']}</g>
    <g>{geom['picots_xl']}</g>
    <g class="line" stroke-width="0.92">{geom['mesh_lines']}</g>
    <g>{geom['pin_nodes']}{geom['anchor_beads']}</g>
    <path class="line" stroke-width="1.05" d="{geom['outer_path']}"/>
    <path class="line" stroke-width="1.05" d="{geom['inner_path']}"/>
    <g mask="url(#cartouche-weave-mask)">
      {geom['wordmark_paths']}
    </g>
  </g>
</svg>
'''


# =============================================================================
# Export Pipeline
# =============================================================================

def export_rasters() -> None:
    if not shutil.which("rsvg-convert"):
        raise RuntimeError("rsvg-convert is required to render PNG exports (or pass --svg-only).")

    PNG_DIR.mkdir(parents=True, exist_ok=True)
    cartouche_h_1920 = round(1920 * CARTOUCHE_H / CARTOUCHE_W)

    exports = [
        ("rt-mesh-bg-1920x1080.svg", "rt-mesh-bg-1920x1080.png", 1920, 1080),
        ("rt-mesh-bg-1920x1080-inverse.svg", "rt-mesh-bg-1920x1080-inverse.png", 1920, 1080),
        ("rt-lace-medallion.svg", "rt-lace-medallion-1024.png", 1024, 1024),
        ("rt-lace-medallion-inverse.svg", "rt-lace-medallion-1024-inverse.png", 1024, 1024),
        ("rt-wordmark-cartouche.svg", "rt-wordmark-cartouche-1920.png", 1920, cartouche_h_1920),
        ("rt-wordmark-cartouche-inverse.svg", "rt-wordmark-cartouche-1920-inverse.png", 1920, cartouche_h_1920),
    ]
    for svg_name, png_name, w, h in exports:
        render_png(SVG_DIR / svg_name, PNG_DIR / png_name, w, h)
        print(f"Rendered { (PNG_DIR / png_name).relative_to(OUT_DIR) } ({w}x{h})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Radical Transparency slideware assets.")
    parser.add_argument("--svg-only", action="store_true", help="Skip PNG rasterization.")
    args = parser.parse_args()

    SVG_DIR.mkdir(parents=True, exist_ok=True)

    mesh_bg = build_seamless_hex_mesh(width=1920, height=1080, n_cols=62, n_rows=40)
    medallion = build_medallion_geometry()
    cartouche = build_cartouche_geometry()

    outputs = {
        SVG_DIR / "rt-mesh-bg-1920x1080.svg": render_mesh_bg_svg(mesh_bg, ink="#000000"),
        SVG_DIR / "rt-mesh-bg-1920x1080-inverse.svg": render_mesh_bg_svg(mesh_bg, ink="#ffffff"),
        SVG_DIR / "rt-lace-medallion.svg": render_medallion_svg(medallion, ink="#000000"),
        SVG_DIR / "rt-lace-medallion-inverse.svg": render_medallion_svg(medallion, ink="#ffffff"),
        SVG_DIR / "rt-wordmark-cartouche.svg": render_cartouche_svg(cartouche, ink="#000000"),
        SVG_DIR / "rt-wordmark-cartouche-inverse.svg": render_cartouche_svg(cartouche, ink="#ffffff"),
    }

    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path.relative_to(OUT_DIR)} ({len(content)} bytes)")

    if not args.svg_only:
        export_rasters()


if __name__ == "__main__":
    main()
