"""Shared Streamlit UI: theme CSS, session state, the board component and small widgets."""
from __future__ import annotations

import html
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from config import settings
from config import theme as T
from engine.game_engine import GameEngine
from environment.map_generator import MapConfig, generate_environment
from persistence.history import load_history, save_game

_BOARD = components.declare_component(
    "cops_board", path=str(Path(__file__).resolve().parent.parent / "components" / "board"))

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');
:root {{ --navy:{T.DEEP_NAVY}; --mid:{T.MIDNIGHT}; --panel:{T.PANEL}; --teal:{T.TEAL}; --aqua:{T.AQUA};
        --coral:{T.CORAL}; --amber:{T.AMBER}; --green:{T.GREEN}; --ice:{T.ICE}; --muted:{T.MUTED}; }}
html, body, [class*="css"], .stApp {{ font-family: 'Inter', 'Segoe UI', sans-serif; }}
.stApp {{ background: radial-gradient(1200px 600px at 75% -10%, rgba(0,179,164,0.10), transparent 60%),
                       radial-gradient(900px 500px at -10% 110%, rgba(54,217,232,0.06), transparent 60%), var(--navy); }}
[data-testid="stSidebar"] {{ background: linear-gradient(180deg, var(--mid), #12202F); border-right: 1px solid rgba(54,217,232,.12); }}
[data-testid="stSidebarNav"] a span {{ font-weight: 500; }}
[data-testid="stSidebarNav"] a[aria-current="page"] {{ background: rgba(54,217,232,.12); border-left: 3px solid var(--aqua); }}
h1, h2, h3, h4 {{ font-family: 'Rajdhani', 'Inter', sans-serif !important; letter-spacing: .02em; }}
.block-container {{ padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1400px; }}
div[data-testid="stMetric"] {{ background: linear-gradient(160deg, var(--panel), var(--mid)); border: 1px solid rgba(54,217,232,.14);
        border-radius: 14px; padding: 12px 14px; }}
div[data-testid="stMetricLabel"] p {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }}
.stButton > button, .stDownloadButton > button {{ border-radius: 10px; border: 1px solid rgba(54,217,232,.35); background: rgba(54,217,232,.07);
        color: var(--ice); font-weight: 600; transition: all .15s ease; }}
.stButton > button:hover, .stDownloadButton > button:hover {{ border-color: var(--aqua); background: rgba(54,217,232,.16); color: var(--ice); box-shadow: 0 0 14px rgba(54,217,232,.18); }}
.stButton > button[kind="primary"] {{ background: linear-gradient(135deg, var(--teal), #00C9B8); border-color: var(--teal); color: #03201D; }}
.stButton > button[kind="primary"]:hover {{ background: linear-gradient(135deg, var(--aqua), var(--teal)); color: #03201D; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
.stTabs [data-baseweb="tab"] {{ background: rgba(32,54,77,.55); border-radius: 10px 10px 0 0; padding: 8px 16px; }}
.stTabs [aria-selected="true"] {{ background: rgba(54,217,232,.14); }}
div[data-testid="stExpander"] details {{ background: rgba(32,54,77,.45); border: 1px solid rgba(54,217,232,.14); border-radius: 12px; }}
div[data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; border: 1px solid rgba(54,217,232,.12); }}

.cr-hero {{ position: relative; overflow: hidden; border-radius: 18px; padding: 26px 30px; margin-bottom: 18px;
        background: linear-gradient(120deg, rgba(32,54,77,.95), rgba(22,38,58,.95)); border: 1px solid rgba(54,217,232,.22);
        box-shadow: 0 18px 40px rgba(0,0,0,.35); }}
.cr-hero::after {{ content: ""; position: absolute; inset: 0; background:
        repeating-linear-gradient(0deg, rgba(54,217,232,.05) 0 1px, transparent 1px 28px),
        repeating-linear-gradient(90deg, rgba(54,217,232,.05) 0 1px, transparent 1px 28px); pointer-events: none;
        mask-image: linear-gradient(90deg, transparent 40%, black); }}
.cr-hero h1 {{ font-size: 44px; margin: 0; line-height: 1; color: var(--ice); font-weight: 700; }}
.cr-hero h1 span {{ color: var(--aqua); }}
.cr-hero .sub {{ color: var(--teal); font-size: 18px; margin-top: 6px; font-family: 'Rajdhani'; font-weight: 600; letter-spacing: .06em; }}
.cr-hero .tag {{ color: var(--muted); margin-top: 8px; font-style: italic; }}
.cr-page-head {{ display: flex; align-items: center; gap: 14px; margin: 0 0 16px; }}
.cr-page-head .icon {{ width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center; font-size: 22px;
        background: rgba(54,217,232,.12); border: 1px solid rgba(54,217,232,.3); }}
.cr-page-head h2 {{ margin: 0; font-size: 30px; color: var(--ice); }}
.cr-page-head p {{ margin: 0; color: var(--muted); font-size: 14px; }}
.cr-card {{ background: linear-gradient(160deg, rgba(32,54,77,.92), rgba(22,38,58,.92)); border: 1px solid rgba(54,217,232,.14);
        border-radius: 14px; padding: 14px 16px; box-shadow: 0 8px 22px rgba(0,0,0,.25); margin-bottom: 12px; transition: border-color .2s, transform .2s; }}
.cr-card:hover {{ border-color: rgba(54,217,232,.35); }}
.cr-card h4 {{ margin: 0 0 6px; font-size: 17px; color: var(--ice); }}
.cr-card p {{ margin: 0; color: var(--muted); font-size: 13px; line-height: 1.45; }}
.cr-card .accent {{ height: 3px; border-radius: 3px; margin: -14px -16px 12px; }}
.cr-stat {{ background: linear-gradient(160deg, rgba(32,54,77,.95), rgba(22,38,58,.95)); border: 1px solid rgba(54,217,232,.14);
        border-radius: 14px; padding: 12px 14px; display: flex; gap: 12px; align-items: center; min-height: 72px; margin-bottom: 10px; }}
.cr-stat .ic {{ width: 38px; height: 38px; border-radius: 10px; display: grid; place-items: center; font-size: 18px; flex: none; }}
.cr-stat .lb {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .07em; }}
.cr-stat .vl {{ color: var(--ice); font-size: 20px; font-weight: 700; font-family: 'Rajdhani', sans-serif; font-variant-numeric: tabular-nums; }}
.cr-badge {{ display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; letter-spacing: .03em; }}
.cr-legend {{ display: flex; flex-wrap: wrap; gap: 6px 14px; padding: 10px 12px; border-radius: 12px; background: rgba(22,38,58,.8);
        border: 1px solid rgba(54,217,232,.1); margin-top: 8px; }}
.cr-legend-item {{ display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: var(--muted); }}
.cr-banner {{ border-radius: 14px; padding: 16px 20px; margin: 6px 0 14px; display: flex; align-items: center; gap: 14px;
        font-family: 'Rajdhani'; font-size: 24px; font-weight: 700; letter-spacing: .04em; }}
.cr-banner small {{ font-family: 'Inter'; font-size: 13px; font-weight: 500; letter-spacing: 0; display: block; color: var(--ice); opacity: .85; }}
.cr-log {{ max-height: 300px; overflow-y: auto; font-size: 12.5px; border-radius: 12px; background: rgba(16,28,44,.7);
        border: 1px solid rgba(54,217,232,.1); padding: 6px 10px; }}
.cr-log div {{ padding: 4px 0; border-bottom: 1px solid rgba(139,155,173,.08); color: var(--ice); }}
.cr-log .t {{ color: var(--muted); font-variant-numeric: tabular-nums; margin-right: 8px; }}
.cr-formula {{ font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 20px; color: var(--aqua); background: rgba(16,28,44,.8);
        border: 1px solid rgba(54,217,232,.25); border-radius: 12px; padding: 14px 18px; text-align: center; margin: 6px 0 10px; }}
.cr-intel {{ width: 100%; border-collapse: collapse; font-size: 12.5px; }}
.cr-intel th {{ color: var(--muted); font-weight: 500; text-align: left; padding: 5px 6px; border-bottom: 1px solid rgba(139,155,173,.2); }}
.cr-intel td {{ padding: 6px; border-bottom: 1px solid rgba(139,155,173,.08); vertical-align: top; color: var(--ice); }}
.cr-intel td.reason {{ color: var(--muted); font-size: 12px; }}
.cr-mini svg {{ border-radius: 12px; border: 1px solid rgba(54,217,232,.15); }}
.cr-section {{ font-family: 'Rajdhani'; font-size: 20px; font-weight: 700; color: var(--ice); margin: 18px 0 8px; letter-spacing: .03em;
        display: flex; align-items: center; gap: 8px; }}
.cr-section::after {{ content: ""; flex: 1; height: 1px; background: linear-gradient(90deg, rgba(54,217,232,.35), transparent); }}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


# ------------------------------------------------------------------ state
def init_state() -> None:
    ss = st.session_state
    if "map_cfg" not in ss:
        ss.map_cfg = MapConfig()
    if "env" not in ss:
        ss.env = generate_environment(ss.map_cfg)
        ss.base_env = ss.env.copy()
    ss.setdefault("game_mode", settings.MODE_PVA)
    ss.setdefault("robber_algo", settings.DEFAULT_ROBBER_ALGORITHM)
    ss.setdefault("minimax_depth", settings.DEFAULT_MINIMAX_DEPTH)
    ss.setdefault("minimax_officers", settings.DEFAULT_MINIMAX_OFFICERS)
    ss.setdefault("sim_speed", 4)
    ss.setdefault("engine", None)
    ss.setdefault("running", False)
    ss.setdefault("nonces", {})
    ss.setdefault("flash", None)


def new_engine() -> GameEngine | None:
    ss = st.session_state
    try:
        ss.engine = GameEngine(ss.env, ss.game_mode, ss.robber_algo, ss.minimax_depth, ss.minimax_officers)
        ss.running = False
        return ss.engine
    except ValueError as exc:
        ss.engine = None
        st.error(f"Cannot start the game: {exc}")
        return None


def record_if_finished(engine: GameEngine | None) -> None:
    if engine is not None and engine.is_over and not getattr(engine, "_saved", False):
        try:
            save_game(engine.summary())
        except OSError as exc:
            st.warning(f"Could not save game history: {exc}")
        engine._saved = True


def history_stats() -> dict:
    hist = load_history()
    return {
        "games": len(hist),
        "escaped": sum(1 for h in hist if h.get("outcome") == "escaped"),
        "captured": sum(1 for h in hist if h.get("outcome") == "captured"),
        "timeout": sum(1 for h in hist if h.get("outcome") == "timeout"),
    }


# ------------------------------------------------------------------ board component
def board(svg: str, rows: int, cols: int, mode: str = "view", keyboard: bool = False,
          key: str = "board", status_text: str = "", paint: bool = True):
    return _BOARD(svg=svg, rows=rows, cols=cols, mode=mode, keyboard=keyboard, status_text=status_text,
                  paint=paint, key=key, default=None)


def fresh_event(key: str, value):
    """Return the component event only the first time we see its nonce (reruns re-send old values)."""
    if not value or not isinstance(value, dict):
        return None
    nonces = st.session_state.nonces
    if nonces.get(key) == value.get("nonce"):
        return None
    nonces[key] = value.get("nonce")
    return value


# ------------------------------------------------------------------ widgets
def page_header(icon: str, title: str, subtitle: str) -> None:
    st.markdown(f'<div class="cr-page-head"><div class="icon">{icon}</div><div><h2>{html.escape(title)}</h2>'
                f'<p>{html.escape(subtitle)}</p></div></div>', unsafe_allow_html=True)


def section(title: str) -> None:
    st.markdown(f'<div class="cr-section">{html.escape(title)}</div>', unsafe_allow_html=True)


def stat(icon: str, label: str, value, color: str = T.AQUA) -> str:
    return (f'<div class="cr-stat"><div class="ic" style="background:{color}22;border:1px solid {color}55;color:{color}">{icon}</div>'
            f'<div><div class="lb">{html.escape(str(label))}</div><div class="vl">{html.escape(str(value))}</div></div></div>')


def card(title: str, body: str, accent: str = T.TEAL, extra: str = "") -> str:
    return (f'<div class="cr-card"><div class="accent" style="background:linear-gradient(90deg,{accent},transparent)"></div>'
            f'<h4>{title}</h4><p>{body}</p>{extra}</div>')


def badge(text: str, color: str) -> str:
    return f'<span class="cr-badge" style="background:{color}22;color:{color};border:1px solid {color}66">{html.escape(text)}</span>'


STATUS_STYLE = {
    "ready": ("READY", T.AQUA), "running": ("RUNNING", T.TEAL), "paused": ("PAUSED", T.AMBER),
    "escaped": ("ESCAPED", T.GREEN), "captured": ("CAPTURED", T.CORAL), "timeout": ("CONTAINED", T.AMBER),
}


def status_badge(status: str) -> str:
    text, color = STATUS_STYLE.get(status, (status.upper(), T.MUTED))
    return badge(text, color)


def fmt_cell(c) -> str:
    return f"({c[0]}, {c[1]})" if c is not None else "—"


def html_block(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)
