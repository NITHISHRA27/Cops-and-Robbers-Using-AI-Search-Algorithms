"""A* search: f(n) = g(n) + h(n) with the weighted Manhattan heuristic.

h(n) = min_step_cost × (|r − r_goal| + |c − c_goal|). Each move changes the Manhattan
distance by exactly one and costs at least `min_step_cost`, so h never overestimates
(admissible) and h(n) ≤ c(n, n') + h(n') (consistent). With a consistent heuristic the
first expansion of a node is via its cheapest path, so A* returns the same optimal cost
as UCS while expanding fewer nodes. Ties on f are broken towards lower h (deeper nodes).
"""
from __future__ import annotations

import heapq
import itertools
import time
from typing import Callable

from algorithms.base import SearchContext, SearchResult, reconstruct
from environment.grid import Cell
from heuristics.manhattan import weighted_manhattan


def astar(ctx: SearchContext, start: Cell, goal: Cell, record: bool = False,
          heuristic: Callable[[Cell, Cell], float] | None = None) -> SearchResult:
    t0 = time.perf_counter()
    res = SearchResult("A*", start, goal, found=False)
    if not (ctx.valid_endpoint(start) and ctx.valid_endpoint(goal)):
        res.time_ms = (time.perf_counter() - t0) * 1000
        return res
    min_cost = ctx.grid.cost_model.min_cost
    h = heuristic or (lambda a, b: weighted_manhattan(a, b, min_cost))

    tie = itertools.count()
    h0 = h(start, goal)
    frontier: list[tuple[float, float, int, Cell]] = [(h0, h0, next(tie), start)]
    g: dict[Cell, float] = {start: 0.0}
    parent: dict[Cell, Cell | None] = {start: None}
    closed: set[Cell] = set()
    res.max_frontier = 1
    while frontier:
        f, hv, _, cur = heapq.heappop(frontier)
        if cur in closed or f > g[cur] + hv + 1e-9:
            continue                          # stale entry
        if cur == goal:
            res.found = True
            res.path = reconstruct(parent, goal)
            res.cost = g[goal]
            res.nodes_expanded += 1
            if record:
                res.events.append([cur[0], cur[1], g[cur], hv, f, len(frontier), []])
            break
        closed.add(cur)
        res.nodes_expanded += 1
        pushed = []
        for nxt in ctx.successors(cur):
            if nxt in closed:
                continue
            new_g = g[cur] + ctx.step_cost(nxt)
            if new_g < g.get(nxt, float("inf")):
                g[nxt] = new_g
                parent[nxt] = cur
                hn = h(nxt, goal)
                heapq.heappush(frontier, (new_g + hn, hn, next(tie), nxt))
                res.nodes_generated += 1
                if record:
                    pushed.append([nxt[0], nxt[1], new_g, hn, new_g + hn])
        res.max_frontier = max(res.max_frontier, len(frontier))
        if record:
            res.events.append([cur[0], cur[1], g[cur], hv, f, len(frontier), pushed])
    res.time_ms = (time.perf_counter() - t0) * 1000
    return res
