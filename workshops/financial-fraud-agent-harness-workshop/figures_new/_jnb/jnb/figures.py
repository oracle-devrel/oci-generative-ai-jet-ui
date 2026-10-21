"""Figure helpers in the SITP visual language.

All colours are resolved from ``assets/tokens.json``.  Roles: blue = input/rows,
orange = output/columns, one highlighted element, everything else grey.

``iso_bars`` is a pure-matplotlib isometric renderer (own orthographic projection,
painter's algorithm, explicit three-shade faces).  The high-fidelity path for
bespoke 3-D figures is TikZ (``jnb.tikz`` / ``%%tikz``).
"""
from __future__ import annotations

import math
from typing import Iterable, Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon, Rectangle

from .tokens import color

__all__ = ["annotated_matrix", "iso_bars", "role_arrow"]


def _mono() -> str:
    from .style import family
    return family("mono")


def _mix(c1: str, c2: str, t: float) -> tuple:
    """Linear mix: t=0 -> c1, t=1 -> c2."""
    a, b = np.array(mpl.colors.to_rgb(c1)), np.array(mpl.colors.to_rgb(c2))
    return tuple(a * (1 - t) + b * t)


def _role(role: str) -> str:
    return color(role)


# ----------------------------------------------------------------------------
# arrows
# ----------------------------------------------------------------------------
def role_arrow(ax, start, end, role: str = "output", label: str | None = None, *,
               lw: float = 1.3, fontsize: float = 12, label_offset: float = 9,
               label_side: int = 1, rotate_label: bool = False, label_ha: str = "center"):
    """Arrow from ``start`` to ``end`` (data coords of a 2-D axes) coloured by ``role``.

    ``label`` (mathtext ok) sits at the midpoint, ``label_offset`` points to the
    left (``label_side=1``) or right (``-1``) of the direction of travel.
    """
    c = _role(role)
    ax.annotate("", xy=end, xytext=start, zorder=5,
                arrowprops=dict(arrowstyle="-|>", color=c, lw=lw, shrinkA=0,
                                shrinkB=0, mutation_scale=11))
    if label:
        dx, dy = end[0] - start[0], end[1] - start[1]
        n = math.hypot(dx, dy) or 1.0
        px, py = -dy / n * label_side, dx / n * label_side
        mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        rot = math.degrees(math.atan2(dy, dx)) if rotate_label else 0
        if rotate_label:  # keep text upright-readable, vertical -> bottom-to-top
            while rot <= -90: rot += 180
            while rot > 90: rot -= 180
            if rot == -90: rot = 90
        ax.annotate(label, xy=mid, xytext=(px * label_offset, py * label_offset),
                    textcoords="offset points", color=c, fontsize=fontsize,
                    ha=label_ha, va="center", rotation=rot,
                    rotation_mode="anchor", zorder=5)


