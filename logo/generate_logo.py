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
import tempfile
from pathlib import Path

# =============================================================================
# Tunable Geometric & LOD Parameters
# =============================================================================

CANVAS_SIZE = 256
CENTER = 128

# Scalloped 8-arch Bruges lintkant ribbon envelope:
# r(theta) = RIBBON_BASE_R + RIBBON_AMP * sqrt(cos(4*theta)^2 + RIBBON_SMOOTH)
LOBE_COUNT = 8
RIBBON_BASE_R = 95.5
RIBBON_AMP = 14.5
RIBBON_SMOOTH = 0.03
RIBBON_HALF_WIDTH = 4.2
RIBBON_SAMPLES = 288          # Divisible by 6 and 8 for symmetric weave & picots
PICOT_EVERY = 4               # 72 picot loops around perimeter (~9px spacing)

# 60-degree Flemish tullegrond lattice
HEX_RADIUS = 8.6              # Circumradius of each hexagonal tulle cell
SPIDER_MOD = 4                # Placement cadence ((r + 2*c) % SPIDER_MOD == 0)

# Cloth-stitch (linnenslag) micro-perforation mask inside XL RT
WEAVE_STEP = 2.95
WEAVE_HOLE_R = 0.56
WEAVE_RIM_PAD = 2.3

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


# =============================================================================
# 1. Exact Geometric RT Monogram Paths (centered around (0, 0))
# =============================================================================

R_PATH_D = (
    "M -49 -38 "
    "H -23 "
    "C -8 -38, -2 -29.5, -2 -16.5 "
    "C -2 -6.5, -6.5 1.0, -15.5 4.2 "
    "L -2.5 38 "
    "H -16.5 "
    "L -28.0 6.0 "
    "H -36.0 "
    "V 38 "
    "H -49 "
    "Z "
    "M -36 -25.5 "
    "V -6.2 "
    "H -23.5 "
    "C -17.5 -6.2, -14.8 -10.2, -14.8 -16.2 "
    "C -14.8 -22.2, -17.5 -25.5, -23.5 -25.5 "
    "Z"
)

T_PATH_D = (
    "M 4.0 -38 "
    "H 50.0 "
    "V -25.2 "
    "H 33.5 "
    "V 38 "
    "H 20.5 "
    "V -25.2 "
    "H 4.0 "
    "Z"
)


# =============================================================================
# 2. Continuous Seam-Free SDF for RT & R-Counter Guard
# =============================================================================

def _sd_box(px: float, py: float, x0: float, y0: float, x1: float, y1: float) -> float:
    cx = 0.5 * (x0 + x1)
    cy = 0.5 * (y0 + y1)
    bx = 0.5 * (x1 - x0)
    by = 0.5 * (y1 - y0)
    dx = abs(px - cx) - bx
    dy = abs(py - cy) - by
    return math.hypot(max(dx, 0.0), max(dy, 0.0)) + min(max(dx, dy), 0.0)


def _sd_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    pax = px - ax
    pay = py - ay
    bax = bx - ax
    bay = by - ay
    denom = bax * bax + bay * bay
    h = max(0.0, min(1.0, (pax * bax + pay * bay) / denom)) if denom > 0 else 0.0
    return math.hypot(pax - bax * h, pay - bay * h)


def _sd_quad(px: float, py: float, pts: list[tuple[float, float]]) -> float:
    n = len(pts)
    min_d2 = float("inf")
    inside_ccw = True
    inside_cw = True
    for i in range(n):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % n]
        d = _sd_segment(px, py, ax, ay, bx, by)
        if d * d < min_d2:
            min_d2 = d * d
        cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
        if cross < 0:
            inside_ccw = False
        if cross > 0:
            inside_cw = False
    d = math.sqrt(min_d2)
    return -d if (inside_ccw or inside_cw) else d


def _sd_r_hole(x: float, y: float) -> float:
    d_hole_rect = _sd_box(x, y, -36.0, -25.5, -23.5, -6.2)
    hx = (x + 23.5) / 8.7
    hy = (y + 15.85) / 9.65
    d_hole_ell = (math.hypot(hx, hy) - 1.0) * 9.1
    return min(d_hole_rect, d_hole_ell)


