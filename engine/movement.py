"""Movement validation shared by human input and AI agents."""
from __future__ import annotations

from environment.grid import ACTIONS, STAY, Cell, Grid, apply_action

KEY_TO_ACTION = {
    "w": "UP", "arrowup": "UP", "up": "UP",
    "s": "DOWN", "arrowdown": "DOWN", "down": "DOWN",
    "a": "LEFT", "arrowleft": "LEFT", "left": "LEFT",
    "d": "RIGHT", "arrowright": "RIGHT", "right": "RIGHT",
    " ": STAY, "space": STAY, "stay": STAY, "wait": STAY,
}


def normalize_action(raw: str) -> str | None:
    if raw is None:
        return None
    raw = str(raw).strip()
    if raw.upper() in ACTIONS or raw.upper() == STAY:
        return raw.upper()
    return KEY_TO_ACTION.get(raw.lower())


def validate_robber_move(grid: Grid, cell: Cell, action: str) -> tuple[bool, Cell, str]:
    """Return (valid, destination, message)."""
    if action != STAY and action not in ACTIONS:
        return False, cell, f"Unknown action {action!r}."
    dest = apply_action(cell, action)
    if not grid.in_bounds(dest):
        return False, cell, "You cannot leave the city grid."
    if not grid.is_passable(dest):
        return False, cell, "That cell is a building — choose another direction."
    return True, dest, ""


def validate_police_move(grid: Grid, cell: Cell, dest: Cell) -> bool:
    if dest == cell:
        return True
    adjacent = abs(dest[0] - cell[0]) + abs(dest[1] - cell[1]) == 1
    return adjacent and grid.police_can_enter(dest)
