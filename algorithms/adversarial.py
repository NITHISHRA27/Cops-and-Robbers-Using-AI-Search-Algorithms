"""Game-tree model shared by Minimax and Alpha-Beta.

Game state      s = (R, C1..Cn)   (exit E and the grid are fixed; ply depth plays the role of t)
MAX player      robber — actions UP/DOWN/LEFT/RIGHT/STAY onto passable cells
MIN player      police — one *joint* action moving the k nearest officers at once
                (others hold position inside the search horizon to bound branching: 5^k)
Terminal        capture: robber and an officer share a cell; escape: robber on exit after
                the police reply (same turn order as the game engine).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Optional

from environment.grid import ACTIONS, STAY, Cell, Grid, apply_action
from heuristics.evaluation import WIN_SCORE, EvalContext, EvalWeights

ROBBER_ACTION_ORDER = ("UP", "DOWN", "LEFT", "RIGHT", STAY)
MAX_TREE_NODES = 4000


@dataclass
class TreeNode:
    id: int
    parent: Optional[int]
    depth: int
    player: str               # "MAX", "MIN" or "LEAF"
    action: str
    value: Optional[float] = None
    alpha: Optional[float] = None
    beta: Optional[float] = None
    pruned: bool = False
    terminal: str = ""        # "", "capture", "escape"


@dataclass
class AdversarialResult:
    algorithm: str
    best_action: str
    best_value: float
    depth: int
    nodes_explored: int = 0
    branches_pruned: int = 0
    time_ms: float = 0.0
    child_values: dict = field(default_factory=dict)
    tree: list = field(default_factory=list)
    tree_truncated: bool = False
    modelled_officers: list = field(default_factory=list)


class GameTree:
    def __init__(self, grid: Grid, exit_: Cell, weights: EvalWeights | None = None,
                 n_modelled: int = 2, record_tree: bool = False) -> None:
        self.grid = grid
        self.exit = exit_
        self.eval = EvalContext(grid, exit_, weights)
        self.n_modelled = max(1, n_modelled)
        self.record_tree = record_tree
        self.tree: list[TreeNode] = []
        self.truncated = False
        self.nodes = 0
        self.pruned = 0
        self.modelled: tuple[int, ...] = ()

    # -------------------------------------------------------------- tree recording
    def add_node(self, parent: Optional[int], depth: int, player: str, action: str) -> Optional[int]:
        if not self.record_tree:
            return None
        if len(self.tree) >= MAX_TREE_NODES:
            self.truncated = True
            return None
        node = TreeNode(len(self.tree), parent, depth, player, action)
        self.tree.append(node)
        return node.id

    def set_node(self, nid: Optional[int], **kw) -> None:
        if nid is not None:
            for k, v in kw.items():
                setattr(self.tree[nid], k, v)

    # -------------------------------------------------------------- game mechanics
    def choose_modelled(self, robber: Cell, police: tuple[Cell, ...]) -> tuple[int, ...]:
        order = sorted(range(len(police)), key=lambda i: (abs(police[i][0] - robber[0]) + abs(police[i][1] - robber[1]), i))
        self.modelled = tuple(order[: self.n_modelled])
        return self.modelled

    def robber_moves(self, robber: Cell) -> list[tuple[str, Cell]]:
        moves = []
        for a in ROBBER_ACTION_ORDER:
            nxt = apply_action(robber, a)
            if self.grid.is_passable(nxt):
                moves.append((a, nxt))
        # Deterministic ordering (identical for both algorithms): closest to the exit first.
        moves.sort(key=lambda m: self.eval.exit_steps.get(m[1], 10**6))
        return moves

    def police_moves(self, robber: Cell, police: tuple[Cell, ...]) -> list[tuple[str, tuple[Cell, ...]]]:
        per_officer = []
        for i in self.modelled:
            p = police[i]
            opts = [(STAY, p)] + [(a, apply_action(p, a)) for a in ACTIONS
                                  if self.grid.police_can_enter(apply_action(p, a))]
            opts.sort(key=lambda o: abs(o[1][0] - robber[0]) + abs(o[1][1] - robber[1]))
            per_officer.append(opts)
        joint = []
        for combo in itertools.product(*per_officer):
            new = list(police)
            for slot, (_, cell) in zip(self.modelled, combo):
                new[slot] = cell
            if len(set(new)) < len(new):          # two officers cannot share a cell
                continue
            label = ",".join(f"C{slot + 1}:{a[0]}" for slot, (a, _) in zip(self.modelled, combo))
            joint.append((label, tuple(new)))
        return joint or [("hold", police)]

    def evaluate(self, robber: Cell, police: tuple[Cell, ...]) -> float:
        return self.eval.evaluate(robber, police)

    @staticmethod
    def capture_value(ply: int) -> float:
        return -WIN_SCORE + ply

    @staticmethod
    def escape_value(ply: int) -> float:
        return WIN_SCORE - ply
