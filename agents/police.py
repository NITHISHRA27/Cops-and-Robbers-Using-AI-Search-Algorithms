"""Police team agent: wraps predictive interception and tracks target changes between turns."""
from __future__ import annotations

from agents.interception import PolicePlan, plan_police
from environment.grid import Cell, Grid


class PoliceTeam:
    def __init__(self) -> None:
        self.previous_targets: dict[int, Cell] = {}

    def plan(self, grid: Grid, robber: Cell, exit_: Cell, police: list[Cell]) -> tuple[PolicePlan, list[str]]:
        """Return the plan and log messages about re-targeting (dynamic replanning)."""
        plan = plan_police(grid, robber, exit_, police)
        changes = []
        for d in plan.decisions:
            prev = self.previous_targets.get(d.officer)
            if prev is not None and prev != d.target:
                changes.append(f"Officer {d.officer + 1} changed target {prev} → {d.target} ({d.role}).")
            self.previous_targets[d.officer] = d.target
        return plan, changes
