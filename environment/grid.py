"""City grid: the static part of the state space.

Static pathfinding state  S = (r, c)  — a cell coordinate (row, column).
Actions                   UP, DOWN, LEFT, RIGHT (four-directional).
Transition model          move to the adjacent cell if it is inside the grid and not a wall.
Step cost                 cost of the destination cell's terrain (see CostModel).
"""
from __future__ import annotations

from collections import deque
from typing import Iterable, Iterator

from environment.terrain import CostModel, Terrain

Cell = tuple[int, int]

ACTIONS: dict[str, tuple[int, int]] = {
    "UP": (-1, 0),
    "DOWN": (1, 0),
    "LEFT": (0, -1),
    "RIGHT": (0, 1),
}
STAY = "STAY"


def apply_action(cell: Cell, action: str) -> Cell:
    if action == STAY:
        return cell
    dr, dc = ACTIONS[action]
    return (cell[0] + dr, cell[1] + dc)


def action_between(a: Cell, b: Cell) -> str:
    delta = (b[0] - a[0], b[1] - a[1])
    for name, d in ACTIONS.items():
        if d == delta:
            return name
    if delta == (0, 0):
        return STAY
    raise ValueError(f"{a} and {b} are not adjacent")


class Grid:
    def __init__(self, rows: int, cols: int, cells: list[list[int]] | None = None,
                 cost_model: CostModel | None = None) -> None:
        if rows <= 0 or cols <= 0:
            raise ValueError("Grid dimensions must be positive")
        self.rows = rows
        self.cols = cols
        self.cells = cells if cells is not None else [[Terrain.ROAD] * cols for _ in range(rows)]
        if len(self.cells) != rows or any(len(row) != cols for row in self.cells):
            raise ValueError("Cell matrix does not match grid dimensions")
        self.cost_model = cost_model or CostModel()

    # ------------------------------------------------------------------ queries
    def in_bounds(self, cell: Cell) -> bool:
        r, c = cell
        return 0 <= r < self.rows and 0 <= c < self.cols

    def terrain(self, cell: Cell) -> int:
        return self.cells[cell[0]][cell[1]]

    def is_passable(self, cell: Cell) -> bool:
        return self.in_bounds(cell) and self.cells[cell[0]][cell[1]] != Terrain.WALL

    def police_can_enter(self, cell: Cell) -> bool:
        """Police may not enter safe zones (crowded civilian areas)."""
        return self.is_passable(cell) and self.cells[cell[0]][cell[1]] != Terrain.SAFE

    def cost(self, cell: Cell) -> float:
        return self.cost_model.cost(self.terrain(cell))

    def neighbors(self, cell: Cell, blocked: Iterable[Cell] | None = None,
                  police: bool = False) -> Iterator[Cell]:
        """Valid successor cells in fixed order UP, DOWN, LEFT, RIGHT."""
        blocked = blocked or ()
        r, c = cell
        check = self.police_can_enter if police else self.is_passable
        for dr, dc in ACTIONS.values():
            nxt = (r + dr, c + dc)
            if check(nxt) and nxt not in blocked:
                yield nxt

    def degree(self, cell: Cell) -> int:
        return sum(1 for _ in self.neighbors(cell))

    def passable_cells(self) -> list[Cell]:
        return [(r, c) for r in range(self.rows) for c in range(self.cols) if self.cells[r][c] != Terrain.WALL]

    def count(self, terrain: Terrain) -> int:
        return sum(row.count(terrain) for row in self.cells)

    # ------------------------------------------------------------------ helpers
    def step_distances(self, source: Cell, police: bool = False,
                       blocked: Iterable[Cell] | None = None) -> dict[Cell, int]:
        """Unweighted BFS distance (number of moves) from source to every reachable cell."""
        blocked = set(blocked or ())
        dist = {source: 0}
        queue = deque([source])
        while queue:
            cur = queue.popleft()
            for nxt in self.neighbors(cur, blocked, police=police):
                if nxt not in dist:
                    dist[nxt] = dist[cur] + 1
                    queue.append(nxt)
        return dist

    def is_reachable(self, a: Cell, b: Cell, police: bool = False) -> bool:
        return b in self.step_distances(a, police=police)

    def set_terrain(self, cell: Cell, terrain: Terrain) -> None:
        if not self.in_bounds(cell):
            raise ValueError(f"Cell {cell} is outside the grid")
        self.cells[cell[0]][cell[1]] = int(terrain)

    def copy(self) -> "Grid":
        return Grid(self.rows, self.cols, [row[:] for row in self.cells], self.cost_model)

    def to_dict(self) -> dict:
        return {"rows": self.rows, "cols": self.cols, "cells": self.cells, "costs": self.cost_model.as_dict()}

    @classmethod
    def from_dict(cls, data: dict) -> "Grid":
        return cls(data["rows"], data["cols"], [list(r) for r in data["cells"]], CostModel(**data["costs"]))

    @classmethod
    def from_strings(cls, rows: list[str], cost_model: CostModel | None = None) -> "Grid":
        """Build from ASCII art: '.' road, '#' wall, '~' difficult, '!' hazard, 's' safe."""
        mapping = {".": Terrain.ROAD, "#": Terrain.WALL, "~": Terrain.DIFFICULT, "!": Terrain.HAZARD, "s": Terrain.SAFE}
        cells = [[int(mapping.get(ch, Terrain.ROAD)) for ch in row] for row in rows]
        return cls(len(rows), len(rows[0]), cells, cost_model)
