"""Live Simulation — play (Player vs AI) or watch (AI vs AI) on the same game engine."""
from __future__ import annotations

import html

import streamlit as st

from config import settings
from config import theme as T
from engine.game_state import PAUSED, RUNNING
from interface import ui
from visualization.grid_renderer import legend_html, render_svg

BOARD_KEY = "play_board"


def _move(action: str) -> None:
    eng = st.session_state.engine
    if eng is None:
        return
    if eng.state.status == PAUSED:
        st.session_state.flash = ("warning", "The game is paused — press Resume to continue.")
        return
    res = eng.step(action)
    if not res.ok and res.message:
        st.session_state.flash = ("warning", res.message)


def _visible_route(route, pos):
    return route[route.index(pos):] if pos in route else route


def _banner(s) -> str:
    if s.status == "escaped":
        return (f'<div class="cr-banner" style="background:linear-gradient(90deg,{T.GREEN}33,transparent);'
                f'border:1px solid {T.GREEN}88;color:{T.GREEN}">🏁 ESCAPE SUCCESSFUL<small>{html.escape(s.message)} '
                f'Turns {s.turn} · moves {s.moves} · route cost {s.robber_cost:g}</small></div>')
    if s.status == "captured":
        return (f'<div class="cr-banner" style="background:linear-gradient(90deg,{T.CORAL}33,transparent);'
                f'border:1px solid {T.CORAL}88;color:{T.CORAL}">🚨 ROBBER CAPTURED<small>{html.escape(s.message)} '
                f'Survived {s.turn} turns.</small></div>')
    return (f'<div class="cr-banner" style="background:linear-gradient(90deg,{T.AMBER}33,transparent);'
            f'border:1px solid {T.AMBER}88;color:{T.AMBER}">⛔ ROBBER CONTAINED<small>{html.escape(s.message)}</small></div>')


