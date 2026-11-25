"""Tactical Command Center palette. Single source of truth for every colour."""

DEEP_NAVY = "#101C2C"      # main background
MIDNIGHT = "#16263A"       # sidebar
PANEL = "#20364D"          # cards and panels
TEAL = "#00B3A4"           # primary highlights
AQUA = "#36D9E8"           # active elements
CORAL = "#FF626B"          # police and danger
AMBER = "#FFB547"          # warnings
GREEN = "#37D69A"          # escape and success
ICE = "#F1F6FA"            # text
MUTED = "#8B9BAD"          # secondary text

# Derived tints (mixes of the palette above, used for grid layers)
PANEL_LIGHT = "#2A4561"
WALL = "#3B4A5C"
ROAD = "#1A2D42"
EXPLORED = "#2F7FD8"
FRONTIER = "#8FF0F7"
HAZARD = "#C8424B"
SAFE = "#0E7F78"

ALGO_COLORS = {"BFS": AQUA, "UCS": AMBER, "A*": GREEN, "Minimax": CORAL, "Alpha-Beta": TEAL}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=ICE, family="Inter, Segoe UI, sans-serif", size=12),
    margin=dict(l=40, r=16, t=40, b=36),
    xaxis=dict(gridcolor="rgba(139,155,173,0.15)", zerolinecolor="rgba(139,155,173,0.25)"),
    yaxis=dict(gridcolor="rgba(139,155,173,0.15)", zerolinecolor="rgba(139,155,173,0.25)"),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)
