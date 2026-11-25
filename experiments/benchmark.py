"""Fair benchmarking of BFS, UCS and A* on an identical environment.

Same start (robber), same goal (exit), same walls/terrain and the same blocked cells (police
positions) for every algorithm. Timing is the median of several repetitions to reduce noise.
"""
from __future__ import annotations

import statistics

from algorithms import SEARCHERS, run_search
from algorithms.base import SearchContext, SearchResult
from environment.state import Environment
from experiments.metrics import optimality_label


def compare(env: Environment, repeats: int = 5, block_police: bool = True,
            record: bool = False) -> dict[str, SearchResult]:
    ctx = SearchContext(env.grid, blocked=set(env.police) if block_police else ())
    results: dict[str, SearchResult] = {}
    for name in SEARCHERS:
        times = []
        res = None
        for _ in range(max(1, repeats)):
            res = run_search(name, ctx, env.robber, env.exit, record=record)
            times.append(res.time_ms)
        res.time_ms = statistics.median(times)
        results[name] = res
    return results


def results_table(results: dict[str, SearchResult]) -> list[dict]:
    opt = results["UCS"].cost if "UCS" in results and results["UCS"].found else None
    rows = []
    for name, r in results.items():
        row = r.summary()
        row["Optimality"] = optimality_label(r, opt)
        rows.append(row)
    return rows
