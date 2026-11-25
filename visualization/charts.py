"""Plotly chart builders. Every chart is drawn from measured data passed in by the caller."""
from __future__ import annotations

import math

import plotly.graph_objects as go

from config import theme as T


def _layout(fig: go.Figure, title: str = "", height: int = 300, **kw) -> go.Figure:
    fig.update_layout(**T.PLOTLY_LAYOUT)
    fig.update_layout(title=dict(text=title, font=dict(size=14, color=T.ICE), x=0.01), height=height, **kw)
    return fig


def metric_bars(rows: list[dict], metric: str, title: str, unit: str = "") -> go.Figure:
    names = [r["Algorithm"] for r in rows]
    vals = [r.get(metric) if r.get(metric) is not None else 0 for r in rows]
    fig = go.Figure(go.Bar(
        x=names, y=vals, marker=dict(color=[T.ALGO_COLORS.get(n, T.TEAL) for n in names],
                                     line=dict(color="rgba(255,255,255,0.15)", width=1)),
        text=[f"{v:g}{unit}" if isinstance(v, (int, float)) else "—" for v in vals], textposition="outside",
        hovertemplate="%{x}: %{y}" + unit + "<extra></extra>", width=0.55))
    _layout(fig, title, 280, showlegend=False)
    fig.update_yaxes(rangemode="tozero")
    if vals and max(vals) > 0:
        fig.update_yaxes(range=[0, max(vals) * 1.22])
    return fig


def grouped_bars(batch: list[dict], metric: str, title: str, log: bool = False) -> go.Figure:
    scenarios = list(dict.fromkeys(r["Scenario"] for r in batch))
    fig = go.Figure()
    for algo in ("BFS", "UCS", "A*"):
        ys = [next((r[metric] for r in batch if r["Scenario"] == s and r["Algorithm"] == algo), None) for s in scenarios]
        fig.add_bar(name=algo, x=scenarios, y=ys, marker_color=T.ALGO_COLORS[algo])
    _layout(fig, title, 340, barmode="group", legend=dict(orientation="h", y=1.12, x=0))
    if log:
        fig.update_yaxes(type="log")
    fig.update_xaxes(tickangle=-18)
    return fig


def heatmap(matrix: list[list[float | None]], title: str, colorscale, zmin=None, zmax=None,
            marker: tuple[int, int] | None = None) -> go.Figure:
    fig = go.Figure(go.Heatmap(z=matrix, colorscale=colorscale, zmin=zmin, zmax=zmax, hoverongaps=False,
                               colorbar=dict(thickness=10, outlinewidth=0, tickfont=dict(color=T.MUTED)),
                               hovertemplate="row %{y}, col %{x}: %{z}<extra></extra>"))
    if marker is not None:
        fig.add_scatter(x=[marker[1]], y=[marker[0]], mode="markers", showlegend=False,
                        marker=dict(symbol="square-open", size=12, color=T.ICE, line=dict(width=2)))
    _layout(fig, title, 330)
    fig.update_yaxes(autorange="reversed", scaleanchor="x", showgrid=False)
    fig.update_xaxes(showgrid=False)
    return fig


def contribution_bars(contrib: dict[str, float], labels: dict[str, str], title: str) -> go.Figure:
    keys = list(contrib)
    vals = [contrib[k] for k in keys]
    fig = go.Figure(go.Bar(y=[labels.get(k, k) for k in keys], x=vals, orientation="h",
                           marker_color=[T.GREEN if v >= 0 else T.CORAL for v in vals],
                           text=[f"{v:+.1f}" for v in vals], textposition="outside",
                           hovertemplate="%{y}: %{x:+.1f}<extra></extra>"))
    _layout(fig, title, 260, showlegend=False)
    span = max([abs(v) for v in vals] + [1]) * 1.3
    fig.update_xaxes(range=[-span, span], zeroline=True, zerolinecolor=T.MUTED)
    return fig


def action_values(child_values: dict[str, float], best: str, title: str) -> go.Figure:
    acts = list(child_values)
    vals = [child_values[a] for a in acts]
    shown = [max(min(v, 200), -200) for v in vals]  # keep ±1000 terminals readable
    fig = go.Figure(go.Bar(x=acts, y=shown, marker_color=[T.GREEN if a == best else T.TEAL for a in acts],
                           text=[("ESCAPE" if v > 900 else "CAPTURE" if v < -900 else f"{v:.1f}") for v in vals],
                           textposition="outside", hovertemplate="%{x}: %{text}<extra></extra>"))
    _layout(fig, title, 260, showlegend=False)
    return fig


