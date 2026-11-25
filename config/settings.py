"""Global, Streamlit-independent configuration values."""
from __future__ import annotations

from pathlib import Path

APP_NAME = "COPS & ROBBERS"
APP_SUBTITLE = "Intelligent Pursuit and Strategic Escape"
TAGLINE = "Outthink the pursuit. Outsmart the escape."

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
HISTORY_FILE = DATA_DIR / "history.json"

# Grid
DEFAULT_ROWS = 30
DEFAULT_COLS = 30
MIN_DIM = 5
MAX_DIM = 60
GRID_PRESETS = {
    "10 × 10": (10, 10),
    "15 × 15": (15, 15),
    "20 × 20": (20, 20),
    "25 × 25": (25, 25),
    "30 × 30": (30, 30),
    "40 × 40": (40, 40),
    "50 × 50": (50, 50),
}

# Police
DEFAULT_POLICE = 2
MIN_POLICE = 1
MAX_POLICE = 8

# Map generation defaults (fractions of all cells)
DEFAULT_WALL_DENSITY = 0.20
DEFAULT_DIFFICULT_DENSITY = 0.07
DEFAULT_HAZARD_DENSITY = 0.03
DEFAULT_SAFE_DENSITY = 0.02

# Game
MODE_PVA = "Player vs AI"
MODE_AVA = "AI vs AI"
GAME_MODES = (MODE_PVA, MODE_AVA)
ROBBER_ALGORITHMS = ("A*", "UCS", "BFS", "Minimax", "Alpha-Beta")
SEARCH_ALGORITHMS = ("BFS", "UCS", "A*")
DEFAULT_ROBBER_ALGORITHM = "A*"
DEFAULT_MINIMAX_DEPTH = 4          # plies (robber, police, robber, police)
DEFAULT_MINIMAX_OFFICERS = 2       # nearest officers modelled as the MIN player

# Turn limit: the police win by containment if the robber has not escaped.
def default_max_turns(rows: int, cols: int) -> int:
    return max(60, 3 * (rows + cols))
