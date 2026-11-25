"""Performance Arena — fair, measured comparison of BFS, UCS and A*."""
from __future__ import annotations

import time

import pandas as pd
import streamlit as st

from config import settings
from experiments.benchmark import compare, results_table
from experiments.metrics import explain
from experiments.scenarios import SCENARIOS, build_scenario
from interface import ui
from visualization.charts import grouped_bars, metric_bars
from visualization.grid_renderer import render_svg

CFG = {"displayModeBar": False}


def render() -> None:
    ss = st.session_state
    ui.page_header("📊", "Performance Arena",
                   "Identical start, goal, walls, terrain and blocked cells for every algorithm. All numbers are measured.")
    tab1, tab2 = st.tabs(["Single environment", "All scenarios (batch)"])

    with tab1:
        c1, c2, c3, c4, c5 = st.columns([1.8, 0.8, 0.8, 0.8, 0.9])
        src = c1.selectbox("Environment", ["Current game map", "Custom (from Game Configuration)"] + list(SCENARIOS),
                           key="arena_src")
        rows_n = c2.number_input("Rows", settings.MIN_DIM, settings.MAX_DIM, value=ss.env.grid.rows, key="arena_rows",
                                 disabled=src.startswith(("Current", "Custom")))
        cols_n = c3.number_input("Cols", settings.MIN_DIM, settings.MAX_DIM, value=ss.env.grid.cols, key="arena_cols",
                                 disabled=src.startswith(("Current", "Custom")))
        seed = c4.number_input("Seed", 0, 99_999, value=11, key="arena_seed", disabled=src.startswith(("Current", "Custom")))
        repeats = c5.number_input("Timing repeats", 1, 25, value=5, key="arena_rep",
                                  help="Each algorithm is timed this many times; the median is reported.")
        if src.startswith(("Current", "Custom")):
            env = ss.env
            if src.startswith("Custom"):
                st.caption("Edit the map in Game Configuration → Map editor; it is used here unchanged.")
        else:
            try:
                env = build_scenario(src, int(rows_n), int(cols_n), len(ss.env.police), int(seed),
                                     costs=ss.env.grid.cost_model)
            except ValueError as exc:
                st.error(f"Could not build scenario: {exc}")
                return
            st.caption("📌 " + SCENARIOS[src])

        if st.button("▶ Run experiment", type="primary") or "arena_res" not in ss or ss.get("arena_sig") != (src, rows_n, cols_n, seed):
            t0 = time.perf_counter()
            ss.arena_res = compare(env, repeats=int(repeats))
            ss.arena_env = env
            ss.arena_sig = (src, rows_n, cols_n, seed)
            ss.arena_wall = (time.perf_counter() - t0) * 1000
        res, env = ss.arena_res, ss.arena_env
        table = results_table(res)

        left, right = st.columns([1, 1.25])
        with left:
            ui.section("Shared environment")
            paths = {k: r.path for k, r in res.items() if r.found}
            svg = render_svg(env.grid, env.robber, env.police, env.exit, max_width=520,
                             path=paths.get("UCS", []), advisory=paths.get("BFS", []))
            st.markdown(f'<div class="cr-mini">{svg}</div>', unsafe_allow_html=True)
            st.caption("Solid green = UCS/A* optimal-cost route · dashed aqua = BFS fewest-moves route.")
        with right:
            ui.section("Comparison table")
            df = pd.DataFrame(table)[["Algorithm", "Path found", "Path length", "Path cost", "Nodes expanded",
                                      "Max frontier", "Time (ms)", "Optimality"]]
            st.dataframe(df, hide_index=True, width="stretch")
            ui.section("Why the results differ")
            for note in explain(res):
                st.markdown(f"• {note}")
            st.caption(f"Benchmark wall time {ss.arena_wall:.1f} ms (including {int(repeats)} repeats per algorithm).")

        ui.section("Charts")
        g1, g2 = st.columns(2)
        g1.plotly_chart(metric_bars(table, "Nodes expanded", "Nodes expanded"), width="stretch", config=CFG)
        g2.plotly_chart(metric_bars(table, "Time (ms)", "Execution time (median)", " ms"), width="stretch", config=CFG)
        g3, g4 = st.columns(2)
        g3.plotly_chart(metric_bars(table, "Path cost", "Path cost"), width="stretch", config=CFG)
        g4.plotly_chart(metric_bars(table, "Path length", "Path length (moves)"), width="stretch", config=CFG)
        st.download_button("⬇ Download this experiment (CSV)", df.to_csv(index=False).encode(),
                           file_name="cops_robbers_experiment.csv", mime="text/csv")

    with tab2:
        c1, c2, c3 = st.columns([1, 1, 1])
        size = c1.selectbox("Grid size", list(settings.GRID_PRESETS), index=4, key="batch_size")
        seeds = c2.slider("Random layouts per scenario", 1, 10, 3, key="batch_seeds",
                          help="Results are averaged over this many seeds per scenario.")
        c3.write("")
        if c3.button("▶ Run all 7 scenarios", type="primary", width="stretch"):
            r, cc = settings.GRID_PRESETS[size]
            batch = []
            prog = st.progress(0.0, text="Running…")
            names = list(SCENARIOS)
            for i, name in enumerate(names):
                acc: dict[str, list] = {}
                for s in range(seeds):
                    env = build_scenario(name, r, cc, len(ss.env.police), seed=100 + s, costs=ss.env.grid.cost_model)
                    for row in results_table(compare(env, repeats=3)):
                        acc.setdefault(row["Algorithm"], []).append(row)
                for algo, rs in acc.items():
                    found = [x for x in rs if x["Path found"]]
                    avg = lambda key: round(sum(x[key] for x in found) / len(found), 3) if found else None
                    batch.append({"Scenario": name, "Algorithm": algo, "Runs": len(rs), "Found": len(found),
                                  "Nodes expanded": avg("Nodes expanded"), "Path cost": avg("Path cost"),
                                  "Path length": avg("Path length"), "Time (ms)": avg("Time (ms)"),
                                  "Optimal runs": sum(1 for x in rs if x["Optimality"] == "Optimal")})
                prog.progress((i + 1) / len(names), text=f"{name} done")
            prog.empty()
            ss.batch = batch
        if ss.get("batch"):
            batch = ss.batch
            st.dataframe(pd.DataFrame(batch), hide_index=True, width="stretch")
            b1, b2 = st.columns(2)
            b1.plotly_chart(grouped_bars(batch, "Nodes expanded", "Mean nodes expanded"), width="stretch", config=CFG)
            b2.plotly_chart(grouped_bars(batch, "Path cost", "Mean path cost"), width="stretch", config=CFG)
            b3, b4 = st.columns(2)
            b3.plotly_chart(grouped_bars(batch, "Time (ms)", "Mean execution time (ms)"), width="stretch", config=CFG)
            b4.plotly_chart(grouped_bars(batch, "Path length", "Mean path length"), width="stretch", config=CFG)
            st.download_button("⬇ Download batch report (CSV)", pd.DataFrame(batch).to_csv(index=False).encode(),
                               file_name="cops_robbers_batch_report.csv", mime="text/csv")
        else:
            st.info("Run the batch to compare all algorithms across every predefined scenario.")
