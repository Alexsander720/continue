"use strict";
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const sleep = ms => new Promise(r => setTimeout(r, ms));
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
let backgroundsPaused = reduced;

const guessLang = () => { const n = (navigator.language || "en").toLowerCase(); return n.startsWith("uk") ? "uk" : /^(ru|be)/.test(n) ? "ru" : "en"; };
let lang = LANGS.includes(localStorage.getItem("lang")) ? localStorage.getItem("lang") : guessLang();
let device = localStorage.getItem("device") === "pc" ? "pc" : "deck";
let cur = 0, renderSeq = 0;
let catalogQuery = "", catalogFilter = "all";

const T = k => (STR[lang] && STR[lang][k]) ?? STR.en[k] ?? "";
const L = v => (v && typeof v === "object" && !Array.isArray(v)) ? (v[lang] ?? v.en) : v;
const media = (g, f) => `media/${g.id}/${f}`;
const LOCALE = { en: "en-US", uk: "uk-UA", ru: "ru-RU" };
const GLYPH = {   // UI symbols for the fact categories; no invented in-game item art.
  coins: ["M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3z", "M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6", "M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"],
  level: ["M4 20h5v-5h5v-5h6V4", "M14 4h6v6"],
  time: ["M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0", "M12 7v5l3 2"],
  heart: ["M12 20 4 12C-1 6 7 1 12 7c5-6 13-1 8 5z"],
  cards: ["M7 3h13v16H7z", "M3 7v14h13", "M11 8h5M11 12h5"],
  book: ["M3 4h7l2 2 2-2h7v15h-7l-2 2-2-2H3z", "M12 6v15"],
  finds: ["m12 3 8 9-8 9-8-9z", "M4 12h16M12 3v18"],
  relic: ["M9 3h6l-1 7 4 4v7H6v-7l4-4z"],
  camera: ["M3 7h5l2-3h4l2 3h5v13H3z", "M16 13a4 4 0 1 1-8 0 4 4 0 0 1 8 0"],
  map: ["m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2z", "M9 3v16M15 5v16"],
  ammo: ["M8 21V8l4-5 4 5v13z", "M8 16h8"],
};
const glyphSvg = n => `<svg class="gh-glyph" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${GLYPH[n].map(d => `<path d="${d}"/>`).join("")}</svg>`;

// текст карточки: язык игры, если он в ней есть; иначе английский (как в плагине)
function gameText(g) {
  const own = g[lang] || {}, sourceLang = g.sourceLanguage || "en", source = g[sourceLang] || {};
  const tx = { ...source, ...own };
  tx.noLang = lang !== sourceLang && !!source.title && !own.title;
  tx.sourceLang = sourceLang;
  // как в плагине: когда известно, где остановился, описание магазина не показываем (только описание цели из сейва)
  if (!tx.detail && !tx.title) tx.detail = (STORE[g.id] || {})[lang] || (STORE[g.id] || {}).en || "";
  return tx;
}

/* ── язык ───────────────────────────────────── */
function applyLang() {
  document.documentElement.lang = lang;
  $$("[data-i18n]").forEach(el => { el.innerHTML = T(el.dataset.i18n).replace("{n}", GAMES.length); });
  $$("[data-i18n-aria]").forEach(el => el.setAttribute("aria-label", T(el.dataset.i18nAria)));
  $$("[data-i18n-placeholder]").forEach(el => el.setAttribute("placeholder", T(el.dataset.i18nPlaceholder)));
  $$(".lang button").forEach(b => { b.classList.toggle("on", b.dataset.lang === lang); b.setAttribute("aria-pressed", b.dataset.lang === lang); });
  backgroundLabel();
  menuLabel();
  musicLabel();
  renderPreset(currentPreset, false);
  renderChips(); renderPower(); renderFaq(); renderCatalog(); fillDonate(); startLocale(); guideLinks();
  renderGame(cur, { soft: true });
  restartTerm();
}
$$(".lang button").forEach(b => b.onclick = () => { lang = b.dataset.lang; localStorage.setItem("lang", lang); applyLang(); });

/* The same navigation remains available throughout the long landing. */
const siteNav = $("nav.top"), navToggle = $("#navToggle");
function menuLabel() { navToggle.setAttribute("aria-label", T(siteNav.classList.contains("nav-open") ? "nav.close" : "nav.open")); }
function setMenu(open, focus = false) {
  siteNav.classList.toggle("nav-open", open); navToggle.setAttribute("aria-expanded", open); menuLabel();
  if (open) $("#navLinks a").focus();
  else if (focus) navToggle.focus();
}
navToggle.onclick = () => setMenu(!siteNav.classList.contains("nav-open"));
$$("#navLinks a").forEach(a => a.addEventListener("click", () => setMenu(false)));
addEventListener("keydown", e => { if (e.key === "Escape" && siteNav.classList.contains("nav-open")) setMenu(false, true); });
addEventListener("pointerdown", e => { if (!siteNav.contains(e.target)) setMenu(false); });
const updateNav = () => siteNav.classList.toggle("scrolled", scrollY > 24);
addEventListener("scroll", updateNav, { passive: true }); updateNav();

