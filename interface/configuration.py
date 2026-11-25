"""Game Configuration — grid size, officers, modes, terrain, costs and a manual map editor."""
from __future__ import annotations

import random

import streamlit as st

from config import settings
from config import theme as T
from environment.map_generator import MapConfig, generate_environment, place_police
from environment.terrain import CostModel, Terrain
from interface import ui
from visualization.grid_renderer import legend_html, render_svg

TOOLS = {
    "🧱 Wall": ("terrain", Terrain.WALL), "🛣 Road": ("terrain", Terrain.ROAD),
    "🟧 Difficult": ("terrain", Terrain.DIFFICULT), "⚠ Hazard": ("terrain", Terrain.HAZARD),
    "✚ Safe zone": ("terrain", Terrain.SAFE), "R Robber": ("robber", None), "⚑ Exit": ("exit", None),
    "⛨ Add officer": ("add_police", None), "✖ Remove officer": ("remove_police", None),
}


def _w(widget_key: str, value):
    """Seed a widget's state from a persistent value (widget state is dropped when a page is left)."""
    if widget_key not in st.session_state:
        st.session_state[widget_key] = value
    return widget_key


def _apply_edit(tool: str, cells: list[list[int]]) -> str | None:
    env = st.session_state.env
    g = env.grid
    kind, terrain = TOOLS[tool]
    cells = [tuple(c) for c in cells if g.in_bounds(tuple(c))]
    if not cells:
        return None
    if kind == "terrain":
        for c in cells:
            if c in (env.robber, env.exit) and terrain == Terrain.WALL:
                return "Cannot place a wall on the robber or the exit."
            if c in env.police and terrain in (Terrain.WALL, Terrain.SAFE):
                return f"Cell {c} holds an officer — move it first."
            g.set_terrain(c, terrain)
        return None
    c = cells[-1]
    if kind == "robber":
        if not g.is_passable(c) or c == env.exit or c in env.police:
            return "The robber needs a free, passable cell."
        env.robber = c
    elif kind == "exit":
        if not g.is_passable(c) or c == env.robber or c in env.police:
            return "The exit needs a free, passable cell."
        env.exit = c
    elif kind == "add_police":
        if len(env.police) >= settings.MAX_POLICE:
            return f"Maximum {settings.MAX_POLICE} officers."
        if not g.police_can_enter(c) or c in (env.robber, env.exit) or c in env.police:
            return "Officers need a free road cell (not a wall, safe zone, robber or exit)."
        env.police.append(c)
    elif kind == "remove_police":
        if c not in env.police:
            return "No officer on that cell."
        if len(env.police) == 1:
            return "At least one officer is required."
        env.police.remove(c)
    return None


