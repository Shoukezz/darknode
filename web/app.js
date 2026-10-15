// DarkNode in the browser: the real Python engine inside Pyodide, wired to a
// retro terminal UI with skins, CRT effects, procedural audio and offline PWA.
"use strict";

const ENGINE_FILES = [
  "__init__.py", "network.py", "sandbox.py", "game.py", "missions.py",
  "content.py", "i18n.py", "save.py", "shop.py", "progress.py",
  "sandbox_gen.py", "runner.py",
];
const LOCALES = ["en.json", "uk.json"];

const $ = (id) => document.getElementById(id);
const SAVE_KEY = "darknode:save";
const CUR_KEY = "darknode:current";

let py = null;
let bridge = null;
let catalog = null;        // localized catalog for the current language
let missionsById = {};
let lang = "en";
let currentId = 1;
let sandboxMode = false;
let sandboxSeed = 1;
let hintLevel = 0;
let editor = null;         // CodeMirror instance (or null -> textarea)
let booted = false;

// --- save (localStorage; the engine computes all rules) ----------------------
function readSaveRaw() { try { return localStorage.getItem(SAVE_KEY) || ""; } catch { return ""; } }
function writeSaveRaw(s) { try { localStorage.setItem(SAVE_KEY, s); } catch { /* private mode */ } }
function save() {
  const raw = readSaveRaw();
  if (!raw) return { credits: 0, completed: {}, achievements: [], unlocked: [], settings: {} };
  try { return JSON.parse(raw); } catch { return { credits: 0, completed: {}, achievements: [], unlocked: [], settings: {} }; }
}
function setSave(obj) { writeSaveRaw(JSON.stringify(obj)); }

function completedIds() { return new Set(Object.keys(save().completed || {}).map(Number)); }
function unlockedSet() {
  const done = completedIds();
  const open = new Set([1]);
  const ids = catalog.missions.map((m) => m.id);
  for (let i = 1; i < ids.length; i++) if (done.has(ids[i - 1])) open.add(ids[i]);
  done.forEach((d) => open.add(d));
  return open;
}
function campaignDone() {
  const done = completedIds();
  return catalog.missions.every((m) => done.has(m.id));
}

// --- i18n helpers (strings come from the catalog) ----------------------------
function S(path, params) {
  const parts = path.split(".");
  let node = catalog.strings;
  for (const p of parts) { node = node && node[p]; }
  let str = typeof node === "string" ? node : path;
  if (params) str = str.replace(/\{(\w+)\}/g, (_, k) => (k in params ? params[k] : `{${k}}`));
  return str;
}
function applyStaticStrings() {
  document.documentElement.lang = lang;
  for (const el of document.querySelectorAll("[data-i18n]")) {
    el.textContent = S(el.getAttribute("data-i18n"));
  }
  $("tagline").textContent = S("ui.tagline");
  $("api-help").textContent = catalog.strings.api_help || "";
  $("mentor-name").textContent = S("ui.mentor_name");
}

// --- boot --------------------------------------------------------------------
async function fetchText(paths) {
  for (const path of paths) {
    try { const r = await fetch(path); if (r.ok) return await r.text(); } catch { /* next */ }
  }
  throw new Error("could not load " + paths[0]);
}

async function boot() {
  document.body.classList.add("booting");
  try {
    py = await loadPyodide();
    py.FS.mkdirTree("/game/darknode/locales");
    for (const f of ENGINE_FILES) {
      const code = await fetchText(["darknode/" + f, "../darknode/" + f]);
      py.FS.writeFile("/game/darknode/" + f, code);
    }
    for (const f of LOCALES) {
      const data = await fetchText(["darknode/locales/" + f, "../darknode/locales/" + f]);
      py.FS.writeFile("/game/darknode/locales/" + f, data);
    }
    const bridgeSrc = await fetchText(["bridge.py"]);
    py.FS.writeFile("/game/bridge.py", bridgeSrc);
    py.runPython("import sys; sys.path.insert(0, '/game'); import bridge");
    bridge = py.pyimport("bridge");

    // migrate / validate any existing save
    const raw = readSaveRaw();
    if (raw) {
      const v = JSON.parse(bridge.validate_save(raw));
      if (v.ok) setSave(v.save); else writeSaveRaw("");
    }

    lang = (save().settings && save().settings.lang) || "en";
    loadCatalog(lang);
    applySettings();
    buildEditor();
    renderAll();
    const startId = Number(localStorage.getItem(CUR_KEY)) || 1;
    selectMission(unlockedSet().has(startId) ? startId : 1);
    $("run").disabled = false;
    setOutput(S("ui.ready"));
    booted = true;
    registerSW();
  } catch (err) {
    setOutput("");
    line(S("ui.boot_fail", { error: err.message }), "denied");
    line(S("ui.boot_fail_hint"), "meta");
  } finally {
    document.body.classList.remove("booting");
  }
}

