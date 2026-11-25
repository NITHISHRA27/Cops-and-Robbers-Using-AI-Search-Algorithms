"""Heuristic Explorer — Manhattan distance, admissibility and consistency on the real grid."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithms.astar import astar
from algorithms.base import SearchContext
from config import theme as T
from heuristics.manhattan import (check_admissible, check_consistent, cost_from_start, manhattan,
                                  true_cost_to_goal)
from interface import ui
from interface.dashboard import env_key
from visualization.charts import heatmap, metric_bars
from visualization.grid_renderer import legend_html, render_svg

SCALE_AQUA = [[0, T.DEEP_NAVY], [0.5, T.TEAL], [1, T.AQUA]]
SCALE_AMBER = [[0, T.DEEP_NAVY], [0.5, "#8A6424"], [1, T.AMBER]]
SCALE_GAP = [[0, T.GREEN], [0.4, T.PANEL], [1, T.CORAL]]


def _analysis(env):
    cache = st.session_state.setdefault("heur_cache", {})
    k = env_key(env)
    if k not in cache:
        cache.clear()
        g = env.grid
        hstar = true_cost_to_goal(g, env.exit)
        gfrom = cost_from_start(g, env.robber)
        adm = check_admissible(g, env.exit)
        con = check_consistent(g, env.exit)
        m = g.cost_model.min_cost
        variants = {}
        ctx = SearchContext(g)
        for label, fn in (("h = 0  (UCS)", lambda a, b: 0.0),
                          ("h = Manhattan × min cost (ours)", lambda a, b: manhattan(a, b) * m),
                          ("h = 2 × Manhattan (inadmissible)", lambda a, b: manhattan(a, b) * m * 2.0),
                          ("h = 4 × Manhattan (inadmissible)", lambda a, b: manhattan(a, b) * m * 4.0)):
            variants[label] = astar(ctx, env.robber, env.exit, heuristic=fn)
        cache[k] = (hstar, gfrom, adm, con, variants)
    return cache[k]


def render() -> None:
    ss = st.session_state
    env = ss.env
    g = env.grid
    ui.page_header("🧭", "Heuristic Explorer", "How A* estimates the remaining distance — and why that estimate is safe.")
    m = g.cost_model.min_cost
    c1, c2, c3 = st.columns(3)
    c1.markdown('<div class="cr-formula">h(n) = |r − r<sub>goal</sub>| + |c − c<sub>goal</sub>|</div>', unsafe_allow_html=True)
    c1.caption("Manhattan distance: the number of 4-directional moves on an empty grid.")
    c2.markdown(f'<div class="cr-formula">h<sub>w</sub>(n) = {m:g} × Manhattan</div>', unsafe_allow_html=True)
    c2.caption("Weighted terrain: multiply by the cheapest step cost so h never overestimates.")
    c3.markdown('<div class="cr-formula">f(n) = g(n) + h(n)</div>', unsafe_allow_html=True)
    c3.caption("A* priority: cost so far + estimated cost to go.")

    hstar, gfrom, (adm_ok, adm_n, worst), (con_ok, con_n), variants = _analysis(env)
    sel = ss.get("h_sel", env.robber)
    if not g.in_bounds(sel):
        sel = env.robber

    ui.section("Pick any cell")
    left, right = st.columns([1.35, 1])
    with left:
        svg = render_svg(g, env.robber, env.police, env.exit, max_width=700, selected=sel)
        ev = ui.fresh_event("heur_board", ui.board(svg, g.rows, g.cols, mode="select", key="heur_board"))
        if ev and ev.get("type") == "click":
            ss.h_sel = (ev["r"], ev["c"])
            st.rerun()
        st.markdown(legend_html(["robber", "police", "exit", "wall", "difficult", "hazard", "safe"], g.cost_model),
                    unsafe_allow_html=True)
    with right:
        dr, dc = abs(sel[0] - env.exit[0]), abs(sel[1] - env.exit[1])
        h = (dr + dc) * m
        if not g.is_passable(sel):
            st.warning(f"{ui.fmt_cell(sel)} is a building — pick a road cell.")
        else:
            hs = hstar.get(sel)
            gs = gfrom.get(sel)
            st.markdown(
                ui.stat("⌖", "Selected cell", ui.fmt_cell(sel), T.ICE)
                + ui.stat("h", f"h(n) = {m:g} × ({dr} + {dc})", f"{h:g}", T.AQUA)
                + ui.stat("h*", "True cost to exit h*(n)", f"{hs:g}" if hs is not None else "unreachable", T.AMBER)
                + ui.stat("g", "Cheapest cost from robber g(n)", f"{gs:g}" if gs is not None else "unreachable", T.TEAL)
                + ui.stat("f", "f(n) = g(n) + h(n)", f"{gs + h:g}" if gs is not None else "—", T.GREEN),
                unsafe_allow_html=True)
            if hs is not None:
                ok = h <= hs + 1e-9
                st.markdown(ui.badge("h ≤ h*  ✓ admissible here" if ok else "h > h*  ✗ overestimate",
                                     T.GREEN if ok else T.CORAL)
                            + f'&nbsp; <span style="color:{T.MUTED};font-size:13px">estimate is '
                              f'{(h / hs * 100 if hs else 100):.0f}% of the true cost</span>', unsafe_allow_html=True)

    ui.section("Estimated vs. actual cost across the whole map")
    def matrix(fn):
        return [[fn((r, c)) for c in range(g.cols)] for r in range(g.rows)]
    hm = matrix(lambda c: manhattan(c, env.exit) * m if c in hstar else None)
    hsm = matrix(lambda c: hstar.get(c))
    gap = matrix(lambda c: (hstar[c] - manhattan(c, env.exit) * m) if c in hstar else None)
    t1, t2, t3 = st.tabs(["h(n) — estimate", "h*(n) — true cost", "h* − h — slack"])
    cfg = {"displayModeBar": False}
    with t1:
        st.plotly_chart(heatmap(hm, "Manhattan estimate to exit", SCALE_AQUA, marker=sel), width="stretch", config=cfg)
    with t2:
        st.plotly_chart(heatmap(hsm, "True cheapest cost to exit (reverse Dijkstra)", SCALE_AMBER, marker=sel),
                        width="stretch", config=cfg)
    with t3:
        st.plotly_chart(heatmap(gap, "Slack h* − h (never negative ⇒ admissible)", SCALE_GAP, zmin=0, marker=sel),
                        width="stretch", config=cfg)

    c1, c2, c3 = st.columns(3)
    c1.markdown(ui.stat("✓" if adm_ok else "✗", f"Admissible on {adm_n} cells", "Yes" if adm_ok else "No",
                        T.GREEN if adm_ok else T.CORAL), unsafe_allow_html=True)
    c2.markdown(ui.stat("✓" if con_ok else "✗", f"Consistent on {con_n} edges", "Yes" if con_ok else "No",
                        T.GREEN if con_ok else T.CORAL), unsafe_allow_html=True)
    c3.markdown(ui.stat("≈", "Tightest h / h* ratio", f"{worst:.2f}", T.AQUA), unsafe_allow_html=True)

    ui.section("Heuristic evaluation — real A* runs with different h")
    ucs_cost = variants["h = 0  (UCS)"].cost
    rows = [{"Algorithm": k, "Nodes expanded": r.nodes_expanded, "Path cost": round(r.cost, 2) if r.found else None,
             "Path length": r.path_length, "Optimal": ("Yes" if r.found and abs(r.cost - ucs_cost) < 1e-9 else "No"),
             "Time (ms)": round(r.time_ms, 3)} for k, r in variants.items()]
    c1, c2 = st.columns([1, 1.1])
    c1.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    fig = metric_bars(rows, "Nodes expanded", "Nodes expanded by heuristic")
    fig.update_xaxes(tickfont=dict(size=10))
    c2.plotly_chart(fig, width="stretch", config=cfg)
    st.caption("A stronger (larger) heuristic expands fewer nodes, but once it overestimates it can return a more "
               "expensive path. Our weighted Manhattan is the largest h that is still provably admissible.")

    ui.section("Concepts")
    cols = st.columns(2)
    with cols[0]:
        with st.expander("💡 What is a heuristic?", expanded=True):
            st.markdown("A **heuristic** h(n) is a cheap estimate of the cost from node *n* to the goal. "
                        "A* uses it to decide which frontier node looks most promising, instead of expanding "
                        "blindly in all directions like UCS.")
        with st.expander("📐 Why Manhattan distance?"):
            st.markdown("Agents move only **up, down, left, right**. On an empty grid the fewest moves between two "
                        "cells is exactly |Δr| + |Δc|. Walls can only make the real route longer, never shorter. "
                        "(Euclidean distance would also be admissible but is a weaker, smaller estimate here.)")
        with st.expander("⚖ Weighted terrain"):
            st.markdown(f"Each move costs **at least {m:g}** (the cheapest terrain). A route with k moves therefore "
                        f"costs ≥ {m:g}·k ≥ {m:g}·Manhattan. Multiplying by the *minimum* cost keeps h admissible; "
                        "multiplying by an average or maximum cost would overestimate on cheap roads.")
    with cols[1]:
        with st.expander("✅ Admissibility", expanded=True):
            st.markdown("h is **admissible** if h(n) ≤ h*(n) for every n — it never overestimates. "
                        "Then A* is guaranteed to return an optimal path. "
                        f"Checked above on all **{adm_n}** reachable cells of this map.")
        with st.expander("🔗 Consistency (monotonicity)"):
            st.markdown("h is **consistent** if h(n) ≤ c(n, n′) + h(n′) for every move n → n′. "
                        "A move changes Manhattan distance by exactly 1 and costs ≥ min cost, so the inequality "
                        f"holds. Consistency means f never decreases along a path, so a closed cell never needs "
                        f"reopening. Verified on **{con_n}** edges.")
        with st.expander("🎯 Where the estimate is weak"):
            st.markdown("Look at the *slack* heatmap: cells behind buildings or past difficult terrain have large "
                        "h* − h. There A* gets less guidance and expands more nodes — the obstacle-heavy and "
                        "weighted scenarios in the Performance Arena show this effect.")
