"""Terrain types and the configurable movement-cost model."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Terrain(IntEnum):
    ROAD = 0
    WALL = 1
    DIFFICULT = 2
    HAZARD = 3
    SAFE = 4


TERRAIN_LABELS = {
    Terrain.ROAD: "Road",
    Terrain.WALL: "Wall",
    Terrain.DIFFICULT: "Difficult terrain",
    Terrain.HAZARD: "Hazard",
    Terrain.SAFE: "Safe zone",
}


@dataclass
class CostModel:
    """Cost of ENTERING a cell of each terrain type. Walls are impassable."""

    road: float = 1.0
    difficult: float = 3.0
    hazard: float = 5.0
    safe: float = 1.0

    def __post_init__(self) -> None:
        for name in ("road", "difficult", "hazard", "safe"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or value <= 0:
                raise ValueError(f"Movement cost for {name} must be a positive number, got {value!r}")

    def cost(self, terrain: int) -> float:
        if terrain == Terrain.WALL:
            return float("inf")
        return {
            Terrain.ROAD: self.road,
            Terrain.DIFFICULT: self.difficult,
            Terrain.HAZARD: self.hazard,
            Terrain.SAFE: self.safe,
        }[Terrain(terrain)]

    @property
    def min_cost(self) -> float:
        """Smallest cost of any passable move. Scales the admissible heuristic."""
        return min(self.road, self.difficult, self.hazard, self.safe)

    def as_dict(self) -> dict:
        return {"road": self.road, "difficult": self.difficult, "hazard": self.hazard, "safe": self.safe}
