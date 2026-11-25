"""Strategic AI — Minimax and Alpha-Beta pruning (optional advanced extension)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from algorithms.alpha_beta import alphabeta_decision
from algorithms.minimax import minimax_decision
from config import theme as T
from environment.grid import apply_action
from heuristics.evaluation import WEIGHT_NOTES, EvalContext, EvalWeights
from interface import ui
from visualization.charts import action_values, contribution_bars, depth_sweep, game_tree
from visualization.grid_renderer import render_svg

CFG = {"displayModeBar": False}
LABELS = {k: v[0] for k, v in WEIGHT_NOTES.items()}


def render() -> None:
    ss = st.session_state
    ui.page_header("♟", "Strategic AI", "Optional extension: adversarial look-ahead with Minimax and Alpha-Beta pruning. "
                                        "BFS, UCS and A* remain the core search algorithms.")
    eng = ss.engine
    env = ss.env
    sources = ["Map start position"] + (["Current game position"] if eng and not eng.is_over else [])
    c1, c2, c3 = st.columns([1.4, 1, 1])
    src = c1.radio("Position", sources, horizontal=True, index=len(sources) - 1)
    officers = c3.select_slider("Officers modelled (MIN)", [1, 2], value=1,
                                help="Nearest officers that move inside the tree. Branching per police ply = 5^k.")
    max_depth = 6 if officers == 1 else 4
    depth = c2.slider("Search depth (plies)", 1, max_depth, min(3, max_depth))
    if src == "Current game position":
        robber, police, grid, exit_ = eng.state.robber, list(eng.state.police), eng.grid, eng.state.exit
    else:
        robber, police, grid, exit_ = env.robber, list(env.police), env.grid, env.exit

    with st.expander("⚖ Evaluation function & weights (configurable, robber = MAX)", expanded=False):
        st.markdown('<div class="cr-formula" style="font-size:15px">E(s) = −w<sub>exit</sub>·d<sub>exit</sub> '
                    '+ w<sub>cop</sub>·min(d<sub>cop</sub>, 6) + w<sub>route</sub>·routes + w<sub>block</sub>·race '
                    '− w<sub>risk</sub>·risk</div>', unsafe_allow_html=True)
        st.caption("Terminal states override E: escape = +1000 − ply, capture = −1000 + ply. Distances are real "
                   "BFS move counts through the city, not straight-line estimates.")
        wcols = st.columns(5)
        weights = {}
        for col, (k, (label, default, why)) in zip(wcols, WEIGHT_NOTES.items()):
            weights[k] = col.number_input(label, 0.0, 200.0, float(default), step=1.0, key=f"w_eval_{k}")
        for k, (label, default, why) in WEIGHT_NOTES.items():
            st.markdown(f"**{label} — default {default:g}.** {why}")
    w = EvalWeights(**weights)

    m = minimax_decision(grid, exit_, robber, police, depth=depth, weights=w, n_modelled=officers, record_tree=True)
    a = alphabeta_decision(grid, exit_, robber, police, depth=depth, weights=w, n_modelled=officers, record_tree=True)
    same = m.best_action == a.best_action and abs(m.best_value - a.best_value) < 1e-9
    saved = 100 * (1 - a.nodes_explored / m.nodes_explored) if m.nodes_explored else 0

    ui.section("Decision")
    k = st.columns(5)
    k[0].markdown(ui.stat("➜", "Chosen move", a.best_action, T.GREEN), unsafe_allow_html=True)
    k[1].markdown(ui.stat("V", "Root value", f"{a.best_value:.1f}", T.AQUA), unsafe_allow_html=True)
    k[2].markdown(ui.stat("M", "Minimax states", f"{m.nodes_explored:,}", T.CORAL), unsafe_allow_html=True)
    k[3].markdown(ui.stat("αβ", "Alpha-Beta states", f"{a.nodes_explored:,} (−{saved:.0f}%)", T.TEAL), unsafe_allow_html=True)
    k[4].markdown(ui.stat("✂", "Branches pruned", f"{a.branches_pruned:,}", T.AMBER), unsafe_allow_html=True)
    st.markdown(ui.badge("✓ Identical decision and value" if same else "✗ Decisions differ", T.GREEN if same else T.CORAL)
                + f'&nbsp; <span style="color:{T.MUTED};font-size:13px">Minimax {m.time_ms:.1f} ms · Alpha-Beta '
                  f'{a.time_ms:.1f} ms · modelled officer(s): {", ".join(str(i + 1) for i in a.modelled_officers)}</span>',
                unsafe_allow_html=True)

    left, right = st.columns([1, 1.25])
    with left:
        nxt = apply_action(robber, a.best_action)
        svg = render_svg(grid, robber, police, exit_, max_width=520, path=[robber, nxt])
        st.markdown(f'<div class="cr-mini">{svg}</div>', unsafe_allow_html=True)
    with right:
        st.plotly_chart(action_values(m.child_values, m.best_action, "Minimax value of each robber move"),
                        width="stretch", config=CFG)
        ec = EvalContext(grid, exit_, w)
        contrib = ec.contributions(nxt, tuple(police))
        st.plotly_chart(contribution_bars(contrib, LABELS, f"Evaluation breakdown after {a.best_action} "
                                                           f"(E = {sum(contrib.values()):.1f})"),
                        width="stretch", config=CFG)

    ui.section("Game tree")
    t1, t2 = st.tabs(["Alpha-Beta tree (pruned nodes marked ✕)", "Minimax tree (full)"])
    with t1:
        if a.tree_truncated:
            st.caption("Tree truncated to the first 4,000 nodes for display — the statistics above are complete.")
        st.plotly_chart(game_tree(a.tree, f"Alpha-Beta · depth {depth} · hover for α/β"), width="stretch", config=CFG)
    with t2:
        if m.tree_truncated:
            st.caption("Tree truncated to the first 4,000 nodes for display — the statistics above are complete.")
        st.plotly_chart(game_tree(m.tree, f"Minimax · depth {depth}"), width="stretch", config=CFG)

    ui.section("Cost of looking further ahead (measured)")
    cache = ss.setdefault("sweep_cache", {})
    key = (str(robber), str(police), officers, tuple(weights.values()), id(grid))
    if key not in cache:
        cache.clear()
        rows = []
        for d in range(1, max_depth + 1):
            mm = minimax_decision(grid, exit_, robber, police, depth=d, weights=w, n_modelled=officers)
            aa = alphabeta_decision(grid, exit_, robber, police, depth=d, weights=w, n_modelled=officers)
            rows.append({"depth": d, "minimax": mm.nodes_explored, "alphabeta": aa.nodes_explored,
                         "pruned": aa.branches_pruned, "mm_ms": round(mm.time_ms, 2), "ab_ms": round(aa.time_ms, 2),
                         "same": mm.best_action == aa.best_action})
        cache[key] = rows
    rows = cache[key]
    c1, c2 = st.columns([1.3, 1])
    c1.plotly_chart(depth_sweep(rows), width="stretch", config=CFG)
    c2.dataframe(pd.DataFrame(rows).rename(columns={"depth": "Depth", "minimax": "Minimax states",
                                                    "alphabeta": "α-β states", "pruned": "Pruned",
                                                    "mm_ms": "Minimax ms", "ab_ms": "α-β ms", "same": "Same move"}),
                 hide_index=True, width="stretch")

    ui.section("How it applies to pursuit & escape")
    cols = st.columns(3)
    cols[0].markdown(ui.card("Robber = MAX", "Chooses the move whose <b>worst</b> outcome (after the police reply) is "
                             "best. It sees captures coming within the horizon, unlike A* which only plans a route.",
                             T.AQUA), unsafe_allow_html=True)
    cols[1].markdown(ui.card("Police = MIN", "One joint move for the nearest officer(s) per ply. Each officer has up "
                             "to 5 options, so k officers give 5^k branches — why depth grows so expensive.",
                             T.CORAL), unsafe_allow_html=True)
    cols[2].markdown(ui.card("Alpha-Beta", "α = value the robber can already guarantee, β = what the police can hold "
                             "it to. When α ≥ β the rest of that branch cannot matter and is skipped — same answer, "
                             "far fewer states.", T.TEAL), unsafe_allow_html=True)
    st.caption("Use Minimax or Alpha-Beta as the robber's brain in Live Simulation (AI vs AI) to watch it play.")