def is_in_r_counter(x: float, y: float, pad: float = 0.8) -> bool:
    return _sd_r_hole(x, y) <= pad


def sdf_r(x: float, y: float) -> float:
    d_stem = _sd_box(x, y, -49.0, -38.0, -36.0, 38.0)
    d_bowl_rect = _sd_box(x, y, -49.0, -38.0, -23.0, 6.0)
    ex = (x + 23.0) / 21.0
    ey = (y + 16.0) / 22.0
    d_bowl_ell = (math.hypot(ex, ey) - 1.0) * 21.5
    d_bowl_outer = min(d_bowl_rect, d_bowl_ell)
    d_hole = _sd_r_hole(x, y)
    d_bowl = max(d_bowl_outer, -d_hole)
    d_leg = _sd_quad(x, y, [(-28.0, 6.0), (-15.5, 4.2), (-2.5, 38.0), (-16.5, 38.0)])
    return min(d_stem, d_bowl, d_leg)


def sdf_t(x: float, y: float) -> float:
    d_bar = _sd_box(x, y, 4.0, -38.0, 50.0, -25.2)
    d_stem = _sd_box(x, y, 20.5, -38.0, 33.5, 38.0)
    return min(d_bar, d_stem)


def sdf_rt(x: float, y: float) -> float:
    return min(sdf_r(x, y), sdf_t(x, y))


def sdf_rt_gradient(x: float, y: float) -> tuple[float, float]:
    eps = 0.25
    gx = sdf_rt(x + eps, y) - sdf_rt(x - eps, y)
    gy = sdf_rt(x, y + eps) - sdf_rt(x, y - eps)
    n = math.hypot(gx, gy)
    if n < 1e-6:
        return (1.0, 0.0)
    return (gx / n, gy / n)


def closest_rt_point(x: float, y: float, steps: int = 5) -> tuple[float, float]:
    px, py = x, y
    for _ in range(steps):
        d = sdf_rt(px, py)
        gx, gy = sdf_rt_gradient(px, py)
        px -= d * gx
        py -= d * gy
    return (px, py)


# =============================================================================
# 3. Geometry & Polygon Utilities
# =============================================================================

def fmt(v: float) -> str:
    s = f"{v:.2f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def point_in_poly(x: float, y: float, poly: list[tuple[float, float]]) -> bool:
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def sd_poly(x: float, y: float, poly: list[tuple[float, float]]) -> float:
    n = len(poly)
    min_d2 = float("inf")
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        d = _sd_segment(x, y, ax, ay, bx, by)
        if d * d < min_d2:
            min_d2 = d * d
    d = math.sqrt(min_d2)
    return -d if point_in_poly(x, y, poly) else d


def closest_poly_point(x: float, y: float, poly: list[tuple[float, float]]) -> tuple[float, float]:
    n = len(poly)
    best_d2 = float("inf")
    best_pt = poly[0]
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        bax, bay = bx - ax, by - ay
        denom = bax * bax + bay * bay
        h = max(0.0, min(1.0, ((x - ax) * bax + (y - ay) * bay) / denom)) if denom > 0 else 0.0
        qx, qy = ax + h * bax, ay + h * bay
        d2 = (x - qx) ** 2 + (y - qy) ** 2
        if d2 < best_d2:
            best_d2 = d2
            best_pt = (qx, qy)
    return best_pt


def bisect_boundary(
    p_in: tuple[float, float],
    p_out: tuple[float, float],
    fn,
    target: float = 0.0,
    iters: int = 14,
) -> tuple[float, float]:
    lo_x, lo_y = p_in
    hi_x, hi_y = p_out
    v_lo = fn(lo_x, lo_y) - target
    for _ in range(iters):
        mx, my = 0.5 * (lo_x + hi_x), 0.5 * (lo_y + hi_y)
        v_m = fn(mx, my) - target
        if (v_lo <= 0 and v_m <= 0) or (v_lo >= 0 and v_m >= 0):
            lo_x, lo_y, v_lo = mx, my, v_m
        else:
            hi_x, hi_y = mx, my
    return (0.5 * (lo_x + hi_x), 0.5 * (lo_y + hi_y))


