// Soft background music on every page: remembers volume, mute and position as you move between pages.
(function () {
  const K = { vol: "music.vol", muted: "music.muted", t: "music.t" };
  const get = (k, d) => { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } };
  const put = (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} };

  let vol = parseFloat(get(K.vol, ".22")); if (!(vol >= 0 && vol <= 1)) vol = .22;
  let muted = get(K.muted, "0") === "1", waiting = false, fade = 0;

  const audio = new Audio("audio/background.mp3");
  audio.loop = true; audio.preload = "auto"; audio.muted = muted; audio.volume = 0;
  audio.addEventListener("loadedmetadata", () => {
    const t = parseFloat(get(K.t, "0"));
    if (isFinite(t) && t > 0 && audio.duration) { try { audio.currentTime = t % audio.duration; } catch (e) {} }
  }, { once: true });

  const box = document.createElement("div");
  box.className = "music"; box.setAttribute("role", "group"); box.setAttribute("aria-label", "Background music");
  box.innerHTML = '<button type="button" class="m-btn"></button><span class="m-hint">tap for music</span>' +
                  '<input class="m-vol" type="range" min="0" max="100" step="1" aria-label="Music volume">';
  document.body.appendChild(box);
  const btn = box.querySelector(".m-btn"), rng = box.querySelector(".m-vol");
  rng.value = Math.round(vol * 100);

  const SPK = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 9v6h4l5 4V5L7 9z"/>';
  const ON = SPK + '<path d="M15.5 8.5a5 5 0 010 7M18 6a8.5 8.5 0 010 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  const OFF = SPK + '<path d="M16 9l5 6M21 9l-5 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  function paint() {
    const silent = muted || vol === 0;
    btn.innerHTML = silent ? OFF : ON;
    btn.setAttribute("aria-label", waiting ? "Play music" : silent ? "Unmute music" : "Mute music");
    box.classList.toggle("waiting", waiting);
  }
  function ramp(target, ms) {
    cancelAnimationFrame(fade);
    const from = audio.volume, t0 = performance.now();
    (function step(now) { const p = Math.min(1, (now - t0) / ms); audio.volume = from + (target - from) * p; if (p < 1) fade = requestAnimationFrame(step); })(t0);
  }
  function start() {
    return audio.play().then(() => { waiting = false; ramp(vol, 1600); paint(); })
                       .catch(() => { waiting = true; paint(); });
  }

  btn.onclick = () => {
    if (audio.paused) { start(); return; }
    muted = !muted; audio.muted = muted; put(K.muted, muted ? "1" : "0");
    if (!muted && vol === 0) { vol = .22; rng.value = 22; put(K.vol, vol); }
    ramp(vol, 300); paint();
  };
  rng.oninput = () => {
    vol = rng.value / 100; put(K.vol, vol);
    if (vol > 0 && muted) { muted = false; audio.muted = false; put(K.muted, "0"); }
    cancelAnimationFrame(fade); audio.volume = vol; paint();
  };

  // browsers only allow sound after a click or key press; begin on the first one
  const unlock = (e) => {
    if (box.contains(e.target)) return;
    if (audio.paused) start();
    if (!audio.paused || !waiting) ["pointerdown", "keydown", "touchstart"].forEach(ev => removeEventListener(ev, unlock, true));
  };
  ["pointerdown", "keydown", "touchstart"].forEach(ev => addEventListener(ev, unlock, true));

  setInterval(() => { if (!audio.paused) put(K.t, audio.currentTime); }, 1000);
  addEventListener("pagehide", () => put(K.t, audio.currentTime));
  audio.addEventListener("error", () => box.remove());   // file missing: no broken control

  paint(); start();
})();
