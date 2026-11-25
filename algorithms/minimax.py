"""Depth-limited Minimax: robber maximises, police minimise. Explores every branch."""
from __future__ import annotations

import math
import time

from algorithms.adversarial import AdversarialResult, GameTree
from environment.grid import Cell, Grid
from heuristics.evaluation import EvalWeights


def _robber_moved(gt: GameTree, robber: Cell, police: tuple, depth: int, ply: int, parent, action) -> float:
    """State after the robber's move — police (MIN) to play."""
    nid = gt.add_node(parent, ply, "MIN", action)
    gt.nodes += 1
    if robber in police:                                   # walked into an officer
        v = gt.capture_value(ply)
        gt.set_node(nid, value=v, player="LEAF", terminal="capture")
        return v
    if depth == 0:
        v = gt.evaluate(robber, police)
        gt.set_node(nid, value=v, player="LEAF")
        return v
    best = math.inf
    for label, new_police in gt.police_moves(robber, police):
        best = min(best, _police_moved(gt, robber, new_police, depth - 1, ply + 1, nid, label))
    gt.set_node(nid, value=best)
    return best


def _police_moved(gt: GameTree, robber: Cell, police: tuple, depth: int, ply: int, parent, action) -> float:
    """State after the police reply — robber (MAX) to play."""
    nid = gt.add_node(parent, ply, "MAX", action)
    gt.nodes += 1
    if robber in police:
        v = gt.capture_value(ply)
        gt.set_node(nid, value=v, player="LEAF", terminal="capture")
        return v
    if robber == gt.exit:
        v = gt.escape_value(ply)
        gt.set_node(nid, value=v, player="LEAF", terminal="escape")
        return v
    if depth == 0:
        v = gt.evaluate(robber, police)
        gt.set_node(nid, value=v, player="LEAF")
        return v
    best = -math.inf
    for action_r, nxt in gt.robber_moves(robber):
        best = max(best, _robber_moved(gt, nxt, police, depth - 1, ply + 1, nid, action_r))
    gt.set_node(nid, value=best)
    return best


def minimax_decision(grid: Grid, exit_: Cell, robber: Cell, police, depth: int = 4,
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
    best_action, best_value, child_values = "STAY", -math.inf, {}
    for action, nxt in gt.robber_moves(robber):
        v = _robber_moved(gt, nxt, police, depth - 1, 1, root, action)
        child_values[action] = v
        if v > best_value:
            best_action, best_value = action, v
    gt.set_node(root, value=best_value)
    return AdversarialResult("Minimax", best_action, best_value, depth, gt.nodes, 0,
                             (time.perf_counter() - t0) * 1000, child_values, gt.tree, gt.truncated,
                             list(gt.modelled))
