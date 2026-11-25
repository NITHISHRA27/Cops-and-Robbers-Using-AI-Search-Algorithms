"""Environment = grid + entity placements. Dynamic game state is in engine.game_state."""
from __future__ import annotations

from dataclasses import dataclass, field

from environment.grid import Cell, Grid
from environment.terrain import Terrain


@dataclass
class Environment:
    grid: Grid
    robber: Cell
    exit: Cell
    police: list[Cell] = field(default_factory=list)

    def validate(self) -> list[str]:
        """Return a list of human-readable problems; an empty list means valid."""
        errors: list[str] = []
        g = self.grid
        for name, cell in (("Robber", self.robber), ("Exit", self.exit)):
            if not g.in_bounds(cell):
                errors.append(f"{name} position {cell} is outside the {g.rows}×{g.cols} grid.")
            elif not g.is_passable(cell):
                errors.append(f"{name} position {cell} is on a wall.")
        if self.robber == self.exit:
            errors.append("Robber and exit cannot share a cell.")
        if not self.police:
            errors.append("At least one police officer is required.")
        seen: set[Cell] = set()
        for i, cell in enumerate(self.police, start=1):
            if not g.in_bounds(cell):
                errors.append(f"Officer {i} position {cell} is outside the grid.")
                continue
            if not g.is_passable(cell):
                errors.append(f"Officer {i} position {cell} is on a wall.")
            elif g.terrain(cell) == Terrain.SAFE:
                errors.append(f"Officer {i} position {cell} is inside a safe zone.")
            if cell == self.robber:
                errors.append(f"Officer {i} overlaps the robber.")
            if cell == self.exit:
                errors.append(f"Officer {i} overlaps the exit.")
            if cell in seen:
                errors.append(f"Officer {i} overlaps another officer.")
            seen.add(cell)
        if not errors and not g.is_reachable(self.robber, self.exit):
            errors.append("The exit is unreachable from the robber's start — remove some walls.")
        return errors

    def copy(self) -> "Environment":
        return Environment(self.grid.copy(), self.robber, self.exit, list(self.police))

    def to_dict(self) -> dict:
        return {"grid": self.grid.to_dict(), "robber": list(self.robber), "exit": list(self.exit),
                "police": [list(p) for p in self.police]}

    @classmethod
    def from_dict(cls, d: dict) -> "Environment":
        return cls(Grid.from_dict(d["grid"]), tuple(d["robber"]), tuple(d["exit"]), [tuple(p) for p in d["police"]])
