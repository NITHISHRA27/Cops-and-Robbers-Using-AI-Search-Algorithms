import pytest

from environment.grid import Grid, action_between, apply_action
from environment.map_generator import MapConfig, generate_environment
from environment.state import Environment
from environment.terrain import CostModel


def test_neighbors_respect_walls_and_bounds():
    g = Grid.from_strings([".#.", "...", "..."])
    assert list(g.neighbors((0, 0))) == [(1, 0)]
    assert set(g.neighbors((1, 1))) == {(2, 1), (1, 0), (1, 2)}


def test_police_cannot_enter_safe_zone():
    g = Grid.from_strings([".s.", "..."])
    assert (0, 1) in set(g.neighbors((0, 0)))
    assert (0, 1) not in set(g.neighbors((0, 0), police=True))


def test_costs_and_validation():
    g = Grid.from_strings([".~!s#"])
    assert [g.cost((0, c)) for c in range(4)] == [1, 3, 5, 1]
    assert g.cost((0, 4)) == float("inf")
    with pytest.raises(ValueError):
        CostModel(road=0)


def test_actions_roundtrip():
    assert apply_action((2, 2), "UP") == (1, 2)
    assert action_between((2, 2), (2, 3)) == "RIGHT"


@pytest.mark.parametrize("rows,cols,police", [(10, 10, 1), (30, 30, 2), (15, 40, 8), (50, 50, 4)])
def test_generator_produces_valid_maps(rows, cols, police):
    env = generate_environment(MapConfig(rows, cols, police, seed=3))
    assert env.validate() == []
    assert env.grid.rows == rows and env.grid.cols == cols
    assert len(env.police) == police
    assert len(set(env.police)) == police


def test_environment_validation_messages():
    g = Grid.from_strings(["..#", "...", "..."])
    env = Environment(g, (0, 0), (0, 2), [(0, 0)])
    errors = env.validate()
    assert any("wall" in e for e in errors)
    assert any("overlaps the robber" in e for e in errors)


def test_invalid_config_rejected():
    with pytest.raises(ValueError):
        generate_environment(MapConfig(rows=3, cols=3))
    with pytest.raises(ValueError):
        generate_environment(MapConfig(n_police=9))


def test_roundtrip_serialisation():
    env = generate_environment(MapConfig(12, 14, 3, seed=1))
    again = Environment.from_dict(env.to_dict())
    assert again.grid.cells == env.grid.cells and again.police == env.police
