#!/usr/bin/env python3
"""Deterministic generator for the Radical Transparency Network logo (v1.0).

Design: "Brugse Schelprand" — 8-arch scalloped Bruges tape-lace (lintkant) ring,
wall-to-wall 60-degree Flemish tullegrond mesh with 6-legged spiders (spinnen),
dual flush anchoring (RT <-> mesh <-> lintkant), and cloth-stitch RT monogram.

Outputs:
  logo/rt-logo.svg                 Master responsive SVG (#000000 on transparent)
  logo/rt-logo-inverse.svg         Master responsive inverse SVG (#ffffff on transparent)
  logo/favicon.svg                 Auto light/dark SVG favicon (prefers-color-scheme)
  logo/favicon.ico                 Multi-size ICO (16px XS, 32px XS, 48px S)
  logo/apple-touch-icon.png        180x180 iOS touch icon on #f8f9ff surface
  logo/svg/rt-logo-{xl,m,s,xs}.svg (+ -inverse)  Fixed-LOD static SVGs
  logo/png/rt-logo-{1024..16}.png  (+ -inverse)  LOD-matched transparent PNGs
"""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from lace_core import (  # noqa: E402
    CANVAS_SIZE,
    CENTER,
    LOBE_COUNT,
    R_PATH_D,
    T_PATH_D,
    build_lintkant_ribbon,
    build_schelprand_spine,
    build_tullegrond_in_ribbon,
    build_weave_holes,
    closed_path,
    closest_rt_point,
    fmt,
    is_in_r_counter,
    render_png,
    sdf_rt,
)

# Responsive @media breakpoints (evaluated against rendered image box)
BP_M = 160
BP_S = 72
BP_XS = 34

SCALE_M = 1.12
SCALE_S = 1.36
SCALE_XS = 1.82
XS_LETTER_SHIFT = 2.2

OUT_DIR = Path(__file__).resolve().parent
SVG_DIR = OUT_DIR / "svg"
PNG_DIR = OUT_DIR / "png"


