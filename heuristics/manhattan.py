"""Manhattan-distance heuristic and admissibility/consistency checks."""
from __future__ import annotations

import heapq

from environment.grid import Cell, Grid


def manhattan(a: Cell, b: Cell) -> int:
    """h(n) = |r − r_goal| + |c − c_goal|"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def weighted_manhattan(a: Cell, b: Cell, min_cost: float = 1.0) -> float:
    """Manhattan × cheapest step cost — admissible for 4-directional weighted grids."""
    return manhattan(a, b) * min_cost


def true_cost_to_goal(grid: Grid, goal: Cell) -> dict[Cell, float]:
    """h*(n): exact cheapest cost from every cell to `goal` (reverse Dijkstra).

    Costs are paid on entering a cell, so moving u → v costs cost(v). Running backwards
    from the goal, relaxing v → u adds cost(v).
    """
    dist = {goal: 0.0}
    heap = [(0.0, goal)]
    while heap:
        d, v = heapq.heappop(heap)
        if d > dist[v]:
            continue
        step = grid.cost(v)
        for u in grid.neighbors(v):
            nd = d + step
            if nd < dist.get(u, float("inf")):
                dist[u] = nd
                heapq.heappush(heap, (nd, u))
    return dist


def cost_from_start(grid: Grid, start: Cell) -> dict[Cell, float]:
    """g*(n): exact cheapest cost from `start` to every cell (forward Dijkstra)."""
    dist = {start: 0.0}
    heap = [(0.0, start)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        for v in grid.neighbors(u):
            nd = d + grid.cost(v)
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return dist


def check_admissible(grid: Grid, goal: Cell) -> tuple[bool, int, float]:
    """Return (admissible?, cells checked, worst h/h* ratio)."""
    hstar = true_cost_to_goal(grid, goal)
    m = grid.cost_model.min_cost
    worst, ok = 0.0, True
    for cell, hs in hstar.items():
        h = weighted_manhattan(cell, goal, m)
        if h > hs + 1e-9:
            ok = False
        if hs > 0:
            worst = max(worst, h / hs)
    return ok, len(hstar), worst


def check_consistent(grid: Grid, goal: Cell) -> tuple[bool, int]:
    """Verify h(n) ≤ c(n, n') + h(n') on every edge. Returns (consistent?, edges checked)."""
    m = grid.cost_model.min_cost
    edges, ok = 0, True
    for cell in grid.passable_cells():
        hn = weighted_manhattan(cell, goal, m)
        for nxt in grid.neighbors(cell):
            edges += 1
            if hn > grid.cost(nxt) + weighted_manhattan(nxt, goal, m) + 1e-9:
                ok = False
    return ok, edges
