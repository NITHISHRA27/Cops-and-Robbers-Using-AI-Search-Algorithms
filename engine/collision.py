"""Capture and escape tests (goal tests of the dynamic game)."""
from __future__ import annotations

from environment.grid import Cell


def is_capture(robber: Cell, police: list[Cell]) -> bool:
    """Police goal: an officer occupies the robber's cell."""
    return robber in police


def is_escape(robber: Cell, exit_: Cell, police: list[Cell]) -> bool:
    """Robber goal: robber on the exit and not captured."""
    return robber == exit_ and robber not in police