# ----------------------------------------------------------------------------
# annotated matrix (right half of the reference figure)
# ----------------------------------------------------------------------------
def annotated_matrix(P, row_labels: Sequence[str], col_labels: Sequence[str], *,
                     highlight: tuple[int, int] | None = None,
                     row_marginals: bool | Iterable[int] = False,
                     col_marginals: bool | Iterable[int] = False,
                     row_title: str | None = None, col_title: str | None = None,
                     fmt: str = "{:.2f}", ax=None):
    """Grey grid of numbers with role-coloured axes.

    * rows: blue mono labels with ``i = k`` index; columns: orange with ``j = k``
    * ``row_title`` (mathtext, e.g. ``r"$w_{t-1}$"``): blue arrow down the left
    * ``col_title`` (e.g. ``r"$w_t$"``): orange arrow along the top
    * ``highlight=(r, c)``: thick highlight border + translucent fill
    * ``row_marginals`` / ``col_marginals``: ``True`` for every row/column, or an
      iterable of indices; the marginal sum sits outside the grid in a blue
      (rows) / orange (columns) bordered cell.
    Returns the axes.
    """
    P = np.asarray(P, dtype=float)
    nr, nc = P.shape
    cw, ch = 1.8, 1.0
    mono = _mono()
    fg, strong, muted = color("text.body"), color("text.strong"), color("text.muted")
    c_in, c_out, c_hl = _role("input"), _role("output"), _role("highlight")
    fill, edge = color("greys.cell_fill"), color("greys.cell_edge")

    def sel(v, n):
        if v is True:
            return list(range(n))
        return [] if not v else sorted(int(k) for k in v)

    rm, cm = sel(row_marginals, nr), sel(col_marginals, nc)

    created = ax is None
    if created:
        left = -3.6 if row_title else -2.6
        right = nc * cw + (cw + 0.45 if rm else 0.2)
        top = 2.2 if col_title else 1.2
        bottom = -nr - (ch + 0.5 if cm else 0.2)
        fig, ax = plt.subplots(figsize=((right - left) * 0.45, (top - bottom) * 0.45))
        ax.set_xlim(left, right)
        ax.set_ylim(bottom, top)
    ax.set_aspect("equal")
    ax.axis("off")

    # cells
    for r in range(nr):
        for c in range(nc):
            ax.add_patch(Rectangle((c * cw, -(r + 1) * ch), cw, ch, facecolor=fill,
                                   edgecolor=edge, lw=1.0, zorder=2))
            is_hl = highlight == (r, c)
            ax.text((c + .5) * cw, -(r + .5) * ch, fmt.format(P[r, c]),
                    ha="center", va="center", fontsize=11, zorder=4,
                    color=strong if is_hl else fg)

    # row labels (blue, mono) with index annotation
    for r, lab in enumerate(row_labels):
        y = -(r + .5) * ch
        ax.text(-0.15, y, f"$i\ =\ {r}$", ha="right", va="center", fontsize=9.5, color=c_in)
        ax.text(-1.2, y, lab, ha="right", va="center", fontsize=10, color=c_in,
                family=mono)
    # column labels (orange)
    for c, lab in enumerate(col_labels):
        x = (c + .5) * cw
        ax.text(x, 0.72, lab, ha="center", va="center", fontsize=10, color=c_out,
                family=mono)
        ax.text(x, 0.28, f"$j\ =\ {c}$", ha="center", va="center", fontsize=9.5, color=c_out)

    # titles / arrows
    if col_title:
        role_arrow(ax, (0.1, 1.3), (nc * cw - 0.1, 1.3), "output", col_title,
                   label_offset=11, fontsize=12)
    if row_title:
        role_arrow(ax, (-2.9, -0.1), (-2.9, -nr * ch + 0.1), "input", row_title,
                   label_offset=11, fontsize=12, rotate_label=True, label_side=-1)

    # highlight
    if highlight is not None:
        r, c = highlight
        ax.add_patch(Rectangle((c * cw, -(r + 1) * ch), cw, ch, facecolor=c_hl,
                               alpha=0.28, edgecolor="none", zorder=3))
        ax.add_patch(Rectangle((c * cw, -(r + 1) * ch), cw, ch, fill=False,
                               edgecolor=c_hl, lw=2.8, zorder=6))

    # marginals
    def marginal_cell(x, y, text, role):
        col = _role(role)
        ax.add_patch(Rectangle((x, y), cw, ch, facecolor=col, alpha=0.16,
                               edgecolor="none", zorder=3))
        ax.add_patch(Rectangle((x, y), cw, ch, fill=False, edgecolor=col, lw=2.2,
                               zorder=6))
        ax.text(x + cw / 2, y + ch / 2, text, ha="center", va="center",
                fontsize=11, color=col, zorder=7)

    if rm:
        x0 = nc * cw + 0.3
        for r in rm:
            marginal_cell(x0, -(r + 1) * ch, fmt.format(P[r].sum()), "input")
        k = str(rm[0]) if len(rm) == 1 else "i"
        ax.text(x0 + cw / 2, 0.5, rf"${{\sum}}_j\,P_{{{k}j}}$", ha="center", va="center",
                fontsize=11, color=c_in)
    if cm:
        y0 = -nr * ch - 0.3 - ch
        for c in cm:
            marginal_cell(c * cw, y0, fmt.format(P[:, c].sum()), "output")
        k = str(cm[0]) if len(cm) == 1 else "j"
        ax.text(-0.15, y0 + ch / 2, rf"${{\sum}}_i\,P_{{i{k}}}$", ha="right", va="center",
                fontsize=11, color=c_out)
    return ax


# ----------------------------------------------------------------------------
# isometric bars (left half of the reference figure)
# ----------------------------------------------------------------------------
_S = 36.0  # points per data unit for auto-created figures (figure is sized from it)


