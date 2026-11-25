from algorithms.base import SearchContext
from environment.grid import Grid

WEIGHTED = [
    "......",
    ".####.",
    ".!!!!.",
    ".####.",
    "......",
]


def ctx(rows, **kw):
    return SearchContext(Grid.from_strings(rows), **kw)


def brute_force_min_cost(grid, start, goal):
    """Bellman-Ford style relaxation — an independent reference for the optimal cost."""
    cells = grid.passable_cells()
    dist = {c: float("inf") for c in cells}
    dist[start] = 0
    for _ in range(len(cells)):
        changed = False
        for c in cells:
            if dist[c] == float("inf"):
                continue
            for n in grid.neighbors(c):
                nd = dist[c] + grid.cost(n)
                if nd < dist[n]:
                    dist[n] = nd
                    changed = True
        if not changed:
            break
    return dist[goal]