/* ── герой: фон из петель + аркадный отсчёт ──── */
const heroVids = $$(".hero-bg video");
let heroIdx = 0, heroFlip = 0, heroVisible = true;
function heroNext() {
  const animated = GAMES.filter(g => g.bg !== "art");
  const g = animated[heroIdx++ % animated.length];
  const nxt = heroVids[heroFlip ^ 1], prev = heroVids[heroFlip];
  nxt.preload = "auto"; nxt.src = media(g, "loop.mp4"); nxt.poster = media(g, "poster.jpg"); nxt.load();
  const go = () => { nxt.classList.add("on"); prev.classList.remove("on"); prev.pause(); heroFlip ^= 1; if (!backgroundsPaused && heroVisible) nxt.play().catch(() => {}); };
  nxt.readyState >= 2 ? go() : nxt.addEventListener("canplay", go, { once: true });
}
heroNext();
setInterval(() => { if (heroVisible && !backgroundsPaused) heroNext(); }, 10500);

const arCount = $("#arCount");
let count = 9;
setInterval(() => {
  if (count > 0) { count--; arCount.className = "ar-count"; void arCount.offsetWidth; arCount.textContent = count; arCount.classList.add("tick"); }
  else if (count === 0) { count = -1; arCount.className = "ar-count go"; arCount.textContent = T("hero.press"); }
  else { count = 9; arCount.className = "ar-count"; arCount.textContent = "9"; }
}, 1000);
const goDemo = () => $("#demo").scrollIntoView({ behavior: "smooth" });
$("#arcade").onclick = goDemo;
$("#arcade").onkeydown = e => { if (e.key === "Enter" || e.key === " ") goDemo(); };

/* ── демо: Дека / ПК ─────────────────────────── */
const screen = $("#screen"), wrap = $("#screenWrap"), dev = $("#device");
const BASE = { deck: 854, pc: 1280 };   // ширина экрана Steam в CSS-px: Дека (DPR 1.5) и Big Picture 720p
function fitScreen() { screen.style.setProperty("--s", wrap.clientWidth / BASE[device]); }
new ResizeObserver(fitScreen).observe(wrap);

function setDevice(d, anim = true) {
  device = d; localStorage.setItem("device", d);
  dev.classList.toggle("is-pc", d === "pc"); dev.classList.toggle("is-deck", d === "deck");
  screen.classList.toggle("pc", d === "pc");
  $$(".devsw button").forEach(b => { b.classList.toggle("on", b.dataset.dev === d); b.setAttribute("aria-pressed", b.dataset.dev === d); });
  fitScreen();
  if (anim) { dev.classList.remove("swap"); void dev.offsetWidth; dev.classList.add("swap"); }
  renderGame(cur, { soft: !anim });
}
$$(".devsw button").forEach(b => b.onclick = () => { if (b.dataset.dev !== device) setDevice(b.dataset.dev); });

const svids = $$(".s-bg video");
let sFlip = 0, demoVisible = false, bgRequest = 0;
function setBg(g) {
  const request = ++bgRequest;
  const background = $(".s-bg");
  background.style.backgroundImage = `url("${media(g, "poster.jpg")}")`;
  if (g.bg === "art") {
    svids.forEach(v => { v.pause(); v.classList.remove("on"); v.removeAttribute("src"); v.load(); });
    return;
  }
  const nxt = svids[sFlip ^ 1], prev = svids[sFlip];
  // невидимое видео браузер сам не грузит — загрузка и play() явно, показ — когда готово
  nxt.preload = "auto"; nxt.src = media(g, "loop.mp4"); nxt.poster = media(g, "poster.jpg"); nxt.load();
  const go = () => { if (request !== bgRequest) return; nxt.classList.add("on"); prev.classList.remove("on"); sFlip ^= 1; prev.pause(); if (!backgroundsPaused) nxt.play().catch(() => {}); };
  nxt.readyState >= 2 ? go() : nxt.addEventListener("canplay", go, { once: true });
}

