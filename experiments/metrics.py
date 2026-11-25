"""Derived metrics and plain-language explanations computed from real results."""
from __future__ import annotations

from algorithms.base import SearchResult


def optimality_label(res: SearchResult, optimal_cost: float | None) -> str:
    if not res.found:
        return "No path"
    if optimal_cost is None:
        return "—"
    if abs(res.cost - optimal_cost) < 1e-9:
        return "Optimal"
    return f"Suboptimal (+{res.cost - optimal_cost:g})"


def explain(results: dict[str, SearchResult]) -> list[str]:
    """Generate observations strictly from the measured numbers."""
    notes: list[str] = []
    bfs, ucs, ast = results.get("BFS"), results.get("UCS"), results.get("A*")
    if not all(r and r.found for r in (bfs, ucs, ast)):
        missing = [k for k, r in results.items() if not r.found]
        if missing:
            notes.append(f"No path exists for {', '.join(missing)}: the exit is unreachable with the blocked cells.")
        return notes
    if bfs.cost > ucs.cost:
        notes.append(f"BFS found a route with the fewest moves ({bfs.path_length}) but it costs {bfs.cost:g} vs. "
                     f"the optimal {ucs.cost:g}: BFS ignores terrain cost and crossed expensive cells.")
    else:
        notes.append(f"BFS matched the optimal cost ({ucs.cost:g}) — its fewest-moves route happened to avoid "
                     f"expensive terrain here.")
    if abs(ast.cost - ucs.cost) < 1e-9:
        notes.append(f"A* and UCS both returned the optimal cost {ucs.cost:g}, as expected with an admissible, "
                     f"consistent heuristic.")
    if ucs.nodes_expanded:
        saved = 100 * (1 - ast.nodes_expanded / ucs.nodes_expanded)
        if saved > 0:
            notes.append(f"A* expanded {ast.nodes_expanded} nodes vs. {ucs.nodes_expanded} for UCS ({saved:.0f}% fewer): "
                         f"the Manhattan heuristic focuses the search towards the exit.")
        else:
            notes.append(f"A* expanded {ast.nodes_expanded} nodes vs. {ucs.nodes_expanded} for UCS: obstacles or "
                         f"terrain made the heuristic weak (the straight line is not the cheap route).")
    if ucs.path_length > bfs.path_length:
        notes.append(f"The cost-optimal route is {ucs.path_length - bfs.path_length} moves longer than BFS's: "
                     f"detours around difficult/hazard cells are cheaper overall.")
    return notes
