"""Game History — persisted results of finished games with inspection and replay trail."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import theme as T
from environment.state import Environment
from interface import ui
from persistence.history import clear_history, load_history
from visualization.grid_renderer import render_svg

OUTCOME_COLORS = {"escaped": T.GREEN, "captured": T.CORAL, "timeout": T.AMBER}


def render() -> None:
    ui.page_header("🗂", "Game History", "Every finished game is saved locally (data/history.json).")
    hist = load_history()
    stats = ui.history_stats()
    c = st.columns(5)
    c[0].markdown(ui.stat("#", "Games played", stats["games"], T.AQUA), unsafe_allow_html=True)
    c[1].markdown(ui.stat("✓", "Escapes", stats["escaped"], T.GREEN), unsafe_allow_html=True)
    c[2].markdown(ui.stat("✕", "Captures", stats["captured"], T.CORAL), unsafe_allow_html=True)
    c[3].markdown(ui.stat("⛔", "Contained (turn limit)", stats["timeout"], T.AMBER), unsafe_allow_html=True)
    rate = f"{100 * stats['escaped'] / stats['games']:.0f}%" if stats["games"] else "—"
    c[4].markdown(ui.stat("%", "Robber escape rate", rate, T.TEAL), unsafe_allow_html=True)

    if not hist:
        st.info("No games yet — finish a game in Live Simulation and it will appear here.")
        if st.button("▶ Play a game", type="primary"):
            st.switch_page(ui.PAGES["sim"])
        return

    df = pd.DataFrame([{
        "ID": h.get("id"), "When": h.get("timestamp"), "Mode": h.get("mode"), "Grid": h.get("grid"),
        "Police": h.get("police"), "Robber algorithm": h.get("algorithm"), "Turns": h.get("turns"),
        "Nodes expanded": h.get("nodes_expanded"), "Outcome": h.get("outcome"), "Compute (ms)": h.get("compute_ms"),
    } for h in hist])
    f1, f2 = st.columns(2)
    modes = f1.multiselect("Mode", sorted(df["Mode"].dropna().unique()), default=None, placeholder="All modes")
    outcomes = f2.multiselect("Outcome", sorted(df["Outcome"].dropna().unique()), default=None, placeholder="All outcomes")
    view = df
    if modes:
        view = view[view["Mode"].isin(modes)]
    if outcomes:
        view = view[view["Outcome"].isin(outcomes)]
    st.dataframe(view, hide_index=True, width="stretch")

    left, right = st.columns([1, 1.2])
    with left:
        ui.section("Outcomes by robber algorithm")
        fig = go.Figure()
        for outcome, color in OUTCOME_COLORS.items():
            sub = df[df["Outcome"] == outcome].groupby("Robber algorithm").size()
            fig.add_bar(name=outcome, x=list(sub.index), y=list(sub.values), marker_color=color)
        fig.update_layout(**T.PLOTLY_LAYOUT)
        fig.update_layout(barmode="stack", height=300, legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with right:
        ui.section("Inspect a game")
        options = {f"{h['id']} · {h.get('timestamp', '')} · {h.get('outcome', '').upper()}": h for h in hist}
        choice = st.selectbox("Game", list(options))
        h = options[choice]
        try:
            env = Environment.from_dict(h["env"])
            trail = [tuple(c) for c in h.get("trail", [])]
            police = [tuple(c) for c in h.get("police_final", [])]
            svg = render_svg(env.grid, trail[-1] if trail else env.robber, police, env.exit, max_width=520,
                             trail=trail, captured=h.get("outcome") == "captured")
            st.markdown(f'<div class="cr-mini">{svg}</div>', unsafe_allow_html=True)
        except (KeyError, TypeError, ValueError):
            st.caption("This record has no replay data.")
        st.markdown(f"**{h.get('message', '')}**  \n{h.get('mode')} · {h.get('grid')} · {h.get('police')} officer(s) · "
                    f"robber: {h.get('algorithm')} · {h.get('turns')} turns · {h.get('moves', '—')} moves · "
                    f"route cost {h.get('robber_cost', '—')} · robber/police nodes "
                    f"{h.get('robber_nodes', '—')}/{h.get('police_nodes', '—')}")

    ui.section("Manage")
    m1, m2, m3 = st.columns([1.2, 1, 2])
    m1.download_button("⬇ Export history (CSV)", df.to_csv(index=False).encode(), "cops_robbers_history.csv", "text/csv")
    confirm = m2.checkbox("I'm sure", key="confirm_clear")
    def _clear() -> None:
        clear_history()
        st.session_state.confirm_clear = False
        st.session_state.flash = ("success", "History cleared.")

    m3.button("🗑 Reset history", disabled=not confirm, on_click=_clear)
    if st.session_state.get("flash"):
        kind, msg = st.session_state.flash
        getattr(st, kind)(msg)
        st.session_state.flash = None