def render() -> None:
    ss = st.session_state
    ui.page_header("⚙", "Game Configuration", "Customise the city, the officers and the game mode before you play.")
    cfg: MapConfig = ss.map_cfg

    tab_grid, tab_env, tab_cost, tab_edit = st.tabs(["Grid & agents", "Environment", "Movement costs", "Map editor"])
    with tab_grid:
        c1, c2 = st.columns(2)
        with c1:
            ui.section("Grid dimensions")
            preset_opts = list(settings.GRID_PRESETS) + ["Custom"]
            current = next((k for k, v in settings.GRID_PRESETS.items() if v == (cfg.rows, cfg.cols)), "Custom")
            preset = st.selectbox("Grid size", preset_opts, key=_w("w_preset", current))
            if preset == "Custom":
                r1, r2 = st.columns(2)
                rows = r1.number_input("Rows", settings.MIN_DIM, settings.MAX_DIM, key=_w("w_rows", cfg.rows))
                cols = r2.number_input("Columns", settings.MIN_DIM, settings.MAX_DIM, key=_w("w_cols", cfg.cols))
            else:
                rows, cols = settings.GRID_PRESETS[preset]
            ui.section("Police force")
            n_police = st.slider("Number of police officers", settings.MIN_POLICE, settings.MAX_POLICE,
                                 key=_w("w_police", cfg.n_police))
        with c2:
            ui.section("Game mode")
            ss.game_mode = st.radio("Mode", settings.GAME_MODES, key=_w("w_mode", ss.game_mode), horizontal=True,
                                    help="Player vs AI: you control the robber. AI vs AI: watch both sides play.")
            ss.robber_algo = st.selectbox("Robber AI algorithm (AI vs AI)", settings.ROBBER_ALGORITHMS,
                                          key=_w("w_algo", ss.robber_algo),
                                          disabled=ss.game_mode == settings.MODE_PVA)
            a1, a2 = st.columns(2)
            ss.minimax_depth = a1.slider("Minimax depth (plies)", 1, 6, key=_w("w_depth", ss.minimax_depth),
                                         disabled=ss.robber_algo not in ("Minimax", "Alpha-Beta"))
            ss.minimax_officers = a2.slider("Officers modelled", 1, 2, key=_w("w_mof", ss.minimax_officers),
                                            disabled=ss.robber_algo not in ("Minimax", "Alpha-Beta"),
                                            help="Nearest officers that move inside the game tree (branching 5^k).")
            if ss.engine is not None and not ss.engine.is_over:
                st.caption("A game is in progress — changes apply when you start a new game.")
    with tab_env:
        c1, c2 = st.columns(2)
        with c1:
            ui.section("Obstacles & terrain density")
            wall = st.slider("Wall / building density", 0, 45, key=_w("w_wall", int(cfg.wall_density * 100)), format="%d%%")
            diff = st.slider("Difficult terrain", 0, 40, key=_w("w_diff", int(cfg.difficult_density * 100)), format="%d%%")
            haz = st.slider("Hazardous cells", 0, 25, key=_w("w_haz", int(cfg.hazard_density * 100)), format="%d%%")
            safe = st.slider("Safe zones", 0, 15, key=_w("w_safe", int(cfg.safe_density * 100)), format="%d%%")
        with c2:
            ui.section("Randomness")
            seed = st.number_input("Map seed", 0, 999_999, key=_w("w_seed", cfg.seed or 0))
            st.button("🎲 Random seed", on_click=lambda: st.session_state.update(w_seed=random.randrange(1_000_000)))
            g = ss.env.grid
            st.markdown(ui.stat("🧱", "Obstacles on current map", g.count(Terrain.WALL), T.MUTED)
                        + ui.stat("🟧", "Difficult / hazard / safe cells",
                                  f"{g.count(Terrain.DIFFICULT)} / {g.count(Terrain.HAZARD)} / {g.count(Terrain.SAFE)}", T.AMBER),
                        unsafe_allow_html=True)
    with tab_cost:
        ui.section("Movement-cost model (cost of entering a cell)")
        cm = ss.env.grid.cost_model
        c1, c2, c3, c4 = st.columns(4)
        road = c1.number_input("Road", 0.5, 20.0, key=_w("w_c_road", float(cm.road)), step=0.5)
        dif = c2.number_input("Difficult", 0.5, 20.0, key=_w("w_c_diff", float(cm.difficult)), step=0.5)
        hz = c3.number_input("Hazard", 0.5, 50.0, key=_w("w_c_haz", float(cm.hazard)), step=0.5)
        sf = c4.number_input("Safe zone", 0.5, 20.0, key=_w("w_c_safe", float(cm.safe)), step=0.5)
        st.caption("Walls are impassable. UCS and A* use these costs; A* scales the Manhattan heuristic by the "
                   "cheapest cost so it stays admissible. BFS counts moves only.")
        if st.button("Apply costs to current map"):
            try:
                ss.env.grid.cost_model = CostModel(road, dif, hz, sf)
                ss.map_cfg.costs = ss.env.grid.cost_model
                ss.base_env.grid.cost_model = ss.env.grid.cost_model
                st.success("Movement costs updated.")
            except ValueError as exc:
                st.error(str(exc))

    # ---- generation actions (shared across tabs)
    st.write("")
    b1, b2, b3, b4 = st.columns(4)
    if b1.button("🗺  Generate new map", type="primary", width="stretch"):
        try:
            new_cfg = MapConfig(int(rows), int(cols), int(n_police), wall / 100, diff / 100, haz / 100, safe / 100,
                                int(seed), CostModel(road, dif, hz, sf))
            ss.env = generate_environment(new_cfg)
            ss.base_env = ss.env.copy()
            ss.map_cfg = new_cfg
            ss.engine = None
            ss.flash = ("success", f"New {rows}×{cols} map with {n_police} officer(s) generated.")
        except ValueError as exc:
            ss.flash = ("error", str(exc))
        st.rerun()
    if b2.button("↺  Reset map", width="stretch", help="Undo manual edits — back to the last generated map."):
        ss.env = ss.base_env.copy()
        ss.flash = ("info", "Map restored to the last generated version.")
        st.rerun()
    if b3.button("⛨  Re-place officers", width="stretch", help="Keep the map, redistribute the chosen number of officers."):
        try:
            ss.env.police = place_police(ss.env.grid, ss.env.robber, ss.env.exit, int(n_police),
                                         random.Random(int(seed) + 1))
            ss.flash = ("success", f"{n_police} officer(s) placed.")
        except ValueError as exc:
            ss.flash = ("error", str(exc))
        st.rerun()
    errors = ss.env.validate()
    if b4.button("▶  Start game", width="stretch", disabled=bool(errors)):
        if ui.new_engine():
            st.switch_page(ui.PAGES["sim"])

    if ss.flash:
        kind, msg = ss.flash
        getattr(st, kind)(msg)
        ss.flash = None

    with tab_edit:
        c1, c2 = st.columns([1.6, 1])
        with c2:
            ui.section("Editing tool")
            tool = st.radio("Tool", list(TOOLS), key=_w("w_tool", "🧱 Wall"), label_visibility="collapsed")
            st.caption("Click a cell, or drag to paint terrain. Entity tools use the cell you click.")
            env = ss.env
            st.markdown(ui.stat("R", "Robber", ui.fmt_cell(env.robber), T.AQUA)
                        + ui.stat("⚑", "Exit", ui.fmt_cell(env.exit), T.GREEN)
                        + ui.stat("⛨", "Officers", ", ".join(ui.fmt_cell(p) for p in env.police), T.CORAL),
                        unsafe_allow_html=True)
        with c1:
            env = ss.env
            svg = render_svg(env.grid, env.robber, env.police, env.exit, max_width=760)
            ev = ui.fresh_event("editor", ui.board(svg, env.grid.rows, env.grid.cols, mode="edit", key="editor"))
            if ev and ev.get("type") in ("paint", "click"):
                cells = ev.get("cells") or [[ev["r"], ev["c"]]]
                msg = _apply_edit(tool, cells)
                if msg:
                    ss.flash = ("warning", msg)
                st.rerun()
            st.markdown(legend_html(["robber", "police", "exit", "wall", "road", "difficult", "hazard", "safe"],
                                    env.grid.cost_model), unsafe_allow_html=True)

    if errors:
        st.error("**Fix before starting:** " + " ".join(errors))
    else:
        st.success("✓ Configuration valid — robber, exit and every officer are on legal cells and the exit is reachable.")
