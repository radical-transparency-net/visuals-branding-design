#!/usr/bin/env python3
"""Fixed-width geometric Bruges lace font phase-locked to the 60-degree hex grid.

Every glyph occupies a 3x5 hexagonal cell (3*DX wide by 5*DY tall) with a
1-hex horizontal inter-letter gap (pitch = 4*DX) and a 2-hex vertical gap
between stacked lines. Because any k-letter line has width (4*k - 1)*DX,
centered words of any parity align identically to the underlying tullegrond
lattice with zero channel guards needed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from lace_core import HEX_RADIUS, fmt, sd_poly

# =============================================================================
# 1. Hex-Grid Typography Metrics (derived from HEX_RADIUS = 8.6)
# =============================================================================

DX = math.sqrt(3) * HEX_RADIUS       # ~14.8956
DY = 1.5 * HEX_RADIUS                # 12.9000

GLYPH_W = 3.0 * DX                   # ~44.6869
GLYPH_H = 5.0 * DY                   # 64.5000
HW = 0.5 * GLYPH_W                   # ~22.3435
HH = 0.5 * GLYPH_H                   # 32.2500

GAP_X = 1.0 * DX                     # ~14.8956 (exact 1-hex inter-letter column)
PITCH_X = GLYPH_W + GAP_X            # 4.0 * DX (~59.5825)
GAP_Y = 2.0 * DY                     # 25.8000 (exact 2-hex inter-line band)

STROKE = 11.6                        # Vertical & perpendicular diagonal stroke width
H_BAR = 11.2                         # Horizontal bar thickness


# =============================================================================
# 2. Synchronized SVG Path + Flattened Polygon Contour Builder
# =============================================================================

class ContourBuilder:
    """Build an SVG closed path and matching flattened polygon simultaneously."""

    def __init__(self, tx: float = 0.0, ty: float = 0.0) -> None:
        self.tx = tx
        self.ty = ty
        self.cmds: list[str] = []
        self.poly: list[tuple[float, float]] = []

    def _pt(self, x: float, y: float) -> tuple[float, float]:
        return (x + self.tx, y + self.ty)

    def move(self, x: float, y: float) -> ContourBuilder:
        px, py = self._pt(x, y)
        self.cmds.append(f"M {fmt(px)} {fmt(py)}")
        self.poly.append((px, py))
        return self

    def line(self, x: float, y: float) -> ContourBuilder:
        px, py = self._pt(x, y)
        if not self.poly or math.hypot(px - self.poly[-1][0], py - self.poly[-1][1]) > 1e-4:
            self.cmds.append(f"L {fmt(px)} {fmt(py)}")
            self.poly.append((px, py))
        return self

    def arc(
        self,
        cx: float,
        cy: float,
        r: float,
        deg_start: float,
        deg_end: float,
        steps: int = 16,
    ) -> ContourBuilder:
        delta = deg_end - deg_start
        if abs(delta) > 180.0:
            mid = 0.5 * (deg_start + deg_end)
            self.arc(cx, cy, r, deg_start, mid, steps=max(4, steps // 2))
            self.arc(cx, cy, r, mid, deg_end, steps=max(4, steps - steps // 2))
            return self

        sx = cx + r * math.cos(math.radians(deg_start))
        sy = cy + r * math.sin(math.radians(deg_start))
        if not self.poly:
            self.move(sx, sy)
        else:
            psx, psy = self._pt(sx, sy)
            if math.hypot(psx - self.poly[-1][0], psy - self.poly[-1][1]) > 1e-3:
                self.line(sx, sy)

        ex, ey = self._pt(
            cx + r * math.cos(math.radians(deg_end)),
            cy + r * math.sin(math.radians(deg_end)),
        )
        sweep = 1 if delta > 0 else 0
        self.cmds.append(f"A {fmt(r)} {fmt(r)} 0 0 {sweep} {fmt(ex)} {fmt(ey)}")
        for k in range(1, steps + 1):
            ang = math.radians(deg_start + delta * (k / steps))
            self.poly.append(self._pt(cx + r * math.cos(ang), cy + r * math.sin(ang)))
        return self

    def close(self) -> tuple[str, list[tuple[float, float]]]:
        self.cmds.append("Z")
        if len(self.poly) > 1 and math.hypot(self.poly[0][0] - self.poly[-1][0], self.poly[0][1] - self.poly[-1][1]) < 1e-4:
            self.poly.pop()
        return (" ".join(self.cmds), self.poly)


def _rect_contour(tx: float, ty: float, x0: float, y0: float, x1: float, y1: float) -> tuple[str, list[tuple[float, float]]]:
    return (
        ContourBuilder(tx, ty)
        .move(x0, y0)
        .line(x1, y0)
        .line(x1, y1)
        .line(x0, y1)
        .close()
    )


def _poly_contour(tx: float, ty: float, pts: list[tuple[float, float]]) -> tuple[str, list[tuple[float, float]]]:
    cb = ContourBuilder(tx, ty).move(*pts[0])
    for x, y in pts[1:]:
        cb.line(x, y)
    return cb.close()


def _round_rect_contour(
    tx: float,
    ty: float,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    r_tl: float = 0.0,
    r_tr: float = 0.0,
    r_br: float = 0.0,
    r_bl: float = 0.0,
) -> tuple[str, list[tuple[float, float]]]:
    cb = ContourBuilder(tx, ty)
    cb.move(x0 + r_tl, y0)
    cb.line(x1 - r_tr, y0)
    if r_tr > 0:
        cb.arc(x1 - r_tr, y0 + r_tr, r_tr, -90, 0)
    cb.line(x1, y1 - r_br)
    if r_br > 0:
        cb.arc(x1 - r_br, y1 - r_br, r_br, 0, 90)
    cb.line(x0 + r_bl, y1)
    if r_bl > 0:
        cb.arc(x0 + r_bl, y1 - r_bl, r_bl, 90, 180)
    cb.line(x0, y0 + r_tl)
    if r_tl > 0:
        cb.arc(x0 + r_tl, y0 + r_tl, r_tl, 180, 270)
    return cb.close()


def _intersect(
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    p4: tuple[float, float],
) -> tuple[float, float]:
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-9:
        return (0.5 * (p2[0] + p3[0]), 0.5 * (p2[1] + p3[1]))
    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / den
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / den
    return (px, py)


def _offset_line(
    p1: tuple[float, float],
    p2: tuple[float, float],
    offset: float,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Shift line (p1->p2) along its left-hand unit normal in SVG coordinates."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    L = math.hypot(dx, dy) or 1.0
    nx, ny = dy / L, -dx / L
    return ((p1[0] + nx * offset, p1[1] + ny * offset), (p2[0] + nx * offset, p2[1] + ny * offset))


# =============================================================================
# 3. Complete A-Z + Punctuation Geometric Sans Glyph Set
# =============================================================================

Contour = tuple[str, list[tuple[float, float]]]
GlyphFactory = Callable[[float, float], tuple[list[Contour], list[Contour]]]


def _glyph_a(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    top_hw = 7.6
    bot_hw = HW
    leg_dx = bot_hw - top_hw
    leg_len = math.hypot(leg_dx, 2.0 * HH)
    leg_w = STROKE * (leg_len / (2.0 * HH))
    bar_y0, bar_y1 = 6.0, 6.0 + H_BAR

    in_l_top = (-top_hw + leg_w, -HH)
    in_l_bot = (-bot_hw + leg_w, HH)
    in_r_top = (top_hw - leg_w, -HH)
    in_r_bot = (bot_hw - leg_w, HH)

    outer = _poly_contour(
        tx,
        ty,
        [
            (-top_hw, -HH),
            (top_hw, -HH),
            (bot_hw, HH),
            in_r_bot,
            _intersect(in_r_bot, in_r_top, (-HW, bar_y1), (HW, bar_y1)),
            _intersect(in_l_bot, in_l_top, (-HW, bar_y1), (HW, bar_y1)),
            in_l_bot,
            (-bot_hw, HH),
        ],
    )
    # Inner triangle apex sits below the top bar where the two inner leg walls meet
    # (note: in_l_top.x > 0 and in_r_top.x < 0, so their inner walls cross inside the glyph!)
    apex = _intersect(in_l_top, in_l_bot, in_r_top, in_r_bot)
    hl = _intersect(in_l_top, in_l_bot, (-HW, bar_y0), (HW, bar_y0))
    hr = _intersect(in_r_top, in_r_bot, (-HW, bar_y0), (HW, bar_y0))
    hole = _poly_contour(tx, ty, [apex, hr, hl])
    return ([outer], [hole])


def _glyph_b(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    up_rx = HW - 2.2
    mid_y0, mid_y1 = -6.7, 4.5
    mid_c = 0.5 * (mid_y0 + mid_y1)  # -1.1
    waist_x = 8.0
    r_up_top = 13.5
    r_up_bot = up_rx - waist_x
    r_lo_top = HW - waist_x
    r_lo_bot = 14.5

    cb = ContourBuilder(tx, ty)
    cb.move(-HW, -HH)
    cb.line(up_rx - r_up_top, -HH)
    cb.arc(up_rx - r_up_top, -HH + r_up_top, r_up_top, -90, 0)
    cb.line(up_rx, mid_c - r_up_bot)
    cb.arc(waist_x, mid_c - r_up_bot, r_up_bot, 0, 90)
    cb.arc(waist_x, mid_c + r_lo_top, r_lo_top, -90, 0)
    cb.line(HW, HH - r_lo_bot)
    cb.arc(HW - r_lo_bot, HH - r_lo_bot, r_lo_bot, 0, 90)
    cb.line(-HW, HH)
    outer = cb.close()

    h_up = _round_rect_contour(
        tx, ty, -HW + STROKE, -HH + H_BAR, up_rx - STROKE, mid_y0, 0, 5.5, 5.5, 0
    )
    h_lo = _round_rect_contour(
        tx, ty, -HW + STROKE, mid_y1, HW - STROKE, HH - H_BAR, 0, 6.5, 6.5, 0
    )
    return ([outer], [h_up, h_lo])


def _glyph_c(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    r_out = 19.5
    r_in = 8.1
    open_y = 10.5
    ix0, iy0, ix1, iy1 = -HW + STROKE, -HH + H_BAR, HW - STROKE, HH - H_BAR

    cb = ContourBuilder(tx, ty)
    cb.move(HW, -open_y)
    cb.line(ix1, -open_y)
    cb.line(ix1, iy0 + r_in)
    cb.arc(ix1 - r_in, iy0 + r_in, r_in, 0, -90)
    cb.line(ix0 + r_in, iy0)
    cb.arc(ix0 + r_in, iy0 + r_in, r_in, -90, -180)
    cb.line(ix0, iy1 - r_in)
    cb.arc(ix0 + r_in, iy1 - r_in, r_in, -180, -270)
    cb.line(ix1 - r_in, iy1)
    cb.arc(ix1 - r_in, iy1 - r_in, r_in, 90, 0)
    cb.line(ix1, open_y)
    cb.line(HW, open_y)
    cb.line(HW, HH - r_out)
    cb.arc(HW - r_out, HH - r_out, r_out, 0, 90)
    cb.line(-HW + r_out, HH)
    cb.arc(-HW + r_out, HH - r_out, r_out, 90, 180)
    cb.line(-HW, -HH + r_out)
    cb.arc(-HW + r_out, -HH + r_out, r_out, 180, 270)
    cb.line(HW - r_out, -HH)
    cb.arc(HW - r_out, -HH + r_out, r_out, -90, 0)
    return ([cb.close()], [])


def _glyph_d(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    outer = _round_rect_contour(tx, ty, -HW, -HH, HW, HH, 0, 21.0, 21.0, 0)
    hole = _round_rect_contour(
        tx, ty, -HW + STROKE, -HH + H_BAR, HW - STROKE, HH - H_BAR, 0, 9.4, 9.4, 0
    )
    return ([outer], [hole])


def _glyph_e(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    mid_y0 = -0.5 * H_BAR
    mid_y1 = 0.5 * H_BAR
    mid_x1 = HW - 5.5
    outer = _poly_contour(
        tx,
        ty,
        [
            (-HW, -HH),
            (HW, -HH),
            (HW, -HH + H_BAR),
            (-HW + STROKE, -HH + H_BAR),
            (-HW + STROKE, mid_y0),
            (mid_x1, mid_y0),
            (mid_x1, mid_y1),
            (-HW + STROKE, mid_y1),
            (-HW + STROKE, HH - H_BAR),
            (HW, HH - H_BAR),
            (HW, HH),
            (-HW, HH),
        ],
    )
    return ([outer], [])


def _glyph_f(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    mid_y0 = -0.5 * H_BAR
    mid_y1 = 0.5 * H_BAR
    mid_x1 = HW - 5.5
    outer = _poly_contour(
        tx,
        ty,
        [
            (-HW, -HH),
            (HW, -HH),
            (HW, -HH + H_BAR),
            (-HW + STROKE, -HH + H_BAR),
            (-HW + STROKE, mid_y0),
            (mid_x1, mid_y0),
            (mid_x1, mid_y1),
            (-HW + STROKE, mid_y1),
            (-HW + STROKE, HH),
            (-HW, HH),
        ],
    )
    return ([outer], [])


def _glyph_g(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    r_out = 19.5
    r_in = 8.1
    open_y = -11.5
    bar_y0, bar_y1 = 1.0, 1.0 + H_BAR
    bar_x0 = 0.5
    ix0, iy0, ix1, iy1 = -HW + STROKE, -HH + H_BAR, HW - STROKE, HH - H_BAR

    cb = ContourBuilder(tx, ty)
    cb.move(HW, open_y)
    cb.line(ix1, open_y)
    cb.line(ix1, iy0 + r_in)
    cb.arc(ix1 - r_in, iy0 + r_in, r_in, 0, -90)
    cb.line(ix0 + r_in, iy0)
    cb.arc(ix0 + r_in, iy0 + r_in, r_in, -90, -180)
    cb.line(ix0, iy1 - r_in)
    cb.arc(ix0 + r_in, iy1 - r_in, r_in, -180, -270)
    cb.line(ix1 - r_in, iy1)
    cb.arc(ix1 - r_in, iy1 - r_in, r_in, 90, 0)
    cb.line(ix1, bar_y1)
    cb.line(bar_x0, bar_y1)
    cb.line(bar_x0, bar_y0)
    cb.line(HW, bar_y0)
    cb.line(HW, HH - r_out)
    cb.arc(HW - r_out, HH - r_out, r_out, 0, 90)
    cb.line(-HW + r_out, HH)
    cb.arc(-HW + r_out, HH - r_out, r_out, 90, 180)
    cb.line(-HW, -HH + r_out)
    cb.arc(-HW + r_out, -HH + r_out, r_out, 180, 270)
    cb.line(HW - r_out, -HH)
    cb.arc(HW - r_out, -HH + r_out, r_out, -90, 0)
    return ([cb.close()], [])


def _glyph_h(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    my0, my1 = -0.5 * H_BAR, 0.5 * H_BAR
    lx1, rx0 = -HW + STROKE, HW - STROKE
    outer = _poly_contour(
        tx,
        ty,
        [
            (-HW, -HH),
            (lx1, -HH),
            (lx1, my0),
            (rx0, my0),
            (rx0, -HH),
            (HW, -HH),
            (HW, HH),
            (rx0, HH),
            (rx0, my1),
            (lx1, my1),
            (lx1, HH),
            (-HW, HH),
        ],
    )
    return ([outer], [])


def _glyph_i(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    slab_hw = HW - 3.5
    sx = 0.5 * STROKE
    outer = _poly_contour(
        tx,
        ty,
        [
            (-slab_hw, -HH),
            (slab_hw, -HH),
            (slab_hw, -HH + H_BAR),
            (sx, -HH + H_BAR),
            (sx, HH - H_BAR),
            (slab_hw, HH - H_BAR),
            (slab_hw, HH),
            (-slab_hw, HH),
            (-slab_hw, HH - H_BAR),
            (-sx, HH - H_BAR),
            (-sx, -HH + H_BAR),
            (-slab_hw, -HH + H_BAR),
        ],
    )
    return ([outer], [])


def _glyph_j(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    r_out = 19.0
    r_in = 7.6
    hook_y = 10.5
    ix0, ix1, iy1 = -HW + STROKE, HW - STROKE, HH - H_BAR

    cb = ContourBuilder(tx, ty)
    cb.move(-3.0, -HH)
    cb.line(HW, -HH)
    cb.line(HW, HH - r_out)
    cb.arc(HW - r_out, HH - r_out, r_out, 0, 90)
    cb.line(-HW + r_out, HH)
    cb.arc(-HW + r_out, HH - r_out, r_out, 90, 180)
    cb.line(-HW, hook_y)
    cb.line(ix0, hook_y)
    cb.line(ix0, iy1 - r_in)
    cb.arc(ix0 + r_in, iy1 - r_in, r_in, 180, 90)
    cb.line(ix1 - r_in, iy1)
    cb.arc(ix1 - r_in, iy1 - r_in, r_in, 90, 0)
    cb.line(ix1, -HH + H_BAR)
    cb.line(-3.0, -HH + H_BAR)
    return ([cb.close()], [])


def _glyph_k(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    # Upper arm centerline: (-HW + STROKE - 2.0, +4.0) -> (HW - 6.0, -HH)
    sx = -HW + STROKE
    u_a = (sx - 1.5, 4.5)
    u_b = (HW - 7.5, -HH)
    u_top = _offset_line(u_a, u_b, 0.5 * STROKE)
    u_bot = _offset_line(u_a, u_b, -0.5 * STROKE)

    # Lower leg centerline: from junction on upper arm down-right to (HW - 6.5, HH)
    l_a = (-1.5, -2.5)
    l_b = (HW - 6.5, HH)
    l_r = _offset_line(l_a, l_b, 0.5 * STROKE)
    l_l = _offset_line(l_a, l_b, -0.5 * STROKE)

    p_top_l = _intersect(u_top[0], u_top[1], (sx, -HH), (sx, HH))
    p_top_r = _intersect(u_top[0], u_top[1], (-HW, -HH), (HW, -HH))
    p_arm_r = _intersect(u_bot[0], u_bot[1], (-HW, -HH), (HW, -HH))
    p_crotch = _intersect(u_bot[0], u_bot[1], l_r[0], l_r[1])
    p_leg_r = _intersect(l_r[0], l_r[1], (-HW, HH), (HW, HH))
    p_leg_l = _intersect(l_l[0], l_l[1], (-HW, HH), (HW, HH))
    p_waist_l = _intersect(l_l[0], l_l[1], (sx, -HH), (sx, HH))
    if p_waist_l[1] < p_top_l[1] + 8.0:
        p_waist_l = (sx, 10.5)

    outer = _poly_contour(
        tx,
        ty,
        [
            (-HW, -HH),
            (sx, -HH),
            p_top_l,
            p_top_r,
            p_arm_r,
            p_crotch,
            p_leg_r,
            p_leg_l,
            p_waist_l,
            (sx, HH),
            (-HW, HH),
        ],
    )
    return ([outer], [])


def _glyph_l(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    outer = _poly_contour(
        tx,
        ty,
        [
            (-HW, -HH),
            (-HW + STROKE, -HH),
            (-HW + STROKE, HH - H_BAR),
            (HW, HH - H_BAR),
            (HW, HH),
            (-HW, HH),
        ],
    )
    return ([outer], [])


def _glyph_m(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    stem_w = 10.2
    diag_w = 9.2
    # Slanted inner V walls with exact parallel stroke width diag_w
    # Note: for (-HW+stem_w, -HH) -> (0, 14), dx>0, dy>0 => left normal points (+, -), i.e. up-right.
    # So shifting down-left (inward toward the bottom vertex) is -diag_w.
    l_top = ((-HW + stem_w, -HH), (0.0, -4.0))
    l_bot = _offset_line(l_top[0], l_top[1], -diag_w)
    r_top = ((HW - stem_w, -HH), (0.0, -4.0))
    r_bot = _offset_line(r_top[0], r_top[1], diag_w)

    v_top = _intersect(l_top[0], l_top[1], r_top[0], r_top[1])
    v_bot = _intersect(l_bot[0], l_bot[1], r_bot[0], r_bot[1])
    in_l = _intersect(l_bot[0], l_bot[1], (-HW + stem_w, -HH), (-HW + stem_w, HH))
    in_r = _intersect(r_bot[0], r_bot[1], (HW - stem_w, -HH), (HW - stem_w, HH))

    outer = _poly_contour(
        tx,
        ty,
        [
            (-HW, -HH),
            (-HW + stem_w, -HH),
            v_top,
            (HW - stem_w, -HH),
            (HW, -HH),
            (HW, HH),
            (HW - stem_w, HH),
            in_r,
            v_bot,
            in_l,
            (-HW + stem_w, HH),
            (-HW, HH),
        ],
    )
    return ([outer], [])


def _glyph_n(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    stem_w = 10.6
    # Diagonal centerline from top-left inner shoulder to bottom-right inner shoulder
    diag_c = ((-HW + 0.5 * stem_w, -HH), (HW - 0.5 * stem_w, HH))
    half_d = 0.5 * 10.6
    d_top = _offset_line(diag_c[0], diag_c[1], half_d)
    d_bot = _offset_line(diag_c[0], diag_c[1], -half_d)

    p_tr = _intersect(d_top[0], d_top[1], (HW - stem_w, -HH), (HW - stem_w, HH))
    p_bl = _intersect(d_bot[0], d_bot[1], (-HW + stem_w, -HH), (-HW + stem_w, HH))

    outer = _poly_contour(
        tx,
        ty,
        [
            (-HW, -HH),
            (-HW + stem_w, -HH),
            p_tr,
            (HW - stem_w, -HH),
            (HW, -HH),
            (HW, HH),
            (HW - stem_w, HH),
            p_bl,
            (-HW + stem_w, HH),
            (-HW, HH),
        ],
    )
    return ([outer], [])


def _glyph_o(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    outer = _round_rect_contour(tx, ty, -HW, -HH, HW, HH, 19.5, 19.5, 19.5, 19.5)
    hole = _round_rect_contour(
        tx, ty, -HW + STROKE, -HH + H_BAR, HW - STROKE, HH - H_BAR, 8.1, 8.1, 8.1, 8.1
    )
    return ([outer], [hole])


def _glyph_p(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    bowl_bot = 5.0
    r_out = 18.0
    r_in = 6.6
    cb = ContourBuilder(tx, ty)
    cb.move(-HW, -HH)
    cb.line(HW - r_out, -HH)
    cb.arc(HW - r_out, -HH + r_out, r_out, -90, 0)
    cb.line(HW, bowl_bot - r_out)
    cb.arc(HW - r_out, bowl_bot - r_out, r_out, 0, 90)
    cb.line(-HW + STROKE, bowl_bot)
    cb.line(-HW + STROKE, HH)
    cb.line(-HW, HH)
    outer = cb.close()

    hole = _round_rect_contour(
        tx, ty, -HW + STROKE, -HH + H_BAR, HW - STROKE, bowl_bot - H_BAR, 0, r_in, r_in, 0
    )
    return ([outer], [hole])


def _glyph_q(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    outer_o = _round_rect_contour(tx, ty, -HW, -HH, HW, HH, 19.5, 19.5, 19.5, 19.5)
    hole = _round_rect_contour(
        tx, ty, -HW + STROKE, -HH + H_BAR, HW - STROKE, HH - H_BAR, 8.1, 8.1, 8.1, 8.1
    )
    # Tail starts along the outer lower-right edge of O so it does not overlap outer_o
    tail = _poly_contour(
        tx,
        ty,
        [(1.5, 16.0), (11.5, 14.0), (HW, HH), (HW - 11.5, HH)],
    )
    return ([outer_o, tail], [hole])


def _glyph_r(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    bowl_bot = 5.0
    r_out = 18.0
    r_in = 6.6
    # Leg: starts smoothly from right-bottom of bowl and meets (HW, HH)
    leg_r_top = (8.5, 4.2)
    leg_r_bot = (HW, HH)
    leg_l_top = (-2.5, bowl_bot)
    leg_l_bot = (HW - 13.0, HH)

    cb = ContourBuilder(tx, ty)
    cb.move(-HW, -HH)
    cb.line(HW - r_out, -HH)
    cb.arc(HW - r_out, -HH + r_out, r_out, -90, 0)
    cb.line(HW, bowl_bot - r_out)
    cb.arc(HW - r_out, bowl_bot - r_out, r_out, 0, 72)
    cb.line(*leg_r_top)
    cb.line(*leg_r_bot)
    cb.line(*leg_l_bot)
    cb.line(*leg_l_top)
    cb.line(-HW + STROKE, bowl_bot)
    cb.line(-HW + STROKE, HH)
    cb.line(-HW, HH)
    outer = cb.close()

    hole = _round_rect_contour(
        tx, ty, -HW + STROKE, -HH + H_BAR, HW - STROKE, bowl_bot - H_BAR, 0, r_in, r_in, 0
    )
    return ([outer], [hole])


def _glyph_s(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    r_out = 15.0
    r_in = 3.8
    mid_h = 5.5
    open_y = 12.0
    ix0, ix1 = -HW + STROKE, HW - STROKE
    iy_top, iy_bot = -HH + H_BAR, HH - H_BAR

    cb = ContourBuilder(tx, ty)
    # Start at upper-right open end, trace inner upper bay clockwise/CCW around S
    cb.move(HW, -open_y)
    cb.line(ix1, -open_y)
    cb.line(ix1, iy_top + r_in)
    cb.arc(ix1 - r_in, iy_top + r_in, r_in, 0, -90)
    cb.line(ix0 + r_in, iy_top)
    cb.arc(ix0 + r_in, iy_top + r_in, r_in, -90, -180)
    cb.line(ix0, -mid_h - r_in)
    cb.arc(ix0 + r_in, -mid_h - r_in, r_in, -180, -270)
    cb.line(HW - r_out, -mid_h)
    cb.arc(HW - r_out, -mid_h + r_out, r_out, -90, 0)
    cb.line(HW, HH - r_out)
    cb.arc(HW - r_out, HH - r_out, r_out, 0, 90)
    cb.line(-HW + r_out, HH)
    cb.arc(-HW + r_out, HH - r_out, r_out, 90, 180)
    cb.line(-HW, open_y)
    cb.line(ix0, open_y)
    cb.line(ix0, iy_bot - r_in)
    cb.arc(ix0 + r_in, iy_bot - r_in, r_in, 180, 90)
    cb.line(ix1 - r_in, iy_bot)
    cb.arc(ix1 - r_in, iy_bot - r_in, r_in, 90, 0)
    cb.line(ix1, mid_h + r_in)
    cb.arc(ix1 - r_in, mid_h + r_in, r_in, 0, -90)
    cb.line(-HW + r_out, mid_h)
    cb.arc(-HW + r_out, mid_h - r_out, r_out, 90, 180)
    cb.line(-HW, -HH + r_out)
    cb.arc(-HW + r_out, -HH + r_out, r_out, 180, 270)
    cb.line(HW - r_out, -HH)
    cb.arc(HW - r_out, -HH + r_out, r_out, -90, 0)
    return ([cb.close()], [])


def _glyph_t(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    sx = 0.5 * STROKE
    outer = _poly_contour(
        tx,
        ty,
        [
            (-HW, -HH),
            (HW, -HH),
            (HW, -HH + H_BAR),
            (sx, -HH + H_BAR),
            (sx, HH),
            (-sx, HH),
            (-sx, -HH + H_BAR),
            (-HW, -HH + H_BAR),
        ],
    )
    return ([outer], [])


def _glyph_u(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    r_out = 19.5
    r_in = 8.1
    ix0, ix1, iy1 = -HW + STROKE, HW - STROKE, HH - H_BAR

    cb = ContourBuilder(tx, ty)
    cb.move(-HW, -HH)
    cb.line(ix0, -HH)
    cb.line(ix0, iy1 - r_in)
    cb.arc(ix0 + r_in, iy1 - r_in, r_in, 180, 90)
    cb.line(ix1 - r_in, iy1)
    cb.arc(ix1 - r_in, iy1 - r_in, r_in, 90, 0)
    cb.line(ix1, -HH)
    cb.line(HW, -HH)
    cb.line(HW, HH - r_out)
    cb.arc(HW - r_out, HH - r_out, r_out, 0, 90)
    cb.line(-HW + r_out, HH)
    cb.arc(-HW + r_out, HH - r_out, r_out, 90, 180)
    return ([cb.close()], [])


def _glyph_v(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    bot_hw = 6.8
    top_hw = HW
    leg_len = math.hypot(top_hw - bot_hw, 2.0 * HH)
    leg_w = STROKE * (leg_len / (2.0 * HH))

    p_l = _offset_line((-top_hw, -HH), (-bot_hw, HH), STROKE)
    p_r = _offset_line((top_hw, -HH), (bot_hw, HH), -STROKE)
    apex = _intersect(p_l[0], p_l[1], p_r[0], p_r[1])

    outer = _poly_contour(
        tx,
        ty,
        [
            (-top_hw, -HH),
            (-top_hw + leg_w, -HH),
            apex,
            (top_hw - leg_w, -HH),
            (top_hw, -HH),
            (bot_hw, HH),
            (-bot_hw, HH),
        ],
    )
    return ([outer], [])


def _shift_up(p1: tuple[float, float], p2: tuple[float, float], dist: float) -> tuple[tuple[float, float], tuple[float, float]]:
    """Shift line (p1->p2) by `dist` along its upward-pointing unit normal."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    L = math.hypot(dx, dy) or 1.0
    nx, ny = dy / L, -dx / L
    if ny > 0:
        nx, ny = -nx, -ny
    return ((p1[0] + nx * dist, p1[1] + ny * dist), (p2[0] + nx * dist, p2[1] + ny * dist))