def build_geometry() -> dict[str, object]:
    """Compute all deterministic vector layers once for reuse across SVG variants."""
    spine = build_schelprand_spine()
    ribbon = build_lintkant_ribbon(spine)
    weave_holes = build_weave_holes(sdf_rt, range(-17, 18), range(-20, 21))
    tulle = build_tullegrond_in_ribbon(
        ribbon["inner_pts"],
        motif_sdf=sdf_rt,
        counter_guard=is_in_r_counter,
        r_range=range(-10, 11),
        c_range=range(-10, 11),
        max_radius=120.0,
    )

    # S-tier simplified scalloped lace contour + 10 flush tralien anchors to 1.36x RT
    s_ring_pts = [(x * 1.03, y * 1.03) for x, y in spine[::3]]
    s_ring_path = closed_path(s_ring_pts)
    s_beads: list[str] = []
    n_s = len(s_ring_pts)
    bead_step = max(1, n_s // (LOBE_COUNT * 2))
    for i in range(0, n_s, bead_step):
        rx, ry = s_ring_pts[i]
        ang = math.atan2(ry, rx)
        bx, by = rx + 4.8 * math.cos(ang), ry + 4.8 * math.sin(ang)
        s_beads.append(f'<circle class="ink" cx="{fmt(bx)}" cy="{fmt(by)}" r="3.4"/>')

    s_anchors: list[str] = []
    for deg_ang in [0, 34, 72, 118, 154, 180, 206, 244, 290, 326]:
        rad = math.radians(deg_ang)
        ux, uy = math.cos(rad), math.sin(rad)
        best_pt = min(s_ring_pts, key=lambda p: abs(math.atan2(p[1], p[0]) - math.atan2(uy, ux)))
        tx, ty = closest_rt_point(best_pt[0] / SCALE_S, best_pt[1] / SCALE_S, steps=6)
        s_anchors.append(
            f'<line x1="{fmt(best_pt[0])}" y1="{fmt(best_pt[1])}" '
            f'x2="{fmt(tx * SCALE_S)}" y2="{fmt(ty * SCALE_S)}"/>'
        )

    return {
        "weave_holes": "".join(weave_holes),
        "spiders_xl": tulle["spiders_xl"],
        "center_path": ribbon["center_path"],
        "outer_path": ribbon["outer_path"],
        "inner_path": ribbon["inner_path"],
        "cross_ticks": ribbon["cross_ticks"],
        "picots_xl": ribbon["picots_xl"],
        "m_beads": ribbon["m_beads"],
        "mesh_lines": tulle["mesh_lines"],
        "pin_nodes": tulle["pin_nodes"],
        "anchor_beads": tulle["anchor_beads"],
        "s_ring_path": s_ring_path,
        "s_beads": "".join(s_beads),
        "s_anchors": "".join(s_anchors),
    }


def render_responsive_svg(geom: dict[str, object], ink: str = "#000000", auto_dark_favicon: bool = False) -> str:
    if auto_dark_favicon:
        color_css = (
            ":root { --ink: #0b1c30; }\n"
            "  @media (prefers-color-scheme: dark) { :root { --ink: #f8f9ff; } }\n"
            "  .ink { fill: var(--ink); }\n"
            "  .line { fill: none; stroke: var(--ink); stroke-linecap: round; stroke-linejoin: round; }"
        )
    else:
        color_css = (
            f".ink {{ fill: {ink}; }}\n"
            f"  .line {{ fill: none; stroke: {ink}; stroke-linecap: round; stroke-linejoin: round; }}"
        )

    style = f"""
  {color_css}
  .rt-scale {{ transform: scale(1); }}
  .rt-letter-r, .rt-letter-t {{ transform: translateX(0); }}
  .rt-solid-group {{ display: none; }}
  .rt-xl-group {{ display: inline; }}
  .lod-xl {{ display: inline; }}
  .lod-m {{ display: inline; }}
  .lod-m-only {{ display: none; }}
  .lod-s {{ display: none; }}

  @media (max-width: {BP_M}px) {{
    .lod-xl {{ display: none; }}
    .lod-s {{ display: none; }}
    .lod-m-only {{ display: inline; }}
    .rt-xl-group {{ display: none; }}
    .rt-solid-group {{ display: inline; }}
    .rt-scale {{ transform: scale({SCALE_M}); }}
    .m-rail-boost {{ stroke-width: 1.45px !important; }}
    .m-mesh-boost {{ stroke-width: 1.25px !important; }}
  }}

  @media (max-width: {BP_S}px) {{
    .lod-xl, .lod-m, .lod-m-only {{ display: none; }}
    .lod-s {{ display: inline; }}
    .rt-xl-group {{ display: none; }}
    .rt-solid-group {{ display: inline; }}
    .rt-scale {{ transform: scale({SCALE_S}); }}
  }}

  @media (max-width: {BP_XS}px) {{
    .lod-xl, .lod-m, .lod-m-only, .lod-s {{ display: none; }}
    .rt-xl-group {{ display: none; }}
    .rt-solid-group {{ display: inline; }}
    .rt-scale {{ transform: scale({SCALE_XS}); }}
    .rt-letter-r {{ transform: translateX(-{XS_LETTER_SHIFT}px); }}
    .rt-letter-t {{ transform: translateX({XS_LETTER_SHIFT}px); }}
  }}
"""

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CANVAS_SIZE} {CANVAS_SIZE}">
  <style>{style}</style>
  <defs>
    <mask id="rt-weave-mask" maskUnits="userSpaceOnUse" x="-60" y="-50" width="120" height="100">
      <rect x="-60" y="-50" width="120" height="100" fill="#ffffff"/>
      {geom['weave_holes']}
    </mask>
  </defs>
  <g transform="translate({CENTER}, {CENTER})">
    <g class="lod-xl">
      <g class="line" stroke-width="0.62">{geom['spiders_xl']}</g>
      <path class="line" stroke-width="0.5" opacity="0.65" d="{geom['center_path']}"/>
      <g class="line" stroke-width="0.56">{geom['cross_ticks']}</g>
      <g>{geom['picots_xl']}</g>
    </g>
    <g class="lod-m-only">{geom['m_beads']}</g>
    <g class="lod-m">
      <g class="line m-mesh-boost" stroke-width="0.92">{geom['mesh_lines']}</g>
      <g>{geom['pin_nodes']}{geom['anchor_beads']}</g>
      <path class="line m-rail-boost" stroke-width="1.05" d="{geom['outer_path']}"/>
      <path class="line m-rail-boost" stroke-width="1.05" d="{geom['inner_path']}"/>
    </g>
    <g class="lod-s">
      <g class="line" stroke-width="2.1">{geom['s_anchors']}</g>
      <path class="line" stroke-width="2.8" d="{geom['s_ring_path']}"/>
      {geom['s_beads']}
    </g>
    <g class="rt-scale">
      <g class="rt-xl-group" mask="url(#rt-weave-mask)">
        <path class="ink" d="{R_PATH_D}"/>
        <path class="ink" d="{T_PATH_D}"/>
      </g>
      <g class="rt-solid-group">
        <path class="ink rt-letter-r" d="{R_PATH_D}"/>
        <path class="ink rt-letter-t" d="{T_PATH_D}"/>
      </g>
    </g>
  </g>
