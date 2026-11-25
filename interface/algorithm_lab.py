"""Algorithm Laboratory — replay genuine BFS / UCS / A* expansion traces on the same grid."""
from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from algorithms import run_search
from algorithms.base import SearchContext
from config import theme as T
from experiments.benchmark import compare, results_table
from experiments.scenarios import SCENARIOS, build_scenario
from interface import ui
from interface.dashboard import env_key
from visualization.animation import search_player_html
from visualization.grid_renderer import auto_cell_size, legend_html, render_svg

INFO = {
    "BFS": {
        "color": T.AQUA, "ds": "FIFO queue", "complete": "Yes (finite grid)",
        "optimal": "Fewest moves only — not least cost on weighted terrain",
        "time": "O(b^d)", "space": "O(b^d)",
        "principle": "Expand the shallowest node first. Every cell at distance k is examined before any cell at "
                     "distance k+1, so the first time the exit is generated the route has the fewest moves.",
        "limit": "Terrain costs are invisible to BFS: a 2-move route through hazards (cost 10) beats a 4-move "
                 "clean detour (cost 4).",
        "code": "frontier ← FIFO[start]; reached ← {start}\nwhile frontier:\n    n ← frontier.pop_front()\n"
                "    for m in successors(n):\n        if m ∉ reached:\n            parent[m] ← n\n"
                "            if m = goal: return path(m)\n            reached.add(m); frontier.push_back(m)\nreturn failure",
    },
    "UCS": {
        "color": T.AMBER, "ds": "Priority queue keyed by g(n)", "complete": "Yes (costs > 0)",
        "optimal": "Yes — least total cost", "time": "O(b^(1+⌊C*/ε⌋))", "space": "O(b^(1+⌊C*/ε⌋))",
        "principle": "Always expand the frontier node with the lowest accumulated cost g(n). Goal test happens on "
                     "expansion, so when the exit is popped no cheaper route can exist.",
        "limit": "It has no sense of direction: it expands in cost-contours around the start, including away "
                 "from the exit.",
        "code": "frontier ← PQ[(0, start)]; g[start] ← 0\nwhile frontier:\n    n ← frontier.pop_min()\n"
                "    if stale(n): continue\n    if n = goal: return path(n)\n    for m in successors(n):\n"
                "        if g[n] + c(m) < g[m]:\n            g[m] ← g[n] + c(m); parent[m] ← n\n"
                "            frontier.push((g[m], m))\nreturn failure",
    },
    "A*": {
        "color": T.GREEN, "ds": "Priority queue keyed by f(n) = g(n) + h(n)", "complete": "Yes",
        "optimal": "Yes — with an admissible, consistent h", "time": "≤ UCS (depends on h quality)",
        "space": "≤ UCS",
        "principle": "Like UCS but ordered by f(n) = g(n) + h(n), where h is the weighted Manhattan distance to the "
                     "exit. The heuristic pulls the search towards the goal, so fewer cells are expanded.",
        "limit": "When walls or expensive terrain block the straight line, h underestimates more and A* "
                 "degrades towards UCS — but it never returns a worse path.",
        "code": "frontier ← PQ[(h(start), start)]; g[start] ← 0\nwhile frontier:\n    n ← frontier.pop_min_f()\n"
                "    if stale(n): continue\n    if n = goal: return path(n)\n    for m in successors(n):\n"
                "        if g[n] + c(m) < g[m]:\n            g[m] ← g[n] + c(m); parent[m] ← n\n"
                "            frontier.push((g[m] + h(m), m))\nreturn failure",
    },
}


def lab_environment():
    ss = st.session_state
    sources = ["Current game map"] + list(SCENARIOS)
    c1, c2, c3 = st.columns([1.2, 1.6, 1])
    algo = c1.radio("Algorithm", ["BFS", "UCS", "A*"], horizontal=True, key="lab_algo")
    src = c2.selectbox("Environment", sources, key="lab_src")
    block = c3.toggle("Officers block cells", value=True, key="lab_block",
                      help="Treat police positions as obstacles (identical for all three algorithms).")
    if src == "Current game map":
        env = ss.env
    else:
        cache = ss.setdefault("scenario_cache", {})
        k = (src, ss.env.grid.rows, ss.env.grid.cols)
        if k not in cache:
            cache[k] = build_scenario(src, ss.env.grid.rows, ss.env.grid.cols, len(ss.env.police),
                                      costs=ss.env.grid.cost_model)
        env = cache[k]
        st.caption(SCENARIOS[src])
    return algo, env, block


def render() -> None:
    ui.page_header("🧪", "Algorithm Laboratory", "Watch the real expansion order of BFS, UCS and A* on the same city.")
    algo, env, block = lab_environment()
    ctx = SearchContext(env.grid, blocked=set(env.police) if block else ())
    cache = st.session_state.setdefault("lab_cache", {})
    k = (env_key(env), algo, block)
    if k not in cache:
        if len(cache) > 12:
            cache.clear()
        cache[k] = run_search(algo, ctx, env.robber, env.exit, record=True)
    res = cache[k]

    cell = auto_cell_size(env.grid, 720)
    base = render_svg(env.grid, env.robber, env.police, env.exit, cell=cell)
    height = int(min(900, max(560, 740 * env.grid.rows / env.grid.cols)))
    components.html(search_player_html(base, res, env.grid.rows, env.grid.cols, cell, height), height=height)
    st.markdown(legend_html(["robber", "police", "exit", "wall", "difficult", "hazard", "safe", "explored",
                             "frontier", "path"], env.grid.cost_model), unsafe_allow_html=True)

    info = INFO[algo]
    ui.section(f"{algo} at a glance")
    c = st.columns(4)
    c[0].markdown(ui.stat("◎", "Nodes expanded", res.nodes_expanded, info["color"]), unsafe_allow_html=True)
    c[1].markdown(ui.stat("↗", "Path length", res.path_length if res.found else "no path", info["color"]), unsafe_allow_html=True)
    c[2].markdown(ui.stat("Σ", "Path cost", f"{res.cost:g}" if res.found else "—", info["color"]), unsafe_allow_html=True)
    c[3].markdown(ui.stat("⏱", "Execution time", f"{res.time_ms:.3f} ms", info["color"]), unsafe_allow_html=True)

    col1, col2 = st.columns([1.1, 1])
    with col1:
        st.markdown(ui.card("Working principle", info["principle"], info["color"])
                    + ui.card("Limitation", info["limit"], T.CORAL), unsafe_allow_html=True)
        with st.expander("Pseudocode (as implemented)"):
            st.code(info["code"], language="text")
    with col2:
        props = pd.DataFrame([
            {"Property": "Data structure", algo: info["ds"]},
            {"Property": "Complete", algo: info["complete"]},
            {"Property": "Optimal", algo: info["optimal"]},
            {"Property": "Time complexity", algo: info["time"]},
            {"Property": "Space complexity", algo: info["space"]},
            {"Property": "Max frontier (this run)", algo: str(res.max_frontier)},
            {"Property": "Nodes generated (this run)", algo: str(res.nodes_generated)},
        ])
        st.dataframe(props, hide_index=True, width="stretch")

    ui.section("Same grid, all three algorithms (measured)")
    rows = results_table(compare(env, repeats=3, block_police=block))
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