def closed_path(pts: list[tuple[float, float]]) -> str:
    parts = [f"M {fmt(pts[0][0])} {fmt(pts[0][1])}"]
    for x, y in pts[1:]:
        parts.append(f"L {fmt(x)} {fmt(y)}")
    parts.append("Z")
    return " ".join(parts)


def make_picot_loop(x: float, y: float, angle: float, length: float = 4.2, width: float = 1.9) -> str:
    ux, uy = math.cos(angle), math.sin(angle)
    nx, ny = -uy, ux
    tip_x, tip_y = x + ux * length, y + uy * length
    c1x, c1y = x + ux * (length * 0.72) + nx * width, y + uy * (length * 0.72) + ny * width
    c2x, c2y = x + ux * (length * 0.72) - nx * width, y + uy * (length * 0.72) - ny * width
    b1x, b1y = x + nx * (width * 0.36), y + ny * (width * 0.36)
    b2x, b2y = x - nx * (width * 0.36), y - ny * (width * 0.36)
    return (
        f"M {fmt(b1x)} {fmt(b1y)} "
        f"Q {fmt(c1x)} {fmt(c1y)}, {fmt(tip_x)} {fmt(tip_y)} "
        f"Q {fmt(c2x)} {fmt(c2y)}, {fmt(b2x)} {fmt(b2y)}"
    )


# =============================================================================
# 4. Precompute Canonical Schelprand Lace Geometry
# =============================================================================

def _schelp_r(theta: float) -> float:
    return RIBBON_BASE_R + RIBBON_AMP * math.sqrt(math.cos(4.0 * theta) ** 2 + RIBBON_SMOOTH)