</svg>
'''


def render_static_svg(geom: dict[str, object], lod: str, ink: str = "#000000") -> str:
    """Render a self-contained static SVG with a single fixed LOD (no @media)."""
    base_style = (
        f".ink {{ fill: {ink}; }}\n"
        f"  .line {{ fill: none; stroke: {ink}; stroke-linecap: round; stroke-linejoin: round; }}"
    )

    if lod == "xl":
        defs = f'''
  <defs>
    <mask id="rt-weave-mask-static" maskUnits="userSpaceOnUse" x="-60" y="-50" width="120" height="100">
      <rect x="-60" y="-50" width="120" height="100" fill="#ffffff"/>
      {geom['weave_holes']}
    </mask>
  </defs>'''
        body = f'''
    <g class="line" stroke-width="0.62">{geom['spiders_xl']}</g>
    <path class="line" stroke-width="0.5" opacity="0.65" d="{geom['center_path']}"/>
    <g class="line" stroke-width="0.56">{geom['cross_ticks']}</g>
    <g>{geom['picots_xl']}</g>
    <g class="line" stroke-width="0.92">{geom['mesh_lines']}</g>
    <g>{geom['pin_nodes']}{geom['anchor_beads']}</g>
    <path class="line" stroke-width="1.05" d="{geom['outer_path']}"/>
    <path class="line" stroke-width="1.05" d="{geom['inner_path']}"/>
    <g mask="url(#rt-weave-mask-static)">
      <path class="ink" d="{R_PATH_D}"/>
      <path class="ink" d="{T_PATH_D}"/>
    </g>'''
    elif lod == "m":
        defs = ""
        body = f'''
    <g>{geom['m_beads']}</g>
    <g class="line" stroke-width="1.25">{geom['mesh_lines']}</g>
    <g>{geom['pin_nodes']}{geom['anchor_beads']}</g>
    <path class="line" stroke-width="1.45" d="{geom['outer_path']}"/>
    <path class="line" stroke-width="1.45" d="{geom['inner_path']}"/>
    <g transform="scale({SCALE_M})">
      <path class="ink" d="{R_PATH_D}"/>
      <path class="ink" d="{T_PATH_D}"/>
    </g>'''
    elif lod == "s":
        defs = ""
        body = f'''
    <g class="line" stroke-width="2.1">{geom['s_anchors']}</g>
    <path class="line" stroke-width="2.8" d="{geom['s_ring_path']}"/>
    {geom['s_beads']}
    <g transform="scale({SCALE_S})">
      <path class="ink" d="{R_PATH_D}"/>
      <path class="ink" d="{T_PATH_D}"/>
    </g>'''
    elif lod == "xs":
        defs = ""
        body = f'''
    <g transform="scale({SCALE_XS})">
      <path class="ink" transform="translate(-{XS_LETTER_SHIFT}, 0)" d="{R_PATH_D}"/>
      <path class="ink" transform="translate({XS_LETTER_SHIFT}, 0)" d="{T_PATH_D}"/>
    </g>'''
    else:
        raise ValueError(f"Unsupported static LOD: {lod}")

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CANVAS_SIZE} {CANVAS_SIZE}">
  <style>{base_style}</style>{defs}
  <g transform="translate({CENTER}, {CENTER})">{body}
  </g>
</svg>
'''


