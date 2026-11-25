"""Pure-Python SVG renderer for the city grid (used by every page and the board component).

Entities never rely on colour alone: the robber is a circle marked "R", officers are shields
numbered 1..n, the exit is a square with a flag, hazards are hatched, difficult terrain is
dotted, safe zones carry a "+" and buildings have window marks.
"""
from __future__ import annotations

import itertools
from typing import Iterable, Optional

from config import theme as T
from environment.grid import Cell, Grid
from environment.terrain import Terrain

_uid = itertools.count()


def auto_cell_size(grid: Grid, max_width: int = 720, min_px: int = 8, max_px: int = 34) -> int:
    return max(min_px, min(max_px, max_width // grid.cols))


def _center(cell: Cell, s: float) -> tuple[float, float]:
    return (cell[1] + 0.5) * s, (cell[0] + 0.5) * s


def _polyline(cells: Iterable[Cell], s: float, color: str, width: float, dash: str = "",
              opacity: float = 1.0) -> str:
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (_center(c, s) for c in cells))
    if not pts or " " not in pts:
        return ""
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width:.1f}" '
            f'stroke-linecap="round" stroke-linejoin="round" opacity="{opacity}"{dash_attr}/>')


def render_svg(grid: Grid, robber: Optional[Cell] = None, police: Iterable[Cell] = (),
               exit_: Optional[Cell] = None, *, cell: Optional[int] = None, max_width: int = 720,
               explored: Iterable[Cell] = (), frontier: Iterable[Cell] = (), path: Iterable[Cell] = (),
               advisory: Iterable[Cell] = (), predicted: Optional[Cell] = None,
               routes: Iterable[Iterable[Cell]] = (), intercepts: Iterable[Cell] = (),
               trail: Iterable[Cell] = (), selected: Optional[Cell] = None,
               captured: bool = False, responsive: bool = True) -> str:
    s = cell or auto_cell_size(grid, max_width)
    w, h = grid.cols * s, grid.rows * s
    uid = f"g{next(_uid)}"
    out: list[str] = []
    size_attr = 'width="100%"' if responsive else f'width="{w}" height="{h}"'
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" {size_attr} '
               f'preserveAspectRatio="xMidYMid meet" role="img" aria-label="City grid {grid.rows} by {grid.cols}">')
    out.append(
        f'<defs>'
        f'<pattern id="{uid}gl" width="{s}" height="{s}" patternUnits="userSpaceOnUse">'
        f'<path d="M {s} 0 L 0 0 0 {s}" fill="none" stroke="rgba(139,155,173,0.13)" stroke-width="1"/></pattern>'
        f'<pattern id="{uid}hz" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        f'<rect width="6" height="6" fill="{T.HAZARD}"/><line x1="0" y1="0" x2="0" y2="6" stroke="#FF8A90" stroke-width="2"/></pattern>'
        f'<pattern id="{uid}df" width="5" height="5" patternUnits="userSpaceOnUse">'
        f'<rect width="5" height="5" fill="#8A6424"/><circle cx="2.5" cy="2.5" r="1" fill="{T.AMBER}"/></pattern>'
        f'<filter id="{uid}glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="1.6" result="b"/>'
        f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        f'</defs>')
    out.append(f'<rect width="{w}" height="{h}" fill="{T.ROAD}"/>')
    out.append(f'<rect width="{w}" height="{h}" fill="url(#{uid}gl)"/>')

    pad = max(1.0, s * 0.08)
    for r in range(grid.rows):
        row = grid.cells[r]
        for c in range(grid.cols):
            t = row[c]
            if t == Terrain.ROAD:
                continue
            x, y = c * s, r * s
            if t == Terrain.WALL:
                out.append(f'<rect x="{x + pad:.1f}" y="{y + pad:.1f}" width="{s - 2 * pad:.1f}" height="{s - 2 * pad:.1f}" '
                           f'rx="{s * 0.12:.1f}" fill="{T.WALL}" stroke="#4C5E73" stroke-width="0.8"/>')
                if s >= 14:
                    q = s * 0.22
                    out.append(f'<rect x="{x + s * 0.3:.1f}" y="{y + s * 0.3:.1f}" width="{q:.1f}" height="{q:.1f}" fill="#5A6E84"/>'
                               f'<rect x="{x + s * 0.55:.1f}" y="{y + s * 0.55:.1f}" width="{q:.1f}" height="{q:.1f}" fill="#5A6E84"/>')
            elif t == Terrain.DIFFICULT:
                out.append(f'<rect x="{x}" y="{y}" width="{s}" height="{s}" fill="url(#{uid}df)" opacity="0.85"/>')
            elif t == Terrain.HAZARD:
                out.append(f'<rect x="{x}" y="{y}" width="{s}" height="{s}" fill="url(#{uid}hz)" opacity="0.9"/>')
            elif t == Terrain.SAFE:
                out.append(f'<rect x="{x}" y="{y}" width="{s}" height="{s}" fill="{T.SAFE}" opacity="0.85"/>')
                if s >= 12:
                    cx, cy = x + s / 2, y + s / 2
                    a = s * 0.22
                    out.append(f'<path d="M{cx - a:.1f} {cy:.1f}H{cx + a:.1f}M{cx:.1f} {cy - a:.1f}V{cy + a:.1f}" '
                               f'stroke="{T.ICE}" stroke-width="{max(1, s * 0.08):.1f}" opacity="0.7"/>')

    for c in explored:
        out.append(f'<rect x="{c[1] * s}" y="{c[0] * s}" width="{s}" height="{s}" fill="{T.EXPLORED}" opacity="0.42"/>')
    for c in frontier:
        out.append(f'<rect x="{c[1] * s + 1}" y="{c[0] * s + 1}" width="{s - 2}" height="{s - 2}" fill="{T.FRONTIER}" '
                   f'opacity="0.55" rx="{s * 0.15:.1f}"/>')

    trail = list(trail)
    if len(trail) > 1:
        out.append(_polyline(trail, s, T.AQUA, max(1.5, s * 0.12), opacity=0.28))
    for route in routes:
        out.append(_polyline(list(route), s, T.CORAL, max(1.2, s * 0.09), dash=f"{s * 0.35:.1f},{s * 0.25:.1f}", opacity=0.75))
    path = list(path)
    if path:
        out.append(_polyline(path, s, T.GREEN, max(2.0, s * 0.22), opacity=0.9))
    advisory = list(advisory)
    if advisory:
        out.append(_polyline(advisory, s, T.AQUA, max(1.6, s * 0.14), dash=f"{s * 0.3:.1f},{s * 0.22:.1f}", opacity=0.85))
    for c in intercepts:
        x, y = _center(c, s)
        a = s * 0.38
        out.append(f'<g stroke="{T.CORAL}" stroke-width="{max(1, s * 0.07):.1f}" opacity="0.9">'
                   f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{a:.1f}" fill="none"/>'
                   f'<path d="M{x - a:.1f} {y:.1f}H{x + a:.1f}M{x:.1f} {y - a:.1f}V{y + a:.1f}"/></g>')
    if predicted is not None:
        x, y = _center(predicted, s)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{s * 0.42:.1f}" fill="rgba(255,181,71,0.15)" stroke="{T.AMBER}" '
                   f'stroke-width="{max(1, s * 0.08):.1f}" stroke-dasharray="{s * 0.18:.1f},{s * 0.12:.1f}"/>')
        if s >= 14:
            out.append(f'<text x="{x:.1f}" y="{y + s * 0.17:.1f}" font-size="{s * 0.5:.1f}" text-anchor="middle" '
                       f'fill="{T.AMBER}" font-weight="700" font-family="Inter,sans-serif">?</text>')

    font = "Inter,Segoe UI,sans-serif"
    if exit_ is not None:
        x, y = exit_[1] * s, exit_[0] * s
        out.append(f'<rect x="{x + 1:.1f}" y="{y + 1:.1f}" width="{s - 2}" height="{s - 2}" rx="{s * 0.18:.1f}" fill="{T.GREEN}" '
                   f'filter="url(#{uid}glow)"/>')
        fx = x + s * 0.34
        out.append(f'<path d="M{fx:.1f} {y + s * 0.2:.1f}V{y + s * 0.82:.1f}" stroke="#0C3B2A" stroke-width="{max(1, s * 0.08):.1f}"/>'
                   f'<path d="M{fx:.1f} {y + s * 0.22:.1f}L{x + s * 0.76:.1f} {y + s * 0.36:.1f}L{fx:.1f} {y + s * 0.5:.1f}Z" fill="#0C3B2A"/>')
    for i, p in enumerate(police):
        x, y = _center(p, s)
        r = s * 0.42
        shield = (f"M{x:.1f} {y - r:.1f} L{x + r:.1f} {y - r * 0.55:.1f} L{x + r * 0.8:.1f} {y + r * 0.45:.1f} "
                  f"L{x:.1f} {y + r:.1f} L{x - r * 0.8:.1f} {y + r * 0.45:.1f} L{x - r:.1f} {y - r * 0.55:.1f} Z")
        out.append(f'<path d="{shield}" fill="{T.CORAL}" stroke="#FFD3D6" stroke-width="{max(0.8, s * 0.05):.1f}" filter="url(#{uid}glow)"/>')
        if s >= 11:
            out.append(f'<text x="{x:.1f}" y="{y + s * 0.15:.1f}" font-size="{s * 0.44:.1f}" text-anchor="middle" '
                       f'fill="#2B0A0D" font-weight="800" font-family="{font}">{i + 1}</text>')
    if robber is not None:
        x, y = _center(robber, s)
        color = T.CORAL if captured else T.AQUA
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{s * 0.42:.1f}" fill="{color}" stroke="{T.ICE}" '
                   f'stroke-width="{max(0.8, s * 0.06):.1f}" filter="url(#{uid}glow)"/>')
        if s >= 11:
            out.append(f'<text x="{x:.1f}" y="{y + s * 0.16:.1f}" font-size="{s * 0.46:.1f}" text-anchor="middle" '
                       f'fill="#06202A" font-weight="800" font-family="{font}">R</text>')
    if selected is not None:
        out.append(f'<rect x="{selected[1] * s + 1}" y="{selected[0] * s + 1}" width="{s - 2}" height="{s - 2}" fill="none" '
                   f'stroke="{T.ICE}" stroke-width="2" rx="3"/>')
    out.append("</svg>")
    return "".join(out)


