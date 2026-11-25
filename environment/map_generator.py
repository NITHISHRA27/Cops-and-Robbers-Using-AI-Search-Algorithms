"""Random city-map generation with guaranteed robber→exit reachability."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from config import settings
from environment.grid import ACTIONS, Cell, Grid
from environment.state import Environment
from environment.terrain import CostModel, Terrain


@dataclass
class MapConfig:
    rows: int = settings.DEFAULT_ROWS
    cols: int = settings.DEFAULT_COLS
    n_police: int = settings.DEFAULT_POLICE
    wall_density: float = settings.DEFAULT_WALL_DENSITY
    difficult_density: float = settings.DEFAULT_DIFFICULT_DENSITY
    hazard_density: float = settings.DEFAULT_HAZARD_DENSITY
    safe_density: float = settings.DEFAULT_SAFE_DENSITY
    seed: int | None = 7
    costs: CostModel = field(default_factory=CostModel)

    def validate(self) -> list[str]:
        errs = []
        for name, v in (("Rows", self.rows), ("Columns", self.cols)):
            if not settings.MIN_DIM <= v <= settings.MAX_DIM:
                errs.append(f"{name} must be between {settings.MIN_DIM} and {settings.MAX_DIM}.")
        if not settings.MIN_POLICE <= self.n_police <= settings.MAX_POLICE:
            errs.append(f"Police count must be between {settings.MIN_POLICE} and {settings.MAX_POLICE}.")
        total = self.wall_density + self.difficult_density + self.hazard_density + self.safe_density
        if total > 0.75:
            errs.append("Combined terrain densities exceed 75% of the map — lower some sliders.")
        if not 0 <= self.wall_density <= 0.45:
            errs.append("Wall density must be between 0% and 45%.")
        return errs


def _carve_path(grid: Grid, a: Cell, b: Cell, rng: random.Random) -> None:
    """Remove walls along a random monotone Manhattan route from a to b."""
    r, c = a
    while (r, c) != b:
        moves = []
        if r != b[0]:
            moves.append((1 if b[0] > r else -1, 0))
        if c != b[1]:
            moves.append((0, 1 if b[1] > c else -1))
        dr, dc = rng.choice(moves)
        r, c = r + dr, c + dc
        if grid.terrain((r, c)) == Terrain.WALL:
            grid.set_terrain((r, c), Terrain.ROAD)


def _blob(grid: Grid, rng: random.Random, terrain: Terrain, budget: int, max_size: int,
          protected: set[Cell]) -> None:
    """Grow random-walk clusters of a terrain type on road cells."""
    placed, attempts = 0, 0
    while placed < budget and attempts < budget * 20:
        attempts += 1
        cur = (rng.randrange(grid.rows), rng.randrange(grid.cols))
        size = rng.randint(1, max_size)
        for _ in range(size):
            if placed >= budget:
                break
            if grid.in_bounds(cur) and grid.terrain(cur) == Terrain.ROAD and cur not in protected:
                grid.set_terrain(cur, terrain)
                placed += 1
            dr, dc = rng.choice(list(ACTIONS.values()))
            cur = (cur[0] + dr, cur[1] + dc)


def _corner_cell(grid: Grid, rng: random.Random, top_left: bool) -> Cell:
    span_r, span_c = max(1, grid.rows // 5), max(1, grid.cols // 5)
    if top_left:
        return rng.randrange(0, span_r), rng.randrange(0, span_c)
    return grid.rows - 1 - rng.randrange(0, span_r), grid.cols - 1 - rng.randrange(0, span_c)


def place_police(grid: Grid, robber: Cell, exit_: Cell, n: int, rng: random.Random,
                 min_gap: int | None = None) -> list[Cell]:
    """Spread officers across the robber's component, away from the robber."""
    dist_r = grid.step_distances(robber)
    candidates = [c for c in dist_r if c not in (robber, exit_) and grid.police_can_enter(c)]
    if len(candidates) < n:
        raise ValueError("Not enough free cells to place every police officer.")
    gap = min_gap if min_gap is not None else max(4, (grid.rows + grid.cols) // 4)
    far = [c for c in candidates if dist_r[c] >= gap] or candidates
    chosen: list[Cell] = []
    rng.shuffle(far)
    # First officer: midway between robber and exit along the step metric (a natural chase start).
    far.sort(key=lambda c: abs(dist_r[c] - dist_r.get(exit_, 0) * 0.6))
    chosen.append(far[0])
    while len(chosen) < n:
        pool = [c for c in far if c not in chosen] or [c for c in candidates if c not in chosen]
        best = max(pool, key=lambda c: (min(abs(c[0] - p[0]) + abs(c[1] - p[1]) for p in chosen), rng.random()))
        chosen.append(best)
    return chosen


def generate_environment(cfg: MapConfig) -> Environment:
    errors = cfg.validate()
    if errors:
        raise ValueError(" ".join(errors))
    rng = random.Random(cfg.seed)
    grid = Grid(cfg.rows, cfg.cols, cost_model=cfg.costs)
    total = cfg.rows * cfg.cols
    robber = _corner_cell(grid, rng, top_left=True)
    exit_ = _corner_cell(grid, rng, top_left=False)
    protected = {robber, exit_}

    # Buildings: small rectangles, the characteristic city-block look.
    target_walls = int(total * cfg.wall_density)
    walls, attempts = 0, 0
    while walls < target_walls and attempts < total * 4:
        attempts += 1
        h, w = rng.randint(1, 3), rng.randint(1, 3)
        r0, c0 = rng.randrange(cfg.rows), rng.randrange(cfg.cols)
        for r in range(r0, min(cfg.rows, r0 + h)):
            for c in range(c0, min(cfg.cols, c0 + w)):
                if walls >= target_walls:
                    break
                if (r, c) not in protected and grid.cells[r][c] == Terrain.ROAD:
                    grid.cells[r][c] = Terrain.WALL
                    walls += 1

    if not grid.is_reachable(robber, exit_):
        _carve_path(grid, robber, exit_, rng)

    _blob(grid, rng, Terrain.DIFFICULT, int(total * cfg.difficult_density), 6, protected)
    _blob(grid, rng, Terrain.HAZARD, int(total * cfg.hazard_density), 2, protected)
    _blob(grid, rng, Terrain.SAFE, int(total * cfg.safe_density), 3, protected)

    police = place_police(grid, robber, exit_, cfg.n_police, rng)
    env = Environment(grid, robber, exit_, police)
    problems = env.validate()
    if problems:  # extremely unlikely after carving; surface clearly rather than silently
        raise ValueError("Generated map is invalid: " + " ".join(problems))
    return env


def empty_environment(rows: int, cols: int, n_police: int = 1, costs: CostModel | None = None) -> Environment:
    grid = Grid(rows, cols, cost_model=costs or CostModel())
    robber, exit_ = (0, 0), (rows - 1, cols - 1)
    police = place_police(grid, robber, exit_, n_police, random.Random(0))
    return Environment(grid, robber, exit_, police)
