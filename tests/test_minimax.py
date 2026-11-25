import pytest

from algorithms.alpha_beta import alphabeta_decision
from algorithms.minimax import minimax_decision
from environment.grid import Grid
from environment.map_generator import MapConfig, generate_environment
from heuristics.evaluation import EvalContext, EvalWeights


@pytest.mark.parametrize("depth", [1, 2, 3, 4])
def test_alphabeta_equals_minimax(depth):
    for seed in range(6):
        env = generate_environment(MapConfig(12, 12, 2, seed=seed))
        m = minimax_decision(env.grid, env.exit, env.robber, env.police, depth=depth)
        a = alphabeta_decision(env.grid, env.exit, env.robber, env.police, depth=depth)
        assert m.best_action == a.best_action
        assert abs(m.best_value - a.best_value) < 1e-9
        assert a.nodes_explored <= m.nodes_explored


def test_alphabeta_prunes_at_depth():
    env = generate_environment(MapConfig(15, 15, 2, seed=3))
    m = minimax_decision(env.grid, env.exit, env.robber, env.police, depth=4)
    a = alphabeta_decision(env.grid, env.exit, env.robber, env.police, depth=4)
    assert a.branches_pruned > 0 and a.nodes_explored < m.nodes_explored


def test_robber_takes_immediate_escape():
    g = Grid.from_strings(["....", "...."])
    r = alphabeta_decision(g, (0, 3), (0, 2), [(1, 0)], depth=2)
    assert r.best_action == "RIGHT" and r.best_value > 900


def test_robber_avoids_stepping_next_to_officer():
    g = Grid.from_strings([".....", ".....", "....."])
    # RIGHT puts the robber next to the officer → certain capture within depth 2.
    r = minimax_decision(g, (2, 4), (0, 1), [(0, 3)], depth=2, n_modelled=1)
    assert r.best_action != "RIGHT"
    assert r.child_values["RIGHT"] <= -900


def test_tree_recording_and_pruned_nodes():
    env = generate_environment(MapConfig(10, 10, 1, seed=2))
    a = alphabeta_decision(env.grid, env.exit, env.robber, env.police, depth=3, n_modelled=1, record_tree=True)
    assert a.tree and a.tree[0].action == "root"
    assert sum(1 for n in a.tree if n.pruned) == a.branches_pruned


def test_evaluation_contributions_sum():
    env = generate_environment(MapConfig(12, 12, 2, seed=1))
    ec = EvalContext(env.grid, env.exit, EvalWeights())
    contrib = ec.contributions(env.robber, tuple(env.police))
    assert abs(sum(contrib.values()) - ec.evaluate(env.robber, tuple(env.police))) < 1e-9
    assert set(contrib) == {"exit", "cop", "routes", "block", "risk"}
