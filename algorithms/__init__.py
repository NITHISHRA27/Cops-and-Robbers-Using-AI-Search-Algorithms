"""Search algorithm registry. All algorithms are pure Python and independent of Streamlit."""
from __future__ import annotations

from algorithms.astar import astar
from algorithms.base import SearchContext, SearchResult
from algorithms.bfs import bfs
from algorithms.ucs import ucs

SEARCHERS = {"BFS": bfs, "UCS": ucs, "A*": astar}


def run_search(name: str, ctx: SearchContext, start, goal, record: bool = False) -> SearchResult:
    try:
        fn = SEARCHERS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown search algorithm {name!r}; choose from {list(SEARCHERS)}") from exc
    return fn(ctx, start, goal, record=record)


__all__ = ["SEARCHERS", "run_search", "SearchContext", "SearchResult", "bfs", "ucs", "astar"]