def build_geometry() -> dict[str, object]:
    """Compute all deterministic vector layers once for reuse across SVG variants."""
    # 4a. Arc-length-uniform closed Bruges lintkant ribbon
    n_raw = 720
    raw_pts: list[tuple[float, float]] = []
    cum_s: list[float] = [0.0]
    for i in range(n_raw):
        th = (2.0 * math.pi * i) / n_raw
        r = _schelp_r(th)
        px, py = r * math.cos(th), r * math.sin(th)
        raw_pts.append((px, py))
        if i > 0:
            cum_s.append(cum_s[-1] + math.hypot(px - raw_pts[-2][0], py - raw_pts[-2][1]))
    total_len = cum_s[-1] + math.hypot(raw_pts[0][0] - raw_pts[-1][0], raw_pts[0][1] - raw_pts[-1][1])

    spine: list[tuple[float, float]] = []
    raw_idx = 0
    raw_closed = raw_pts + [raw_pts[0]]
    cum_closed = cum_s + [total_len]
    for k in range(RIBBON_SAMPLES):
        s_target = (k * total_len) / RIBBON_SAMPLES
        while raw_idx < n_raw - 1 and cum_closed[raw_idx + 1] < s_target:
            raw_idx += 1
        s0, s1 = cum_closed[raw_idx], cum_closed[raw_idx + 1]
        t = (s_target - s0) / (s1 - s0) if (s1 > s0) else 0.0
        ax, ay = raw_closed[raw_idx]
        bx, by = raw_closed[raw_idx + 1]
        spine.append((ax + t * (bx - ax), ay + t * (by - ay)))

    outer_pts: list[tuple[float, float]] = []
    inner_pts: list[tuple[float, float]] = []
    cross_ticks: list[str] = []
    picots_xl: list[str] = []
    m_beads: list[str] = []

    for i in range(RIBBON_SAMPLES):
        p_prev = spine[(i - 1) % RIBBON_SAMPLES]
        p_next = spine[(i + 1) % RIBBON_SAMPLES]
        x, y = spine[i]
        tx, ty = p_next[0] - p_prev[0], p_next[1] - p_prev[1]
        tl = math.hypot(tx, ty) or 1.0
        tx, ty = tx / tl, ty / tl
        nx, ny = ty, -tx
        if nx * x + ny * y < 0:
            nx, ny = -nx, -ny

        p_out = (x + nx * RIBBON_HALF_WIDTH, y + ny * RIBBON_HALF_WIDTH)
        p_in = (x - nx * RIBBON_HALF_WIDTH, y - ny * RIBBON_HALF_WIDTH)
        outer_pts.append(p_out)
        inner_pts.append(p_in)

        tilt = 0.72 if (i % 2 == 0) else -0.72
        cross_ticks.append(
            f'<line x1="{fmt(p_out[0] + tx * tilt)}" y1="{fmt(p_out[1] + ty * tilt)}" '
            f'x2="{fmt(p_in[0] - tx * tilt)}" y2="{fmt(p_in[1] - ty * tilt)}"/>'
        )

        if i % PICOT_EVERY == 0:
            ang = math.atan2(ny, nx)
            picots_xl.append(
                f'<path class="line" stroke-width="0.82" d="{make_picot_loop(p_out[0], p_out[1], ang)}"/>'
            )
            if i % (PICOT_EVERY * 2) == 0:
                bx, by = p_out[0] + nx * 2.1, p_out[1] + ny * 2.1
                m_beads.append(f'<circle class="ink" cx="{fmt(bx)}" cy="{fmt(by)}" r="1.4"/>')

    # 4b. Cloth-stitch (linnenslag) mask holes inside XL RT (explicit #000000 cutouts)
    weave_holes: list[str] = []
    row = 0
    for wy in [i * (WEAVE_STEP * 0.86) for i in range(-17, 18)]:
        offset = (WEAVE_STEP * 0.5) if (row % 2) else 0.0
        for wx in [j * WEAVE_STEP + offset for j in range(-20, 21)]:
            if sdf_rt(wx, wy) <= -WEAVE_RIM_PAD:
                r = WEAVE_HOLE_R
                weave_holes.append(
                    f'<polygon points="{fmt(wx)},{fmt(wy-r)} {fmt(wx+r)},{fmt(wy)} '
                    f'{fmt(wx)},{fmt(wy+r)} {fmt(wx-r)},{fmt(wy)}" fill="#000000"/>'
                )
        row += 1

    # 4c. 60-degree Flemish tullegrond lattice with flush dual anchoring
    dx_col = math.sqrt(3) * HEX_RADIUS
    dy_row = 1.5 * HEX_RADIUS

    hex_centers: list[tuple[int, int, float, float]] = []
    for r_idx in range(-10, 11):
        for c_idx in range(-10, 11):
            cx = (c_idx + (0.5 if (r_idx % 2) else 0.0)) * dx_col
            cy = r_idx * dy_row
            if math.hypot(cx, cy) < 120.0:
                hex_centers.append((r_idx, c_idx, cx, cy))

    def hex_vertices(cx: float, cy: float) -> list[tuple[float, float]]:
        return [
            (
                round(cx + HEX_RADIUS * math.cos(math.radians(30 + 60 * k)), 2),
                round(cy + HEX_RADIUS * math.sin(math.radians(30 + 60 * k)), 2),
            )
            for k in range(6)
        ]

    def vkey(x: float, y: float) -> tuple[int, int]:
        return (int(round(x * 10)), int(round(y * 10)))

    edge_seen: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    cand_edges: list[tuple[tuple[float, float], tuple[float, float]]] = []
    spiders_xl: list[str] = []

    for r_idx, c_idx, cx, cy in hex_centers:
        verts = hex_vertices(cx, cy)
        d_rt_c = sdf_rt(cx, cy)
        d_rib_c = -sd_poly(cx, cy, inner_pts)
        if d_rt_c >= 10.2 and d_rib_c >= 9.5 and ((r_idx + 2 * c_idx) % SPIDER_MOD == 0):
            for vx, vy in verts:
                spiders_xl.append(
                    f'<line x1="{fmt(cx)}" y1="{fmt(cy)}" x2="{fmt(vx)}" y2="{fmt(vy)}"/>'
                )
            spiders_xl.append(f'<circle class="ink" cx="{fmt(cx)}" cy="{fmt(cy)}" r="1.6"/>')

        for k in range(6):
            p1, p2 = verts[k], verts[(k + 1) % 6]
            k1, k2 = vkey(*p1), vkey(*p2)
            ek = (k1, k2) if k1 < k2 else (k2, k1)
            if ek not in edge_seen:
                edge_seen.add(ek)
                cand_edges.append((p1, p2))

    def is_cavity_pt(x: float, y: float) -> bool:
        return (
            sdf_rt(x, y) >= 2.0
            and sd_poly(x, y, inner_pts) <= -1.4
            and not is_in_r_counter(x, y, pad=0.8)
        )

    interior_edges: list[tuple[tuple[int, int], tuple[int, int], tuple[float, float], tuple[float, float]]] = []
    ribbon_anchors: list[tuple[tuple[int, int], tuple[float, float], tuple[float, float]]] = []
    rt_anchors: list[tuple[tuple[int, int], tuple[float, float], tuple[float, float]]] = []
    v_coords: dict[tuple[int, int], tuple[float, float]] = {}

    for p1, p2 in cand_edges:
        c1, c2 = is_cavity_pt(*p1), is_cavity_pt(*p2)
        if not c1 and not c2:
            continue
        k1, k2 = vkey(*p1), vkey(*p2)
        if c1 and c2:
            mx, my = 0.5 * (p1[0] + p2[0]), 0.5 * (p1[1] + p2[1])
            if sdf_rt(mx, my) >= 0.8 and sd_poly(mx, my, inner_pts) <= -0.3 and not is_in_r_counter(mx, my, pad=0.4):
                interior_edges.append((k1, k2, p1, p2))
                v_coords[k1] = p1
                v_coords[k2] = p2
            continue

        p_in, k_in, p_out = (p1, k1, p2) if c1 else (p2, k2, p1)
        v_coords[k_in] = p_in

        if sd_poly(*p_out, inner_pts) > -1.4 and sdf_rt(*p_out) >= 0.0:
            p_hit = bisect_boundary(p_in, p_out, lambda x, y: sd_poly(x, y, inner_pts), target=0.0)
            if math.hypot(p_hit[0] - p_in[0], p_hit[1] - p_in[1]) >= 1.2:
                ribbon_anchors.append((k_in, p_in, p_hit))
        elif sdf_rt(*p_out) < 2.0 and not is_in_r_counter(*p_out, pad=1.0):
            p_hit = bisect_boundary(p_in, p_out, sdf_rt, target=-0.35)
            if not is_in_r_counter(*p_hit, pad=0.6) and math.hypot(p_hit[0] - p_in[0], p_hit[1] - p_in[1]) >= 1.2:
                rt_anchors.append((k_in, p_in, p_hit))

    deg: dict[tuple[int, int], int] = {}
    for k1, k2, _, _ in interior_edges:
        deg[k1] = deg.get(k1, 0) + 1
        deg[k2] = deg.get(k2, 0) + 1
    for k_in, _, _ in ribbon_anchors:
        deg[k_in] = deg.get(k_in, 0) + 1
    for k_in, _, _ in rt_anchors:
        deg[k_in] = deg.get(k_in, 0) + 1

    # Bridge any remaining degree-1 vertices to nearest surface, else prune
    for kv, d_val in list(deg.items()):
        if d_val != 1:
            continue
        vx, vy = v_coords[kv]
        d_rt = sdf_rt(vx, vy)
        d_rib = -sd_poly(vx, vy, inner_pts)
        if d_rt <= d_rib and d_rt <= 11.5:
            tx, ty = closest_rt_point(vx, vy, steps=5)
            if not is_in_r_counter(tx, ty, pad=0.6):
                gx, gy = sdf_rt_gradient(tx, ty)
                rt_anchors.append((kv, (vx, vy), (tx - 0.35 * gx, ty - 0.35 * gy)))
                deg[kv] = 2
        elif d_rib <= 11.5:
            hx, hy = closest_poly_point(vx, vy, inner_pts)
            ribbon_anchors.append((kv, (vx, vy), (hx, hy)))
            deg[kv] = 2

    changed = True
    while changed:
        changed = False
        dead = {kv for kv, d_val in deg.items() if d_val == 1}
        if not dead:
            break
        new_int = []
        for k1, k2, p1, p2 in interior_edges:
            if k1 in dead or k2 in dead:
                deg[k1] = max(0, deg[k1] - 1)
                deg[k2] = max(0, deg[k2] - 1)
                changed = True
            else:
                new_int.append((k1, k2, p1, p2))
        interior_edges = new_int
        ribbon_anchors = [r for r in ribbon_anchors if r[0] not in dead]
        rt_anchors = [r for r in rt_anchors if r[0] not in dead]

    mesh_lines: list[str] = [
        f'<line x1="{fmt(p1[0])}" y1="{fmt(p1[1])}" x2="{fmt(p2[0])}" y2="{fmt(p2[1])}"/>'
        for _, _, p1, p2 in interior_edges
    ]
    anchor_beads: list[str] = []
    for _, p_in, p_hit in ribbon_anchors:
        mesh_lines.append(f'<line x1="{fmt(p_in[0])}" y1="{fmt(p_in[1])}" x2="{fmt(p_hit[0])}" y2="{fmt(p_hit[1])}"/>')
        anchor_beads.append(f'<circle class="ink" cx="{fmt(p_hit[0])}" cy="{fmt(p_hit[1])}" r="1.25"/>')
    for _, p_in, p_hit in rt_anchors:
        mesh_lines.append(f'<line x1="{fmt(p_in[0])}" y1="{fmt(p_in[1])}" x2="{fmt(p_hit[0])}" y2="{fmt(p_hit[1])}"/>')
        if math.hypot(p_hit[0] - p_in[0], p_hit[1] - p_in[1]) >= 5.2:
            mx, my = 0.5 * (p_in[0] + p_hit[0]), 0.5 * (p_in[1] + p_hit[1])
            anchor_beads.append(f'<circle class="ink" cx="{fmt(mx)}" cy="{fmt(my)}" r="1.1"/>')

    pin_nodes: list[str] = [
        f'<circle class="ink" cx="{fmt(v_coords[kv][0])}" cy="{fmt(v_coords[kv][1])}" r="1.22"/>'
        for kv, d_val in deg.items()
        if d_val >= 2
    ]

    # 4d. S-tier simplified scalloped lace contour + 10 flush tralien anchors to 1.36x RT
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
        "spiders_xl": "".join(spiders_xl),
        "center_path": closed_path(spine),
        "outer_path": closed_path(outer_pts),
        "inner_path": closed_path(inner_pts),
        "cross_ticks": "".join(cross_ticks),
        "picots_xl": "".join(picots_xl),
        "m_beads": "".join(m_beads),
        "mesh_lines": "".join(mesh_lines),
        "pin_nodes": "".join(pin_nodes),
        "anchor_beads": "".join(anchor_beads),
        "s_ring_path": s_ring_path,
        "s_beads": "".join(s_beads),
        "s_anchors": "".join(s_anchors),
    }