def _glyph_w(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    w_s = 8.4
    apex_y = 2.5
    peak_x = 11.2
    foot_hw = 4.4

    l1_out = ((-HW, -HH), (-peak_x - foot_hw, HH))
    l2_out = ((-peak_x + foot_hw, HH), (0.0, apex_y))
    l3_out = ((0.0, apex_y), (peak_x - foot_hw, HH))
    l4_out = ((peak_x + foot_hw, HH), (HW, -HH))

    l1_in = _shift_up(*l1_out, w_s)
    l2_in = _shift_up(*l2_out, w_s)
    l3_in = _shift_up(*l3_out, w_s)
    l4_in = _shift_up(*l4_out, w_s)

    in_top_l = _intersect(l1_in[0], l1_in[1], (-HW, -HH), (HW, -HH))
    in_bot_l = _intersect(l1_in[0], l1_in[1], l2_in[0], l2_in[1])
    in_mid = _intersect(l2_in[0], l2_in[1], l3_in[0], l3_in[1])
    in_bot_r = _intersect(l3_in[0], l3_in[1], l4_in[0], l4_in[1])
    in_top_r = _intersect(l4_in[0], l4_in[1], (-HW, -HH), (HW, -HH))

    outer = _poly_contour(
        tx,
        ty,
        [
            (-HW, -HH),
            in_top_l,
            in_bot_l,
            in_mid,
            in_bot_r,
            in_top_r,
            (HW, -HH),
            (peak_x + foot_hw, HH),
            (peak_x - foot_hw, HH),
            (0.0, apex_y),
            (-peak_x + foot_hw, HH),
            (-peak_x - foot_hw, HH),
        ],
    )
    return ([outer], [])


def _glyph_x(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    # Exact symmetric crossing bars (-HW,-HH)->(HW,HH) and (HW,-HH)->(-HW,HH)
    a_r = _offset_line((-HW + 6.5, -HH), (HW - 6.5, HH), 0.5 * STROKE)
    a_l = _offset_line((-HW + 6.5, -HH), (HW - 6.5, HH), -0.5 * STROKE)
    b_l = _offset_line((HW - 6.5, -HH), (-HW + 6.5, HH), 0.5 * STROKE)
    b_r = _offset_line((HW - 6.5, -HH), (-HW + 6.5, HH), -0.5 * STROKE)

    outer = _poly_contour(
        tx,
        ty,
        [
            _intersect(a_l[0], a_l[1], (-HW, -HH), (HW, -HH)),
            _intersect(a_r[0], a_r[1], (-HW, -HH), (HW, -HH)),
            _intersect(a_r[0], a_r[1], b_l[0], b_l[1]),
            _intersect(b_l[0], b_l[1], (-HW, -HH), (HW, -HH)),
            _intersect(b_r[0], b_r[1], (-HW, -HH), (HW, -HH)),
            _intersect(a_r[0], a_r[1], b_r[0], b_r[1]),
            _intersect(a_r[0], a_r[1], (-HW, HH), (HW, HH)),
            _intersect(a_l[0], a_l[1], (-HW, HH), (HW, HH)),
            _intersect(a_l[0], a_l[1], b_r[0], b_r[1]),
            _intersect(b_r[0], b_r[1], (-HW, HH), (HW, HH)),
            _intersect(b_l[0], b_l[1], (-HW, HH), (HW, HH)),
            _intersect(a_l[0], a_l[1], b_l[0], b_l[1]),
        ],
    )
    return ([outer], [])


def _glyph_y(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    sx = 0.5 * STROKE
    # V arms converge at y = 4.0
    l_out = ((-HW, -HH), (-sx, 4.0))
    l_in = _offset_line((-HW, -HH), (-sx, 4.0), STROKE)
    r_out = ((HW, -HH), (sx, 4.0))
    r_in = _offset_line((HW, -HH), (sx, 4.0), -STROKE)

    in_top_l = _intersect(l_in[0], l_in[1], (-HW, -HH), (HW, -HH))
    in_top_r = _intersect(r_in[0], r_in[1], (-HW, -HH), (HW, -HH))
    in_crotch = _intersect(l_in[0], l_in[1], r_in[0], r_in[1])

    outer = _poly_contour(
        tx,
        ty,
        [
            (-HW, -HH),
            in_top_l,
            in_crotch,
            in_top_r,
            (HW, -HH),
            (sx, 4.0),
            (sx, HH),
            (-sx, HH),
            (-sx, 4.0),
        ],
    )
    return ([outer], [])


def _glyph_z(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    # Diagonal bar from (+HW, -HH + H_BAR) to (-HW, +HH - H_BAR)
    # Note: vector (HW-6, -HH) -> (-HW+6, HH) has dx < 0, dy > 0 => left normal points (+, +) (right/down).
    d_right = _offset_line((HW - 6.0, -HH), (-HW + 6.0, HH), 0.5 * STROKE)
    d_left = _offset_line((HW - 6.0, -HH), (-HW + 6.0, HH), -0.5 * STROKE)

    p_top_left = _intersect(d_left[0], d_left[1], (-HW, -HH + H_BAR), (HW, -HH + H_BAR))
    p_top_right = _intersect(d_right[0], d_right[1], (-HW, -HH + H_BAR), (HW, -HH + H_BAR))
    p_bot_right = _intersect(d_right[0], d_right[1], (-HW, HH - H_BAR), (HW, HH - H_BAR))
    p_bot_left = _intersect(d_left[0], d_left[1], (-HW, HH - H_BAR), (HW, HH - H_BAR))

    outer = _poly_contour(
        tx,
        ty,
        [
            (-HW, -HH),
            (HW, -HH),
            (HW, -HH + H_BAR),
            p_top_right,
            p_bot_right,
            (HW, HH - H_BAR),
            (HW, HH),
            (-HW, HH),
            (-HW, HH - H_BAR),
            p_bot_left,
            p_top_left,
            (-HW, -HH + H_BAR),
        ],
    )
    return ([outer], [])


def _glyph_space(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    return ([], [])


def _glyph_hyphen(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    return ([_rect_contour(tx, ty, -13.0, -0.5 * H_BAR, 13.0, 0.5 * H_BAR)], [])


def _glyph_period(tx: float, ty: float) -> tuple[list[Contour], list[Contour]]:
    sx = 0.5 * STROKE
    return ([_rect_contour(tx, ty, -sx, HH - STROKE, sx, HH)], [])


GLYPHS: dict[str, GlyphFactory] = {
    "A": _glyph_a,
    "B": _glyph_b,
    "C": _glyph_c,
    "D": _glyph_d,
    "E": _glyph_e,
    "F": _glyph_f,
    "G": _glyph_g,
    "H": _glyph_h,
    "I": _glyph_i,
    "J": _glyph_j,
    "K": _glyph_k,
    "L": _glyph_l,
    "M": _glyph_m,
    "N": _glyph_n,
    "O": _glyph_o,
    "P": _glyph_p,
    "Q": _glyph_q,
    "R": _glyph_r,
    "S": _glyph_s,
    "T": _glyph_t,
    "U": _glyph_u,
    "V": _glyph_v,
    "W": _glyph_w,
    "X": _glyph_x,
    "Y": _glyph_y,
    "Z": _glyph_z,
    " ": _glyph_space,
    "-": _glyph_hyphen,
    ".": _glyph_period,
}


# =============================================================================
# 4. Stacked Layout & Continuous Polygon SDF
# =============================================================================

@dataclass
class _PlacedGlyph:
    bbox: tuple[float, float, float, float]
    outer_polys: list[list[tuple[float, float]]]
    hole_polys: list[list[tuple[float, float]]]


@dataclass
class LaceWordmark:
    svg_paths: list[str]
    bounds: tuple[float, float, float, float]
    glyphs: list[_PlacedGlyph]

    def sdf(self, x: float, y: float) -> float:
        best = 1e9
        for g in self.glyphs:
            x0, y0, x1, y1 = g.bbox
            dx = max(x0 - x, 0.0, x - x1)
            dy = max(y0 - y, 0.0, y - y1)
            if math.hypot(dx, dy) >= best:
                continue
            d_outer = min(sd_poly(x, y, poly) for poly in g.outer_polys)
            if g.hole_polys:
                d_hole = min(sd_poly(x, y, poly) for poly in g.hole_polys)
                d = max(d_outer, -d_hole)
            else:
                d = d_outer
            if d < best:
                best = d
        return best

    def is_in_counter(self, x: float, y: float, pad: float = 0.8) -> bool:
        for g in self.glyphs:
            if not g.hole_polys:
                continue
            x0, y0, x1, y1 = g.bbox
            if x < x0 - pad or x > x1 + pad or y < y0 - pad or y > y1 + pad:
                continue
            for poly in g.hole_polys:
                if sd_poly(x, y, poly) <= pad:
                    return True
        return False


def layout_lace_wordmark(lines: list[str]) -> LaceWordmark:
    """Place stacked uppercase lines in exact phase lock with the 60-degree hex grid."""
    n_lines = len(lines)
    total_rows = 5 * n_lines + 2 * (n_lines - 1)
    top_y = -0.5 * total_rows * DY

    svg_paths: list[str] = []
    glyphs: list[_PlacedGlyph] = []

    for row_idx, raw_line in enumerate(lines):
        text = raw_line.upper()
        n_chars = len(text)
        cy = top_y + (row_idx * 7 + 2.5) * DY

        for col_idx, ch in enumerate(text):
            if ch not in GLYPHS:
                raise KeyError(f"Unsupported character {ch!r} in lace_font")
            cx = (col_idx - 0.5 * (n_chars - 1)) * PITCH_X
            outers, holes = GLYPHS[ch](cx, cy)
            if not outers:
                continue

            if holes:
                # Primary outer + holes share one evenodd path; extra non-holed appendages
                # (like Q's tail) emit separately so overlap never cuts an evenodd hole.
                svg_paths.append(" ".join([outers[0][0]] + [d for d, _ in holes]))
                for d, _ in outers[1:]:
                    svg_paths.append(d)
            else:
                svg_paths.append(" ".join(d for d, _ in outers))

            outer_polys = [poly for _, poly in outers]
            hole_polys = [poly for _, poly in holes]
            xs = [p[0] for poly in outer_polys for p in poly]
            ys = [p[1] for poly in outer_polys for p in poly]
            glyphs.append(
                _PlacedGlyph(
                    bbox=(min(xs), min(ys), max(xs), max(ys)),
                    outer_polys=outer_polys,
                    hole_polys=hole_polys,
                )
            )

    all_bounds = (
        min(g.bbox[0] for g in glyphs),
        min(g.bbox[1] for g in glyphs),
        max(g.bbox[2] for g in glyphs),
        max(g.bbox[3] for g in glyphs),
    )

    return LaceWordmark(svg_paths=svg_paths, bounds=all_bounds, glyphs=glyphs)
