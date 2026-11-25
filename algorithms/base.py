"""Shared search result type and helpers for BFS, UCS and A*."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional

from environment.grid import Cell, Grid


@dataclass
class SearchResult:
    algorithm: str
    start: Cell
    goal: Cell
    found: bool
    path: list[Cell] = field(default_factory=list)
    cost: float = float("inf")
    nodes_expanded: int = 0
    nodes_generated: int = 0
    max_frontier: int = 0
    time_ms: float = 0.0
    # Visualisation trace. Each event is one expansion:
    #   [r, c, g, h, f, frontier_size, [[r, c, g, h, f], ...pushed nodes]]
    events: list = field(default_factory=list)

    @property
    def path_length(self) -> int:
        """Number of moves in the path (cells − 1)."""
        return max(0, len(self.path) - 1)

    def summary(self) -> dict:
        return {
            "Algorithm": self.algorithm,
            "Path found": self.found,
            "Path length": self.path_length if self.found else None,
            "Path cost": round(self.cost, 2) if self.found else None,
            "Nodes expanded": self.nodes_expanded,
            "Nodes generated": self.nodes_generated,
            "Max frontier": self.max_frontier,
            "Time (ms)": round(self.time_ms, 3),
        }


class SearchContext:
    """Everything an algorithm needs: grid, passability rules and optional extra step costs.

    `extra_cost` adds a non-negative penalty for entering a cell (used by the robber to
    keep its distance from police). It never makes a step cheaper than the terrain cost,
    so the Manhattan × min-cost heuristic stays admissible.
    """

    def __init__(self, grid: Grid, blocked: Iterable[Cell] | None = None, police: bool = False,
                 extra_cost: Optional[Callable[[Cell], float]] = None) -> None:
        self.grid = grid
        self.blocked = frozenset(blocked or ())
        self.police = police
        self.extra_cost = extra_cost

    def successors(self, cell: Cell):
        return self.grid.neighbors(cell, self.blocked, police=self.police)

    def step_cost(self, cell: Cell) -> float:
        base = self.grid.cost(cell)
        if self.extra_cost is not None:
            extra = self.extra_cost(cell)
            if extra < 0:
                raise ValueError("Extra step costs must be non-negative")
            base += extra
        return base

    def valid_endpoint(self, cell: Cell) -> bool:
        return self.grid.is_passable(cell)


def reconstruct(parent: dict[Cell, Optional[Cell]], goal: Cell) -> list[Cell]:
    path = [goal]
    while parent[path[-1]] is not None:
        path.append(parent[path[-1]])
    path.reverse()
    return path


def path_cost(ctx: SearchContext, path: list[Cell]) -> float:
    return sum(ctx.step_cost(c) for c in path[1:])
