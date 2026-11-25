from algorithms.bfs import bfs
from tests.helpers import ctx


def test_bfs_shortest_moves_open_grid():
    c = ctx(["....", "....", "...."])
    r = bfs(c, (0, 0), (2, 3))
    assert r.found and r.path_length == 5
    assert r.path[0] == (0, 0) and r.path[-1] == (2, 3)


def test_bfs_path_is_contiguous_and_avoids_walls():
    c = ctx([".#..", ".#.#", "...."])
    r = bfs(c, (0, 0), (0, 2))
    assert r.found
    for a, b in zip(r.path, r.path[1:]):
        assert abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1
        assert c.grid.is_passable(b)


def test_bfs_unreachable():
    c = ctx([".#.", "##.", "..."])
    r = bfs(c, (0, 0), (2, 2))
    assert not r.found and r.path == []


def test_bfs_start_equals_goal_and_records_events():
    c = ctx(["..."])
    assert bfs(c, (0, 1), (0, 1)).cost == 0
    r = bfs(c, (0, 0), (0, 2), record=True)
    assert r.events and r.nodes_expanded == len(r.events)


def test_bfs_ignores_cost():
    # Straight through a hazard: 2 moves, cost 5 + 1 = 6 (the 4-move detour would cost 4)
    c = ctx([".!.", "...", "..."])
    r = bfs(c, (0, 0), (0, 2))
    assert r.path_length == 2 and r.cost == 6