def _seg_text(ax, x, y, segs, fontsize, ha="center"):
    """Draw [(mathtext, role|None), ...] left-to-right, each coloured by role."""
    fig = ax.figure
    r = fig.canvas.get_renderer()
    items, total = [], 0.0
    inv = ax.transData.inverted()
    for txt, role in segs:
        t = ax.text(x, y, txt, fontsize=fontsize, va="baseline", ha="left",
                    color=_role(role) if role else color("text.strong"), zorder=9)
        bb = t.get_window_extent(r)
        w = inv.transform((bb.x1, 0))[0] - inv.transform((bb.x0, 0))[0]
        items.append((t, w))
        total += w
    x0 = x - total / 2 if ha == "center" else x
    for t, w in items:
        t.set_x(x0)
        x0 += w
    return total


def iso_bars(P, row_labels: Sequence[str], col_labels: Sequence[str], *,
             highlight: tuple[int, int] | None = None, annotate: str | None = None,
             row_title: str | None = None, col_title: str | None = None,
             equation=None, view: tuple[float, float] = (20.0, 32.0),
             max_height: float = 1.3, ax=None):
    """Oblique-isometric 3-D bar chart of ``P`` (rows ``i`` blue, columns ``j`` orange).

    ``view=(angle_i, angle_j)``: degrees below horizontal at which the row axis
    (down-left) and column axis (down-right) run on screen; the asymmetric default
    matches the reference so diagonals do not collapse into towers.  Own
    orthographic projection + painter's order (far bars first); face shades come
    from tokens (``greys.cuboid_top/left/right``); ``highlight`` uses the highlight
    role.  Label stacks are pushed outward until they clear every bar polygon.
    ``annotate``: mathtext with orange leader line.  ``equation``: mathtext string
    or list of ``(mathtext, role|None)`` segments drawn under the figure.
    Matplotlib approximation -- use TikZ (``jnb.tikz``) for the high-fidelity version.
    """
    from matplotlib.path import Path as MPath

    P = np.asarray(P, dtype=float)
    nr, nc = P.shape
    w = 0.72
    pad = (1 - w) / 2
    mono = _mono()
    c_in, c_out, c_hl = _role("input"), _role("output"), _role("highlight")
    top_c, left_c, right_c = (color(f"greys.cuboid_{k}") for k in ("top", "left", "right"))
    edge_c = color("text.muted")
    bg = color("surface.bg")
    ca, sa = math.cos(math.radians(view[0])), math.sin(math.radians(view[0]))
    cb, sb = math.cos(math.radians(view[1])), math.sin(math.radians(view[1]))

    def iso(i, j, z):
        return (-i * ca + j * cb, -i * sa - j * sb + z)

    created = ax is None
    if created:
        fig, ax = plt.subplots(figsize=(6.6, 4.8))
    ax.set_aspect("equal")
    ax.axis("off")

    hs = np.maximum(P / P.max() * max_height, 0.08)
    pts, polys = [], []
    order = sorted(((i, j) for i in range(nr) for j in range(nc)),
                   key=lambda ij: (ij[0] + ij[1], ij[0]))

    def face(poly3, fc, ec, lw, z):
        xy = [iso(*p) for p in poly3]
        pts.extend(xy)
        polys.append(MPath(xy + [xy[0]], closed=True))
        ax.add_patch(Polygon(xy, closed=True, facecolor=fc, edgecolor=ec, lw=lw,
                             joinstyle="round", zorder=z))

    for n, (i, j) in enumerate(order):
        i0, i1, j0, j1 = i + pad, i + pad + w, j + pad, j + pad + w
        h = hs[i, j]
        hl = highlight == (i, j)
        if hl:
            fcs = (_mix(c_hl, bg, .12), _mix(c_hl, bg, .35), _mix(c_hl, bg, .55))
            ec, lw = c_hl, 1.9
        else:
            fcs, ec, lw = (top_c, left_c, right_c), edge_c, 0.6
        z = 2 + n * 0.01 + (3 if hl else 0)
        face([(i1, j0, 0), (i1, j1, 0), (i1, j1, h), (i1, j0, h)], fcs[1], ec, lw, z)
        face([(i0, j1, 0), (i1, j1, 0), (i1, j1, h), (i0, j1, h)], fcs[2], ec, lw, z)
        face([(i0, j0, h), (i1, j0, h), (i1, j1, h), (i0, j1, h)], fcs[0], ec, lw, z)

    def clear(anchor, width_pt, side):
        """True if the label rect (extending ``side`` = -1 left / +1 right) hits no bar."""
        x, y = anchor
        xs = np.linspace(0, 1, 18) * width_pt / _S * side + x
        gy = np.linspace(-.28, .28, 4) + y
        g = np.array([(a, b) for a in xs for b in gy])
        return not any(p.contains_points(g).any() for p in polys)

    idx_w = 40  # points taken by the "i = k" annotation + gap
    rw = max(len(l) for l in row_labels) * 6.2 + idx_w + 4
    cw_ = max(len(l) for l in col_labels) * 6.2 + idx_w + 4
    d_r = d_c = 0.5
    while d_r < 6 and not all(clear(iso(i + .5, -d_r, 0), rw, -1) for i in range(nr)):
        d_r += 0.1
    while d_c < 6 and not all(clear(iso(-d_c, j + .5, 0), cw_, 1) for j in range(nc)):
        d_c += 0.1
    d_r += 0.25
    d_c += 0.25

    for i, lab in enumerate(row_labels):
        x, y = iso(i + .5, -d_r, 0)
        ax.annotate(f"$i\\ =\\ {i}$", (x, y), ha="right", va="center", fontsize=9.5,
                    color=c_in, xytext=(-2, 0), textcoords="offset points")
        ax.annotate(lab, (x, y), ha="right", va="center", fontsize=10, color=c_in,
                    family=mono, xytext=(-idx_w, 0), textcoords="offset points")
        pts.append((x - rw / _S, y))
    for j, lab in enumerate(col_labels):
        x, y = iso(-d_c, j + .5, 0)
        ax.annotate(f"$j\\ =\\ {j}$", (x, y), ha="left", va="center", fontsize=9.5,
                    color=c_out, xytext=(2, 0), textcoords="offset points")
        ax.annotate(lab, (x, y), ha="left", va="center", fontsize=10, color=c_out,
                    family=mono, xytext=(idx_w, 0), textcoords="offset points")
        pts.append((x + cw_ / _S, y))

    if row_title:
        k = d_r + rw / _S / max(cb, .3) * .95 + .6
        a, b = iso(-.2, -k, 0), iso(nr + .2, -k, 0)
        role_arrow(ax, a, b, "input", row_title, label_offset=12, fontsize=13, label_side=-1)
        pts += [a, b]
    if col_title:
        k = d_c + cw_ / _S / max(ca, .3) * .95 + .6
        a, b = iso(-k, -.2, 0), iso(-k, nc + .2, 0)
        role_arrow(ax, a, b, "output", col_title, label_offset=12, fontsize=13)
        pts += [a, b]

    if annotate and highlight is not None:
        i, j = highlight
        sx, sy = iso(i + .5, j + .5, hs[i, j] * .55)
        tx, ty = sx + 1.7, sy - 1.5
        ax.plot([sx, tx - .1], [sy, ty + .1], color=c_hl, lw=1.6, zorder=9,
                solid_capstyle="round")
        ax.text(tx, ty, annotate, color=c_hl, fontsize=13.5, ha="left", va="center", zorder=9)
        pts += [(tx + 3.2, ty), (tx, ty)]

    xs, ys = zip(*pts)
    ymin = min(ys)
    cx = (min(xs) + max(xs)) / 2
    if equation:
        segs = [(equation, None)] if isinstance(equation, str) else list(equation)
        if created:
            ax.set_xlim(min(xs) - .2, max(xs) + .2)
            ax.set_ylim(ymin - 1.4, max(ys) + .2)
            fig.set_size_inches((max(xs) - min(xs) + .4) * _S / 72,
                                (max(ys) - ymin + 1.6) * _S / 72)
        wq = _seg_text(ax, cx, ymin - 0.85, segs, 15)
        ymin -= 1.2
        pts += [(cx - wq / 2, ymin), (cx + wq / 2, ymin)]
        xs, ys = zip(*pts)
    ax.set_xlim(min(xs) - .2, max(xs) + .2)
    ax.set_ylim(ymin - .2, max(ys) + .2)
    if created:
        fig.set_size_inches((max(xs) - min(xs) + .4) * _S / 72, (max(ys) - ymin + .4) * _S / 72)
    return ax