def depth_sweep(rows: list[dict]) -> go.Figure:
    fig = go.Figure()
    d = [r["depth"] for r in rows]
    fig.add_scatter(x=d, y=[r["minimax"] for r in rows], name="Minimax", mode="lines+markers",
                    line=dict(color=T.CORAL, width=3))
    fig.add_scatter(x=d, y=[r["alphabeta"] for r in rows], name="Alpha-Beta", mode="lines+markers",
                    line=dict(color=T.AQUA, width=3))
    _layout(fig, "States explored vs. depth (log scale)", 300, legend=dict(orientation="h", y=1.14, x=0))
    fig.update_yaxes(type="log", title="states")
    fig.update_xaxes(title="search depth (plies)", dtick=1)
    return fig


def game_tree(nodes, title: str) -> go.Figure:
    """Tidy layout: leaves spaced evenly, parents centred over children."""
    children: dict[int, list[int]] = {}
    for n in nodes:
        if n.parent is not None:
            children.setdefault(n.parent, []).append(n.id)
    x: dict[int, float] = {}
    counter = [0]

    def place(nid: int) -> float:
        kids = children.get(nid, [])
        if not kids:
            x[nid] = counter[0]
            counter[0] += 1
        else:
            xs = [place(k) for k in kids]
            x[nid] = sum(xs) / len(xs)
        return x[nid]

    if not nodes:
        return _layout(go.Figure(), title)
    place(nodes[0].id)
    # best line: follow children whose value equals parent's value
    best_edges = set()
    cur = nodes[0]
    while children.get(cur.id):
        match = [nodes[k] for k in children[cur.id] if not nodes[k].pruned and nodes[k].value is not None
                 and cur.value is not None and abs(nodes[k].value - cur.value) < 1e-9]
        if not match:
            break
        best_edges.add((cur.id, match[0].id))
        cur = match[0]

    ex, ey, bx, by = [], [], [], []
    for n in nodes:
        if n.parent is None:
            continue
        tx, ty = (bx, by) if (n.parent, n.id) in best_edges else (ex, ey)
        tx += [x[n.parent], x[n.id], None]
        ty += [-nodes[n.parent].depth, -n.depth, None]
    fig = go.Figure()
    fig.add_scatter(x=ex, y=ey, mode="lines", line=dict(color="rgba(139,155,173,0.35)", width=1), hoverinfo="skip", showlegend=False)
    fig.add_scatter(x=bx, y=by, mode="lines", line=dict(color=T.GREEN, width=3), hoverinfo="skip", name="Principal variation")

    def fmt(v):
        if v is None:
            return "—"
        if v in (math.inf, -math.inf):
            return "∞" if v > 0 else "−∞"
        return f"{v:.1f}"

    groups = {"MAX (robber)": ([], T.AQUA, "circle"), "MIN (police)": ([], T.CORAL, "diamond"),
              "Leaf / terminal": ([], T.AMBER, "square"), "Pruned": ([], "#5D6B7B", "x")}
    for n in nodes:
        key = "Pruned" if n.pruned else ("Leaf / terminal" if n.player == "LEAF" else
                                          "MAX (robber)" if n.player == "MAX" else "MIN (police)")
        groups[key][0].append(n)
    for name, (items, color, symbol) in groups.items():
        if not items:
            continue
        hover = [f"<b>{n.action}</b><br>depth {n.depth}<br>value {fmt(n.value)}"
                 + (f"<br>α {fmt(n.alpha)} · β {fmt(n.beta)}" if n.alpha is not None else "")
                 + (f"<br>{n.terminal.upper()}" if n.terminal else "") + ("<br><i>pruned — never evaluated</i>" if n.pruned else "")
                 for n in items]
        size = 7 if len(nodes) > 600 else 10
        fig.add_scatter(x=[x[n.id] for n in items], y=[-n.depth for n in items], mode="markers", name=name,
                        marker=dict(color=color, size=size, symbol=symbol, line=dict(color="rgba(0,0,0,.4)", width=1)),
                        hovertext=hover, hoverinfo="text")
    _layout(fig, title, 420, legend=dict(orientation="h", y=1.1, x=0))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(tickvals=[-d for d in range(0, max(n.depth for n in nodes) + 1)],
                     ticktext=[f"ply {d}" for d in range(0, max(n.depth for n in nodes) + 1)], showgrid=False)
    return fig