def export_rasters() -> None:
    if not shutil.which("rsvg-convert"):
        raise RuntimeError("rsvg-convert is required to render PNG/ICO exports (or pass --svg-only).")

    PNG_DIR.mkdir(parents=True, exist_ok=True)

    exports = [
        (SVG_DIR / "rt-logo-xl.svg", PNG_DIR / "rt-logo-1024.png", 1024),
        (SVG_DIR / "rt-logo-xl.svg", PNG_DIR / "rt-logo-512.png", 512),
        (SVG_DIR / "rt-logo-xl.svg", PNG_DIR / "rt-logo-256.png", 256),
        (SVG_DIR / "rt-logo-m.svg", PNG_DIR / "rt-logo-128.png", 128),
        (SVG_DIR / "rt-logo-s.svg", PNG_DIR / "rt-logo-64.png", 64),
        (SVG_DIR / "rt-logo-xs.svg", PNG_DIR / "rt-logo-32.png", 32),
        (SVG_DIR / "rt-logo-xs.svg", PNG_DIR / "rt-logo-16.png", 16),
        (SVG_DIR / "rt-logo-xl-inverse.svg", PNG_DIR / "rt-logo-512-inverse.png", 512),
        (SVG_DIR / "rt-logo-xl-inverse.svg", PNG_DIR / "rt-logo-256-inverse.png", 256),
        (SVG_DIR / "rt-logo-m-inverse.svg", PNG_DIR / "rt-logo-128-inverse.png", 128),
        (SVG_DIR / "rt-logo-s-inverse.svg", PNG_DIR / "rt-logo-64-inverse.png", 64),
    ]
    for src_svg, dst_png, px in exports:
        render_png(src_svg, dst_png, px, px)
        print(f"Rendered {dst_png.relative_to(OUT_DIR)} ({px}x{px})")

    from PIL import Image

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        touch_fg = tmp / "touch_148.png"
        render_png(SVG_DIR / "rt-logo-m.svg", touch_fg, 148, 148)
        canvas = Image.new("RGBA", (180, 180), "#f8f9ff")
        fg = Image.open(touch_fg).convert("RGBA")
        canvas.alpha_composite(fg, dest=(16, 16))
        canvas.convert("RGB").save(OUT_DIR / "apple-touch-icon.png", format="PNG")
        print("Rendered apple-touch-icon.png (180x180)")

        ico_48 = tmp / "ico_48.png"
        render_png(SVG_DIR / "rt-logo-s.svg", ico_48, 48, 48)
        ico_path = OUT_DIR / "favicon.ico"
        if shutil.which("magick"):
            subprocess.run(
                [
                    "magick",
                    str(PNG_DIR / "rt-logo-16.png"),
                    str(PNG_DIR / "rt-logo-32.png"),
                    str(ico_48),
                    str(ico_path),
                ],
                check=True,
            )
        else:
            img48 = Image.open(ico_48).convert("RGBA")
            img32 = Image.open(PNG_DIR / "rt-logo-32.png").convert("RGBA")
            img16 = Image.open(PNG_DIR / "rt-logo-16.png").convert("RGBA")
            img48.save(ico_path, format="ICO", append_images=[img32, img16])
        print("Rendered favicon.ico (16x16, 32x32, 48x48)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Radical Transparency lace logo assets.")
    parser.add_argument("--svg-only", action="store_true", help="Skip PNG and ICO rasterization.")
    args = parser.parse_args()

    SVG_DIR.mkdir(parents=True, exist_ok=True)
    geom = build_geometry()

    masters = {
        OUT_DIR / "rt-logo.svg": render_responsive_svg(geom, ink="#000000", auto_dark_favicon=False),
        OUT_DIR / "rt-logo-inverse.svg": render_responsive_svg(geom, ink="#ffffff", auto_dark_favicon=False),
        OUT_DIR / "favicon.svg": render_responsive_svg(geom, auto_dark_favicon=True),
    }

    for lod in ("xl", "m", "s", "xs"):
        masters[SVG_DIR / f"rt-logo-{lod}.svg"] = render_static_svg(geom, lod=lod, ink="#000000")
        masters[SVG_DIR / f"rt-logo-{lod}-inverse.svg"] = render_static_svg(geom, lod=lod, ink="#ffffff")

    for path, content in masters.items():
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path.relative_to(OUT_DIR)} ({len(content)} bytes)")

    if not args.svg_only:
        export_rasters()


if __name__ == "__main__":
    main()