def _intel_table(eng) -> str:
    s = eng.state
    plan = s.last_plan
    if plan is None:
        return ""
    rows = []
    for d in plan.decisions:
        route = _visible_route(d.route, s.police[d.officer])
        rows.append(
            f'<tr><td><b style="color:{T.CORAL}">⛨ {d.officer + 1}</b></td><td>{html.escape(d.role)}</td>'
            f'<td>{ui.fmt_cell(d.target)}</td><td>{ui.fmt_cell(d.intercept)}</td><td>{max(0, len(route) - 1)}</td>'
            f'<td class="reason">{html.escape(d.reason)}</td></tr>')
    return ('<table class="cr-intel"><thead><tr><th>Unit</th><th>Role</th><th>Target</th><th>Intercept</th>'
            '<th>Route</th><th>Reason</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table>")


def _log_html(s) -> str:
    colors = {"robber": T.AQUA, "police": T.CORAL, "end": T.GREEN, "info": T.MUTED}
    items = []
    for turn, kind, msg in reversed(s.log[-60:]):
        items.append(f'<div><span class="t">T{turn:03d}</span><span style="color:{colors.get(kind, T.ICE)}">●</span> '
                     f'{html.escape(msg)}</div>')
    return '<div class="cr-log">' + "".join(items) + "</div>"


def render() -> None:
    ss = st.session_state
    ui.page_header("🎮", "Live Simulation", "Robber vs. predictive police — every move recomputed with real search.")
    if ss.engine is None:
        ui.new_engine()
    eng = ss.engine
    if eng is None:
        st.warning("Fix the configuration first.")
        if st.button("Open Game Configuration"):
            st.switch_page(ui.PAGES["config"])
        return

    is_pva = eng.mode == settings.MODE_PVA
    s = eng.state

    # ---------------- control panel (full-page reruns) ----------------
    c = st.columns([1.3, 1, 1, 1, 1, 1, 2.2])
    c[0].markdown(f'<div style="padding-top:6px">{ui.badge(eng.mode, T.TEAL)} {ui.status_badge(s.status)}</div>',
                  unsafe_allow_html=True)
    over = eng.is_over
    if c[1].button("▶ Start", type="primary", width="stretch", disabled=over or s.status == RUNNING):
        eng.start()
        ss.running = not is_pva
        st.rerun()
    if c[2].button("⏸ Pause", width="stretch", disabled=over or s.status != RUNNING):
        eng.pause()
        ss.running = False
        st.rerun()
    if c[3].button("⏯ Resume", width="stretch", disabled=over or s.status != PAUSED):
        eng.start()
        ss.running = not is_pva
        st.rerun()
    if c[4].button("⏭ Next turn", width="stretch", disabled=over or is_pva or ss.running,
                   help="Advance the AI vs AI game by exactly one turn."):
        eng.step()
        if s.status == "ready":
            s.status = PAUSED
        st.rerun()
    if c[5].button("↺ Reset", width="stretch"):
        ui.new_engine()
        st.rerun()
    with c[6]:
        if is_pva:
            st.caption("**Controls:** W A S D / arrow keys · Space = wait · or the on-screen pad.")
        else:
            ss.sim_speed = st.slider("Speed (turns / second)", 1, 12, value=ss.sim_speed)

    if not is_pva:
        a1, a2, a3 = st.columns([1.4, 1, 3])
        algo = a1.selectbox("Robber algorithm", settings.ROBBER_ALGORITHMS,
                            index=settings.ROBBER_ALGORITHMS.index(eng.robber_algorithm))
        if algo != eng.robber_algorithm:
            eng.robber_algorithm = algo
            ss.robber_algo = algo
        if algo in ("Minimax", "Alpha-Beta"):
            eng.minimax_depth = a2.slider("Depth", 1, 6, value=eng.minimax_depth)

    o1, o2, o3, o4 = st.columns(4)
    show_routes = o1.toggle("Police routes", value=True)
    show_pred = o2.toggle("Predicted robber cell", value=True)
    show_path = o3.toggle("Robber route / advisory", value=True)
    show_trail = o4.toggle("Movement trail", value=True)

    interval = (1.0 / ss.sim_speed) if (ss.running and not is_pva and not over) else None

    @st.fragment(run_every=interval)
    def live() -> None:
        eng = ss.engine
        s = eng.state
        if ss.running and not is_pva and not eng.is_over:
            res = eng.step()
            if not res.ok:
                ss.running = False
                st.error(res.message)
        if is_pva:
            ev = ui.fresh_event(BOARD_KEY, ss.get(BOARD_KEY))
            if ev and ev.get("type") == "key":
                _move(ev["action"])
        if ss.get("sim_seen") != (id(eng), s.status) and not eng.is_over:
            first = ss.get("sim_seen", (None,))[0] == id(eng)
            ss.sim_seen = (id(eng), s.status)
            if first:
                st.rerun(scope="app")           # status changed: refresh controls and sidebar
        if eng.is_over:
            ui.record_if_finished(eng)
            if not getattr(eng, "_announced", False):
                eng._announced = True
                ss.running = False
                st.rerun(scope="app")           # stop the timer and refresh the controls

        left, right = st.columns([1.45, 1])
        with left:
            if s.is_over:
                st.markdown(_banner(s), unsafe_allow_html=True)
            plan = s.last_plan
            routes, intercepts, predicted = [], [], None
            if plan and not s.is_over:
                if show_routes:
                    routes = [_visible_route(d.route, s.police[d.officer]) for d in plan.decisions]
                    intercepts = [d.intercept for d in plan.decisions if d.intercept]
                if show_pred:
                    predicted = plan.predicted_position
            path, advisory = [], []
            if show_path and not s.is_over:
                if is_pva:
                    advisory = s.advisory_path
                elif s.last_robber_decision and len(s.last_robber_decision.planned_path) > 2:
                    p = s.last_robber_decision.planned_path
                    path = p[p.index(s.robber):] if s.robber in p else []
            svg = render_svg(eng.grid, s.robber, s.police, s.exit, max_width=780,
                             routes=routes, intercepts=intercepts, predicted=predicted, path=path,
                             advisory=advisory, trail=s.trail if show_trail else (),
                             captured=s.status == "captured")
            armed = is_pva and not s.is_over and s.status != PAUSED
            status_text = ("AI vs AI — watching" if not is_pva else
                           "Game over" if s.is_over else "Paused — press Resume")
            ui.board(svg, eng.grid.rows, eng.grid.cols, mode="play" if armed else "view",
                     keyboard=armed, key=BOARD_KEY, status_text=status_text)
            if ss.flash:
                kind, msg = ss.flash
                getattr(st, kind)(msg)
                ss.flash = None
            if is_pva:
                d1, d2, d3, d4, d5 = st.columns([1, 1, 1, 1, 1])
                dis = s.is_over or s.status == PAUSED
                d1.button("⬅ Left", on_click=_move, args=("LEFT",), width="stretch", disabled=dis, key="pad_l")
                d2.button("⬆ Up", on_click=_move, args=("UP",), width="stretch", disabled=dis, key="pad_u")
                d3.button("⏺ Wait", on_click=_move, args=("STAY",), width="stretch", disabled=dis, key="pad_w")
                d4.button("⬇ Down", on_click=_move, args=("DOWN",), width="stretch", disabled=dis, key="pad_d")
                d5.button("➡ Right", on_click=_move, args=("RIGHT",), width="stretch", disabled=dis, key="pad_r")
            st.markdown(legend_html(["robber", "police", "exit", "wall", "difficult", "hazard", "safe", "path",
                                     "advisory", "route", "predicted"], eng.grid.cost_model), unsafe_allow_html=True)
        with right:
            ui.section("Live statistics")
            exit_d = eng.grid.step_distances(s.exit).get(s.robber, "∞")
            cop_map = eng.grid.step_distances(s.robber, police=True)
            near = min((cop_map.get(p, 999) for p in s.police), default=999)
            near = "∞" if near >= 999 else near
            g = st.columns(2)
            items = [
                ("⏱", "Turn", f"{s.turn} / {eng.max_turns}", T.AQUA), ("R", "Robber", ui.fmt_cell(s.robber), T.AQUA),
                ("⚑", "Moves to exit", exit_d, T.GREEN), ("⛨", "Nearest officer", f"{near} moves", T.CORAL),
                ("↗", "Robber moves", s.moves, T.TEAL), ("Σ", "Route cost", f"{s.robber_cost:g}", T.AMBER),
                ("◎", "Nodes (robber / police)", f"{s.robber_nodes} / {s.police_nodes}", T.TEAL),
                ("●", "Status", ui.STATUS_STYLE.get(s.status, (s.status,))[0], T.AQUA),
            ]
            for i, it in enumerate(items):
                g[i % 2].markdown(ui.stat(*it), unsafe_allow_html=True)
            st.caption("Officers: " + "  ".join(f"⛨{i + 1} {ui.fmt_cell(p)}" for i, p in enumerate(s.police)))

            ui.section("Tactical intelligence")
            plan = s.last_plan
            if plan:
                st.markdown(
                    f'<p style="color:{T.MUTED};font-size:13px;margin:0 0 6px">Likely robber position in 2 turns: '
                    f'<b style="color:{T.AMBER}">{ui.fmt_cell(plan.predicted_position)}</b> '
                    f'<i>(an estimate, not a certainty)</i> · predicted route {max(0, len(plan.predicted_path) - 1)} moves'
                    f' · planning {plan.time_ms:.1f} ms</p>', unsafe_allow_html=True)
                st.markdown(_intel_table(eng), unsafe_allow_html=True)
            dec = s.last_robber_decision
            if not is_pva and dec:
                st.markdown(f'<p style="margin:10px 0 0;font-size:13px"><b style="color:{T.AQUA}">Robber AI ({dec.algorithm})'
                            f'</b> → {dec.action}. <span style="color:{T.MUTED}">{html.escape(dec.reason)} '
                            f'{dec.nodes} nodes, {dec.time_ms:.1f} ms.</span></p>', unsafe_allow_html=True)
            elif is_pva and s.advisory_path:
                st.markdown(f'<p style="margin:10px 0 0;font-size:13px"><b style="color:{T.AQUA}">A* advisory</b>: '
                            f'{len(s.advisory_path) - 1} moves to the exit (dashed line). You are free to ignore it.</p>',
                            unsafe_allow_html=True)
            ui.section("Event log")
            st.markdown(_log_html(s), unsafe_allow_html=True)

    live()