# =============================================================================
# 5. SVG Serialization (Responsive Masters, Auto Light/Dark Favicon, Static LOD)
# =============================================================================

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


# =============================================================================
# 6. Raster PNG / ICO / Touch Icon Export
# =============================================================================

def render_png(svg_path: Path, png_path: Path, size: int) -> None:
    subprocess.run(
        ["rsvg-convert", "-w", str(size), "-h", str(size), str(svg_path), "-o", str(png_path)],
        check=True,
    )


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
        render_png(src_svg, dst_png, px)
        print(f"Rendered {dst_png.relative_to(OUT_DIR)} ({px}x{px})")

    # Apple touch icon (180x180 on solid #f8f9ff RT surface with generous safe padding)
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        touch_fg = tmp / "touch_148.png"
        render_png(SVG_DIR / "rt-logo-m.svg", touch_fg, 148)
        canvas = Image.new("RGBA", (180, 180), "#f8f9ff")
        fg = Image.open(touch_fg).convert("RGBA")
        canvas.alpha_composite(fg, dest=(16, 16))
        canvas.convert("RGB").save(OUT_DIR / "apple-touch-icon.png", format="PNG")
        print("Rendered apple-touch-icon.png (180x180)")

        # Multi-size favicon.ico (16px XS, 32px XS, 48px S)
        ico_48 = tmp / "ico_48.png"
        render_png(SVG_DIR / "rt-logo-s.svg", ico_48, 48)
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
