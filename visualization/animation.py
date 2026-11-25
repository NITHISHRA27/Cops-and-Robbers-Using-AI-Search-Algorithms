"""Client-side playback of a REAL search trace (events recorded by the algorithm itself).

The Python algorithm runs once with record=True; this player only replays its expansion
events in the browser so Start/Pause/Resume/Step/Reset/speed are instant and smooth.
"""
from __future__ import annotations

import json

from algorithms.base import SearchResult
from config import theme as T


def search_player_html(base_svg: str, result: SearchResult, rows: int, cols: int, cell: int,
                       height: int) -> str:
    payload = {
        "events": result.events,
        "path": [list(c) for c in result.path],
        "found": result.found,
        "algo": result.algorithm,
        "cost": result.cost if result.found else None,
        "expanded": result.nodes_expanded,
        "time": round(result.time_ms, 3),
        "rows": rows, "cols": cols, "s": cell,
        "start": list(result.start), "goal": list(result.goal),
    }
    data = json.dumps(payload)
    return f"""
<!doctype html><html><head><meta charset="utf-8"><style>
:root {{ --navy:{T.DEEP_NAVY}; --mid:{T.MIDNIGHT}; --panel:{T.PANEL}; --teal:{T.TEAL}; --aqua:{T.AQUA};
        --coral:{T.CORAL}; --amber:{T.AMBER}; --green:{T.GREEN}; --ice:{T.ICE}; --muted:{T.MUTED}; }}
html,body {{ margin:0; background:transparent; color:var(--ice); font-family:Inter,"Segoe UI",sans-serif; }}
.wrap {{ display:grid; grid-template-columns: minmax(0,1.55fr) minmax(250px,1fr); gap:14px; }}
@media (max-width: 760px) {{ .wrap {{ grid-template-columns: 1fr; }} }}
.card {{ background:linear-gradient(160deg, var(--panel), var(--mid)); border:1px solid rgba(54,217,232,.18);
        border-radius:14px; padding:10px; box-shadow:0 8px 24px rgba(0,0,0,.3); }}
.board {{ margin-top:10px; }}
.board svg {{ display:block; margin:0 auto; border-radius:8px; width:auto; height:auto;
             max-width:100%; max-height:calc(100vh - 110px); }}
.controls {{ display:flex; flex-wrap:wrap; gap:6px; margin:0 0 6px; align-items:center; }}
button {{ background:rgba(54,217,232,.08); color:var(--ice); border:1px solid rgba(54,217,232,.35); border-radius:9px;
         padding:7px 12px; font-weight:600; font-size:13px; cursor:pointer; transition:all .15s; font-family:inherit; }}
button:hover {{ background:rgba(54,217,232,.18); border-color:var(--aqua); }}
button.primary {{ background:var(--teal); border-color:var(--teal); color:#04201E; }}
button.primary:hover {{ background:var(--aqua); }}
button:disabled {{ opacity:.4; cursor:not-allowed; }}
label {{ font-size:12px; color:var(--muted); display:flex; align-items:center; gap:8px; margin-left:auto; }}
input[type=range] {{ accent-color: var(--aqua); width:120px; }}
h4 {{ margin:2px 0 8px; font-size:13px; letter-spacing:.08em; text-transform:uppercase; color:var(--aqua); }}
.kv {{ display:grid; grid-template-columns: 1fr auto; gap:5px 10px; font-size:13px; }}
.kv span:nth-child(odd) {{ color:var(--muted); }}
.kv span:nth-child(even) {{ font-variant-numeric: tabular-nums; font-weight:600; text-align:right; }}
.ghf {{ display:grid; grid-template-columns:repeat(3,1fr); gap:6px; margin:10px 0; }}
.ghf div {{ background:rgba(16,28,44,.7); border-radius:10px; padding:6px; text-align:center; border:1px solid rgba(139,155,173,.15); }}
.ghf b {{ display:block; font-size:18px; color:var(--ice); }} .ghf small {{ color:var(--muted); font-size:11px; }}
table {{ width:100%; border-collapse:collapse; font-size:12px; }}
th,td {{ padding:3px 4px; text-align:right; border-bottom:1px solid rgba(139,155,173,.12); font-variant-numeric:tabular-nums; }}
th:first-child, td:first-child {{ text-align:left; }}
th {{ color:var(--muted); font-weight:500; }}
.status {{ margin-top:8px; padding:7px 10px; border-radius:9px; font-size:12px; background:rgba(16,28,44,.6); color:var(--muted); }}
.status.done {{ color:var(--green); border:1px solid rgba(55,214,154,.35); }}
.status.fail {{ color:var(--coral); border:1px solid rgba(255,98,107,.35); }}
.progress {{ height:4px; background:rgba(139,155,173,.15); border-radius:3px; overflow:hidden; margin-top:6px; }}
.progress div {{ height:100%; width:0; background:linear-gradient(90deg,var(--teal),var(--aqua)); transition:width .1s; }}
</style></head><body>
<div class="wrap">
  <div class="card">
    <div class="controls">
      <button class="primary" id="bStart">▶ Start</button>
      <button id="bPause">⏸ Pause</button>
      <button id="bStep">⏭ Step</button>
      <button id="bReset">↺ Reset</button>
      <label>Speed <input type="range" id="speed" min="1" max="100" value="35"><span id="spv"></span></label>
    </div>
    <div class="progress"><div id="prog"></div></div>
    <div class="board" id="board">{base_svg}</div>
  </div>
  <div class="card">
    <h4 id="title"></h4>
    <div class="kv">
      <span>Current node</span><span id="cur">—</span>
      <span>Nodes expanded</span><span id="exp">0</span>
      <span>Frontier size</span><span id="fs">1</span>
      <span>Current path cost g(n)</span><span id="cost">0</span>
      <span>Status</span><span id="st">Ready</span>
    </div>
    <div class="ghf" id="ghf"><div><small>g(n)</small><b id="g">0</b></div><div><small>h(n)</small><b id="h">—</b></div><div><small>f(n)</small><b id="f">—</b></div></div>
    <h4 id="qtitle">Frontier</h4>
    <table><thead id="qhead"></thead><tbody id="queue"></tbody></table>
    <div class="status" id="msg">Press Start to replay the recorded search, or Step through it one expansion at a time.</div>
  </div>
</div>
<script>
const D = {data};
const NS = "http://www.w3.org/2000/svg";
const svg = document.querySelector("#board svg");
const s = D.s;
const layer = document.createElementNS(NS, "g");
const firstEntity = [...svg.children].find(el => el.hasAttribute("filter") || ["polyline", "circle", "g", "text"].includes(el.tagName));
svg.insertBefore(layer, firstEntity || null);
const pathLayer = document.createElementNS(NS, "g"); svg.appendChild(pathLayer);
const topLayer = document.createElementNS(NS, "g"); svg.appendChild(topLayer);
const isBFS = D.algo === "BFS", isA = D.algo === "A*";
document.getElementById("title").textContent = D.algo + " — live trace";
document.getElementById("qtitle").textContent = isBFS ? "FIFO queue (front first)" : "Priority queue (lowest " + (isA ? "f" : "g") + " first)";
document.getElementById("qhead").innerHTML = "<tr><th>cell</th><th>g</th>" + (isA ? "<th>h</th><th>f</th>" : "") + "</tr>";
if (!isA) document.getElementById("ghf").style.display = "none";

let idx = 0, timer = null, rects = new Map(), frontier = new Map(), order = [], curMarker = null;
const key = (r, c) => r + "," + c;
function mk(r, c, color, op, inset) {{
  const el = document.createElementNS(NS, "rect");
  el.setAttribute("x", c * s + inset); el.setAttribute("y", r * s + inset);
  el.setAttribute("width", s - 2 * inset); el.setAttribute("height", s - 2 * inset);
  el.setAttribute("fill", color); el.setAttribute("opacity", op); el.setAttribute("rx", inset ? s * .15 : 0);
  layer.appendChild(el); return el;
}}
function setCell(r, c, kind) {{
  const k = key(r, c); const old = rects.get(k); if (old) old.remove();
  const el = kind === "explored" ? mk(r, c, "{T.EXPLORED}", .45, 0) : mk(r, c, "{T.FRONTIER}", .6, 1);
  rects.set(k, el);
}}
function fmt(v) {{ return (v === null || v === undefined) ? "—" : (Math.round(v * 100) / 100).toString(); }}
function renderQueue() {{
  let items = [...frontier.entries()];
  if (isBFS) items = order.filter(k => frontier.has(k)).map(k => [k, frontier.get(k)]);
  else items.sort((a, b) => (a[1][2] - b[1][2]) || (a[1][1] - b[1][1]));
  document.getElementById("queue").innerHTML = items.slice(0, 7).map(([k, v]) =>
    "<tr><td>(" + k + ")</td><td>" + fmt(v[0]) + "</td>" + (isA ? "<td>" + fmt(v[1]) + "</td><td>" + fmt(v[2]) + "</td>" : "") + "</tr>").join("")
    + (items.length > 7 ? "<tr><td colspan=4 style='color:var(--muted)'>… " + (items.length - 7) + " more</td></tr>" : "");
}}
function marker(r, c) {{
  if (!curMarker) {{ curMarker = document.createElementNS(NS, "rect"); curMarker.setAttribute("fill", "none");
    curMarker.setAttribute("stroke", "{T.ICE}"); curMarker.setAttribute("stroke-width", Math.max(1.5, s * .1)); curMarker.setAttribute("rx", 3); topLayer.appendChild(curMarker); }}
  curMarker.setAttribute("x", c * s + 1); curMarker.setAttribute("y", r * s + 1);
  curMarker.setAttribute("width", s - 2); curMarker.setAttribute("height", s - 2);
}}
function apply(ev) {{
  const [r, c, g, h, f, fsz, pushed] = ev;
  frontier.delete(key(r, c));
  if (!(r === D.start[0] && c === D.start[1]) && !(r === D.goal[0] && c === D.goal[1])) setCell(r, c, "explored");
  for (const p of pushed) {{
    const k = key(p[0], p[1]);
    if (!frontier.has(k)) order.push(k);
    frontier.set(k, [p[2], p[3], p[4]]);
    if (!(p[0] === D.goal[0] && p[1] === D.goal[1])) setCell(p[0], p[1], "frontier");
  }}
  marker(r, c);
  document.getElementById("cur").textContent = "(" + r + ", " + c + ")";
  document.getElementById("exp").textContent = idx + 1;
  document.getElementById("fs").textContent = frontier.size;
  document.getElementById("cost").textContent = fmt(g);
  document.getElementById("g").textContent = fmt(g); document.getElementById("h").textContent = fmt(h); document.getElementById("f").textContent = fmt(f);
}}
function drawPath() {{
  if (!D.found) return;
  const pts = D.path.map(p => ((p[1] + .5) * s) + "," + ((p[0] + .5) * s)).join(" ");
  const pl = document.createElementNS(NS, "polyline");
  pl.setAttribute("points", pts); pl.setAttribute("fill", "none"); pl.setAttribute("stroke", "{T.GREEN}");
  pl.setAttribute("stroke-width", Math.max(2, s * .24)); pl.setAttribute("stroke-linecap", "round"); pl.setAttribute("stroke-linejoin", "round");
  pathLayer.appendChild(pl);
}}
function finish() {{
  stop(); drawPath();
  const m = document.getElementById("msg");
  if (D.found) {{ m.className = "status done"; m.textContent = "Goal reached. Path cost " + fmt(D.cost) + ", " + (D.path.length - 1) + " moves, " + D.expanded + " nodes expanded, measured " + D.time + " ms (search only)."; document.getElementById("st").textContent = "Goal found"; }}
  else {{ m.className = "status fail"; m.textContent = "Frontier exhausted — the exit is unreachable from this start."; document.getElementById("st").textContent = "No path"; }}
}}
function progress() {{ document.getElementById("prog").style.width = (D.events.length ? 100 * idx / D.events.length : 100) + "%"; }}
function step() {{
  if (idx >= D.events.length) {{ finish(); return false; }}
  apply(D.events[idx]); idx++; renderQueue(); progress();
  document.getElementById("st").textContent = timer ? "Running" : "Paused";
  if (idx >= D.events.length) {{ finish(); return false; }}
  return true;
}}
function speedParams() {{ const v = +document.getElementById("speed").value; const perSec = Math.round(2 + v * v * 0.08);
  document.getElementById("spv").textContent = perSec + "/s"; return perSec; }}
function tick() {{ const per = speedParams(); const batch = Math.max(1, Math.round(per / 30)); for (let i = 0; i < batch; i++) if (!step()) return; }}
function start() {{ if (timer || idx >= D.events.length) return; const per = speedParams(); timer = setInterval(tick, Math.max(16, 1000 / Math.min(per, 30)));
  document.getElementById("st").textContent = "Running"; document.getElementById("bStart").textContent = "▶ Resume"; }}
function stop() {{ if (timer) clearInterval(timer); timer = null; if (idx < D.events.length) document.getElementById("st").textContent = "Paused"; }}
function reset() {{ stop(); idx = 0; layer.innerHTML = ""; pathLayer.innerHTML = ""; rects.clear(); frontier.clear(); order = [];
  if (curMarker) {{ curMarker.remove(); curMarker = null; }}
  frontier.set(key(D.start[0], D.start[1]), [0, isA ? D.events.length ? D.events[0][3] : 0 : 0, isA && D.events.length ? D.events[0][4] : 0]); order.push(key(D.start[0], D.start[1]));
  ["cur"].forEach(i => document.getElementById(i).textContent = "—");
  document.getElementById("exp").textContent = 0; document.getElementById("fs").textContent = 1; document.getElementById("cost").textContent = 0;
  document.getElementById("st").textContent = "Ready"; document.getElementById("bStart").textContent = "▶ Start";
  const m = document.getElementById("msg"); m.className = "status"; m.textContent = "Press Start to replay the recorded search, or Step through it one expansion at a time.";
  renderQueue(); progress(); }}
document.getElementById("bStart").onclick = start;
document.getElementById("bPause").onclick = stop;
document.getElementById("bStep").onclick = () => {{ stop(); step(); }};
document.getElementById("bReset").onclick = reset;
document.getElementById("speed").oninput = () => {{ speedParams(); if (timer) {{ stop(); start(); }} }};
speedParams(); reset();
</script></body></html>
"""
