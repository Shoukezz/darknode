// DarkNode audio: procedural synthwave/chiptune + SFX via Web Audio.
// No audio files are loaded — everything is synthesized. Muted until the
// player's first interaction (browsers require a user gesture anyway).
"use strict";

const DarkAudio = (() => {
  let ctx = null;
  let musicGain = null, sfxGain = null;
  let musicVol = 0.4, sfxVol = 0.6;
  let started = false;
  let loop = null;
  let act = 1;

  // One scale per act, to give each act its own mood.
  const SCALES = {
    1: [0, 3, 5, 7, 10],       // minor pentatonic — neutral onboarding
    2: [0, 2, 4, 7, 9],        // major pentatonic — brighter
    3: [0, 2, 3, 5, 7, 10],    // dorian-ish
    4: [0, 1, 5, 7, 8],        // phrygian tension
    5: [0, 3, 6, 7, 10],       // blues-ish, moody finale
  };
  const ROOT = { 1: 55, 2: 58.27, 3: 49, 4: 61.74, 5: 43.65 }; // Hz (low)

  function ensure() {
    if (ctx) return;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    ctx = new AC();
    musicGain = ctx.createGain(); musicGain.gain.value = 0; musicGain.connect(ctx.destination);
    sfxGain = ctx.createGain(); sfxGain.gain.value = sfxVol; sfxGain.connect(ctx.destination);
  }

  function note(freq, start, dur, type, gain, dest) {
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = type; o.frequency.value = freq;
    g.gain.setValueAtTime(0, start);
    g.gain.linearRampToValueAtTime(gain, start + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0008, start + dur);
    o.connect(g); g.connect(dest);
    o.start(start); o.stop(start + dur + 0.02);
  }

  // A rolling 8-step arpeggio + a bass pulse, scheduled a bar at a time.
  function scheduleBar(at) {
    const scale = SCALES[act] || SCALES[1];
    const root = ROOT[act] || 55;
    const step = 0.28;
    // bass
    note(root, at, step * 7.5, "triangle", 0.5, musicGain);
    note(root * 1.5, at + step * 4, step * 3.5, "triangle", 0.3, musicGain);
    // arp
    for (let i = 0; i < 8; i++) {
      const deg = scale[(i * 2 + act) % scale.length];
      const oct = 4 + (i % 3 === 0 ? 1 : 0);
      const freq = root * Math.pow(2, oct) * Math.pow(2, deg / 12);
      note(freq, at + i * step, step * 0.9, i % 2 ? "square" : "sawtooth", 0.08, musicGain);
    }
    // soft pad
    note(root * 4 * Math.pow(2, scale[2] / 12), at, step * 8, "sine", 0.05, musicGain);
  }

  function runLoop() {
    if (!ctx) return;
    const barLen = 0.28 * 8;
    let next = ctx.currentTime + 0.1;
    const tick = () => {
      if (!started) return;
      while (next < ctx.currentTime + 1.0) {
        scheduleBar(next);
        next += barLen;
      }
      loop = setTimeout(tick, 250);
    };
    tick();
  }

  function start() {
    ensure();
    if (!ctx || started) return;
    if (ctx.state === "suspended") ctx.resume();
    started = true;
    musicGain.gain.setTargetAtTime(musicVol, ctx.currentTime, 0.5);
    runLoop();
  }

  function setAct(a) {
    act = Math.max(1, Math.min(5, a | 0));
  }

  function setMusic(v) {
    musicVol = v;
    if (musicGain && started) musicGain.gain.setTargetAtTime(v, ctx.currentTime, 0.2);
    if (musicGain) musicGain.gain.value = started ? v : 0;
  }
  function setSfx(v) { sfxVol = v; if (sfxGain) sfxGain.gain.value = v; }

  // --- SFX -----------------------------------------------------------------
  function blip(freq, dur, type = "square", gain = 0.2) {
    ensure(); if (!ctx) return;
    if (ctx.state === "suspended") ctx.resume();
    note(freq, ctx.currentTime, dur, type, gain, sfxGain);
  }

  const sfx = {
    key() { blip(420 + Math.random() * 120, 0.03, "square", 0.05); },
    granted() {
      ensure(); if (!ctx) return;
      const t = ctx.currentTime;
      [523, 659, 784, 1047].forEach((f, i) => note(f, t + i * 0.08, 0.18, "square", 0.18, sfxGain));
    },
    denied() {
      ensure(); if (!ctx) return;
      const t = ctx.currentTime;
      note(180, t, 0.18, "sawtooth", 0.2, sfxGain);
      note(120, t + 0.12, 0.26, "sawtooth", 0.2, sfxGain);
    },
    alarm() {
      ensure(); if (!ctx) return;
      const t = ctx.currentTime;
      for (let i = 0; i < 4; i++) {
        note(880, t + i * 0.18, 0.12, "square", 0.2, sfxGain);
        note(660, t + i * 0.18 + 0.09, 0.09, "square", 0.2, sfxGain);
      }
    },
    buy() { blip(880, 0.12, "triangle", 0.2); },
  };

  return {
    start, setAct, setMusic, setSfx, sfx,
    get started() { return started; },
  };
})();