function countUp(el, text, delay) {
  const m = /\d+(?:[.,]\d+)?/.exec(text);
  if (!m || reduced) { el.textContent = text; return; }
  const target = parseFloat(m[0].replace(",", ".")), dec = /[.,]/.test(m[0]);
  if (target > 9999 || /\d[ ,]\d{3}/.test(text)) { el.textContent = text; return; }
  const pre = text.slice(0, m.index), post = text.slice(m.index + m[0].length);
  const t0 = performance.now() + delay, dur = 700;
  el.textContent = pre + "0" + post;
  const step = now => {
    const k = Math.min(1, Math.max(0, (now - t0) / dur)), e = 1 - Math.pow(1 - k, 3);
    el.textContent = pre + (dec ? (target * e).toFixed(1) : Math.round(target * e)) + post;
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

async function typeTitle(el, text, seq) {
  el.innerHTML = "";
  if (!text) return;
  if (reduced) { el.textContent = text; return; }
  const caret = document.createElement("span"); caret.className = "caret";
  const tn = document.createTextNode(""); el.append(tn, caret);
  await sleep(380);
  for (const ch of text) { if (seq !== renderSeq) return; tn.data += ch; await sleep(ch === " " ? 70 : 40); }
  fitPanel();
  await sleep(1400); if (seq === renderSeq) caret.remove();
}

const fmtNum = n => new Intl.NumberFormat(LOCALE[lang], { maximumFractionDigits: 1 }).format(n);
const fmtDate = iso => new Intl.DateTimeFormat(LOCALE[lang], { day: "numeric", month: "short" }).format(new Date(iso + "T12:00:00"));

function renderGame(i, opt = {}) {
  const g = GAMES[i], tx = gameText(g), seq = ++renderSeq, st = STORE[g.id] || {};
  cur = i;
  $("#demoGameName").textContent = g.name;
  $("#expandedGameName").textContent = g.name;
  document.documentElement.style.setProperty("--accent", g.accent);
  if (!opt.soft && !opt.keepBg) { setBg(g); screen.classList.remove("fade"); void screen.offsetWidth; screen.classList.add("fade"); }

  const logo = $("#ghLogo");
  logo.onload = fitPanel;   // высота логотипа известна только после загрузки — пересчитать раскладку
  if (!opt.soft || !logo.src.includes(`/${g.id}/`)) { logo.classList.remove("in"); logo.src = media(g, "logo.png"); logo.alt = g.name; void logo.offsetWidth; logo.classList.add("in"); }
  $("#ghPanel").classList.toggle("no-title", !tx.title);
  $("#ghKicker").textContent = tx.kicker || "";
  $("#ghSub").textContent = tx.sub || "";
  const det = $("#ghDetail"); det.classList.remove("in"); det.textContent = tx.detail || ""; void det.offsetWidth; det.classList.add("in");
  if (opt.soft) $("#ghTitle").textContent = tx.title || ""; else typeTitle($("#ghTitle"), tx.title, seq);

  const bar = $("#ghFacts"); bar.innerHTML = "";
  g.facts.forEach((f, k) => {
    const d = document.createElement("div"); d.className = "gh-fact";
    d.innerHTML = (f.glyph ? glyphSvg(f.glyph) : `<img src="${media(g, f.icon)}" alt="">`) + `<div><div class="gh-fl"></div><div class="gh-fv"></div></div>`;
    d.querySelector(".gh-fl").textContent = L(f.l);
    bar.append(d);
    const delay = (opt.soft ? 0 : 650) + k * 110;
    d.style.animationDelay = delay + "ms"; d.classList.add("in");
    if (opt.soft) d.querySelector(".gh-fv").textContent = L(f.value); else countUp(d.querySelector(".gh-fv"), L(f.value), delay + 150);
  });
  if (g.people) {
    const p = document.createElement("div"); p.className = "gh-people";
    p.innerHTML = `<div class="gh-hd"><div class="gh-fl"></div><div class="gh-fv"></div></div><div class="gh-pp-row"></div>`;
    p.querySelector(".gh-fl").textContent = L(g.people.l);
    p.querySelector(".gh-fv").textContent = g.people.value;
    const row = p.querySelector(".gh-pp-row");
    g.people.list.forEach(([key, en, ru], k) => {
      const pp = document.createElement("div"); pp.className = "gh-pp";
      pp.innerHTML = `<img src="${media(g, "p_" + key + ".png")}" alt=""><span></span>`;
      pp.querySelector("span").textContent = lang === "ru" ? ru : en;
      pp.style.animationDelay = ((opt.soft ? 0 : 1100) + k * 70) + "ms"; pp.classList.add("in");
      row.append(pp);
    });
    p.style.animationDelay = (opt.soft ? 0 : 1000) + "ms"; p.classList.add("in");
    bar.prepend(p);
  }

  const h = T("s.h"), cells = st.last ? [[T("s.last"), fmtDate(st.last)]] : [];
  if (st.played >= 0.5) cells.push([T("s.played"), `${fmtNum(st.played)} ${h}`]);
  if (st.story) cells.push([T("s.story"), `~${fmtNum(st.story)} ${h}`]);
  if (st.full) cells.push([T("s.full"), `~${fmtNum(st.full)} ${h}`]);
  $("#sStats").innerHTML = cells.map(([b, s]) => `<div class="s-stat"><b>${b}</b><span>${s}</span></div>`).join("");
  // в Big Picture кнопка становится «Продолжить», когда известно, где остановился
  $("#sPlay span").textContent = device === "pc" && tx.title ? { en: "Continue", uk: "Продовжити", ru: "Продолжить" }[lang] : T("s.play");

  $$(".cover").forEach((c, k) => { c.classList.toggle("on", k === i); c.setAttribute("aria-pressed", k === i); });
  $("#bgCap").textContent = T("demo.bg." + g.bg);
  $("#bgCap").classList.toggle("is-rec", g.bg === "rec");
  const snap = g.snapshot;
  const sourceCaption = $("#demoSource");
  sourceCaption.textContent = T(snap?.kind === "community" ? "demo.source.community" : "demo.source.owner")
    + (snap?.author ? " · " + snap.author : "") + (snap?.date ? " · " + fmtDate(snap.date) + " " + snap.date.slice(0, 4) : "");
  sourceCaption.href = snap?.url || "#games";
  sourceCaption.classList.toggle("has-source", !!snap?.url);
  sourceCaption.setAttribute("aria-label", sourceCaption.textContent);
  $("#noLang").textContent = T("demo.sourceLanguage").replace("{lang}", tx.sourceLang.toUpperCase());
  $("#noLang").classList.toggle("on", tx.noLang);
  $("#noLang").hidden = !tx.noLang;
  $("#provenBadge").title = T("demo.proven.t");
  scrollSelectedCover();
  if (musicOn && !opt.soft) playTheme(g);
  fitPanel();
}

function fitPanel() {
  // факты растут снизу вверх — описание ужимается, чтобы не наезжать (как fitPanel() в плагине)
  const det = $("#ghDetail"), bar = $("#ghFacts"), panel = $("#ghPanel");
  const base = device === "pc" ? 3 : (panel.classList.contains("no-title") ? 5 : 4);
  for (let n = base; n >= 0; n--) {
    det.style.display = n ? "" : "none";
    det.style.webkitLineClamp = n;
    if (!n || panel.offsetTop + det.offsetTop + det.offsetHeight <= bar.offsetTop - 14) break;
  }
}

// обложки
$("#switcher").innerHTML = GAMES.map((g, i) => `<button class="cover" data-i="${i}" aria-label="${g.name}"><img src="${media(g, "cover.jpg")}" alt="" loading="lazy"><span class="nm">${g.name}</span></button>`).join("");
$$(".cover").forEach(c => c.onclick = () => { if (+c.dataset.i !== cur) renderGame(+c.dataset.i); });
const move = d => renderGame((cur + d + GAMES.length) % GAMES.length);
$$("[data-demo-step]").forEach(b => b.onclick = () => { move(+b.dataset.demoStep); scrollSelectedCover(); });
function scrollSelectedCover() {
  const track = $("#switcher"), cover = $(".cover.on");
  if (track.scrollWidth <= track.clientWidth) return;
  const left = cover.offsetLeft - track.offsetLeft - (track.clientWidth - cover.offsetWidth) / 2;
  track.scrollTo({ left, behavior: reduced ? "instant" : "smooth" });
}

/* Enlarge the same live device; restore its game, layout and keyboard focus on close. */
const demoDialog = $("#demoDialog"), deviceMount = $("#deviceMount");
let demoReturnFocus;
function openDemo(trigger) {
  setMenu(false);
  demoReturnFocus = trigger;
  const rect = dev.getBoundingClientRect();
  deviceMount.style.minHeight = rect.height + "px";
  $("#expandedDeviceMount").append(dev);
  $("#expandedEvidenceMount").append($("#demoEvidence"));
  demoDialog.showModal(); document.body.classList.add("has-dialog");
  $("#demoClose").focus(); fitScreen();
}
$("#demoExpand").onclick = e => openDemo(e.currentTarget);
$("#tryDemo").onclick = e => { e.preventDefault(); openDemo(e.currentTarget); };
$("#demoClose").onclick = () => demoDialog.close();
demoDialog.addEventListener("close", () => {
  deviceMount.append(dev); deviceMount.style.minHeight = "";
  $("#evidenceMount").append($("#demoEvidence"));
  document.body.classList.remove("has-dialog"); fitScreen();
  (demoReturnFocus || $("#demoExpand")).focus({ preventScroll: true });
});
demoDialog.addEventListener("click", e => {
  if (e.target !== demoDialog) return;
  const r = demoDialog.getBoundingClientRect();
  if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) demoDialog.close();
});
function backgroundLabel() {
  $("#demoPauseLabel").textContent = T(backgroundsPaused ? "demo.resume" : "demo.pause");
  $("#demoPause").setAttribute("aria-pressed", backgroundsPaused);
}
$("#demoPause").onclick = () => {
  backgroundsPaused = !backgroundsPaused; backgroundLabel();
  $$(".hero-bg video,.s-bg video").forEach(v => {
    if (backgroundsPaused) v.pause();
    else if (v.classList.contains("on")) v.play().catch(() => {});
  });
};

new IntersectionObserver(es => es.forEach(e => demoVisible = e.isIntersecting), { threshold: .3 }).observe(dev);
new IntersectionObserver(es => es.forEach(e => heroVisible = e.isIntersecting)).observe($(".hero"));
addEventListener("keydown", e => {
  if (!$("#tourModal").hidden || (!demoVisible && !demoDialog.open) || (e.target.closest && e.target.closest("input,textarea"))) return;
  if (e.key === "ArrowRight") { move(1); scrollSelectedCover(); e.preventDefault(); }
  if (e.key === "ArrowLeft") { move(-1); scrollSelectedCover(); e.preventDefault(); }
});

const toast = $("#sToast");
let toastT;
function playPress() {
  toast.classList.add("on"); clearTimeout(toastT); toastT = setTimeout(() => toast.classList.remove("on"), 2200);
  dev.classList.add("press"); setTimeout(() => dev.classList.remove("press"), 180);
}
$("#sPlay").onclick = playPress;

function tickClock() { $("#sClock").textContent = new Date().toLocaleTimeString(LOCALE[lang], { hour: "numeric", minute: "2-digit" }); }
tickClock(); setInterval(tickClock, 15000);

/* ── музыка темы ───────────────────────────── */
const audio = $("#theme");
let musicOn = false, fadeT;
function musicLabel() { $("#musicLbl").textContent = T(musicOn ? "demo.music.on" : "demo.music.off"); $("#musicBtn").setAttribute("aria-pressed", musicOn); }
function fadeTo(v, ms, done) {
  clearInterval(fadeT); const v0 = audio.volume, t0 = performance.now();
  fadeT = setInterval(() => { const k = Math.min(1, (performance.now() - t0) / Math.max(ms, 1)); audio.volume = v0 + (v - v0) * k; if (k >= 1) { clearInterval(fadeT); done && done(); } }, 30);
}
function playTheme(g) {
  const src = media(g, "theme.m4a");
  if (audio.src.endsWith(src) && !audio.paused) return;
  fadeTo(0, audio.paused ? 0 : 400, () => { audio.src = src; audio.volume = 0; audio.play().then(() => fadeTo(.55, 1200)).catch(() => {}); });
}
// музыки тем может не быть в публичной сборке (права) — тогда кнопку прячем
fetch(media(GAMES[0], "theme.m4a"), { method: "HEAD" }).then(r => { if (!r.ok) $("#musicBtn").hidden = true; }).catch(() => { $("#musicBtn").hidden = true; });
$("#musicBtn").onclick = () => {
  musicOn = !musicOn; musicLabel();
  if (musicOn) playTheme(GAMES[cur]); else fadeTo(0, 500, () => audio.pause());
};

/* ── геймпад: крестовина/бамперы — игры, A — «Играть», Y — музыка, View — Дека/ПК ── */
let padPrev = {};
function pollPad() {
  const pads = navigator.getGamepads ? [...navigator.getGamepads()].filter(Boolean) : [];
  $("#padHint").classList.toggle("on", pads.length > 0);
  for (const p of pads) {
    const b = i => p.buttons[i] && p.buttons[i].pressed;
    const now = { r: b(15) || b(5) || p.axes[0] > .6, l: b(14) || b(4) || p.axes[0] < -.6, a: b(0), y: b(3), v: b(8) };
    const canControlDemo = $("#tourModal").hidden && (demoVisible || demoDialog.open);
    if (canControlDemo) {
      if (now.r && !padPrev.r) move(1);
      if (now.l && !padPrev.l) move(-1);
      if (now.a && !padPrev.a) playPress();
      if (now.v && !padPrev.v) setDevice(device === "pc" ? "deck" : "pc");
    }
    if (canControlDemo && now.y && !padPrev.y && !$("#musicBtn").hidden) $("#musicBtn").click();
    padPrev = now;
  }
  requestAnimationFrame(pollPad);
}
requestAnimationFrame(pollPad);

/* ── плитка «сейв → где остановился» (по кругу три игры) ── */
const hexLine = $("#hexLine"), resolveLine = $("#resolveLine"), resolveSub = $("#resolveSub");
const HEX = "0123456789abcdef";
async function saveLoop() {
  for (let n = 0; ; n++) {
    const g = [GAMES[0], GAMES[1], GAMES[4]][n % 3], tx = gameText(g);
    resolveSub.textContent = "";
    for (let k = 0; k < 14; k++) { hexLine.textContent = Array.from({ length: 12 }, () => HEX[Math.random() * 16 | 0] + HEX[Math.random() * 16 | 0]).join(" "); await sleep(70); }
    let out = "";
    for (const ch of tx.title) {
      for (let s = 0; s < 3; s++) { resolveLine.textContent = out + "▓▒░"[s]; await sleep(18); }
      out += ch; resolveLine.textContent = out;
    }
    resolveSub.textContent = tx.sub ? `${tx.sub} · ${g.name}` : g.name;
    await sleep(2800); resolveLine.textContent = "";
  }
}
if (!reduced) saveLoop(); else resolveLine.textContent = "MEMENTO MORI";

/* ── плитка «живая главная»: фокус бежит по обложкам ── */
setInterval(() => {
  const covers = $$(".home-row i"); if (!covers.length) return;
  const k = covers.findIndex(c => c.classList.contains("on"));
  covers.forEach((c, j) => c.classList.toggle("on", j === (k + 1) % covers.length));
}, 2600);

/* ── пресеты ──────────────────────────────── */
let currentPreset = "lite";
function renderPreset(p, anim = true) {
  currentPreset = p; const v = PRESETS[p];
  $$("#presetSeg button").forEach((b, k) => { b.classList.toggle("on", b.dataset.p === p); if (b.dataset.p === p) $(".seg-ind").style.transform = `translateX(${k * 100}%)`; });
  const rows = [["p.video", v.video], ["p.disk", v.disk], ["p.scope", L(v.scope)], ["p.power", L(v.power)]];
  $("#presetList").innerHTML = rows.map(([k, val]) => `<dt>${T(k)}</dt><dd class="${anim ? "pop" : ""}">${val}</dd>`).join("");
}
$$("#presetSeg button").forEach(b => b.onclick = () => renderPreset(b.dataset.p));

/* ── языки игры ───────────────────────────── */
const flip = $("#langFlip");
let li = 0;
const startLocale = () => { li = Math.max(0, LOCALES.findIndex(([c]) => c.toLowerCase() === lang)); showLocale(); };
function showLocale() { const [c, t] = LOCALES[li % LOCALES.length]; flip.querySelector(".lc").textContent = c; flip.querySelector(".lt").textContent = t; }
showLocale();
setInterval(async () => { if (reduced) return; flip.className = "lang-flip out"; await sleep(330); li++; showLocale(); flip.className = "lang-flip inn"; }, 2000);

/* ── каталог игр ──────────────────────────── */
function renderCatalog() {
  const query = catalogQuery.trim().toLocaleLowerCase();
  const matches = CATALOG.filter(c => (catalogFilter === "all" || c.status === catalogFilter) && c.name.toLocaleLowerCase().includes(query));
  $("#catalog").innerHTML = matches.map(c => `
    <article class="game ${c.status}">
      ${c.cover === false ? `<div class="game-cover-placeholder" aria-hidden="true">${c.name.slice(0, 1)}</div>` : `<img src="media/${c.id}/cover.jpg" alt="" loading="lazy">`}
      <div class="g-body">
        <h3>${c.name}</h3>
        <span class="g-status">${c.status === "proven" ? "✓ " : ""}${T("cat." + c.status)}</span>
        <ul>${c.f.map(k => `<li class="ft-${k}">${T("ft." + k)}</li>`).join("")}</ul>
        ${GAMES.some(g => g.id === c.id) ? `<button class="game-demo" data-demo-game="${c.id}" aria-label="${T("cat.demo")} · ${c.name}">${T("cat.demo")} <span aria-hidden="true">↗</span></button>` : ""}
      </div>
    </article>`).join("");
  $("#catalogResults").textContent = T("cat.results").replace("{n}", matches.length).replace("{total}", CATALOG.length);
  $("#catalogEmpty").hidden = matches.length !== 0;
  $("#catalogClear").hidden = !catalogQuery;
  $$("[data-cat-filter]").forEach(b => b.setAttribute("aria-pressed", b.dataset.catFilter === catalogFilter));
  $("#catCountAll").textContent = CATALOG.length;
  $("#catCountProven").textContent = CATALOG.filter(c => c.status === "proven").length;
  $("#catCountCheck").textContent = CATALOG.filter(c => c.status === "check").length;
  $$("[data-demo-game]").forEach(b => b.onclick = () => {
    renderGame(GAMES.findIndex(g => g.id === b.dataset.demoGame)); openDemo(b);
  });
  const repo = DONATE.repo;
  $("#catReq").href = repo ? repo + "/issues/new?template=game_request.md" : "#";
  $("#catAdd").href = repo ? repo + "/blob/main/AGENTS.md" : "#agents";
}
$("#catalogSearch").addEventListener("input", e => { catalogQuery = e.target.value; renderCatalog(); });
function clearCatalogSearch() { catalogQuery = ""; $("#catalogSearch").value = ""; renderCatalog(); $("#catalogSearch").focus(); }
$("#catalogClear").onclick = clearCatalogSearch;
$("#catalogSearch").addEventListener("keydown", e => { if (e.key === "Escape" && catalogQuery) { e.preventDefault(); clearCatalogSearch(); } });
$$("[data-cat-filter]").forEach(b => b.onclick = () => { catalogFilter = b.dataset.catFilter; renderCatalog(); });

/* ── мелочи, батарея, вопросы ─────────────── */
function renderChips() {
  $("#chipList").innerHTML = Array.from({ length: 13 }, (_, i) => T("c" + (i + 1))).filter(Boolean).map(t => `<li>${t}</li>`).join("");
}
function renderPower() {
  const max = Math.max(...POWER.map(p => p.w)) * 1.08, unit = T("pw.unit");
  const dec = s => lang === "en" ? s : s.replace(".", ",");
  const fmtW = w => dec(w.toFixed(Math.round(w * 100) % 10 ? 2 : 1));
  $("#powerBars").innerHTML = POWER.map(p => `
    <div class="bar-row${p.bad ? " bad" : ""}" role="row" title="${T(p.k)}: ${fmtW(p.w)} ${unit}">
      <span class="bl" role="cell">${T(p.k)}</span>
      <span class="bt" role="cell"><i style="--w:${(p.w / max * 100).toFixed(1)}%"></i></span>
      <span class="bv" role="cell">${fmtW(p.w)} ${unit}${p.d ? ` <em>${dec(p.d)}</em>` : ""}<small>≈ ${dec((50 / p.w).toFixed(1))} ${T("pw.hours")}</small></span>
    </div>`).join("");
}
function renderFaq() {
  $("#qaList").innerHTML = [1, 2, 3, 4, 5, 6].map(i => `<details${i === 1 ? " open" : ""}><summary>${T("q" + i)}</summary><p>${T("a" + i)}</p></details>`).join("");
}

/* ── терминал агента ──────────────────────── */
let agent = "claude", termRun = 0, termSeen = false;
const termBody = $("#termBody");
async function runTerm() {
  const my = ++termRun;
  const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");
  let html = "";
  const paint = extra => { termBody.innerHTML = html + (extra || "") + '<span class="cur"></span>'; };
  const cmd = AGENTS[agent];
  for (let k = 1; k <= cmd.length; k++) { if (my !== termRun) return; paint(`<span class="cmd">${esc(cmd.slice(0, k))}</span>`); await sleep(reduced ? 0 : 24); }
  html += `<span class="cmd">${esc(cmd)}</span>\n\n`; paint();
  for (const [cls, line] of TERM[lang] || TERM.en) {
    await sleep(reduced ? 0 : (cls === "dim" ? 520 : 760)); if (my !== termRun) return;
    html += `<span class="${cls}">${esc(line)}</span>\n`; paint();
  }
  await sleep(6000); if (my === termRun) runTerm();
}
function restartTerm() { if (termSeen) runTerm(); }
$$(".term-tabs button").forEach(b => b.onclick = () => { $$(".term-tabs button").forEach(x => x.classList.toggle("on", x === b)); agent = b.dataset.a; runTerm(); });
new IntersectionObserver((es, ob) => es.forEach(e => { if (e.isIntersecting) { termSeen = true; runTerm(); ob.disconnect(); } }), { threshold: .4 }).observe($("#term"));

/* ── донаты и автор ───────────────────────── */
function fillDonate() {
  $$("[data-copy]").forEach(el => {
    const v = DONATE[el.dataset.copy];
    el.classList.toggle("disabled", !v);
    el.querySelector("span").textContent = v || T("sup.soon");
    el.onclick = () => {
      if (el.dataset.qr) $("#cryptoQr").src = el.dataset.qr;
      if (!v) return;
      navigator.clipboard.writeText(v.replace(/\s/g, "")).then(() => {
        const s = el.querySelector("span"); s.textContent = T("sup.copied"); el.classList.add("copied");
        setTimeout(() => { s.textContent = v; el.classList.remove("copied"); }, 1400);
      });
    };
    if (el.dataset.qr) el.onmouseenter = () => { $("#cryptoQr").src = el.dataset.qr; };
  });
  $$("[data-link]").forEach(el => { const v = DONATE[el.dataset.link]; if (v) { el.href = v; el.target = "_blank"; el.rel = "noopener"; } else el.classList.add("disabled"); });
  if (DONATE.repo) $("#guideLink").href = DONATE.repo + "/blob/main/AGENTS.md";
  const discord = $("#discordLink");
  if (DONATE.discord) { discord.href = DONATE.discord; discord.removeAttribute("aria-disabled"); discord.removeAttribute("tabindex"); }
  else { discord.removeAttribute("href"); discord.setAttribute("aria-disabled", "true"); discord.setAttribute("tabindex", "-1"); }
  const a = $("#authorLine");
  a.innerHTML = AUTHOR.steam || AUTHOR.github
    ? `<a href="${AUTHOR.steam || AUTHOR.github}" target="_blank" rel="noopener">${AUTHOR.name}</a>` : AUTHOR.name;
}

/* ── тур: модальное видео на языке сайта; ссылки на инструкции ── */
const tourModal = $("#tourModal"), tourVideo = $("#tourVideo");
$("#tourBtn").onclick = () => {
  setMenu(false);
  tourVideo.src = `media/tour-${lang}.mp4`; tourModal.hidden = false;
  $$("nav.top,header,main,footer").forEach(el => el.inert = true);
  document.body.classList.add("has-dialog"); $("#tourClose").focus();
  tourVideo.play().catch(() => {});
};
const closeTour = () => {
  tourVideo.pause(); tourModal.hidden = true;
  $$("nav.top,header,main,footer").forEach(el => el.inert = false);
  document.body.classList.remove("has-dialog"); $("#tourBtn").focus({ preventScroll: true });
};
$("#tourClose").onclick = closeTour;
tourModal.onclick = e => { if (e.target === tourModal) closeTour(); };
addEventListener("keydown", e => {
  if (tourModal.hidden) return;
  if (e.key === "Escape") closeTour();
  if (e.key === "Tab") {
    const close = $("#tourClose");
    if (e.shiftKey && document.activeElement === tourVideo) { e.preventDefault(); close.focus(); }
    else if (!e.shiftKey && document.activeElement === close) { e.preventDefault(); tourVideo.focus(); }
  }
});
function guideLinks() {
  const base = (DONATE.repo || "") + "/blob/main/docs/", suf = lang === "en" ? "" : "." + lang;
  const gd = $("#guideDeck"), gp = $("#guidePc");
  if (gd) gd.href = `${base}install-deck${suf}.md`;
  if (gp) gp.href = `${base}install-pc${suf}.md`;
  const dd = $("#downloadDeck"), sd = $("#shaDeck"), rd = $("#relDeck");
  const dp = $("#downloadPc"), sp = $("#shaPc"), rp = $("#relPc");
  const hd = $("#heroDownload");
  if (typeof RELEASE !== "undefined") {
    if (dd) dd.href = RELEASE.deck_zip;
    if (sd) sd.href = RELEASE.deck_sha;
    if (rd) rd.href = RELEASE.tag;
    if (dp) dp.href = RELEASE.pc_zip;
    if (sp) sp.href = RELEASE.pc_sha;
    if (rp) rp.href = RELEASE.tag;
  }
  if (hd) hd.href = "#install";
}

/* ── видео играют, только когда видны (Chrome сам глушит невидимые) ── */
const vio = new IntersectionObserver(es => es.forEach(e => {
  e.target.querySelectorAll("video").forEach(v => {
    const isBackground = !!v.closest(".s-bg,.hero-bg");
    const want = e.isIntersecting && (isBackground ? (v.classList.contains("on") && !backgroundsPaused) : (!reduced || REEL));
    if (want) v.play().catch(() => {}); else v.pause();
  });
}), { threshold: .05 });
[".hero-bg", ".s-bg", ".viz-home", ".rec-reel"].forEach(sel => vio.observe($(sel)));

/* ── появление секций ─────────────────────── */
const ro = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add("in"); ro.unobserve(e.target); } }), { threshold: .12 });
$$(".reveal").forEach(el => ro.observe(el));

