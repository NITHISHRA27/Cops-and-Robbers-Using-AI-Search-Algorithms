"""Predefined experiment environments. All are generated deterministically from a seed."""
from __future__ import annotations

import random

from environment.grid import Grid
from environment.map_generator import MapConfig, generate_environment, place_police
from environment.state import Environment
from environment.terrain import CostModel, Terrain

SCENARIOS = {
    "Open city grid": "Few buildings, uniform roads. All three algorithms find equally short routes; "
                      "the difference is how many cells they examine.",
    "Obstacle-heavy city": "Dense buildings force detours. Heuristic guidance matters less when the "
                           "straight line is blocked.",
    "Weighted terrain": "Large difficult and hazardous zones. BFS counts moves only, so it walks straight "
                        "through expensive terrain; UCS and A* go around it.",
    "Narrow corridors": "Walls with single gaps create a maze of corridors — long detours for everyone.",
    "Multiple escape routes": "A central block splits the city: a short route through hazards and a longer "
                              "clean road. Shows the move-count vs. cost trade-off.",
    "Police near the robber": "Officers start a few moves from the robber; their cells are blocked, "
                              "forcing an immediate detour.",
    "Exit surrounded by difficult terrain": "The exit sits inside a ring of difficult terrain with a single "
                                            "cheaper gap that cost-aware search finds.",
}


def _env_from_grid(grid: Grid, robber, exit_, n_police: int, seed: int, gap: int | None = None) -> Environment:
    for cell in (robber, exit_):
        grid.set_terrain(cell, Terrain.ROAD)
    police = place_police(grid, robber, exit_, n_police, random.Random(seed), min_gap=gap)
    env = Environment(grid, robber, exit_, police)
    problems = env.validate()
    if problems:
        raise ValueError(" ".join(problems))
    return env


def build_scenario(name: str, rows: int = 30, cols: int = 30, n_police: int = 2, seed: int = 11,
                   costs: CostModel | None = None) -> Environment:
    costs = costs or CostModel()
    rng = random.Random(seed)
    if name == "Open city grid":
        return generate_environment(MapConfig(rows, cols, n_police, 0.05, 0.0, 0.0, 0.0, seed, costs))
    if name == "Obstacle-heavy city":
        return generate_environment(MapConfig(rows, cols, n_police, 0.36, 0.03, 0.01, 0.0, seed, costs))
    if name == "Weighted terrain":
        return generate_environment(MapConfig(rows, cols, n_police, 0.10, 0.26, 0.10, 0.02, seed, costs))
    if name == "Police near the robber":
        env = generate_environment(MapConfig(rows, cols, n_police, 0.18, 0.06, 0.03, 0.0, seed, costs))
        return _env_from_grid(env.grid, env.robber, env.exit, n_police, seed, gap=2)

    grid = Grid(rows, cols, cost_model=costs)
    if name == "Narrow corridors":
        for r in range(2, rows - 1, 3):
            gaps = {rng.randrange(cols)}
            if rng.random() < 0.35:
                gaps.add(rng.randrange(cols))
            for c in range(cols):
                if c not in gaps:
                    grid.cells[r][c] = Terrain.WALL
        for _ in range(int(rows * cols * 0.04)):
            r, c = rng.randrange(rows), rng.randrange(cols)
            if grid.cells[r][c] == Terrain.ROAD:
                grid.cells[r][c] = Terrain.DIFFICULT
        return _env_from_grid(grid, (0, 0), (rows - 1, cols - 1), n_police, seed)
    if name == "Multiple escape routes":
        r0, r1 = rows // 4, rows - rows // 4
        c0, c1 = cols // 4, cols - cols // 4
        for r in range(r0, r1):
            for c in range(c0, c1):
                grid.cells[r][c] = Terrain.WALL
        # Short diagonal-side route (upper/right) is hazardous; the long side is clean road.
        for c in range(c0, cols):
            for r in range(max(0, r0 - 2), r0):
                grid.cells[r][c] = Terrain.HAZARD
        for _ in range(int(rows * cols * 0.05)):
            r, c = rng.randrange(rows), rng.randrange(cols)
            if grid.cells[r][c] == Terrain.ROAD and not (r0 - 3 <= r <= r1 + 2 and c0 - 3 <= c <= c1 + 2):
                grid.cells[r][c] = Terrain.WALL
        return _env_from_grid(grid, (rows // 2, 0), (rows // 2, cols - 1), n_police, seed)
    if name == "Exit surrounded by difficult terrain":
        env = generate_environment(MapConfig(rows, cols, n_police, 0.15, 0.03, 0.02, 0.0, seed, costs))
        g = env.grid
        er, ec = env.exit
        radius = max(2, min(rows, cols) // 7)
        gap_dir = rng.choice([(-1, 0), (0, -1)])
        for r in range(rows):
            for c in range(cols):
                d = abs(r - er) + abs(c - ec)
                if 0 < d <= radius and g.cells[r][c] != Terrain.WALL:
                    g.cells[r][c] = Terrain.DIFFICULT
        # one cheap corridor in
        r, c = er, ec
        for _ in range(radius):
            r, c = r + gap_dir[0], c + gap_dir[1]
            if g.in_bounds((r, c)):
                g.cells[r][c] = Terrain.ROAD
        return _env_from_grid(g, env.robber, env.exit, n_police, seed)
    raise ValueError(f"Unknown scenario {name!r}")
