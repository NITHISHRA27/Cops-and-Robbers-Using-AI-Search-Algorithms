"""Predictive interception for police officers.

Each turn (dynamic replanning):
 1. Predict the robber's most likely escape route with A* (robber → exit, avoiding officers),
    plus an alternative route that avoids the primary one.
 2. For every route cell at index k (the robber needs k moves to get there) an officer whose
    BFS step distance d ≤ k can be there first: that cell is *interceptable*.
 3. Assign distinct roles so officers do not duplicate effort:
      Direct pursuit         → the robber's predicted next cell
      Exit interception      → earliest interceptable cell on the predicted route
      Corridor blocking      → earliest interceptable choke point (≤ 2 open neighbours)
      Secondary interception → earliest interceptable cell on the alternative route
      Perimeter guard        → unclaimed cells around the exit
 4. Route every officer to its target with A* (police cannot enter safe zones and do not walk
    through each other). An officer adjacent to the robber always takes the capture.
Predictions are estimates of likely movement, not guaranteed future positions.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from algorithms.astar import astar
from algorithms.base import SearchContext
from environment.grid import Cell, Grid

ROLES = ("Direct pursuit", "Exit interception", "Corridor blocking", "Secondary interception")
EXTRA_ROLE = "Perimeter guard"


@dataclass
class OfficerDecision:
    officer: int
    role: str
    position: Cell
    target: Cell
    intercept: Optional[Cell]
    route: list[Cell]
    next_cell: Cell
    reason: str
    nodes: int = 0


@dataclass
class PolicePlan:
    decisions: list[OfficerDecision]
    predicted_path: list[Cell]
    predicted_position: Cell
    alt_path: list[Cell] = field(default_factory=list)
    nodes_expanded: int = 0
    time_ms: float = 0.0


def predict_robber_routes(grid: Grid, robber: Cell, exit_: Cell, police: list[Cell]) -> tuple[list[Cell], list[Cell], int]:
    """Primary and alternative likely robber routes (A* from the robber's point of view)."""
    pset = set(police)
    danger = {n for p in police for n in grid.neighbors(p)} - {exit_}
    ctx = SearchContext(grid, blocked=pset, extra_cost=lambda c: 3.0 if c in danger else 0.0)
    res = astar(ctx, robber, exit_)
    nodes = res.nodes_expanded
    if not res.found:
        res = astar(SearchContext(grid), robber, exit_)
        nodes += res.nodes_expanded
    primary = res.path if res.found else [robber]
    interior = set(primary[1:-1])
    alt_ctx = SearchContext(grid, blocked=pset,
                            extra_cost=lambda c: (8.0 if c in interior else 0.0) + (3.0 if c in danger else 0.0))
    alt = astar(alt_ctx, robber, exit_)
    nodes += alt.nodes_expanded
    alt_path = alt.path if alt.found and alt.path != primary else []
    return primary, alt_path, nodes


def _earliest_intercept(path: list[Cell], dist: dict[Cell, int], claimed: set[Cell],
                        only: Optional[set[Cell]] = None) -> tuple[Optional[Cell], int, float]:
    """Earliest route cell the officer reaches no later than the robber.

    Returns (cell, index, score). If no cell is reachable in time, returns the cell with the
    smallest time deficit (score = deficit + large constant so feasible cells always win).
    """
    best, best_idx, best_score = None, -1, float("inf")
    for idx, cell in enumerate(path[1:], start=1):
        if cell in claimed or (only is not None and cell not in only) or cell not in dist:
            continue
        deficit = dist[cell] - idx
        if deficit <= 0:
            return cell, idx, float(dist[cell])
        score = 1000.0 + deficit
        if score < best_score:
            best, best_idx, best_score = cell, idx, score
    return best, best_idx, best_score


def plan_police(grid: Grid, robber: Cell, exit_: Cell, police: list[Cell]) -> PolicePlan:
    t0 = time.perf_counter()
    primary, alt_path, nodes = predict_robber_routes(grid, robber, exit_, police)
    predicted_position = primary[min(2, len(primary) - 1)]
    dists = [grid.step_distances(p, police=True) for p in police]
    chokes = {c for c in primary[1:] if grid.degree(c) <= 2}
    alt_only = set(alt_path) - set(primary)

    unassigned = list(range(len(police)))
    claimed: set[Cell] = set()
    assignment: dict[int, tuple[str, Cell, Optional[Cell], str]] = {}

    def candidate(role: str, i: int):
        d = dists[i]
        if role == "Direct pursuit":
            tgt = robber if d.get(robber, 99) <= 1 or len(primary) < 2 else primary[1]
            if tgt in claimed:
                tgt = robber
            if tgt not in d:
                return None
            return tgt, None, float(d[tgt]), f"Chasing the robber's likely next cell {tgt}."
        if role == "Exit interception":
            cell, idx, score = _earliest_intercept(primary, d, claimed)
            if cell is None:
                return None
            if score < 1000:
                why = f"Robber needs ~{idx} moves to reach {cell}; officer needs {d[cell]} — cut the route there."
            else:
                why = f"Cannot beat the robber anywhere on its route; closing the gap at {cell}."
            return cell, cell, score, why
        if role == "Corridor blocking":
            if not chokes:
                return None
            cell, idx, score = _earliest_intercept(primary, d, claimed, only=chokes)
            if cell is None:
                return None
            return cell, cell, score, f"{cell} is a narrow corridor (≤2 exits) on the predicted route — block it."
        if role == "Secondary interception":
            if not alt_only:
                return None
            cell, idx, score = _earliest_intercept(alt_path, d, claimed, only=alt_only)
            if cell is None:
                return None
            return cell, cell, score, f"Covering the alternative escape route at {cell}."
        # Perimeter guard: unclaimed reachable cell nearest the exit
        ring = sorted((c for c in d if c not in claimed),
                      key=lambda c: (abs(c[0] - exit_[0]) + abs(c[1] - exit_[1]), d[c]))
        if not ring:
            return None
        return ring[0], None, float(d[ring[0]]), f"Guarding the exit perimeter at {ring[0]}."

    for role in list(ROLES) + [EXTRA_ROLE] * len(police):
        if not unassigned:
            break
        options = [(candidate(role, i), i) for i in unassigned]
        options = [(o, i) for o, i in options if o is not None]
        if not options:
            continue
        (tgt, icpt, _, why), officer = min(options, key=lambda oi: (oi[0][2], oi[1]))
        assignment[officer] = (role, tgt, icpt, why)
        claimed.add(tgt)
        unassigned.remove(officer)
    for i in unassigned:  # officers that cannot reach anything useful
        assignment[i] = ("Hold position", police[i], None, "No reachable target — holding position.")

    decisions = []
    for i, pos in enumerate(police):
        role, tgt, icpt, why = assignment[i]
        others = set(police) - {pos}
        node_count = 0
        if robber in set(grid.neighbors(pos, police=True)):
            route, nxt = [pos, robber], robber
            role_reason = "Robber is adjacent — moving in for the capture."
            decisions.append(OfficerDecision(i, role, pos, robber, icpt, route, nxt, role_reason))
            continue
        if tgt == pos:
            route, nxt = [pos], pos
        else:
            res = astar(SearchContext(grid, blocked=others, police=True), pos, tgt)
            node_count += res.nodes_expanded
            if not res.found:  # target blocked (e.g. by an officer): fall back to pursuing the robber
                res = astar(SearchContext(grid, blocked=others, police=True), pos, robber)
                node_count += res.nodes_expanded
                why += " Route blocked — falling back to direct pursuit."
            route = res.path if res.found else [pos]
            nxt = route[1] if len(route) > 1 else pos
        nodes += node_count
        decisions.append(OfficerDecision(i, role, pos, tgt, icpt, route, nxt, why, node_count))

    return PolicePlan(decisions, primary, predicted_position, alt_path, nodes, (time.perf_counter() - t0) * 1000)
