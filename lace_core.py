#!/usr/bin/env python3
"""Shared procedural Bruges bobbin-lace geometry and SVG/raster utilities.

Provides canonical parameters, continuous SDFs, arc-length-uniform ribbon
builders, 60-degree Flemish tullegrond mesh generators (both bounded and
periodically seamless), font-to-path wordmark compilation, and raster export.
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path
from typing import Callable, Iterable

# =============================================================================
# Canonical Tunable Geometric & LOD Parameters
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

# Cloth-stitch (linnenslag) micro-perforation mask inside XL motifs
WEAVE_STEP = 2.95
WEAVE_HOLE_R = 0.56
WEAVE_RIM_PAD = 2.3


# =============================================================================
# 1. Exact Geometric RT Monogram Paths & SDF (centered around (0, 0))
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


def sd_box(px: float, py: float, x0: float, y0: float, x1: float, y1: float) -> float:
    cx = 0.5 * (x0 + x1)
    cy = 0.5 * (y0 + y1)
    bx = 0.5 * (x1 - x0)
    by = 0.5 * (y1 - y0)
    dx = abs(px - cx) - bx
    dy = abs(py - cy) - by
    return math.hypot(max(dx, 0.0), max(dy, 0.0)) + min(max(dx, dy), 0.0)


def sd_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    pax = px - ax
    pay = py - ay
    bax = bx - ax
    bay = by - ay
    denom = bax * bax + bay * bay
    h = max(0.0, min(1.0, (pax * bax + pay * bay) / denom)) if denom > 0 else 0.0
    return math.hypot(pax - bax * h, pay - bay * h)


def sd_quad(px: float, py: float, pts: list[tuple[float, float]]) -> float:
    n = len(pts)
    min_d2 = float("inf")
    inside_ccw = True
    inside_cw = True
    for i in range(n):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % n]
        d = sd_segment(px, py, ax, ay, bx, by)
        if d * d < min_d2:
            min_d2 = d * d
        cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
        if cross < 0:
            inside_ccw = False
        if cross > 0:
            inside_cw = False
    d = math.sqrt(min_d2)
    return -d if (inside_ccw or inside_cw) else d


def sd_r_hole(x: float, y: float) -> float:
    d_hole_rect = sd_box(x, y, -36.0, -25.5, -23.5, -6.2)
    hx = (x + 23.5) / 8.7
    hy = (y + 15.85) / 9.65
    d_hole_ell = (math.hypot(hx, hy) - 1.0) * 9.1
    return min(d_hole_rect, d_hole_ell)


def is_in_r_counter(x: float, y: float, pad: float = 0.8) -> bool:
    return sd_r_hole(x, y) <= pad


def sdf_r(x: float, y: float) -> float:
    d_stem = sd_box(x, y, -49.0, -38.0, -36.0, 38.0)
    d_bowl_rect = sd_box(x, y, -49.0, -38.0, -23.0, 6.0)
    ex = (x + 23.0) / 21.0
    ey = (y + 16.0) / 22.0
    d_bowl_ell = (math.hypot(ex, ey) - 1.0) * 21.5
    d_bowl_outer = min(d_bowl_rect, d_bowl_ell)
    d_hole = sd_r_hole(x, y)
    d_bowl = max(d_bowl_outer, -d_hole)
    d_leg = sd_quad(x, y, [(-28.0, 6.0), (-15.5, 4.2), (-2.5, 38.0), (-16.5, 38.0)])
    return min(d_stem, d_bowl, d_leg)


def sdf_t(x: float, y: float) -> float:
    d_bar = sd_box(x, y, 4.0, -38.0, 50.0, -25.2)
    d_stem = sd_box(x, y, 20.5, -38.0, 33.5, 38.0)
    return min(d_bar, d_stem)


def sdf_rt(x: float, y: float) -> float:
    return min(sdf_r(x, y), sdf_t(x, y))


# =============================================================================
# 2. General SDF, Polygon & SVG Formatting Utilities
# =============================================================================

def fmt(v: float) -> str:
    s = f"{v:.2f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def sdf_gradient(
    sdf_fn: Callable[[float, float], float],
    x: float,
    y: float,
    eps: float = 0.25,
) -> tuple[float, float]:
    gx = sdf_fn(x + eps, y) - sdf_fn(x - eps, y)
    gy = sdf_fn(x, y + eps) - sdf_fn(x, y - eps)
    n = math.hypot(gx, gy)
    if n < 1e-6:
        return (1.0, 0.0)
    return (gx / n, gy / n)


def closest_sdf_point(
    sdf_fn: Callable[[float, float], float],
    x: float,
    y: float,
    steps: int = 5,
) -> tuple[float, float]:
    px, py = x, y
    for _ in range(steps):
        d = sdf_fn(px, py)
        gx, gy = sdf_gradient(sdf_fn, px, py)
        px -= d * gx
        py -= d * gy
    return (px, py)


def sdf_rt_gradient(x: float, y: float) -> tuple[float, float]:
    return sdf_gradient(sdf_rt, x, y)


def closest_rt_point(x: float, y: float, steps: int = 5) -> tuple[float, float]:
    return closest_sdf_point(sdf_rt, x, y, steps=steps)


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
        d = sd_segment(x, y, ax, ay, bx, by)
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
    fn: Callable[[float, float], float],
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
# 3. Arc-Length-Uniform Ribbon Spines & Lintkant Builder
# =============================================================================

def resample_closed_curve(raw_pts: list[tuple[float, float]], n_samples: int) -> list[tuple[float, float]]:
    """Resample a closed polyline uniformly by arc length."""
    n_raw = len(raw_pts)
    cum_s: list[float] = [0.0]
    for i in range(1, n_raw):
        px, py = raw_pts[i]
        cum_s.append(cum_s[-1] + math.hypot(px - raw_pts[i - 1][0], py - raw_pts[i - 1][1]))
    total_len = cum_s[-1] + math.hypot(raw_pts[0][0] - raw_pts[-1][0], raw_pts[0][1] - raw_pts[-1][1])

    spine: list[tuple[float, float]] = []
    raw_idx = 0
    raw_closed = raw_pts + [raw_pts[0]]
    cum_closed = cum_s + [total_len]
    for k in range(n_samples):
        s_target = (k * total_len) / n_samples
        while raw_idx < n_raw - 1 and cum_closed[raw_idx + 1] < s_target:
            raw_idx += 1
        s0, s1 = cum_closed[raw_idx], cum_closed[raw_idx + 1]
        t = (s_target - s0) / (s1 - s0) if (s1 > s0) else 0.0
        ax, ay = raw_closed[raw_idx]
        bx, by = raw_closed[raw_idx + 1]
        spine.append((ax + t * (bx - ax), ay + t * (by - ay)))
    return spine


def schelp_r(theta: float) -> float:
    return RIBBON_BASE_R + RIBBON_AMP * math.sqrt(math.cos(4.0 * theta) ** 2 + RIBBON_SMOOTH)


def build_schelprand_spine(n_raw: int = 720, n_samples: int = RIBBON_SAMPLES) -> list[tuple[float, float]]:
    """Build the canonical 8-arch circular Bruges schelprand ribbon spine."""
    raw_pts: list[tuple[float, float]] = []
    for i in range(n_raw):
        th = (2.0 * math.pi * i) / n_raw
        r = schelp_r(th)
        raw_pts.append((r * math.cos(th), r * math.sin(th)))
    return resample_closed_curve(raw_pts, n_samples)


def build_cartouche_spine(
    half_w: float,
    half_h: float,
    exponent: float = 0.68,
    lobe_count: int = 24,
    scallop_amp: float = 13.5,
    scallop_smooth: float = 0.03,
    n_raw: int = 2048,
    n_samples: int = 864,
) -> list[tuple[float, float]]:
    """Build an elongated 4-way-symmetric scalloped Bruges cartouche spine."""
    base_raw: list[tuple[float, float]] = []
    for i in range(n_raw):
        t = (2.0 * math.pi * i) / n_raw
        ct = math.cos(t)
        st = math.sin(t)
        x = half_w * math.copysign(abs(ct) ** exponent, ct)
        y = half_h * math.copysign(abs(st) ** exponent, st)
        base_raw.append((x, y))

    base_uniform = resample_closed_curve(base_raw, n_raw)
    scalloped_raw: list[tuple[float, float]] = []
    half_lobes = lobe_count / 2.0
    for i in range(n_raw):
        p_prev = base_uniform[(i - 1) % n_raw]
        p_next = base_uniform[(i + 1) % n_raw]
        x, y = base_uniform[i]
        tx, ty = p_next[0] - p_prev[0], p_next[1] - p_prev[1]
        tl = math.hypot(tx, ty) or 1.0
        tx, ty = tx / tl, ty / tl
        nx, ny = ty, -tx
        if nx * x + ny * y < 0:
            nx, ny = -nx, -ny
        u = i / n_raw
        offset = scallop_amp * math.sqrt(math.cos(half_lobes * 2.0 * math.pi * u) ** 2 + scallop_smooth)
        scalloped_raw.append((x + nx * offset, y + ny * offset))

    return resample_closed_curve(scalloped_raw, n_samples)


def build_lintkant_ribbon(
    spine: list[tuple[float, float]],
    half_width: float = RIBBON_HALF_WIDTH,
    picot_every: int = PICOT_EVERY,
) -> dict[str, object]:
    """Generate double rails, linen cross-ticks, center warp, and outward picots."""
    n = len(spine)
    outer_pts: list[tuple[float, float]] = []
    inner_pts: list[tuple[float, float]] = []
    cross_ticks: list[str] = []
    picots_xl: list[str] = []
    m_beads: list[str] = []

    for i in range(n):
        p_prev = spine[(i - 1) % n]
        p_next = spine[(i + 1) % n]
        x, y = spine[i]
        tx, ty = p_next[0] - p_prev[0], p_next[1] - p_prev[1]
        tl = math.hypot(tx, ty) or 1.0
        tx, ty = tx / tl, ty / tl
        nx, ny = ty, -tx
        if nx * x + ny * y < 0:
            nx, ny = -nx, -ny

        p_out = (x + nx * half_width, y + ny * half_width)
        p_in = (x - nx * half_width, y - ny * half_width)
        outer_pts.append(p_out)
        inner_pts.append(p_in)

        tilt = 0.72 if (i % 2 == 0) else -0.72
        cross_ticks.append(
            f'<line x1="{fmt(p_out[0] + tx * tilt)}" y1="{fmt(p_out[1] + ty * tilt)}" '
            f'x2="{fmt(p_in[0] - tx * tilt)}" y2="{fmt(p_in[1] - ty * tilt)}"/>'
        )

        if i % picot_every == 0:
            ang = math.atan2(ny, nx)
            picots_xl.append(
                f'<path class="line" stroke-width="0.82" d="{make_picot_loop(p_out[0], p_out[1], ang)}"/>'
            )
            if i % (picot_every * 2) == 0:
                bx, by = p_out[0] + nx * 2.1, p_out[1] + ny * 2.1
                m_beads.append(f'<circle class="ink" cx="{fmt(bx)}" cy="{fmt(by)}" r="1.4"/>')

    return {
        "outer_pts": outer_pts,
        "inner_pts": inner_pts,
        "center_path": closed_path(spine),
        "outer_path": closed_path(outer_pts),
        "inner_path": closed_path(inner_pts),
        "cross_ticks": "".join(cross_ticks),
        "picots_xl": "".join(picots_xl),
        "m_beads": "".join(m_beads),
    }


# =============================================================================
# 4. Cloth-Stitch (Linnenslag) Mask Cutouts
# =============================================================================

def build_weave_holes(
    sdf_fn: Callable[[float, float], float],
    y_indices: Iterable[int],
    x_indices: Iterable[int],
    step: float = WEAVE_STEP,
    hole_r: float = WEAVE_HOLE_R,
    rim_pad: float = WEAVE_RIM_PAD,
) -> list[str]:
    """Generate invariant #000000 diamond mask holes inside solid letter ink."""
    weave_holes: list[str] = []
    x_list = list(x_indices)
    row = 0
    for wy in [i * (step * 0.86) for i in y_indices]:
        offset = (step * 0.5) if (row % 2) else 0.0
        for wx in [j * step + offset for j in x_list]:
            if sdf_fn(wx, wy) <= -rim_pad:
                r = hole_r
                weave_holes.append(
                    f'<polygon points="{fmt(wx)},{fmt(wy-r)} {fmt(wx+r)},{fmt(wy)} '
                    f'{fmt(wx)},{fmt(wy+r)} {fmt(wx-r)},{fmt(wy)}" fill="#000000"/>'
                )
        row += 1
    return weave_holes


