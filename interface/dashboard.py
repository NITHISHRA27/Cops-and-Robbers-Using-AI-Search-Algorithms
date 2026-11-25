"""Command Center — landing dashboard. Every number is read from live game data or real runs."""
from __future__ import annotations

import json

import streamlit as st
import streamlit.components.v1 as components

from algorithms import run_search
from algorithms.alpha_beta import alphabeta_decision
from algorithms.base import SearchContext
from algorithms.minimax import minimax_decision
from config import settings
from config import theme as T
from experiments.benchmark import compare, results_table
from experiments.metrics import explain
from interface import ui
from visualization.charts import metric_bars
from visualization.animation import search_player_html
from visualization.grid_renderer import auto_cell_size, legend_html, render_svg


def env_key(env) -> str:
    return str(hash(json.dumps(env.to_dict(), sort_keys=True)))


def cached_compare(env):
    cache = st.session_state.setdefault("cmp_cache", {})
    k = env_key(env)
    if k not in cache:
        cache.clear()
        cache[k] = compare(env, repeats=3)
    return cache[k]


def cached_adversarial(env, depth: int = 3):
    cache = st.session_state.setdefault("adv_cache", {})
    k = env_key(env) + f"-{depth}"
    if k not in cache:
        cache.clear()
        m = minimax_decision(env.grid, env.exit, env.robber, env.police, depth=depth)
        a = alphabeta_decision(env.grid, env.exit, env.robber, env.police, depth=depth)
        cache[k] = (m, a)
    return cache[k]


