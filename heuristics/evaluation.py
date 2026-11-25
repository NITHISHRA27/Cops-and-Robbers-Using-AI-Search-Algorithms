"""Evaluation function for Minimax / Alpha-Beta (robber = MAX, police = MIN).

This is a *game evaluation score*, not a path cost: higher means better for the robber.

    E(s) = − w_exit  · d_exit(R)                     escape distance (moves to exit)
           + w_cop   · min(d_cop(R), CAP)            cop proximity (capped)
           + w_route · routes(R)                     available escape routes
           + w_block · clamp(d_exit(C*) − d_exit(R)) exit-blocking race
           − w_risk  · risk(R)                       officers able to capture next turn

Terminal states override E: escape = +1000 − ply, capture = −1000 + ply (sooner escape and
later capture are preferred). Default weights and their justification are in WEIGHT_NOTES.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from environment.grid import Cell, Grid

WIN_SCORE = 1000.0
COP_DISTANCE_CAP = 6
RACE_CLAMP = 5


@dataclass
class EvalWeights:
    exit: float = 10.0
    cop: float = 6.0
    routes: float = 3.0
    block: float = 5.0
    risk: float = 40.0

    def as_dict(self) -> dict:
        return asdict(self)


WEIGHT_NOTES = {
    "exit": ("Escape distance", 10.0,
             "The robber's only goal. One move closer to the exit is the reference unit of value, so it "
             "carries the largest per-unit weight."),
    "cop": ("Cop proximity", 6.0,
            "Safety matters but must not dominate progress: 6 < 10 means the robber accepts moving one "
            "step closer to a cop if it gains a step towards the exit. Capped at 6 moves so the robber "
            "does not run away from the exit just to gain distance."),
    "routes": ("Escape routes", 3.0,
               "Counts open neighbour cells that are not next to a cop (max 4 → max 12 points). It is a "
               "tie-breaker that steers away from dead ends and corridors without overriding one real "
               "step of progress (10)."),
    "block": ("Exit blocking", 5.0,
              "Race margin: how many moves sooner the robber reaches the exit than the nearest cop, "
              "clamped to ±5. If a cop gets there first the route is effectively closed, so a lost race "
              "costs up to 25 points — more than two steps of progress."),
    "risk": ("Capture risk", 40.0,
             "Number of cops within one move (they capture on their next turn). Large enough to outweigh "
             "any positional gain (4 exit steps) but far below the ±1000 terminal values so real "
             "outcomes inside the search horizon always dominate."),
}


class EvalContext:
    """Precomputes distance fields so each leaf evaluation is a few dictionary lookups."""

    def __init__(self, grid: Grid, exit_: Cell, weights: EvalWeights | None = None) -> None:
        self.grid = grid
        self.exit = exit_
        self.w = weights or EvalWeights()
        self.exit_steps = grid.step_distances(exit_)                  # robber movement rules
        self.exit_steps_police = grid.step_distances(exit_, police=True)
        self.unreachable = grid.rows + grid.cols
        self._from_robber: dict[Cell, dict[Cell, int]] = {}

    def cop_steps_from(self, robber: Cell) -> dict[Cell, int]:
        """Police-movement step distances from the robber's cell (symmetric moves)."""
        if robber not in self._from_robber:
            dist = {robber: 0}
            frontier = [robber]
            while frontier:
                nxt_frontier = []
                for cur in frontier:
                    for n in self.grid.neighbors(cur, police=True):
                        if n not in dist:
                            dist[n] = dist[cur] + 1
                            nxt_frontier.append(n)
                frontier = nxt_frontier
            self._from_robber[robber] = dist
        return self._from_robber[robber]

    def features(self, robber: Cell, police: tuple[Cell, ...]) -> dict[str, float]:
        d_exit = self.exit_steps.get(robber, self.unreachable)
        dmap = self.cop_steps_from(robber)
        cop_d = [dmap.get(p, self.unreachable) for p in police]
        d_cop = min(cop_d) if cop_d else self.unreachable
        pset = set(police)
        danger = {n for p in police for n in self.grid.neighbors(p, police=True)} | pset
        routes = sum(1 for n in self.grid.neighbors(robber) if n not in danger)
        cop_exit = min((self.exit_steps_police.get(p, self.unreachable) for p in police), default=self.unreachable)
        race = max(-RACE_CLAMP, min(RACE_CLAMP, cop_exit - d_exit))
        risk = sum(1 for d in cop_d if d <= 1)
        return {"d_exit": d_exit, "d_cop": d_cop, "routes": routes, "race": race, "risk": risk}

    def contributions(self, robber: Cell, police: tuple[Cell, ...]) -> dict[str, float]:
        f = self.features(robber, police)
        return {
            "exit": -self.w.exit * f["d_exit"],
            "cop": self.w.cop * min(f["d_cop"], COP_DISTANCE_CAP),
            "routes": self.w.routes * f["routes"],
            "block": self.w.block * f["race"],
            "risk": -self.w.risk * f["risk"],
        }

    def evaluate(self, robber: Cell, police: tuple[Cell, ...]) -> float:
        return sum(self.contributions(robber, police).values())
