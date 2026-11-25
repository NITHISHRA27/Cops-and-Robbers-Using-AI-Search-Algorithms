"""Uniform Cost Search with a binary-heap priority queue ordered by g(n).

Priority updates use the standard "lazy deletion" technique: when a cheaper route to a
frontier node is found it is pushed again with the lower g, and stale heap entries are
skipped when popped. The goal test happens on expansion, which is what makes UCS optimal
for non-negative step costs.
"""
from __future__ import annotations

import heapq
import itertools
import time

from algorithms.base import SearchContext, SearchResult, reconstruct
from environment.grid import Cell


def ucs(ctx: SearchContext, start: Cell, goal: Cell, record: bool = False) -> SearchResult:
    t0 = time.perf_counter()
    res = SearchResult("UCS", start, goal, found=False)
    if not (ctx.valid_endpoint(start) and ctx.valid_endpoint(goal)):
        res.time_ms = (time.perf_counter() - t0) * 1000
        return res

    tie = itertools.count()
    frontier: list[tuple[float, int, Cell]] = [(0.0, next(tie), start)]
    g: dict[Cell, float] = {start: 0.0}
    parent: dict[Cell, Cell | None] = {start: None}
    expanded: set[Cell] = set()
    res.max_frontier = 1
    while frontier:
        cost, _, cur = heapq.heappop(frontier)
        if cur in expanded or cost > g[cur]:
            continue                          # stale entry
        if cur == goal:
            res.found = True
            res.path = reconstruct(parent, goal)
            res.cost = g[goal]
            if record:
                res.events.append([cur[0], cur[1], cost, 0, cost, len(frontier), []])
            res.nodes_expanded += 1
            break
        expanded.add(cur)
        res.nodes_expanded += 1
        pushed = []
        for nxt in ctx.successors(cur):
            if nxt in expanded:
                continue
            new_g = cost + ctx.step_cost(nxt)
            if new_g < g.get(nxt, float("inf")):
                g[nxt] = new_g
                parent[nxt] = cur
                heapq.heappush(frontier, (new_g, next(tie), nxt))
                res.nodes_generated += 1
                if record:
                    pushed.append([nxt[0], nxt[1], new_g, 0, new_g])
        res.max_frontier = max(res.max_frontier, len(frontier))
        if record:
            res.events.append([cur[0], cur[1], cost, 0, cost, len(frontier), pushed])
    res.time_ms = (time.perf_counter() - t0) * 1000
    return res
