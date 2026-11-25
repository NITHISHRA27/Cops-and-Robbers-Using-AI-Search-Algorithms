"""Breadth-First Search with a FIFO queue.

Explores the grid level by level, so the first time the goal is generated the path has the
fewest moves. It ignores terrain cost, which is why its *cost* can be higher than UCS/A*
on weighted maps (it happily walks through hazards if that saves a move).
"""
from __future__ import annotations

import time
from collections import deque

from algorithms.base import SearchContext, SearchResult, path_cost, reconstruct
from environment.grid import Cell


def bfs(ctx: SearchContext, start: Cell, goal: Cell, record: bool = False) -> SearchResult:
    t0 = time.perf_counter()
    res = SearchResult("BFS", start, goal, found=False)
    if not (ctx.valid_endpoint(start) and ctx.valid_endpoint(goal)):
        res.time_ms = (time.perf_counter() - t0) * 1000
        return res
    if start == goal:
        res.found, res.path, res.cost = True, [start], 0.0
        res.time_ms = (time.perf_counter() - t0) * 1000
        return res

    frontier: deque[Cell] = deque([start])
    parent: dict[Cell, Cell | None] = {start: None}   # doubles as the reached set
    depth = {start: 0}
    res.max_frontier = 1
    while frontier:
        cur = frontier.popleft()
        res.nodes_expanded += 1
        pushed = []
        for nxt in ctx.successors(cur):
            if nxt in parent:          # never revisit a reached cell
                continue
            parent[nxt] = cur
            depth[nxt] = depth[cur] + 1
            res.nodes_generated += 1
            if record:
                pushed.append([nxt[0], nxt[1], depth[nxt], 0, depth[nxt]])
            if nxt == goal:            # early goal test: optimal in number of moves
                if record:
                    res.events.append([cur[0], cur[1], depth[cur], 0, depth[cur], len(frontier), pushed])
                res.found = True
                res.path = reconstruct(parent, goal)
                res.cost = path_cost(ctx, res.path)
                res.time_ms = (time.perf_counter() - t0) * 1000
                return res
            frontier.append(nxt)
        res.max_frontier = max(res.max_frontier, len(frontier))
        if record:
            res.events.append([cur[0], cur[1], depth[cur], 0, depth[cur], len(frontier), pushed])
    res.time_ms = (time.perf_counter() - t0) * 1000
    return res
