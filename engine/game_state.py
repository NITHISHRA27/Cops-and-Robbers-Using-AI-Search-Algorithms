"""Dynamic game state  S = (R, C1..Cn, E, t)  plus bookkeeping for statistics and UI."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from environment.grid import Cell

READY, RUNNING, PAUSED = "ready", "running", "paused"
ESCAPED, CAPTURED, TIMEOUT = "escaped", "captured", "timeout"
FINAL_STATUSES = (ESCAPED, CAPTURED, TIMEOUT)


@dataclass
class GameState:
    robber: Cell                     # R
    police: list[Cell]               # C1..Cn
    exit: Cell                       # E
    turn: int = 0                    # t
    status: str = READY
    moves: int = 0
    robber_cost: float = 0.0
    robber_nodes: int = 0
    police_nodes: int = 0
    robber_time_ms: float = 0.0
    police_time_ms: float = 0.0
    log: list[tuple[int, str, str]] = field(default_factory=list)   # (turn, kind, message)
    trail: list[Cell] = field(default_factory=list)
    police_trails: list[list[Cell]] = field(default_factory=list)
    last_plan: Optional[Any] = None
    last_robber_decision: Optional[Any] = None
    advisory_path: list[Cell] = field(default_factory=list)
    message: str = ""

    @property
    def is_over(self) -> bool:
        return self.status in FINAL_STATUSES

    def as_tuple(self) -> tuple:
        return (self.robber, *self.police, self.exit, self.turn)
