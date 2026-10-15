// DarkNode in the browser: loads the Python engine into Pyodide and wires up the page.
"use strict";

const ENGINE_FILES = [
  "__init__.py", "network.py", "sandbox.py", "game.py", "missions.py", "runner.py",
];

const $ = (id) => document.getElementById(id);
const editor = $("editor");
const output = $("output");
const runBtn = $("run");

let py = null;
let missions = [];
let currentId = 1;

// --- storage (per-viewer convenience; the game works without it) -------------
const store = {
  get(key, fallback) {
    try { const v = localStorage.getItem("darknode:" + key); return v === null ? fallback : v; }
    catch { return fallback; }
  },
  set(key, value) {
    try { localStorage.setItem("darknode:" + key, value); } catch { /* storage unavailable */ }
  },
};

const completed = new Set(JSON.parse(store.get("completed", "[]")));

// --- loading the engine ------------------------------------------------------
async function fetchText(paths) {
  for (const path of paths) {
    try {
      const res = await fetch(path);
      if (res.ok) return await res.text();
    } catch { /* try the next path */ }
  }
  throw new Error("could not load " + paths[0]);
}

async function boot() {
  try {
    py = await loadPyodide();
    py.FS.mkdirTree("/game/darknode");
    for (const file of ENGINE_FILES) {
      // deployed site: darknode/x.py; local dev from /web/: ../darknode/x.py
      const code = await fetchText(["darknode/" + file, "../darknode/" + file]);
      py.FS.writeFile("/game/darknode/" + file, code);
    }
    py.FS.writeFile("/game/bridge.py", await fetchText(["bridge.py"]));
    py.runPython("import sys; sys.path.insert(0, '/game'); import bridge");

    const data = JSON.parse(py.runPython("bridge.missions_json()"));
    missions = data.missions;
    $("api-help").textContent = data.api;
    renderMissionNav();
    selectMission(Number(store.get("current", "1")) || 1);
    runBtn.disabled = false;
    output.textContent = "Ready. Edit the script and press Run.";
  } catch (err) {
    output.innerHTML = "";
    line("Python failed to load: " + err.message, "denied");
    line("Check your connection and reload the page.", "meta");
  }
}

// --- missions ------------------------------------------------------------------
function renderMissionNav() {
  const nav = $("missions");
  nav.innerHTML = "";
  for (const m of missions) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "mission-btn" + (completed.has(m.id) ? " done" : "");
    b.textContent = m.id + ". " + m.title;
    b.dataset.id = m.id;
    b.addEventListener("click", () => selectMission(m.id));
    nav.appendChild(b);
  }
}

function selectMission(id) {
  const mission = missions.find((m) => m.id === id) || missions[0];
  saveScript();
  currentId = mission.id;
  store.set("current", String(currentId));
  for (const b of document.querySelectorAll(".mission-btn")) {
    b.setAttribute("aria-current", String(Number(b.dataset.id) === currentId));
  }
  $("mission-title").textContent = mission.title;
  $("briefing").textContent = mission.briefing;
  editor.value = store.get("script:" + currentId, mission.template);
  output.textContent = "Mission " + mission.id + " loaded. CPU budget: " +
    mission.max_cycles.toLocaleString("en") + " cycles.";
  setBudget(0, mission.max_cycles);
  drawMap({ nodes: [{ host: "home", state: "open", current: true }], links: [], total: null });
}

function saveScript() {
  if (missions.length && editor.value) store.set("script:" + currentId, editor.value);
}

// --- running ---------------------------------------------------------------------
async function run() {
  if (!py || runBtn.disabled) return;
  saveScript();
  runBtn.disabled = true;
  output.innerHTML = "";
  line("running mission.py…", "meta");
  await new Promise((r) => setTimeout(r, 30)); // let the page repaint first

  try {
    py.globals.set("_src", editor.value);
    const result = JSON.parse(py.runPython(`bridge.run_json(${currentId}, _src)`));
    output.innerHTML = "";
    for (const text of result.output) line(text);
    line(`cycles used: ${result.cycles.toLocaleString("en")} / ${result.max_cycles.toLocaleString("en")}`, "meta");
    if (result.success) {
      line("ACCESS GRANTED: " + result.message, "granted");
      completed.add(currentId);
      store.set("completed", JSON.stringify([...completed]));
      renderMissionNav();
      selectNavState();
    } else {
      line("FAILED: " + result.message, "denied");
    }
    setBudget(result.cycles, result.max_cycles);
    if (result.map) drawMap(result.map);
  } catch (err) {
    line("Engine error: " + err.message, "denied");
  } finally {
    runBtn.disabled = false;
  }
}

