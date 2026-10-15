# DarkNode — Design Document

> Everything in DarkNode is fictional. The "network" is a graph inside the game.
> No real systems are touched, and all companies, characters and products are invented.

This document records the design decisions made while turning the prototype into a
finished game. It is updated as decisions are made, per the project brief.

## Vision

DarkNode teaches Python from zero to an advanced level by disguising a programming
course as an infiltration game. You play a freelance operator poking at the networks of
**OmniGrid Dynamics**, an absurd bureaucratic mega-corporation, under the "guidance" of
**BYTE**, a sarcastic AI mentor who would rather be doing anything else. Every mission is
a small, self-contained Python problem; the story and jokes are the sugar around it.

The same engine runs in a terminal (Python 3.10+, no dependencies) and in the browser
(the real engine inside Pyodide), so a mission behaves identically in both.

## Pillars

1. **One concept per mission.** Each mission introduces exactly one new idea and gives a
   short reference card with a worked example. Difficulty ramps across 5 acts.
2. **No solutions in the game.** Hints come in three escalating levels (nudge, direction,
   almost-there) but never the full answer. Reference solutions live *only* in the test
   suite, which proves every mission is solvable inside its CPU budget.
3. **Clever beats brute force.** Every executed line of the player's script costs one CPU
   "cycle". Missions are tuned so the naive approach runs out of cycles and the intended
   algorithm fits comfortably. Spare cycles are rewarded with bonus credits.
4. **Two languages, one source of truth.** Every player-facing string (UI, briefings,
   concept cards, hints, mentor lines, check messages) lives in `darknode/locales/*.json`
   and is shared by the web and terminal front-ends. A test fails if any key is missing
   from either language.
5. **Atmosphere.** Retro CRT terminal — phosphor glow, scanlines, gentle screen curvature,
   a boot flicker — with humour baked into the world. Every effect is switchable and
   respects `prefers-reduced-motion`.

## Architecture

```
darknode/
  network.py    # the fictional network: Node graph, locked hosts, files
  game.py       # GameSession: the API player scripts call
  sandbox.py    # runs player code with limited builtins + a CPU-cycle budget
  missions.py   # mission mechanics: networks, checkers, budgets, concepts
  content.py    # the campaign: acts, mission order, achievements (data)
  shop.py       # buyable helper commands (three-level hints live in the locales)
  i18n.py       # translation loader + completeness helpers
  save.py       # progress, credits, achievements, best scores; export/import
  progress.py   # ties save + content together (credits, shop, unlocks)
  sandbox_gen.py# random network generator for free-play mode
  runner.py     # plays a script against a mission, returns a structured result
  terminal.py   # the interactive shell (language-aware)
  locales/
    en.json     # English strings
    uk.json     # Ukrainian strings
web/
  index.html    # browser version: editor, output, live map, settings
  app.js        # loads the engine into Pyodide; UI, skins, audio, PWA wiring
  style.css     # CRT theme, 4 skins, responsive layout
  audio.js      # procedural synthwave/chiptune + SFX via Web Audio
  bridge.py     # JSON bridge between the page and the engine
  manifest.webmanifest, sw.js, icon.svg  # PWA
```

### Checker protocol

A mission's `check(session)` returns `(success: bool, key: str, params: dict)`. The key is
an i18n key under `check.*`; the front-end formats it in the player's language. This keeps
all prose out of the engine and makes the translation-completeness test meaningful.

### Cycle model

The sandbox counts one cycle per executed source line of the *player's* script via
`sys.settrace` (engine/library lines are not counted). This is deliberately a teaching
device, not a security boundary — the README says so plainly. Budgets are chosen so that:

- the reference solution passes with headroom, and
- the obvious brute-force blows the budget (asserted by tests for the relevant missions).

Cycle **bonus** = `max(0, budget - used)`. Credits awarded = base mission reward + a
fraction of the cycle bonus, so tight code pays better.

### Sandbox module allow-list

`math, string, itertools, collections, functools, heapq, base64, re, bisect, textwrap,
json, hashlib`. `hashlib` is allowed for the "toy hashing" act but the toy scheme the game
uses is a tiny hand-rolled hash so players implement it themselves first; `hashlib` is
there for a later optional comparison. `random` is intentionally **excluded** from player
scripts so mission results are deterministic (the sandbox-mode generator seeds its own RNG
engine-side).

### Save format (v1)

```json
{
  "version": 1,
  "credits": 120,
  "completed": {"1": {"best_cycles": 88, "stars": 3}, ...},
  "achievements": ["first-blood", "under-budget"],
  "unlocked": ["grep", "sortkey"],
  "settings": {"lang": "en", "skin": "amber", "crt": true, "music": 0.5, "sfx": 0.7}
}
```

Terminal stores it at `~/.darknode/save.json`; the browser mirrors the same structure in
`localStorage` and can export/import it as a `.json` file.

## Decisions log

- **2026-10-15 — Text lives in JSON, mechanics in Python.** Missions reference i18n keys
  rather than embedding prose, so adding a language is a pure-data change and completeness
  is testable.
- **2026-10-15 — Checkers return keys, not sentences.** See "Checker protocol".
- **2026-10-15 — `random` excluded from the player sandbox** for deterministic grading;
  the free-play generator holds its own RNG in the engine.
- **2026-10-15 — Pages deploy hardened.** `actions/configure-pages` with `enablement: true`
  needs repo-admin rights the CI token may lack on first run, which failed the deploy job.
  The owner enables Pages once (Settings → Pages → Source: "GitHub Actions"); the workflow
  now tolerates the already-/not-yet-enabled states instead of hard-failing. Documented in
  README and SESSION_REPORT.
- **2026-10-15 — Screenshots via a headless harness.** The build sandbox blocks all hosts
  except package registries, so Pyodide/CodeMirror (CDN) can't load here and the live page
  can't be driven directly. The front-end was instead verified and screenshotted in headless
  Chromium by serving the real `web/index.html`, intercepting the CDN scripts, stubbing
  `loadPyodide`, and feeding a mock bridge the **real** catalog/result JSON generated from the
  Python engine. This exercises the actual shipped HTML/CSS/JS (rendering, unlock progression,
  run flow, skins, live language switch, shop, achievements). The Python engine itself is
  covered by the 41-test unit suite. Screenshots live in `docs/screenshots/`.
- **2026-10-15 — Assets are code, not files.** No binary assets are fetched or committed:
  music/SFX are synthesized with Web Audio, avatars and icons are inline SVG, the CRT look
  is CSS. External scripts (CodeMirror, Pyodide) load only from cdn.jsdelivr.net /
  cdnjs.cloudflare.com, per the brief.
