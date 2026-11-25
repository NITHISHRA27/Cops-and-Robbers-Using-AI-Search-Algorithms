import pytest

from config import settings
from engine.game_engine import GameEngine
from environment.grid import Grid
from environment.map_generator import MapConfig, generate_environment
from environment.state import Environment


def test_human_cannot_walk_into_wall_or_off_grid():
    g = Grid.from_strings([".#..", "....", "...."])
    eng = GameEngine(Environment(g, (0, 0), (2, 3), [(2, 0)]), mode=settings.MODE_PVA)
    assert not eng.step("RIGHT").ok        # wall
    assert not eng.step("UP").ok           # off grid
    assert not eng.step("w").ok            # key alias, still off grid
    assert eng.state.turn == 0


def test_walking_into_officer_is_capture():
    g = Grid.from_strings(["....", "...."])
    eng = GameEngine(Environment(g, (0, 0), (1, 3), [(0, 1)]), mode=settings.MODE_PVA)
    eng.step("RIGHT")
    assert eng.state.status == "captured"
    assert not eng.step("DOWN").ok          # cannot continue after the game ends


def test_adjacent_officer_captures_after_robber_moves():
    g = Grid.from_strings([".....", "....."])
    eng = GameEngine(Environment(g, (0, 0), (1, 4), [(0, 2)]), mode=settings.MODE_PVA)
    eng.step("RIGHT")                       # robber steps next to the officer at (0,2)
    assert eng.state.status == "captured"   # officer moves onto the robber in the same turn
    assert eng.state.police == [(0, 1)]


def test_escape_detected():
    g = Grid.from_strings(["...", "...", "..."])
    eng = GameEngine(Environment(g, (0, 1), (0, 2), [(2, 0)]), mode=settings.MODE_PVA)
    eng.step("RIGHT")
    assert eng.state.status == "escaped"


@pytest.mark.parametrize("algo", settings.ROBBER_ALGORITHMS)
def test_ai_vs_ai_terminates_for_every_robber_algorithm(algo):
    env = generate_environment(MapConfig(12, 12, 2, seed=5))
    eng = GameEngine(env, robber_algorithm=algo, minimax_depth=2)
    state = eng.run_to_end()
    assert state.is_over
    assert state.status in ("escaped", "captured", "timeout")
    assert state.robber_nodes > 0 and state.police_nodes > 0
    for a, b in zip(state.trail, state.trail[1:]):
        assert abs(a[0] - b[0]) + abs(a[1] - b[1]) <= 1 and env.grid.is_passable(b)


def test_police_never_stack_or_enter_walls():
    env = generate_environment(MapConfig(20, 20, 6, seed=2))
    eng = GameEngine(env)
    for _ in range(40):
        if eng.is_over:
            break
        eng.step()
        assert len(set(eng.state.police)) == len(eng.state.police)
        for p in eng.state.police:
            assert env.grid.police_can_enter(p)


def test_advisory_path_only_in_human_mode():
    env = generate_environment(MapConfig(15, 15, 1, seed=1))
    assert GameEngine(env, mode=settings.MODE_PVA).state.advisory_path
    assert not GameEngine(env, mode=settings.MODE_AVA).state.advisory_path


def test_summary_contains_history_fields():
    env = generate_environment(MapConfig(10, 10, 1, seed=1))
    eng = GameEngine(env)
    eng.run_to_end()
    s = eng.summary()
    for k in ("mode", "grid", "police", "algorithm", "turns", "nodes_expanded", "outcome", "compute_ms"):
        assert k in s
    assert s["outcome"] in ("escaped", "captured", "timeout")


def test_different_grid_sizes_run():
    for rows, cols in ((10, 10), (25, 40), (50, 50)):
        env = generate_environment(MapConfig(rows, cols, 3, seed=6))
        eng = GameEngine(env)
        for _ in range(5):
            eng.step()
        assert eng.state.turn >= 1