LEGEND_ITEMS = [
    ("robber", "Robber (R)"), ("police", "Police (1..n)"), ("exit", "Exit"), ("wall", "Building / wall"),
    ("road", "Road · cost 1"), ("difficult", "Difficult · cost 3"), ("hazard", "Hazard · cost 5"),
    ("safe", "Safe zone · police barred"), ("explored", "Explored"), ("frontier", "Frontier"),
    ("path", "Final / planned path"), ("advisory", "A* advisory route"), ("route", "Police route"),
    ("predicted", "Predicted robber cell"),
]


def legend_swatch(kind: str) -> str:
    base = 'width="18" height="18" viewBox="0 0 18 18"'
    shapes = {
        "robber": f'<circle cx="9" cy="9" r="7" fill="{T.AQUA}"/><text x="9" y="12.5" font-size="9" text-anchor="middle" font-weight="800" fill="#06202A">R</text>',
        "police": f'<path d="M9 2L16 5L14.5 12L9 16L3.5 12L2 5Z" fill="{T.CORAL}"/><text x="9" y="12" font-size="8" text-anchor="middle" font-weight="800" fill="#2B0A0D">1</text>',
        "exit": f'<rect x="2" y="2" width="14" height="14" rx="3" fill="{T.GREEN}"/><path d="M7 4V14M7 4L13 6.5L7 9Z" stroke="#0C3B2A" fill="#0C3B2A"/>',
        "wall": f'<rect x="2" y="2" width="14" height="14" rx="2" fill="{T.WALL}" stroke="#4C5E73"/>',
        "road": f'<rect x="2" y="2" width="14" height="14" rx="2" fill="{T.ROAD}" stroke="rgba(139,155,173,.35)"/>',
        "difficult": f'<rect x="2" y="2" width="14" height="14" rx="2" fill="#8A6424"/><circle cx="6" cy="6" r="1.2" fill="{T.AMBER}"/><circle cx="12" cy="12" r="1.2" fill="{T.AMBER}"/><circle cx="12" cy="6" r="1.2" fill="{T.AMBER}"/><circle cx="6" cy="12" r="1.2" fill="{T.AMBER}"/>',
        "hazard": f'<rect x="2" y="2" width="14" height="14" rx="2" fill="{T.HAZARD}"/><path d="M2 10L10 2M6 16L16 6" stroke="#FF8A90" stroke-width="2"/>',
        "safe": f'<rect x="2" y="2" width="14" height="14" rx="2" fill="{T.SAFE}"/><path d="M5 9H13M9 5V13" stroke="{T.ICE}" stroke-width="1.6"/>',
        "explored": f'<rect x="2" y="2" width="14" height="14" rx="2" fill="{T.EXPLORED}" opacity=".7"/>',
        "frontier": f'<rect x="2" y="2" width="14" height="14" rx="4" fill="{T.FRONTIER}" opacity=".8"/>',
        "path": f'<path d="M2 9H16" stroke="{T.GREEN}" stroke-width="4" stroke-linecap="round"/>',
        "advisory": f'<path d="M2 9H16" stroke="{T.AQUA}" stroke-width="3" stroke-dasharray="4,3"/>',
        "route": f'<path d="M2 9H16" stroke="{T.CORAL}" stroke-width="2" stroke-dasharray="3,3"/>',
        "predicted": f'<circle cx="9" cy="9" r="6.5" fill="none" stroke="{T.AMBER}" stroke-width="1.6" stroke-dasharray="3,2"/><text x="9" y="12" font-size="8" text-anchor="middle" fill="{T.AMBER}" font-weight="700">?</text>',
    }
    return f'<svg {base}>{shapes[kind]}</svg>'


def legend_html(kinds: Optional[list[str]] = None, cost_model=None) -> str:
    items = LEGEND_ITEMS if kinds is None else [i for i in LEGEND_ITEMS if i[0] in kinds]
    labels = dict(items)
    if cost_model is not None:
        labels["road"] = f"Road · cost {cost_model.road:g}"
        labels["difficult"] = f"Difficult · cost {cost_model.difficult:g}"
        labels["hazard"] = f"Hazard · cost {cost_model.hazard:g}"
        labels["safe"] = f"Safe zone · cost {cost_model.safe:g}, police barred"
    chips = "".join(f'<span class="cr-legend-item">{legend_swatch(k)}<span>{labels[k]}</span></span>' for k, _ in items)
    return f'<div class="cr-legend">{chips}</div>'
