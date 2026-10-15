# Changelog

All notable changes to DarkNode are documented here. The format loosely follows
[Keep a Changelog](https://keepachangelog.com/); the project uses date-based releases.

## [0.2.0] — 2026-10-15

A full pass turning the prototype into a finished, polished game.

### Added
- **Campaign**: 25 missions across 5 acts (Orientation, Loops & Collections, Functions &
  Text, Algorithms, Ciphers & Forensics), each introducing one concept with a worked
  example, from `print`/variables to BFS/DFS, Dijkstra, Caesar/Vigenère/XOR/base64, toy
  password hashing and regex log parsing.
- **Three-level hints** (nudge → direction → almost-there) per mission; full solutions are
  kept only in the test suite.
- **Internationalisation**: English and Ukrainian, switchable live, with every player-facing
  string in shared `darknode/locales/*.json`. A test fails on any missing key.
- **Save system**: credits, stars, best cycle counts, achievements, unlocked commands;
  JSON export/import to a file. Terminal saves to `~/.darknode/save.json`; the browser mirrors
  it in `localStorage`.
- **Progression**: credits (plus a cycle-saving bonus), an 11-badge achievement set, a shop of
  helper commands (`grep`, `freq`, `nums`, `uniq`), and linear mission unlocks.
- **Free-play sandbox**: a deterministic random-network generator, unlocked after the campaign.
- **Browser version overhaul**: retro CRT look (glow, scanlines, curvature, boot flicker — all
  toggleable and honouring `prefers-reduced-motion`), four skins (amber, green, ice, corporate
  beige), a CodeMirror editor with a textarea fallback, an animated layered network map, acts
  drawer, shop and achievements panels, and settings.
- **Procedural audio**: synthwave/chiptune music (per-act scales) and SFX (keys, granted,
  denied, alarm, buy) via Web Audio — no audio files; separate music/SFX volumes; muted until
  first interaction.
- **PWA**: web app manifest, SVG icon and a service worker (precached app shell + engine +
  locales; runtime caching for offline play after the first load).
- **Engine**: weighted links + Dijkstra, a dataset oracle (`size`/`at`) for search missions,
  an alarm mechanic for noisy cracking, and an expanded import allow-list.

### Changed
- Checkers now return an i18n key + params instead of a sentence, so all prose stays in the
  locale files and translation completeness is testable.
- The web and terminal front-ends now share one rulebook (`progress.py`), the browser calling
  it through Pyodide, so they cannot drift apart.
- The Pages workflow bundles `locales/` and documents the one-time Pages-enablement step.

### Fixed
- Hardened the Pages deploy against the first-run "Resource not accessible by integration"
  error (documented owner action; the workflow self-heals once Pages is enabled).

## [0.1.0] — 2026-10-15

- Initial prototype: core engine, cycle-budget sandbox, three missions, interactive terminal,
  a browser version with a live network map, and cross-platform CI.