function selectNavState() {
  for (const b of document.querySelectorAll(".mission-btn")) {
    b.setAttribute("aria-current", String(Number(b.dataset.id) === currentId));
  }
}

function line(text, cls) {
  const span = document.createElement("span");
  if (cls) span.className = cls;
  span.textContent = text + "\n";
  output.appendChild(span);
}

function setBudget(used, max) {
  const bar = $("budget-bar");
  bar.style.width = Math.min(100, (used / max) * 100) + "%";
  bar.classList.toggle("over", used > max);
}

// --- network map ------------------------------------------------------------------
// Layered layout: hosts are placed in columns by their hop distance from "home".
function drawMap(map) {
  const svg = $("map");
  const NS = "http://www.w3.org/2000/svg";
  const adj = new Map(map.nodes.map((n) => [n.host, []]));
  for (const [a, b] of map.links) { adj.get(a).push(b); adj.get(b).push(a); }

  const depth = new Map([["home", 0]]);
  const queue = ["home"];
  while (queue.length) {
    const h = queue.shift();
    for (const n of (adj.get(h) || []).sort()) {
      if (!depth.has(n)) { depth.set(n, depth.get(h) + 1); queue.push(n); }
    }
  }
  const columns = [];
  for (const n of map.nodes) {
    const d = depth.has(n.host) ? depth.get(n.host) : 0;
    (columns[d] = columns[d] || []).push(n);
  }

  const colW = 120, rowH = 52, pad = 34;
  const rows = Math.max(1, ...columns.map((c) => (c ? c.length : 0)));
  const width = Math.max(320, pad * 2 + (columns.length - 1) * colW + 60);
  const height = pad * 2 + (rows - 1) * rowH;
  const pos = new Map();
  columns.forEach((col, ci) => {
    (col || []).forEach((n, ri) => {
      const offset = ((rows - col.length) * rowH) / 2;
      pos.set(n.host, [pad + ci * colW, pad + offset + ri * rowH]);
    });
  });

  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.innerHTML = "";
  for (const [a, b] of map.links) {
    const [x1, y1] = pos.get(a), [x2, y2] = pos.get(b);
    const l = document.createElementNS(NS, "line");
    Object.entries({ x1, y1, x2, y2, class: "link" }).forEach(([k, v]) => l.setAttribute(k, v));
    svg.appendChild(l);
  }
  for (const n of map.nodes) {
    const [x, y] = pos.get(n.host);
    const g = document.createElementNS(NS, "g");
    g.setAttribute("class", `node ${n.state}${n.current ? " current" : ""}`);
    const c = document.createElementNS(NS, "circle");
    c.setAttribute("cx", x); c.setAttribute("cy", y); c.setAttribute("r", 9);
    const t = document.createElementNS(NS, "text");
    t.setAttribute("x", x + 14); t.setAttribute("y", y + 4);
    t.textContent = n.host;
    g.append(c, t);
    svg.appendChild(g);
  }

  const seen = map.nodes.length;
  $("map-caption").textContent = map.total
    ? `${seen} of ${map.total} hosts discovered. Amber is where you are; red dashes are locked.`
    : "Run a script to map what you can see.";
}

// --- editor comfort ---------------------------------------------------------------
editor.addEventListener("keydown", (e) => {
  if (e.key === "Tab" && !e.shiftKey) {
    e.preventDefault();
    const { selectionStart: s, selectionEnd: end } = editor;
    editor.setRangeText("    ", s, end, "end");
  } else if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    run();
  }
});
editor.addEventListener("input", () => store.set("script:" + currentId, editor.value));

runBtn.addEventListener("click", run);
$("reset").addEventListener("click", () => {
  const mission = missions.find((m) => m.id === currentId);
  if (mission && confirm("Replace your script with the mission template?")) {
    editor.value = mission.template;
    saveScript();
  }
});

boot();
