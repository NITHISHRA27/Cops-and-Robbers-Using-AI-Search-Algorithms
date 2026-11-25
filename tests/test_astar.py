from algorithms.astar import astar
from algorithms.base import SearchContext
from algorithms.ucs import ucs
from environment.map_generator import MapConfig, generate_environment
from environment.terrain import CostModel
from heuristics.manhattan import check_admissible, check_consistent, manhattan, weighted_manhattan
from tests.helpers import ctx


def test_manhattan():
    assert manhattan((0, 0), (3, 4)) == 7
    assert weighted_manhattan((0, 0), (3, 4), 2) == 14


def test_astar_matches_ucs_cost_and_expands_no_more():
    for seed in range(10):
        env = generate_environment(MapConfig(25, 25, 1, 0.18, 0.12, 0.05, 0.02, seed))
        c = SearchContext(env.grid)
        a, u = astar(c, env.robber, env.exit), ucs(c, env.robber, env.exit)
        assert a.found and u.found
        assert abs(a.cost - u.cost) < 1e-9
        assert a.nodes_expanded <= u.nodes_expanded


def test_astar_open_grid_is_focused():
    c = ctx(["." * 20] * 20)
    a = astar(c, (0, 0), (19, 19))
    u = ucs(c, (0, 0), (19, 19))
    assert a.cost == 38 and a.nodes_expanded < u.nodes_expanded


def test_heuristic_admissible_and_consistent_with_custom_costs():
    env = generate_environment(MapConfig(20, 20, 1, 0.15, 0.2, 0.1, 0.05, 4, CostModel(2, 4, 7, 2)))
    ok, n, worst = check_admissible(env.grid, env.exit)
    assert ok and n > 0 and worst <= 1
    assert check_consistent(env.grid, env.exit)[0]


def test_astar_with_extra_cost_still_optimal():
    env = generate_environment(MapConfig(20, 20, 1, 0.15, 0.1, 0.05, 0.0, 9))
    c = SearchContext(env.grid, extra_cost=lambda cell: 2.0 if (cell[0] + cell[1]) % 3 == 0 else 0.0)
    assert abs(astar(c, env.robber, env.exit).cost - ucs(c, env.robber, env.exit).cost) < 1e-9


def test_astar_unreachable():
    c = ctx([".#.", "##.", "..."])
    assert not astar(c, (0, 0), (2, 2)).found