function loadCatalog(l) {
  lang = l;
  catalog = JSON.parse(bridge.catalog(l));
  missionsById = {};
  for (const m of catalog.missions) missionsById[m.id] = m;
}

// --- rendering ---------------------------------------------------------------
function renderAll() {
  applyStaticStrings();
  renderLangSelect();
  renderSkinSelect();
  renderStats();
  renderActs();
  renderShop();
  renderAchievements();
  renderSandboxBox();
  drawMentor();
}

function renderStats() {
  const s = save();
  const stars = Object.values(s.completed || {}).reduce((a, r) => a + (r.stars || 0), 0);
  const max = catalog.missions.length * 3;
  $("credits-stat").textContent = "◈ " + (s.credits || 0);
  $("stars-stat").textContent = "★ " + stars + "/" + max;
}

function renderLangSelect() {
  const sel = $("lang-select");
  sel.innerHTML = "";
  for (const l of catalog.languages) {
    const o = document.createElement("option");
    o.value = l.id; o.textContent = l.name; if (l.id === lang) o.selected = true;
    sel.appendChild(o);
  }
}

function renderSkinSelect() {
  const sel = $("skin-select");
  const skins = [["amber", "ui.skin_amber"], ["green", "ui.skin_green"],
                 ["ice", "ui.skin_ice"], ["corp", "ui.skin_corp"]];
  const cur = document.body.dataset.skin;
  sel.innerHTML = "";
  for (const [id, key] of skins) {
    const o = document.createElement("option");
    o.value = id; o.textContent = S(key); if (id === cur) o.selected = true;
    sel.appendChild(o);
  }
}

function renderActs() {
  const wrap = $("acts-list");
  wrap.innerHTML = "";
  const open = unlockedSet();
  const s = save();
  for (const act of catalog.acts) {
    const box = document.createElement("div");
    box.className = "act";
    box.innerHTML = `<h4>${act.name}</h4><p class="blurb">${act.blurb}</p>`;
    for (const mid of act.missions) {
      const m = missionsById[mid];
      const rec = (s.completed || {})[mid];
      const locked = !open.has(mid);
      const btn = document.createElement("button");
      btn.className = "mission-btn" + (locked ? " locked" : "");
      btn.type = "button";
      if (mid === currentId && !sandboxMode) btn.setAttribute("aria-current", "true");
      const stars = rec && rec.stars ? "★".repeat(rec.stars) : "";
      btn.innerHTML = `<span class="num">${locked ? "🔒" : mid}</span>` +
        `<span class="t">${m.title}</span><span class="stars">${stars}</span>`;
      if (!locked) btn.addEventListener("click", () => { selectMission(mid); closeDrawers(); });
      box.appendChild(btn);
    }
    wrap.appendChild(box);
  }
}

function renderShop() {
  const s = save();
  $("shop-credits").textContent = S("ui.credits", { credits: s.credits || 0 });
  const wrap = $("shop-list");
  wrap.innerHTML = "";
  for (const item of catalog.shop) {
    const owned = (s.unlocked || []).includes(item.id);
    const div = document.createElement("div");
    div.className = "shop-item";
    div.innerHTML = `<div class="name">${item.name}</div><div class="desc">${item.desc}</div>`;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = owned ? S("ui.owned") : (S("ui.buy") + " · " + S("ui.cost", { cost: item.cost }));
    btn.disabled = owned;
    if (!owned) btn.addEventListener("click", () => buy(item.id));
    div.appendChild(btn);
    wrap.appendChild(div);
  }
}

