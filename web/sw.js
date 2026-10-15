// DarkNode service worker: offline app shell + opportunistic runtime caching.
// The app shell, engine and locales are precached. Cross-origin runtime files
// (Pyodide, CodeMirror) are cached the first time they load, so the game works
// offline after one online visit.
"use strict";

const VERSION = "darknode-v2";
const SHELL = [
  ".", "index.html", "style.css", "app.js", "audio.js",
  "manifest.webmanifest", "icon.svg", "bridge.py",
  "darknode/__init__.py", "darknode/network.py", "darknode/sandbox.py",
  "darknode/game.py", "darknode/missions.py", "darknode/content.py",
  "darknode/i18n.py", "darknode/save.py", "darknode/shop.py",
  "darknode/progress.py", "darknode/sandbox_gen.py", "darknode/runner.py",
  "darknode/locales/en.json", "darknode/locales/uk.json",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(VERSION).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
      .catch(() => { /* a missing shell file must not block install */ })
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  // network-first for the page itself, cache-first for everything else.
  event.respondWith(
    caches.match(req).then((cached) => {
      const fetched = fetch(req).then((res) => {
        if (res && (res.ok || res.type === "opaque")) {
          const copy = res.clone();
          caches.open(VERSION).then((cache) => cache.put(req, copy)).catch(() => {});
        }
        return res;
      }).catch(() => cached);
      return cached || fetched;
    })
  );
});
