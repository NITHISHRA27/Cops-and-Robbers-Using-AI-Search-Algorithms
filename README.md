# COPS & ROBBERS — Intelligent Pursuit and Strategic Escape

> *Outthink the pursuit. Outsmart the escape.*

25AM2304 – Artificial Intelligence · Mini-project · **Game AI (Search-Based)**

An interactive pursuit-and-escape game on a customisable city grid. A robber tries to reach an
exit; police officers use **predictive interception** to cut it off. The project implements and
compares the mandatory search algorithms **BFS, UCS and A\*** and adds **Minimax** and
**Alpha-Beta pruning** as the optional advanced extension. Every number in the app comes from a
real algorithm run. Nothing is hard-coded.

---

## Quick start (Windows)

```powershell
cd COPS_AND_ROBBERS
python -m pip install -r requirements.txt
streamlit run app.py
```

Or double-click **`run_app.bat`**. The app opens at <http://localhost:8501>.

Run the tests:

```powershell
python -m pytest -q
```

**Requirements:** Python 3.11+, Streamlit ≥ 1.40, Plotly, pandas, pytest (see `requirements.txt`).

---

## Technology stack

| Layer | Technology |
|---|---|
| UI | Streamlit multipage app (`st.navigation`), custom CSS (tactical command-center theme) |
| Grid & input | A custom bidirectional Streamlit component (`components/board/index.html`) that renders the SVG grid and captures keyboard and mouse input |
| Algorithm playback | A client-side HTML/JS player that replays the **recorded** expansion events |
| Charts | Plotly |
| Logic | Pure Python 3.11, no pathfinding libraries, independent of Streamlit |
| Tests | pytest (unit and integration) |

---

## How to play

1. **Game Configuration**: choose a grid size (default **30 × 30**, presets up to 50 × 50 or custom
   rows/columns), the number of officers (**1–8**, default 2), the game mode and terrain densities.
   Edit the map by clicking or dragging (walls, terrain, robber, exit, officers).
2. **Live Simulation**
   - **Player vs AI**: move the robber with **W A S D / arrow keys** (Space = wait) or the
     on-screen pad. A dashed **A\* advisory route** is shown; you are free to ignore it.
   - **AI vs AI**: pick the robber's algorithm (A\*, UCS, BFS, Minimax, Alpha-Beta), then use
     Start / Pause / Resume / Next turn / Reset and the speed slider.
3. The robber **wins** by reaching the exit. The police **win** by capturing it, or by containing it
   until the turn limit (3 × (rows + cols)). Finished games are saved to `data/history.json`.

| Key | Action |
|---|---|
| W / ↑ | Move up |
| S / ↓ | Move down |
| A / ← | Move left |
| D / → | Move right |
| Space | Wait one turn |

Keys are only captured while the board is armed (a green dot). They are ignored while typing in an
input field, and they never scroll the page.

---

## Problem formulation

| Element | Definition |
|---|---|
| **Static state** (pathfinding) | `S = (r, c)`, a grid cell |
| **Dynamic state** (game) | `S = (R, C1 … Cn, E, t)`: robber, officers, exit, turn |
| **Actions** | UP, DOWN, LEFT, RIGHT (plus WAIT in the game) |
| **Transition model** | Move to the adjacent cell if it is inside the grid and not a wall. Police may not enter safe zones |
| **Goal test** | Robber: `R = E` and not captured. Police: an officer occupies `R` |
| **Step cost** | Cost of the **destination** terrain: road 1, difficult 3, hazard 5, safe 1 (configurable). Walls are impassable |
| **Path cost** | `g(n') = g(n) + cost(n')` |

Path **costs** (BFS/UCS/A\*) are kept separate from game **evaluation scores** (Minimax/Alpha-Beta).

**Turn order:** robber moves → police replan → police move → capture check → escape check →
statistics. A robber that walks into an officer is captured immediately, so it can never "swap"
through an officer.

---

## Algorithms

| | Frontier | Optimal? | Notes |
|---|---|---|---|
| **BFS** | FIFO queue | Fewest **moves** only | Early goal test. Ignores terrain cost, so on weighted maps it walks through hazards |
| **UCS** | Binary heap on `g(n)` | Least **cost** | Lazy-deletion priority updates. Goal test on expansion |
| **A\*** | Binary heap on `f = g + h` | Least **cost** | `h = min_cost × Manhattan`, which is admissible and consistent. Ties broken towards lower `h` |
| **Minimax** | Depth-limited game tree | Best worst-case | Robber = MAX. The police (MIN) move the k nearest officers jointly |
| **Alpha-Beta** | Same tree with pruning | Same decision as Minimax | Verified identical on every test position |