function renderAchievements() {
  const s = save();
  const have = new Set(s.achievements || []);
  const wrap = $("ach-list");
  wrap.innerHTML = "";
  const defs = catalog.strings.achievement || {};
  for (const id of Object.keys(defs)) {
    const got = have.has(id);
    const div = document.createElement("div");
    div.className = "ach-item" + (got ? "" : " locked");
    div.innerHTML = `<div class="name">${defs[id].name}</div><div class="desc">${defs[id].desc}</div>`;
    wrap.appendChild(div);
  }
}

function renderSandboxBox() {
  const unlocked = campaignDone();
  $("sandbox-note").style.display = unlocked ? "none" : "";
  $("sandbox-controls").hidden = !unlocked;
}

// --- mission view ------------------------------------------------------------
function selectMission(id) {
  saveScript();
  sandboxMode = false;
  currentId = id;
  localStorage.setItem(CUR_KEY, String(id));
  hintLevel = 0;
  const m = missionsById[id];
  $("mission-tag").textContent = "#" + id;
  $("mission-title").textContent = m.title;
  $("briefing").textContent = m.briefing;
  $("concept").textContent = m.conceptHelp;
  renderHints(m.hints);
  setEditorValue(scriptFor(id) || m.template);
  setBudget(0, m.max_cycles);
  setOutput(S("ui.mission_loaded", { id, cycles: m.max_cycles.toLocaleString() }));
  drawMap({ nodes: [{ host: "home", state: "open", current: true }], links: [], total: null });
  renderActs();
  DarkAudio.setAct(m.act);
}

function startSandbox(seed) {
  sandboxMode = true;
  sandboxSeed = seed;
  hintLevel = 0;
  $("mission-tag").textContent = "∞";
  $("mission-title").textContent = S("ui.sandbox_mode") + " · " + S("ui.sandbox_seed") + " " + seed;
  $("briefing").textContent = S("sandbox.intro");
  $("concept").textContent = catalog.strings.api_help || "";
  renderHints([]);
  setEditorValue(scriptFor("sb") ||
    "# Free play. Map the network, or crack the gateway and read flag.txt.\n\nprint(scan())\n");
  setOutput(S("ui.sandbox_mode") + " · seed " + seed);
  drawMap({ nodes: [{ host: "home", state: "open", current: true }], links: [], total: null });
  closeDrawers();
}

function renderHints(hints) {
  const wrap = $("hints");
  wrap.innerHTML = "";
  if (!hints || !hints.length) {
    wrap.innerHTML = `<p class="muted">${S("ui.hint_locked")}</p>`;
    return;
  }
  for (let i = 0; i < hints.length; i++) {
    const row = document.createElement("div");
    row.className = "hint-row";
    if (i < hintLevel) {
      row.innerHTML = `<span class="hint-level">${i + 1}/3</span><span class="hint-text">${hints[i]}</span>`;
    } else if (i === hintLevel) {
      const btn = document.createElement("button");
      btn.className = "hint-btn";
      btn.type = "button";
      btn.textContent = (i === 0 ? S("ui.hint") : S("ui.hint_more")) + ` (${i + 1}/3)`;
      btn.addEventListener("click", () => { hintLevel = i + 1; renderHints(hints); });
      row.appendChild(btn);
    } else { continue; }
    wrap.appendChild(row);
  }
}