def build_weave_holes_in_bbox(
    sdf_fn: Callable[[float, float], float],
    bounds: tuple[float, float, float, float],
    step: float = WEAVE_STEP,
    hole_r: float = WEAVE_HOLE_R,
    rim_pad: float = WEAVE_RIM_PAD,
) -> list[str]:
    """Compute integer grid bounds for `bounds` and emit cloth-stitch mask holes."""
    x0, y0, x1, y1 = bounds
    dy = step * 0.86
    y_min_i = math.floor(y0 / dy) - 1
    y_max_i = math.ceil(y1 / dy) + 1
    x_min_j = math.floor(x0 / step) - 2
    x_max_j = math.ceil(x1 / step) + 2
    return build_weave_holes(
        sdf_fn,
        range(y_min_i, y_max_i + 1),
        range(x_min_j, x_max_j + 1),
        step=step,
        hole_r=hole_r,
        rim_pad=rim_pad,
    )


# =============================================================================
# 5. Bounded 60-Degree Flemish Tullegrond + Spinnen Builder
# =============================================================================

def build_tullegrond_in_ribbon(
    inner_pts: list[tuple[float, float]],
    hex_radius: float = HEX_RADIUS,
    spider_mod: int = SPIDER_MOD,
    motif_sdf: Callable[[float, float], float] | None = None,
    counter_guard: Callable[..., bool] | None = None,
    channel_guard: Callable[[float, float], bool] | None = None,
    r_range: range | None = None,
    c_range: range | None = None,
    max_radius: float | None = None,
) -> dict[str, object]:
    """Build 60-degree tullegrond mesh + 6-legged spiders with flush dual anchoring."""
    dx_col = math.sqrt(3) * hex_radius
    dy_row = 1.5 * hex_radius

    if r_range is None or c_range is None:
        xs = [p[0] for p in inner_pts]
        ys = [p[1] for p in inner_pts]
        if r_range is None:
            r_min = math.floor((min(ys) - 2.0 * hex_radius) / dy_row)
            r_max = math.ceil((max(ys) + 2.0 * hex_radius) / dy_row)
            r_range = range(r_min, r_max + 1)
        if c_range is None:
            c_min = math.floor((min(xs) - 2.0 * hex_radius) / dx_col) - 1
            c_max = math.ceil((max(xs) + 2.0 * hex_radius) / dx_col) + 1
            c_range = range(c_min, c_max + 1)

    hex_centers: list[tuple[int, int, float, float]] = []
    for r_idx in r_range:
        for c_idx in c_range:
            cx = (c_idx + (0.5 if (r_idx % 2) else 0.0)) * dx_col
            cy = r_idx * dy_row
            if max_radius is not None:
                keep = math.hypot(cx, cy) < max_radius
            else:
                keep = sd_poly(cx, cy, inner_pts) <= 2.5 * hex_radius
            if keep:
                hex_centers.append((r_idx, c_idx, cx, cy))

    def hex_vertices(cx: float, cy: float) -> list[tuple[float, float]]:
        return [
            (
                round(cx + hex_radius * math.cos(math.radians(30 + 60 * k)), 2),
                round(cy + hex_radius * math.sin(math.radians(30 + 60 * k)), 2),
            )
            for k in range(6)
        ]

    def vkey(x: float, y: float) -> tuple[int, int]:
        return (int(round(x * 10)), int(round(y * 10)))

    edge_seen: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    cand_edges: list[tuple[tuple[float, float], tuple[float, float]]] = []
    spider_cands: list[tuple[float, float, list[tuple[float, float]]]] = []

    for r_idx, c_idx, cx, cy in hex_centers:
        verts = hex_vertices(cx, cy)
        d_motif_c = motif_sdf(cx, cy) if motif_sdf is not None else 999.0
        d_rib_c = -sd_poly(cx, cy, inner_pts)
        in_channel = channel_guard(cx, cy) if channel_guard is not None else False
        if (
            d_motif_c >= 10.2
            and d_rib_c >= 9.5
            and not in_channel
            and ((r_idx + 2 * c_idx) % spider_mod == 0)
        ):
            spider_cands.append((cx, cy, verts))

        for k in range(6):
            p1, p2 = verts[k], verts[(k + 1) % 6]
            k1, k2 = vkey(*p1), vkey(*p2)
            ek = (k1, k2) if k1 < k2 else (k2, k1)
            if ek not in edge_seen:
                edge_seen.add(ek)
                cand_edges.append((p1, p2))

    def is_cavity_pt(x: float, y: float) -> bool:
        if sd_poly(x, y, inner_pts) > -1.4:
            return False
        if motif_sdf is not None and motif_sdf(x, y) < 2.0:
            return False
        if counter_guard is not None and counter_guard(x, y, pad=0.8):
            return False
        if channel_guard is not None and channel_guard(x, y):
            return False
        return True

    interior_edges: list[tuple[tuple[int, int], tuple[int, int], tuple[float, float], tuple[float, float]]] = []
    ribbon_anchors: list[tuple[tuple[int, int], tuple[float, float], tuple[float, float]]] = []
    motif_anchors: list[tuple[tuple[int, int], tuple[float, float], tuple[float, float]]] = []
    v_coords: dict[tuple[int, int], tuple[float, float]] = {}

    for p1, p2 in cand_edges:
        c1, c2 = is_cavity_pt(*p1), is_cavity_pt(*p2)
        if not c1 and not c2:
            continue
        k1, k2 = vkey(*p1), vkey(*p2)
        if c1 and c2:
            mx, my = 0.5 * (p1[0] + p2[0]), 0.5 * (p1[1] + p2[1])
            ok_motif = motif_sdf is None or motif_sdf(mx, my) >= 0.8
            ok_rib = sd_poly(mx, my, inner_pts) <= -0.3
            ok_cnt = counter_guard is None or not counter_guard(mx, my, pad=0.4)
            ok_chn = channel_guard is None or not channel_guard(mx, my)
            if ok_motif and ok_rib and ok_cnt and ok_chn:
                interior_edges.append((k1, k2, p1, p2))
                v_coords[k1] = p1
                v_coords[k2] = p2
            continue

        p_in, k_in, p_out = (p1, k1, p2) if c1 else (p2, k2, p1)
        v_coords[k_in] = p_in

        out_motif = motif_sdf(*p_out) if motif_sdf is not None else 999.0
        if sd_poly(*p_out, inner_pts) > -1.4 and out_motif >= 0.0:
            p_hit = bisect_boundary(p_in, p_out, lambda x, y: sd_poly(x, y, inner_pts), target=0.0)
            if math.hypot(p_hit[0] - p_in[0], p_hit[1] - p_in[1]) >= 1.2:
                ribbon_anchors.append((k_in, p_in, p_hit))
        elif motif_sdf is not None and out_motif < 2.0 and (
            counter_guard is None or not counter_guard(*p_out, pad=1.0)
        ):
            p_hit = bisect_boundary(p_in, p_out, motif_sdf, target=-0.35)
            if (
                (counter_guard is None or not counter_guard(*p_hit, pad=0.6))
                and math.hypot(p_hit[0] - p_in[0], p_hit[1] - p_in[1]) >= 1.2
            ):
                motif_anchors.append((k_in, p_in, p_hit))

    deg: dict[tuple[int, int], int] = {}
    for k1, k2, _, _ in interior_edges:
        deg[k1] = deg.get(k1, 0) + 1
        deg[k2] = deg.get(k2, 0) + 1
    for k_in, _, _ in ribbon_anchors:
        deg[k_in] = deg.get(k_in, 0) + 1
    for k_in, _, _ in motif_anchors:
        deg[k_in] = deg.get(k_in, 0) + 1

    # Bridge any remaining degree-1 vertices to nearest surface, else prune
    bridge_max = 13.0 if channel_guard is not None else 11.5
    for kv, d_val in list(deg.items()):
        if d_val != 1:
            continue
        vx, vy = v_coords[kv]
        d_motif = motif_sdf(vx, vy) if motif_sdf is not None else 1e9
        d_rib = -sd_poly(vx, vy, inner_pts)
        if motif_sdf is not None and d_motif <= d_rib and d_motif <= bridge_max:
            tx, ty = closest_sdf_point(motif_sdf, vx, vy, steps=5)
            if counter_guard is None or not counter_guard(tx, ty, pad=0.6):
                gx, gy = sdf_gradient(motif_sdf, tx, ty)
                motif_anchors.append((kv, (vx, vy), (tx - 0.35 * gx, ty - 0.35 * gy)))
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
        motif_anchors = [r for r in motif_anchors if r[0] not in dead]

    mesh_lines: list[str] = [
        f'<line x1="{fmt(p1[0])}" y1="{fmt(p1[1])}" x2="{fmt(p2[0])}" y2="{fmt(p2[1])}"/>'
        for _, _, p1, p2 in interior_edges
    ]
    anchor_beads: list[str] = []
    for _, p_in, p_hit in ribbon_anchors:
        mesh_lines.append(f'<line x1="{fmt(p_in[0])}" y1="{fmt(p_in[1])}" x2="{fmt(p_hit[0])}" y2="{fmt(p_hit[1])}"/>')
        anchor_beads.append(f'<circle class="ink" cx="{fmt(p_hit[0])}" cy="{fmt(p_hit[1])}" r="1.25"/>')
    for _, p_in, p_hit in motif_anchors:
        mesh_lines.append(f'<line x1="{fmt(p_in[0])}" y1="{fmt(p_in[1])}" x2="{fmt(p_hit[0])}" y2="{fmt(p_hit[1])}"/>')
        if math.hypot(p_hit[0] - p_in[0], p_hit[1] - p_in[1]) >= 5.2:
            mx, my = 0.5 * (p_in[0] + p_hit[0]), 0.5 * (p_in[1] + p_hit[1])
            anchor_beads.append(f'<circle class="ink" cx="{fmt(mx)}" cy="{fmt(my)}" r="1.1"/>')

    pin_nodes: list[str] = [
        f'<circle class="ink" cx="{fmt(v_coords[kv][0])}" cy="{fmt(v_coords[kv][1])}" r="1.22"/>'
        for kv, d_val in deg.items()
        if d_val >= 2
    ]

    spiders_xl: list[str] = []
    for cx, cy, verts in spider_cands:
        if all(deg.get(vkey(*v), 0) >= 2 for v in verts):
            for vx, vy in verts:
                spiders_xl.append(
                    f'<line x1="{fmt(cx)}" y1="{fmt(cy)}" x2="{fmt(vx)}" y2="{fmt(vy)}"/>'
                )
            spiders_xl.append(f'<circle class="ink" cx="{fmt(cx)}" cy="{fmt(cy)}" r="1.6"/>')

    return {
        "spiders_xl": "".join(spiders_xl),
        "mesh_lines": "".join(mesh_lines),
        "pin_nodes": "".join(pin_nodes),
        "anchor_beads": "".join(anchor_beads),
    }


