"""Single turn-based game engine used by BOTH game modes.

Turn order (one call to `step`):
  1. Robber moves (human input or robber AI). Entering an officer's cell = capture.
  2. Police replan with predictive interception (dynamic replanning every turn).
  3. Police move one cell each (sequentially, never stacking on each other).
  4. Collision check → capture.
  5. Escape check   → robber on exit and not captured.
  6. Statistics update, turn-limit check.
Because the robber's move is resolved before the police move and entering an officer's cell
is itself a capture, the robber can never "swap" through an officer.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from agents import robber as robber_ai
from agents.police import PoliceTeam
from config import settings
from engine.collision import is_capture, is_escape
from engine.game_state import CAPTURED, ESCAPED, PAUSED, READY, RUNNING, TIMEOUT, GameState
from engine.movement import normalize_action, validate_police_move, validate_robber_move
from environment.state import Environment


@dataclass
class StepResult:
    ok: bool
    message: str = ""


class GameEngine:
    def __init__(self, env: Environment, mode: str = settings.MODE_AVA,
                 robber_algorithm: str = settings.DEFAULT_ROBBER_ALGORITHM,
                 minimax_depth: int = settings.DEFAULT_MINIMAX_DEPTH,
                 minimax_officers: int = settings.DEFAULT_MINIMAX_OFFICERS,
                 max_turns: int | None = None) -> None:
        problems = env.validate()
        if problems:
            raise ValueError(" ".join(problems))
        if mode not in settings.GAME_MODES:
            raise ValueError(f"Unknown game mode {mode!r}")
        if robber_algorithm not in settings.ROBBER_ALGORITHMS:
            raise ValueError(f"Unknown robber algorithm {robber_algorithm!r}")
        self.env = env.copy()
        self.grid = self.env.grid
        self.mode = mode
        self.robber_algorithm = robber_algorithm
        self.minimax_depth = minimax_depth
        self.minimax_officers = minimax_officers
        self.max_turns = max_turns or settings.default_max_turns(self.grid.rows, self.grid.cols)
        self.police_team = PoliceTeam()
        self.started_at = time.time()
        self.state = GameState(env.robber, list(env.police), env.exit,
                               trail=[env.robber], police_trails=[[p] for p in env.police])
        self._log("info", f"Game ready — {mode}, {len(env.police)} officer(s), "
                          f"{self.grid.rows}×{self.grid.cols} grid.")
        self._refresh_police_plan(log_changes=False)
        self._refresh_advisory()

    # ---------------------------------------------------------------- helpers
    def _log(self, kind: str, msg: str) -> None:
        self.state.log.append((self.state.turn, kind, msg))

    def _refresh_police_plan(self, log_changes: bool = True):
        s = self.state
        plan, changes = self.police_team.plan(self.grid, s.robber, s.exit, s.police)
        s.police_nodes += plan.nodes_expanded
        s.police_time_ms += plan.time_ms
        s.last_plan = plan
        if log_changes:
            for msg in changes:
                self._log("police", msg)
        return plan

    def _refresh_advisory(self) -> None:
        """A* advisory route for the human player (never applied automatically)."""
        s = self.state
        if self.mode != settings.MODE_PVA or s.is_over:
            s.advisory_path = []
            return
        res, _ = robber_ai.plan_escape(self.grid, s.robber, s.exit, s.police, "A*")
        s.advisory_path = res.path if res is not None and res.found else []

    # ---------------------------------------------------------------- control
    def start(self) -> None:
        if not self.state.is_over:
            self.state.status = RUNNING

    def pause(self) -> None:
        if self.state.status == RUNNING:
            self.state.status = PAUSED

    @property
    def is_over(self) -> bool:
        return self.state.is_over

    # ---------------------------------------------------------------- main step
    def step(self, human_action: str | None = None) -> StepResult:
        s = self.state
        if s.is_over:
            return StepResult(False, "The game is over — reset to play again.")

        # 1. Robber move
        if self.mode == settings.MODE_PVA:
            action = normalize_action(human_action)
            if action is None:
                return StepResult(False, "Use W/A/S/D, the arrow keys or the on-screen buttons to move.")
            ok, dest, msg = validate_robber_move(self.grid, s.robber, action)
            if not ok:
                return StepResult(False, msg)
            reason = "Player move."
        else:
            decision = robber_ai.decide(self.grid, s.robber, s.exit, s.police, self.robber_algorithm,
                                        self.minimax_depth, self.minimax_officers)
            s.robber_nodes += decision.nodes
            s.robber_time_ms += decision.time_ms
            s.last_robber_decision = decision
            action = decision.action
            ok, dest, msg = validate_robber_move(self.grid, s.robber, action)
            if not ok:  # defensive: AI must never make an illegal move
                return StepResult(False, f"Robber AI produced an invalid move: {msg}")
            reason = decision.reason

        if s.status in (READY, PAUSED) and self.mode == settings.MODE_PVA:
            s.status = RUNNING
        s.turn += 1
        s.robber = dest
        s.trail.append(dest)
        if action != "STAY":
            s.moves += 1
            s.robber_cost += self.grid.cost(dest)
        self._log("robber", f"Robber {'waited' if action == 'STAY' else 'moved ' + action} → {dest}. {reason}")

        if is_capture(s.robber, s.police):
            return self._finish(CAPTURED, f"Robber ran into an officer at {s.robber}. Captured!")

        # 2–3. Police replan and move
        plan = self._refresh_police_plan()
        self._log("police", f"Police replanned: robber predicted near {plan.predicted_position}.")
        new_positions = list(s.police)
        for d in plan.decisions:
            dest_p = d.next_cell
            occupied = set(new_positions[:d.officer] + new_positions[d.officer + 1:])
            if dest_p in occupied or not validate_police_move(self.grid, new_positions[d.officer], dest_p):
                dest_p = new_positions[d.officer]
            new_positions[d.officer] = dest_p
            s.police_trails[d.officer].append(dest_p)
        s.police = new_positions

        # 4. Collision, 5. escape
        if is_capture(s.robber, s.police):
            officer = s.police.index(s.robber) + 1
            return self._finish(CAPTURED, f"Officer {officer} captured the robber at {s.robber}.")
        if is_escape(s.robber, s.exit, s.police):
            return self._finish(ESCAPED, f"The robber reached the exit {s.exit} and escaped!")
        if s.turn >= self.max_turns:
            return self._finish(TIMEOUT, f"Turn limit {self.max_turns} reached — the police contained the robber.")

        self._refresh_advisory()
        return StepResult(True, "")

    def _finish(self, status: str, msg: str) -> StepResult:
        s = self.state
        s.status = status
        s.message = msg
        s.advisory_path = []
        self._log("end", msg)
        return StepResult(True, msg)

    def run_to_end(self, limit: int | None = None) -> GameState:
        """Run AI vs AI to completion (used by tests and quick simulations)."""
        steps = 0
        while not self.state.is_over and (limit is None or steps < limit):
            res = self.step()
            if not res.ok:
                break
            steps += 1
        return self.state

    # ---------------------------------------------------------------- reporting
    def summary(self) -> dict:
        s = self.state
        return {
            "mode": self.mode,
            "grid": f"{self.grid.rows}×{self.grid.cols}",
            "police": len(s.police),
            "algorithm": "Human" if self.mode == settings.MODE_PVA else self.robber_algorithm,
            "turns": s.turn,
            "moves": s.moves,
            "robber_cost": round(s.robber_cost, 2),
            "nodes_expanded": s.robber_nodes + s.police_nodes,
            "robber_nodes": s.robber_nodes,
            "police_nodes": s.police_nodes,
            "compute_ms": round(s.robber_time_ms + s.police_time_ms, 2),
            "outcome": s.status,
            "message": s.message,
            "trail": [list(c) for c in s.trail],
            "police_final": [list(c) for c in s.police],
            "env": self.env.to_dict(),
        }