// --- editor ------------------------------------------------------------------
function buildEditor() {
  const ta = $("editor");
  if (window.CodeMirror) {
    editor = CodeMirror.fromTextArea(ta, {
      mode: "python", theme: "darknode", lineNumbers: true,
      indentUnit: 4, tabSize: 4, indentWithTabs: false,
      autofocus: false, viewportMargin: Infinity,
      extraKeys: {
        "Ctrl-Enter": run, "Cmd-Enter": run,
        Tab: (cm) => cm.replaceSelection("    "),
      },
    });
    editor.on("keydown", () => DarkAudio.sfx.key());
    editor.on("change", saveScript);
  } else {
    ta.addEventListener("keydown", (e) => {
      DarkAudio.sfx.key();
      if (e.key === "Tab" && !e.shiftKey) {
        e.preventDefault();
        const { selectionStart: s, selectionEnd: en } = ta;
        ta.setRangeText("    ", s, en, "end");
      } else if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); run(); }
    });
    ta.addEventListener("input", saveScript);
  }
}
function getEditorValue() { return editor ? editor.getValue() : $("editor").value; }
function setEditorValue(v) { if (editor) editor.setValue(v); else $("editor").value = v; }
function scriptKey() { return sandboxMode ? "darknode:script:sb" : "darknode:script:" + currentId; }
function scriptFor(id) { try { return localStorage.getItem(id === "sb" ? "darknode:script:sb" : "darknode:script:" + id); } catch { return null; } }
function saveScript() { try { localStorage.setItem(scriptKey(), getEditorValue()); } catch { /* ignore */ } }

// --- running -----------------------------------------------------------------
async function run() {
  if (!py || $("run").disabled) return;
  DarkAudio.start();
  saveScript();
  $("run").disabled = true;
  setOutput("");
  line(S("ui.running"), "meta");
  await new Promise((r) => setTimeout(r, 30));
  try {
    py.globals.set("_src", getEditorValue());
    let json;
    if (sandboxMode) {
      json = bridge.sandbox_json(sandboxSeed, py.globals.get("_src"), readSaveRaw(), lang);
    } else {
      json = bridge.run_json(currentId, py.globals.get("_src"), readSaveRaw(), lang);
    }
    const r = JSON.parse(json);
    showResult(r);
  } catch (err) {
    line("Engine error: " + err.message, "denied");
  } finally {
    $("run").disabled = false;
  }
}

function showResult(r) {
  setOutput("");
  for (const t of r.output) line(t);
  line(S("ui.cycles", { used: r.cycles.toLocaleString(), max: r.max_cycles.toLocaleString() }), "meta");
  if (r.success) {
    line(S("ui.granted", { message: r.message }), "granted");
    if (r.stars) line("★".repeat(r.stars) + "☆".repeat(3 - r.stars), "meta");
    DarkAudio.sfx.granted();
  } else {
    line(S("ui.failed", { message: r.message }), "denied");
    if (r.message && r.message.toLowerCase().includes("alarm")) DarkAudio.sfx.alarm();
    else DarkAudio.sfx.denied();
  }
  setBudget(r.cycles, r.max_cycles);
  if (r.map) drawMap(r.map);

  if (r.save) {
    setSave(r.save);
    renderStats(); renderActs(); renderShop(); renderAchievements(); renderSandboxBox();
  }
  if (r.award) {
    if (r.award.awarded) line(S("ui.awarded", { awarded: r.award.awarded }), "meta");
    if (r.award.bonus) line(S("ui.bonus", { bonus: r.award.bonus }), "meta");
    for (const a of (r.award.new_achievements || [])) {
      const def = (catalog.strings.achievement || {})[a];
      if (def) toast("🏆 " + def.name);
    }
  }
}

// --- buy ---------------------------------------------------------------------
function buy(itemId) {
  const r = JSON.parse(bridge.buy_json(itemId, readSaveRaw(), lang));
  if (!r.ok) {
    if (r.reason === "poor") toast(S("ui.too_poor", { need: r.need }));
    return;
  }
  setSave(r.save);
  DarkAudio.sfx.buy();
  renderStats(); renderShop(); renderAchievements();
  for (const a of (r.new_achievements || [])) {
    const def = (catalog.strings.achievement || {})[a];
    if (def) toast("🏆 " + def.name);
  }
}

// --- output / budget ---------------------------------------------------------
function setOutput(text) { $("output").textContent = text; }
function line(text, cls) {
  const span = document.createElement("span");
  if (cls) span.className = cls;
  span.textContent = text + "\n";
  $("output").appendChild(span);
  $("output").scrollTop = $("output").scrollHeight;
}
function setBudget(used, max) {
  const bar = $("budget-bar");
  bar.style.width = Math.min(100, (used / max) * 100) + "%";
  bar.classList.toggle("over", used > max);
}