# =============================================================================
# 6. Seamless Periodic Hex-Mesh + Spiders Tile Builder
# =============================================================================

def build_seamless_hex_mesh(
    width: int = 1920,
    height: int = 1080,
    n_cols: int = 62,
    n_rows: int = 40,
    spider_mod: int = SPIDER_MOD,
    include_spiders: bool = True,
    pin_r: float = 2.2,
    spider_bead_r: float = 2.9,
) -> dict[str, str]:
    """Build a strictly periodic 60-degree hex mesh (+ spiders) with zero tile seams."""
    assert n_cols % 2 == 0, f"n_cols ({n_cols}) must be even for seamless periodicity"
    assert n_rows % 2 == 0, f"n_rows ({n_rows}) must be even for staggered row periodicity"
    if include_spiders:
        assert n_rows % spider_mod == 0, f"n_rows ({n_rows}) must be divisible by spider_mod ({spider_mod})"

    dx = width / n_cols
    dy = height / n_rows
    hx = dx * 0.5
    hy = dy / 3.0
    pad = max(dx, dy)

    def vkey(x: float, y: float) -> tuple[int, int]:
        return (int(round(x * 100)), int(round(y * 100)))

    def in_tile_band(x: float, y: float) -> bool:
        return (-pad <= x <= width + pad) and (-pad <= y <= height + pad)

    edge_seen: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    edge_cmds: list[str] = []
    node_coords: dict[tuple[int, int], tuple[float, float]] = {}
    spider_leg_cmds: list[str] = []
    spider_beads: list[str] = []

    for r_idx in range(-1, n_rows + 2):
        for c_idx in range(-1, n_cols + 2):
            cx = (c_idx + (0.5 if (r_idx % 2) else 0.0)) * dx
            cy = r_idx * dy
            verts = [
                (cx + hx, cy + hy),
                (cx, cy + 2.0 * hy),
                (cx - hx, cy + hy),
                (cx - hx, cy - hy),
                (cx, cy - 2.0 * hy),
                (cx + hx, cy - hy),
            ]

            for k in range(6):
                p1, p2 = verts[k], verts[(k + 1) % 6]
                if not (in_tile_band(*p1) or in_tile_band(*p2)):
                    continue
                k1, k2 = vkey(*p1), vkey(*p2)
                ek = (k1, k2) if k1 < k2 else (k2, k1)
                if ek not in edge_seen:
                    edge_seen.add(ek)
                    edge_cmds.append(f"M {fmt(p1[0])} {fmt(p1[1])} L {fmt(p2[0])} {fmt(p2[1])}")
                    node_coords[k1] = p1
                    node_coords[k2] = p2

            if include_spiders and ((r_idx + 2 * c_idx) % spider_mod == 0):
                if in_tile_band(cx, cy) or any(in_tile_band(vx, vy) for vx, vy in verts):
                    for vx, vy in verts:
                        spider_leg_cmds.append(f"M {fmt(cx)} {fmt(cy)} L {fmt(vx)} {fmt(vy)}")
                    if -spider_bead_r - 2.0 <= cx <= width + spider_bead_r + 2.0 and -spider_bead_r - 2.0 <= cy <= height + spider_bead_r + 2.0:
                        spider_beads.append(
                            f'<circle class="ink" cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(spider_bead_r)}"/>'
                        )

    pin_nodes = [
        f'<circle class="ink" cx="{fmt(vx)}" cy="{fmt(vy)}" r="{fmt(pin_r)}"/>'
        for vx, vy in node_coords.values()
        if -pin_r - 2.0 <= vx <= width + pin_r + 2.0 and -pin_r - 2.0 <= vy <= height + pin_r + 2.0
    ]

    return {
        "mesh_path": " ".join(edge_cmds),
        "spider_path": " ".join(spider_leg_cmds),
        "spider_beads": "".join(spider_beads),
        "pin_nodes": "".join(pin_nodes),
    }


# =============================================================================
# 7. Raster PNG Export Helper
# =============================================================================

def render_png(svg_path: Path, png_path: Path, width: int, height: int | None = None) -> None:
    """Rasterize an SVG file to PNG via rsvg-convert."""
    cmd = ["rsvg-convert", "-w", str(width)]
    if height is not None:
        cmd.extend(["-h", str(height)])
    cmd.extend([str(svg_path), "-o", str(png_path)])
    subprocess.run(cmd, check=True)