### A\* in the pursuit-and-escape game

- **AI robber:** replans an A\* route to the exit every turn. Officer cells are blocked and nearby
  cells carry a non-negative danger penalty, which keeps the heuristic admissible.
- **Police:** predict the robber's likely route with A\* (plus an alternative route), find the
  **interceptable** cells (an officer's step distance ≤ the robber's step index), and route there
  with A\*.
- **Human mode:** A\* is advisory only. It never overrides the player.
- The Performance Arena compares A\* with BFS and UCS on **identical** environments (same start,
  goal, walls, terrain and blocked cells; median of repeated timings) across 7 predefined scenarios
  plus custom maps.

### Police coordination (predictive interception)

Roles are assigned so that officers do not duplicate effort: **Direct pursuit**, **Exit
interception**, **Corridor blocking** (choke points with ≤ 2 exits), **Secondary interception**
(the alternative route) and **Perimeter guard**. Plans are recomputed every turn (dynamic
replanning). Target changes appear in the event log, and each officer's role, target, interception
cell, route and reason appear in the Tactical Intelligence panel. Predictions are labelled as
estimates.

### Evaluation function (Minimax / Alpha-Beta)

```
E(s) = −10·d_exit + 6·min(d_cop, 6) + 3·routes + 5·race − 40·risk
terminal: escape = +1000 − ply, capture = −1000 + ply
```

| Term | Weight | Why |
|---|---|---|
| Escape distance (real BFS moves) | 10 | The goal. One step of progress is the reference unit |
| Cop proximity (capped at 6) | 6 | Below 10, so the robber trades a little safety for progress. The cap stops it fleeing forever |
| Escape routes (open, unthreatened neighbours) | 3 | Tie-breaker against dead ends. At most 12 points, which is about one step |
| Exit blocking (race margin, ±5) | 5 | If a cop reaches the exit first, that route is lost (up to 25 points) |
| Capture risk (cops within 1 move) | 40 | Outweighs any positional gain but stays far below the ±1000 terminal scores |

All weights can be changed on the **Strategic AI** page, which also shows each factor's contribution.

---

## Application sections

1. **Command Center**: live statistics, mini-map, measured algorithm cards, insights
2. **Game Configuration**: grid, officers, modes, terrain, costs, map editor, validation
3. **Live Simulation**: gameplay, controls, live stats, tactical intelligence, event log
4. **Algorithm Laboratory**: step-by-step replay of real BFS/UCS/A\* traces (frontier/queue, g/h/f)
5. **Heuristic Explorer**: click any cell for h, h\*, g and f. Heatmaps, admissibility and consistency checks, heuristic comparison
6. **Performance Arena**: comparison table, 4 charts, 7 scenarios, batch runs, CSV export
7. **Strategic AI**: Minimax vs Alpha-Beta, game tree with α/β and pruned nodes, depth sweep
8. **Game History**: saved games, filters, replay trail, export, reset with confirmation

---

## Project structure

```
COPS_AND_ROBBERS/
├── app.py                  # Streamlit entry point: navigation and wiring only
├── run_app.bat             # Windows launcher
├── config/                 # settings.py, theme.py (palette)
├── environment/            # grid.py, terrain.py, map_generator.py, state.py
├── algorithms/             # base.py, bfs.py, ucs.py, astar.py, adversarial.py, minimax.py, alpha_beta.py
├── heuristics/             # manhattan.py (+ admissibility/consistency checks), evaluation.py
├── agents/                 # robber.py, police.py, interception.py
├── engine/                 # game_engine.py, game_state.py, movement.py, collision.py
├── experiments/            # benchmark.py, scenarios.py, metrics.py
├── persistence/            # history.py (JSON storage)
├── visualization/          # grid_renderer.py (SVG), charts.py (Plotly), animation.py (trace player)
├── components/board/       # custom Streamlit component (keyboard + click + paint)
├── interface/              # one module per page + ui.py (theme, state, widgets)
├── data/history.json
└── tests/                  # pytest suite
```

Algorithms, agents and the engine never import Streamlit, so they can be tested and reused on their own.