/* ── ролик-тур: index.html?reel=1&lang=en (снимается скриптом, кадры — в README и на сайт) ── */
const QS = new URLSearchParams(location.search);
const REEL = QS.has("reel");
if (REEL) {
  const L0 = LANGS.includes(QS.get("lang")) ? QS.get("lang") : "en";
  lang = L0; device = "deck";
  window.__reelStart = () => runReel(L0);
}
async function runReel(L0) {
  backgroundsPaused = false; backgroundLabel();
  const R = $("#reel"), RT = REEL_TXT[L0];
  document.body.classList.add("reel"); R.hidden = false;
  const z = parseFloat(QS.get("zoom") || "1"); if (z !== 1) R.style.zoom = z;   // 1280×720-вёрстка на экран 1920×1080
  $(".rl-stage").append(dev); dev.classList.add("in");
  demoVisible = true; fitScreen();
  const cap = $(".rl-cap"), stage = $(".rl-stage"), full = $(".rl-full"), title = $(".rl-title"), bg = $(".rl-bg"), chip = $(".rl-chip");
  const fullV = full.querySelector("video"), bgImgs = [...bg.querySelectorAll("img")];
  let bgFlip = 0;
  const setBackdrop = g => {   // неподвижный размытый кадр игры за устройством — живое видео только на экране
    const nxt = bgImgs[bgFlip ^ 1]; nxt.src = media(g, "poster.jpg");
    nxt.onload = () => { nxt.classList.add("on"); bgImgs[bgFlip].classList.remove("on"); bgFlip ^= 1; };
  };
  const setCap = async (k, t) => {
    cap.classList.remove("on"); await sleep(420);
    $(".rl-kick").textContent = k; $(".rl-text").textContent = t; cap.classList.add("on");
  };
  const typeInto = async (el, text, ms = 38) => { el.textContent = ""; for (const ch of text) { el.textContent += ch; await sleep(ms); } };

  // 0 · заставка
  setBackdrop(GAMES[0]); bg.classList.add("on");
  document.documentElement.style.setProperty("--accent", "#e9cf96");
  title.classList.add("on"); $(".rl-url").textContent = "";
  await sleep(700); await typeInto($(".rl-tag"), RT.tag, 42); await sleep(1300);
  title.classList.remove("on"); await sleep(500);

  // 1 · Дека · God of War — где остановился
  setDevice("deck", false); renderGame(0);
  stage.classList.add("on"); setCap(RT.k1, RT.t1);
  await sleep(5600);
  // 2 · Until Dawn — доказанные факты, кто жив
  await setCap(RT.k2, RT.t2); renderGame(1); setBackdrop(GAMES[1]);
  await sleep(5200);
  // 3 · Nine Sols — язык из файлов игры: название перепечатывается на трёх языках
  await setCap(RT.k3, RT.t3);
  const order = [L0, ...LANGS.filter(x => x !== L0)];
  lang = order[0]; renderGame(4); setBackdrop(GAMES[4]);
  chip.textContent = order[0].toUpperCase(); chip.classList.add("on");
  await sleep(2600);
  for (const l of order.slice(1)) {
    lang = l; chip.textContent = l.toUpperCase(); chip.classList.remove("pop"); void chip.offsetWidth; chip.classList.add("pop");
    renderGame(4, { keepBg: true }); await sleep(2300);
  }
  chip.classList.remove("on"); lang = L0;
  // 4 · твой геймплей — запись Steam на весь экран
  await setCap(RT.k4, RT.t4);
  fullV.src = media(GAMES[0], "loop.mp4"); fullV.currentTime = 1; fullV.play().catch(() => {});
  stage.classList.remove("on"); full.classList.add("on"); bg.classList.remove("on");
  await sleep(2700);
  full.classList.remove("on"); await sleep(250);
  fullV.src = "media/1778820/loop.mp4"; fullV.play().catch(() => {}); full.classList.add("on");
  await sleep(2700);
  // 5 · ПК · Big Picture — «Продолжить»
  await setCap(RT.k5, RT.t5);
  full.classList.remove("on"); bg.classList.add("on");
  setDevice("pc", false); renderGame(0); setBackdrop(GAMES[0]); stage.classList.add("on");
  await sleep(2600); $("#sPlay").classList.add("pulse");
  await sleep(3000);
  // 6 · финал
  cap.classList.remove("on"); stage.classList.remove("on");
  document.documentElement.style.setProperty("--accent", "#e9cf96");
  $(".rl-tag").textContent = RT.end; $(".rl-url").textContent = "github.com/Alexsander720/continue";
  title.classList.add("on");
  await sleep(3800);
  window.__reelDone = true;
}

// старт
setDevice(device, false);
applyLang();
renderGame(0);
document.fonts && document.fonts.ready.then(fitPanel);
