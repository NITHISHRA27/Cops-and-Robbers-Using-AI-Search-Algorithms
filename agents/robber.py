"""Robber intelligence.

Path-planning strategies (BFS / UCS / A*) replan every turn from the robber's current cell
to the exit. Officers' cells are blocked and cells next to officers carry a danger penalty
(UCS/A*) or are avoided when possible (BFS, which cannot weigh costs). If no route exists the
robber evades: it picks the move that maximises its distance to the nearest officer.

Adversarial strategies (Minimax / Alpha-Beta) look ahead over robber and police replies
using the shared evaluation function.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from algorithms import run_search
from algorithms.alpha_beta import alphabeta_decision
from algorithms.base import SearchContext
from algorithms.minimax import minimax_decision
from environment.grid import STAY, Cell, Grid, action_between, apply_action

DANGER_ADJACENT = 6.0
DANGER_NEAR = 2.0


@dataclass
class RobberDecision:
    action: str
    algorithm: str
    planned_path: list[Cell] = field(default_factory=list)
    nodes: int = 0
    time_ms: float = 0.0
    reason: str = ""
    extra: dict = field(default_factory=dict)


def danger_map(grid: Grid, police: list[Cell], exit_: Cell) -> dict[Cell, float]:
    penalty: dict[Cell, float] = {}
    for p in police:
        for n in grid.neighbors(p):
            penalty[n] = max(penalty.get(n, 0.0), DANGER_ADJACENT)
            for m in grid.neighbors(n):
                penalty[m] = max(penalty.get(m, 0.0), DANGER_NEAR)
    penalty.pop(exit_, None)
    return penalty


def plan_escape(grid: Grid, robber: Cell, exit_: Cell, police: list[Cell], algorithm: str = "A*"):
    """Plan a route with BFS/UCS/A*; returns the SearchResult and total nodes expanded."""
    pset = set(police)
    nodes = 0
    if algorithm == "BFS":
        adjacent = {n for p in police for n in grid.neighbors(p)} - {exit_}
        attempts = [SearchContext(grid, blocked=pset | adjacent), SearchContext(grid, blocked=pset)]
    else:
        danger = danger_map(grid, police, exit_)
        attempts = [SearchContext(grid, blocked=pset, extra_cost=lambda c: danger.get(c, 0.0))]
    res = None
    for ctx in attempts:
        if robber in ctx.blocked:
            continue
        res = run_search(algorithm, ctx, robber, exit_)
        nodes += res.nodes_expanded
        if res.found:
            break
    return res, nodes


def evade_action(grid: Grid, robber: Cell, police: list[Cell], exit_: Cell) -> str:
    best, best_score = STAY, None
    for nxt in [robber] + list(grid.neighbors(robber)):
        if nxt in police:
            continue
        dmin = min(abs(nxt[0] - p[0]) + abs(nxt[1] - p[1]) for p in police)
        score = (dmin, -(abs(nxt[0] - exit_[0]) + abs(nxt[1] - exit_[1])))
        if best_score is None or score > best_score:
            best, best_score = action_between(robber, nxt), score
    return best


def decide(grid: Grid, robber: Cell, exit_: Cell, police: list[Cell], algorithm: str,
           depth: int = 4, n_modelled: int = 2) -> RobberDecision:
    if algorithm in ("Minimax", "Alpha-Beta"):
        fn = minimax_decision if algorithm == "Minimax" else alphabeta_decision
        res = fn(grid, exit_, robber, police, depth=depth, n_modelled=n_modelled)
        nxt = apply_action(robber, res.best_action)
        return RobberDecision(res.best_action, algorithm, [robber, nxt], res.nodes_explored, res.time_ms,
                              f"Best worst-case value {res.best_value:.1f} at depth {depth} "
                              f"({res.nodes_explored} states, {res.branches_pruned} pruned).",
                              {"child_values": res.child_values, "pruned": res.branches_pruned})
    res, nodes = plan_escape(grid, robber, exit_, police, algorithm)
    if res is not None and res.found and len(res.path) > 1:
        return RobberDecision(action_between(robber, res.path[1]), algorithm, res.path, nodes, res.time_ms,
                              f"{algorithm} route to exit: {res.path_length} moves, cost {res.cost:.1f}.")
    action = evade_action(grid, robber, police, exit_)
    return RobberDecision(action, algorithm, [robber, apply_action(robber, action)], nodes,
                          res.time_ms if res else 0.0, "No safe route to the exit — evading the nearest officer.")