def render() -> None:
    ss = st.session_state
    env, eng = ss.env, ss.engine
    st.markdown(
        f"""<div class="cr-hero"><h1>COPS <span>&amp;</span> ROBBERS</h1>
        <div class="sub">{settings.APP_SUBTITLE.upper()}</div>
        <div class="tag">“{settings.TAGLINE}”</div></div>""", unsafe_allow_html=True)
    b1, b2, b3, _ = st.columns([1.1, 1.2, 1.1, 2])
    if b1.button("▶  Start New Game", type="primary", width="stretch"):
        if ui.new_engine():
            st.switch_page(ui.PAGES["sim"])
    if b2.button("⚙  Configure Environment", width="stretch"):
        st.switch_page(ui.PAGES["config"])
    if b3.button("🧪  Explore Algorithms", width="stretch"):
        st.switch_page(ui.PAGES["lab"])

    hs = ui.history_stats()
    s = eng.state if eng else None
    left, right = st.columns([1.35, 1])
    with left:
        ui.section("Game status")
        cards = [
            ("▦", "Grid dimensions", f"{env.grid.rows} × {env.grid.cols}", T.AQUA),
            ("⛨", "Police officers", len(s.police) if s else len(env.police), T.CORAL),
            ("R", "Robber position", ui.fmt_cell(s.robber if s else env.robber), T.AQUA),
            ("⚑", "Exit position", ui.fmt_cell(env.exit), T.GREEN),
            ("◎", "Nodes expanded", (s.robber_nodes + s.police_nodes) if s else "—", T.TEAL),
            ("⌘", "Current algorithm", "Human" if ss.game_mode == settings.MODE_PVA else ss.robber_algo, T.AMBER),
            ("●", "Game status", ui.STATUS_STYLE.get(s.status if s else "ready")[0], T.TEAL),
            ("✓", "Successful escapes", hs["escaped"], T.GREEN),
            ("✕", "Captures", hs["captured"], T.CORAL),
        ]
        cols = st.columns(3)
        for i, c in enumerate(cards):
            cols[i % 3].markdown(ui.stat(*c), unsafe_allow_html=True)
        if s and s.is_over:
            st.info(s.message)
    with right:
        ui.section("Current city")
        robber = s.robber if s else env.robber
        police = s.police if s else env.police
        svg = render_svg(env.grid, robber, police, env.exit, max_width=520,
                         trail=s.trail if s else (), captured=bool(s and s.status == "captured"))
        st.markdown(f'<div class="cr-mini">{svg}</div>', unsafe_allow_html=True)
        st.markdown(legend_html(["robber", "police", "exit", "wall", "difficult", "hazard", "safe"]),
                    unsafe_allow_html=True)

    results = cached_compare(env)
    rows = results_table(results)
    ui.section("Algorithm overview — measured on the current map")
    blurbs = {
        "BFS": ("Breadth-First Search", "Explores the grid level by level using a FIFO queue.", T.AQUA),
        "UCS": ("Uniform Cost Search", "Finds the least-cost path using accumulated movement costs.", T.AMBER),
        "A*": ("A* Search", "Combines actual movement cost g(n) and heuristic estimate h(n).", T.GREEN),
    }
    cols = st.columns(3)
    for col, row in zip(cols, rows):
        name = row["Algorithm"]
        title, body, color = blurbs[name]
        extra = (f'<div style="display:flex;gap:16px;margin-top:10px;font-size:12px;color:{T.MUTED}">'
                 f'<span>Nodes <b style="color:{T.ICE}">{row["Nodes expanded"]}</b></span>'
                 f'<span>Cost <b style="color:{T.ICE}">{row["Path cost"] if row["Path found"] else "—"}</b></span>'
                 f'<span>Moves <b style="color:{T.ICE}">{row["Path length"] if row["Path found"] else "—"}</b></span>'
                 f'<span>{row["Optimality"]}</span></div>')
        col.markdown(ui.card(f'<span style="color:{color}">{name}</span> · {title}', body, color, extra),
                     unsafe_allow_html=True)

    c1, c2 = st.columns([1.25, 1])
    with c1:
        st.plotly_chart(metric_bars(rows, "Nodes expanded", "Nodes expanded (robber start → exit)"),
                        width="stretch", config={"displayModeBar": False})
    with c2:
        ui.section("Key insights")
        for note in explain(results):
            st.markdown(f"✅ {note}")

    ui.section("Search expansion — watch BFS, UCS and A* explore the city")
    st.caption("A replay of the real expansion trace, recorded by the algorithm on the current map (officer cells "
               "blocked). Frontier = light aqua, explored = blue, final path = green. Press Start or Step.")
    algo = st.radio("Algorithm to replay", ["BFS", "UCS", "A*"], horizontal=True, key="dash_algo")
    trace_cache = st.session_state.setdefault("dash_trace", {})
    tk = (env_key(env), algo)
    if tk not in trace_cache:
        if len(trace_cache) > 6:
            trace_cache.clear()
        ctx = SearchContext(env.grid, blocked=set(env.police))
        trace_cache[tk] = run_search(algo, ctx, env.robber, env.exit, record=True)
    trace = trace_cache[tk]
    cell = auto_cell_size(env.grid, 720)
    base = render_svg(env.grid, env.robber, env.police, env.exit, cell=cell)
    height = int(min(900, max(560, 740 * env.grid.rows / env.grid.cols)))
    components.html(search_player_html(base, trace, env.grid.rows, env.grid.cols, cell, height), height=height)
    if st.button("Open the full Algorithm Laboratory →"):
        st.switch_page(ui.PAGES["lab"])

    ui.section("Advanced AI — strategic extension")
    m, a = cached_adversarial(env)
    saved = 100 * (1 - a.nodes_explored / m.nodes_explored) if m.nodes_explored else 0
    c1, c2 = st.columns(2)
    c1.markdown(ui.card(f'<span style="color:{T.CORAL}">Minimax</span>',
                        "Robber = MAX, police = MIN. Looks ahead over every reply and picks the best worst-case move.",
                        T.CORAL, f'<p style="margin-top:8px">Depth 3 from the start position: <b style="color:{T.ICE}">'
                                 f'{m.nodes_explored}</b> states · decision <b style="color:{T.ICE}">{m.best_action}</b></p>'),
                unsafe_allow_html=True)
    c2.markdown(ui.card(f'<span style="color:{T.TEAL}">Alpha-Beta Pruning</span>',
                        "Same decision as Minimax, but skips branches that cannot change it.",
                        T.TEAL, f'<p style="margin-top:8px">Depth 3: <b style="color:{T.ICE}">{a.nodes_explored}</b> states '
                                f'({saved:.0f}% fewer) · {a.branches_pruned} branches pruned · decision '
                                f'<b style="color:{T.ICE}">{a.best_action}</b></p>'),
                unsafe_allow_html=True)
    if st.button("Open Strategic AI →"):
        st.switch_page(ui.PAGES["strategic"])
