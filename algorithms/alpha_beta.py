"""Minimax with Alpha-Beta pruning.

α = best value the robber (MAX) can already guarantee, β = best value the police (MIN) can
already guarantee. A branch is cut as soon as α ≥ β because the opponent would never let
play reach it. With the same move ordering and evaluation function this returns exactly the
same decision and root value as plain Minimax while visiting fewer nodes.
"""
from __future__ import annotations

import math
import time

from algorithms.adversarial import AdversarialResult, GameTree
from environment.grid import Cell, Grid
from heuristics.evaluation import EvalWeights


def _mark_pruned(gt: GameTree, parent, depth: int, player: str, labels: list[str]) -> None:
    gt.pruned += len(labels)
    for label in labels:
        nid = gt.add_node(parent, depth, player, label)
        gt.set_node(nid, pruned=True)


def _robber_moved(gt: GameTree, robber: Cell, police: tuple, depth: int, ply: int,
                  alpha: float, beta: float, parent, action) -> float:
    nid = gt.add_node(parent, ply, "MIN", action)
    gt.nodes += 1
    if robber in police:
        v = gt.capture_value(ply)
        gt.set_node(nid, value=v, player="LEAF", terminal="capture", alpha=alpha, beta=beta)
        return v
    if depth == 0:
        v = gt.evaluate(robber, police)
        gt.set_node(nid, value=v, player="LEAF", alpha=alpha, beta=beta)
        return v
    best = math.inf
    moves = gt.police_moves(robber, police)
    for i, (label, new_police) in enumerate(moves):
        best = min(best, _police_moved(gt, robber, new_police, depth - 1, ply + 1, alpha, beta, nid, label))
        beta = min(beta, best)
        if best <= alpha:                       # MAX above already has something better
            _mark_pruned(gt, nid, ply + 1, "MAX", [m[0] for m in moves[i + 1:]])
            break
    gt.set_node(nid, value=best, alpha=alpha, beta=beta)
    return best


def _police_moved(gt: GameTree, robber: Cell, police: tuple, depth: int, ply: int,
                  alpha: float, beta: float, parent, action) -> float:
    nid = gt.add_node(parent, ply, "MAX", action)
    gt.nodes += 1
    if robber in police:
        v = gt.capture_value(ply)
        gt.set_node(nid, value=v, player="LEAF", terminal="capture", alpha=alpha, beta=beta)
        return v
    if robber == gt.exit:
        v = gt.escape_value(ply)
        gt.set_node(nid, value=v, player="LEAF", terminal="escape", alpha=alpha, beta=beta)
        return v
    if depth == 0:
        v = gt.evaluate(robber, police)
        gt.set_node(nid, value=v, player="LEAF", alpha=alpha, beta=beta)
        return v
    best = -math.inf
    moves = gt.robber_moves(robber)
    for i, (action_r, nxt) in enumerate(moves):
        best = max(best, _robber_moved(gt, nxt, police, depth - 1, ply + 1, alpha, beta, nid, action_r))
        alpha = max(alpha, best)
        if best >= beta:                        # MIN above already has something better
            _mark_pruned(gt, nid, ply + 1, "MIN", [m[0] for m in moves[i + 1:]])
            break
    gt.set_node(nid, value=best, alpha=alpha, beta=beta)
    return best


def alphabeta_decision(grid: Grid, exit_: Cell, robber: Cell, police, depth: int = 4,
                       weights: EvalWeights | None = None, n_modelled: int = 2,
                       record_tree: bool = False) -> AdversarialResult:
    if depth < 1:
        raise ValueError("Search depth must be at least 1 ply")
    t0 = time.perf_counter()
    gt = GameTree(grid, exit_, weights, n_modelled, record_tree)
    police = tuple(police)
    gt.choose_modelled(robber, police)
    root = gt.add_node(None, 0, "MAX", "root")
    gt.nodes += 1
    alpha, beta = -math.inf, math.inf
    best_action, best_value, child_values = "STAY", -math.inf, {}
    for action, nxt in gt.robber_moves(robber):
        v = _robber_moved(gt, nxt, police, depth - 1, 1, alpha, beta, root, action)
        child_values[action] = v              # exact for the best move, an upper bound for the rest
        if v > best_value:
            best_action, best_value = action, v
        alpha = max(alpha, best_value)
    gt.set_node(root, value=best_value, alpha=alpha, beta=beta)
    return AdversarialResult("Alpha-Beta", best_action, best_value, depth, gt.nodes, gt.pruned,
                             (time.perf_counter() - t0) * 1000, child_values, gt.tree, gt.truncated,
                             list(gt.modelled))