// --- network map (layered by hop distance from home) -------------------------
function drawMap(map) {
  const svg = $("map");
  const NS = "http://www.w3.org/2000/svg";
  const adj = new Map(map.nodes.map((n) => [n.host, []]));
  for (const [a, b] of map.links) { if (adj.has(a)) adj.get(a).push(b); if (adj.has(b)) adj.get(b).push(a); }
  const depth = new Map([["home", 0]]);
  const queue = ["home"];
  while (queue.length) {
    const h = queue.shift();
    for (const n of (adj.get(h) || []).sort()) if (!depth.has(n)) { depth.set(n, depth.get(h) + 1); queue.push(n); }
  }
  const columns = [];
  for (const n of map.nodes) { const d = depth.has(n.host) ? depth.get(n.host) : 0; (columns[d] = columns[d] || []).push(n); }
  const colW = 120, rowH = 52, pad = 34;
  const rows = Math.max(1, ...columns.map((c) => (c ? c.length : 0)));
  const width = Math.max(320, pad * 2 + (columns.length - 1) * colW + 60);
  const height = pad * 2 + (rows - 1) * rowH;
  const pos = new Map();
  columns.forEach((col, ci) => (col || []).forEach((n, ri) => {
    const offset = ((rows - col.length) * rowH) / 2;
    pos.set(n.host, [pad + ci * colW, pad + offset + ri * rowH]);
  }));
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.innerHTML = "";
  for (const [a, b] of map.links) {
    if (!pos.has(a) || !pos.has(b)) continue;
    const [x1, y1] = pos.get(a), [x2, y2] = pos.get(b);
    const l = document.createElementNS(NS, "line");
    Object.entries({ x1, y1, x2, y2, class: "link" }).forEach(([k, v]) => l.setAttribute(k, v));
    svg.appendChild(l);
  }
  for (const n of map.nodes) {
    if (!pos.has(n.host)) continue;
    const [x, y] = pos.get(n.host);
    const g = document.createElementNS(NS, "g");
    g.setAttribute("class", `node ${n.state}${n.current ? " current" : ""}`);
    const c = document.createElementNS(NS, "circle");
    c.setAttribute("cx", x); c.setAttribute("cy", y); c.setAttribute("r", 9);
    const t = document.createElementNS(NS, "text");
    t.setAttribute("x", x + 14); t.setAttribute("y", y + 4); t.textContent = n.host;
    g.append(c, t); svg.appendChild(g);
  }
  const seen = map.nodes.length;
  $("map-caption").textContent = map.total
    ? S("ui.map_caption", { seen, total: map.total })
    : S("ui.map_caption_empty");
}

// BYTE's little pixel avatar, drawn in SVG (no asset files).
function drawMentor() {
  const svg = $("mentor-avatar");
  svg.innerHTML = `
    <rect x="8" y="6" width="32" height="30" rx="3" fill="none" stroke="currentColor" stroke-width="2"/>
    <rect x="15" y="15" width="6" height="6" fill="currentColor"/>
    <rect x="27" y="15" width="6" height="6" fill="currentColor"/>
    <rect x="16" y="27" width="16" height="3" fill="currentColor"/>
    <line x1="24" y1="36" x2="24" y2="42" stroke="currentColor" stroke-width="2"/>
    <circle cx="24" cy="44" r="2" fill="currentColor"/>`;
  svg.style.color = "var(--primary)";
}

// --- settings ----------------------------------------------------------------
function applySettings() {
  const s = save().settings || {};
  document.body.dataset.skin = s.skin || "amber";
  document.body.classList.toggle("no-crt", s.crt === false);
  document.body.classList.toggle("no-scan", s.scanlines === false);
  document.body.classList.toggle("no-flicker", s.flicker === false);
  $("opt-crt").checked = s.crt !== false;
  $("opt-scan").checked = s.scanlines !== false;
  $("opt-flicker").checked = s.flicker !== false;
  $("opt-music").value = s.music ?? 0.4;
  $("opt-sfx").value = s.sfx ?? 0.6;
  DarkAudio.setMusic(Number($("opt-music").value));
  DarkAudio.setSfx(Number($("opt-sfx").value));
}
function patchSettings(patch) {
  const s = save();
  s.settings = Object.assign({}, s.settings, patch);
  setSave(s);
}

