"""COPS & ROBBERS — Intelligent Pursuit and Strategic Escape.

Entry point: `streamlit run app.py`. This file only wires the interface together; all game
logic and algorithms live in Streamlit-independent packages (environment, algorithms,
agents, engine, heuristics, experiments).
"""
import streamlit as st

st.set_page_config(page_title="Cops & Robbers — AI Pursuit & Escape", page_icon="🚨", layout="wide",
                   initial_sidebar_state="expanded")

from config import settings  # noqa: E402
from config import theme as T  # noqa: E402
from interface import (algorithm_lab, configuration, dashboard, heuristic_view, history,  # noqa: E402
                       performance, simulation, strategic_ai, ui)

ui.inject_css()
ui.init_state()

PAGES = {
    "dashboard": st.Page(dashboard.render, title="Command Center", icon=":material/space_dashboard:",
                         url_path="command-center", default=True),
    "config": st.Page(configuration.render, title="Game Configuration", icon=":material/tune:", url_path="configuration"),
    "sim": st.Page(simulation.render, title="Live Simulation", icon=":material/sports_esports:", url_path="live-simulation"),
    "lab": st.Page(algorithm_lab.render, title="Algorithm Laboratory", icon=":material/science:", url_path="algorithm-lab"),
    "heuristic": st.Page(heuristic_view.render, title="Heuristic Explorer", icon=":material/explore:", url_path="heuristics"),
    "arena": st.Page(performance.render, title="Performance Arena", icon=":material/leaderboard:", url_path="performance"),
    "strategic": st.Page(strategic_ai.render, title="Strategic AI", icon=":material/account_tree:", url_path="strategic-ai"),
    "history": st.Page(history.render, title="Game History", icon=":material/history:", url_path="history"),
}
ui.PAGES = PAGES

with st.sidebar:
    st.markdown(
        f"""<div style="display:flex;align-items:center;gap:10px;padding:4px 2px 12px">
        <div style="width:40px;height:40px;border-radius:11px;display:grid;place-items:center;font-size:20px;
             background:linear-gradient(135deg,{T.CORAL}33,{T.AQUA}33);border:1px solid {T.AQUA}55">🚨</div>
        <div><div style="font-family:Rajdhani;font-weight:700;font-size:19px;color:{T.ICE};line-height:1">COPS &amp; ROBBERS</div>
        <div style="font-size:11px;color:{T.MUTED};letter-spacing:.05em">TACTICAL AI COMMAND</div></div></div>""",
        unsafe_allow_html=True)

nav = st.navigation(list(PAGES.values()))

with st.sidebar:
    eng = st.session_state.engine
    env = st.session_state.env
    status = eng.state.status if eng else "ready"
    st.markdown(
        f"""<div class="cr-card" style="margin-top:8px"><h4 style="font-size:14px">Session</h4>
        <p>Grid <b style="color:{T.ICE}">{env.grid.rows}×{env.grid.cols}</b> · Officers <b style="color:{T.ICE}">{len(env.police)}</b><br>
        Mode <b style="color:{T.ICE}">{st.session_state.game_mode}</b><br>Status {ui.status_badge(status)}</p></div>""",
        unsafe_allow_html=True)
    st.caption(f"25AM2304 · Artificial Intelligence · Game AI (Search-Based)\n\n*{settings.TAGLINE}*")

nav.run()
