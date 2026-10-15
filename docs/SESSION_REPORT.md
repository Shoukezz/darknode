# DarkNode — Session Report (2026-10-15)

An autonomous pass that turned the DarkNode prototype (3 missions, a thin browser page) into
a finished, polished, bilingual game. This report records what was done, what remains, and
what is worth checking by hand.

## What was done

### Engine, i18n and save
- Rewrote the engine around a clean separation of **mechanics (Python)** and **text (JSON)**.
  Checkers return an i18n key + params; no player-facing prose lives in code.
- Added `i18n.py` (loader + completeness check), `save.py` (credits, stars, best cycles,
  achievements, unlocks, export/import), `progress.py` (all award/shop/unlock rules, shared
  by both front-ends), `content.py` (acts + achievements), `shop.py` (buyable helpers) and
  `sandbox_gen.py` (deterministic random networks for free play).
- Extended `network.py` with weighted links + Dijkstra, and `game.py` with `links()`, a
  dataset oracle (`size`/`at`) and an alarm on noisy cracking. Expanded the sandbox import
  allow-list.

### Campaign
- **25 missions in 5 acts**, one concept each: `print`/variables/arithmetic/f-strings/booleans
  → loops/lists/nested-loops/dicts/sets → functions/string-methods/slicing/recursion/
  comprehensions → sorting/binary-search/BFS/DFS/Dijkstra → Caesar/Vigenère/XOR/base64/
  toy-hash/log-parsing + a capstone.
- Every mission has a concept card, three-level hints, a starter template, and a reference
  solution kept **only** in the tests. Three missions carry brute-force traps (binary search,
  naive recursion, full-PIN alarm) that the tests assert actually fail.
- Full English + Ukrainian text, including code-comment templates.

### Web
- CRT terminal UI with glow/scanlines/curvature/boot-flicker (all toggleable, reduced-motion
  aware), four skins, a CodeMirror editor (+ textarea fallback), animated map, acts/shop/
  achievements drawers, settings, live language switch, and save export/import.
- Procedural synthwave/chiptune + SFX via Web Audio (no asset files).
- PWA: manifest, SVG icon, service worker (offline app shell + engine + locales).
- The browser runs the real engine via Pyodide and calls `progress.py` through a JSON bridge,
  so web and terminal share one rulebook.

### Quality
- **41 unit tests**, green locally and in CI design: engine/sandbox, every mission's reference
  solution within budget, every template running-but-not-solving in both languages, the three
  traps, i18n completeness, save round-trip, progression, shop, free-play generator and the
  web bridge.
- Front-end verified end-to-end in headless Chromium against engine-generated JSON (run flow,
  unlock progression 24→23 locked after mission 1, skins, EN↔UK switch, shop, achievements).
- README rewritten with screenshots; `docs/DESIGN.md`, `CHANGELOG.md` and this report added.

## What remains / nice-to-haves
- More Act V missions and a daily-seed challenge (listed in the README roadmap).
- Optional opt-in leaderboards.
- A short animated GIF of a mission being solved (only static screenshots were produced; see
  the verification note below for why).

## Worth checking by hand
1. **GitHub Pages enablement (one-time, owner action).** Set **Settings → Pages → Source:
   "GitHub Actions"**. The first deploy failed before this with "Resource not accessible by
   integration"; it self-heals once enabled. After that, confirm
   [shoukezz.github.io/darknode](https://shoukezz.github.io/darknode/) loads.
2. **Live browser run.** This build sandbox blocks all hosts except package registries, so
   Pyodide/CodeMirror (served from cdn.jsdelivr.net / cdnjs.cloudflare.com) could not be
   loaded here. The UI was verified with those CDNs stubbed and a mock bridge fed **real**
   engine JSON. Please open the deployed site once and confirm Pyodide boots, a mission runs,
   audio starts on first tap, and the PWA installs/works offline.
3. **Mobile input.** The layout and editor were checked at phone width; try the on-screen
   keyboard on a real device (the editor uses 15px text to avoid iOS zoom-on-focus).
4. **CI.** Confirm the Tests workflow is green on `main` across Windows/macOS/Linux × 3.10/3.13.

## Commits this session (author: Krokha Maksym; committer: Claude)
1. Rebuild engine: i18n (en/uk), save/progress, 25-mission campaign
2. Web UI: CRT terminal, 4 skins, audio, PWA, shop, sandbox, i18n
3. Docs: README, DESIGN, CHANGELOG, SESSION_REPORT + screenshots