// --- drawers -----------------------------------------------------------------
function openDrawer(id) {
  closeDrawers();
  $("overlay").hidden = false;
  $(id).hidden = false;
}
function closeDrawers() {
  $("overlay").hidden = true;
  for (const d of document.querySelectorAll(".drawer")) d.hidden = true;
}

function toast(msg) {
  const t = $("toast");
  t.textContent = msg; t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { t.hidden = true; }, 2600);
}

// --- wiring ------------------------------------------------------------------
function wire() {
  $("run").addEventListener("click", run);
  $("reset").addEventListener("click", () => {
    const m = sandboxMode ? null : missionsById[currentId];
    if (confirm(S("ui.reset_confirm"))) {
      setEditorValue(m ? m.template : "print(scan())\n");
      saveScript();
    }
  });
  $("lang-select").addEventListener("change", (e) => {
    loadCatalog(e.target.value);
    patchSettings({ lang: e.target.value });
    renderAll();
    if (sandboxMode) startSandbox(sandboxSeed); else selectMission(currentId);
  });
  $("btn-acts").addEventListener("click", () => openDrawer("acts-drawer"));
  $("btn-shop").addEventListener("click", () => { renderShop(); openDrawer("shop-drawer"); });
  $("btn-ach").addEventListener("click", () => { renderAchievements(); openDrawer("ach-drawer"); });
  $("btn-settings").addEventListener("click", () => openDrawer("settings-drawer"));
  $("overlay").addEventListener("click", closeDrawers);
  for (const b of document.querySelectorAll("[data-close]")) b.addEventListener("click", closeDrawers);

  $("skin-select").addEventListener("change", (e) => {
    document.body.dataset.skin = e.target.value;
    patchSettings({ skin: e.target.value });
    drawMentor();
  });
  $("opt-crt").addEventListener("change", (e) => { document.body.classList.toggle("no-crt", !e.target.checked); patchSettings({ crt: e.target.checked }); });
  $("opt-scan").addEventListener("change", (e) => { document.body.classList.toggle("no-scan", !e.target.checked); patchSettings({ scanlines: e.target.checked }); });
  $("opt-flicker").addEventListener("change", (e) => { document.body.classList.toggle("no-flicker", !e.target.checked); patchSettings({ flicker: e.target.checked }); });
  $("opt-music").addEventListener("input", (e) => { DarkAudio.start(); DarkAudio.setMusic(Number(e.target.value)); patchSettings({ music: Number(e.target.value) }); });
  $("opt-sfx").addEventListener("input", (e) => { DarkAudio.setSfx(Number(e.target.value)); DarkAudio.sfx.key(); patchSettings({ sfx: Number(e.target.value) }); });

  $("sandbox-start").addEventListener("click", () => startSandbox(Number($("sandbox-seed").value) || 1));

  $("btn-export").addEventListener("click", exportSave);
  $("btn-import").addEventListener("click", () => $("import-file").click());
  $("import-file").addEventListener("change", importSave);
  $("btn-reset-progress").addEventListener("click", () => {
    if (confirm(S("ui.reset_progress_confirm"))) {
      const skin = document.body.dataset.skin;
      writeSaveRaw("");
      patchSettings({ lang, skin });
      renderAll(); selectMission(1);
      $("settings-msg").textContent = "✓";
    }
  });
}

function exportSave() {
  const blob = new Blob([readSaveRaw() || "{}"], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "darknode-save.json";
  a.click();
  URL.revokeObjectURL(a.href);
}
function importSave(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    const v = JSON.parse(bridge.validate_save(String(reader.result)));
    if (v.ok) {
      setSave(v.save);
      lang = (v.save.settings && v.save.settings.lang) || lang;
      loadCatalog(lang); applySettings(); renderAll(); selectMission(1);
      $("settings-msg").textContent = S("ui.import_ok");
    } else {
      $("settings-msg").textContent = S("ui.import_fail");
    }
  };
  reader.readAsText(file);
  e.target.value = "";
}

function registerSW() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js").catch(() => { /* offline unavailable */ });
  }
}

// kick off
window.addEventListener("pointerdown", () => DarkAudio.start(), { once: true });
wire();
boot();
