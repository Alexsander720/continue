// Optional public visual decorator. Owns no card data, bridge or React component.
(() => {
  const config = /*CONTINUE_THEME_CONFIG*/null;
  if (!config?.payload) return false;
  const {payload, version, leaseMs} = config;
  const current = window.__continueOwnerTheme;
  if (current?.app === payload.app && current.version === version) { current.renew(); return true; }
  current?.unload();
  const view = window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance;
  const doc = view?.BrowserWindow?.document;
  const root = doc?.querySelector('.gh-root');
  const owner = window.__ghPC, bridge = window.__ghBridge;
  const path = () => view?.m_history?.location?.pathname;
  if (!root || doc.querySelectorAll('.gh-root').length !== 1 || !owner || typeof bridge !== 'function' || path() !== '/library/app/' + payload.app) return false;
  const records = new Map();
  const owned = new Set();
  let timer, alive = true, until = Date.now() + leaseMs;
  const own = el => { owned.add(el); return el; };
  function hide(el, inserted = null) {
    const original = el.getAttribute('class');
    el.classList.add('continue-owner-original');
    records.set(el, {original, patched:el.getAttribute('class'), inserted});
  }
  function restore(el, rec) {
    rec.inserted?.remove();
    if (rec.inserted) owned.delete(rec.inserted);
    if (el.getAttribute('class') === rec.patched) {
      if (rec.original === null) el.removeAttribute('class'); else el.setAttribute('class', rec.original);
    } else el.classList.remove('continue-owner-original');
  }
  function unload() {
    if (!alive) return true;
    alive = false;
    clearInterval(timer);
    releaseVideo();
    for (const [el, rec] of records) restore(el, rec);
    for (const el of owned) el.remove();
    records.clear(); owned.clear();
    if (window.__continueOwnerTheme === api) delete window.__continueOwnerTheme;
    return true;
  }
  const css = own(doc.createElement('style'));
  css.textContent = '.continue-owner-original{display:none!important}.continue-owner-icon{width:34px!important;height:34px!important;object-fit:contain!important;flex:none!important;filter:drop-shadow(0 2px 6px rgba(0,0,0,.8))}.continue-owner-rail{pointer-events:none!important;object-fit:contain!important}';
  if (/^#[0-9a-f]{6}$/i.test(payload.accent || '')) css.textContent += `.gh-root .gh-kicker{color:${payload.accent}!important}`;
  root.appendChild(css);
  let video;
  function releaseVideo() {
    if (!video) return;
    video.pause(); video.removeAttribute('src'); video.load();
    video.remove(); owned.delete(video); video = null;
  }
  // A hidden Big Picture window rejects play() to save power; that is not a
  // broken file. Keep the layer and resume once the window is visible again.
  function playVideo() {
    video?.play()?.catch(error => { if (error?.name === 'NotSupportedError') releaseVideo(); });
  }
  if (/^http:\/\/127\.0\.0\.1:[0-9]+\/recordings\/[1-9][0-9]*\.mp4\?key=[a-f0-9]{64}(?:&v=[0-9]+)?$/.test(payload.recording || '')) {
    video = own(doc.createElement('video'));
    video.className = 'gh-bg continue-owner-recording';
    video.muted = true; video.defaultMuted = true; video.loop = true; video.autoplay = true; video.playsInline = true;
    video.setAttribute('aria-hidden', 'true');
    video.style.cssText = 'pointer-events:none;opacity:0;';
    video.onloadeddata = () => { if (video) video.style.opacity = '1'; };
    video.onerror = releaseVideo;
    video.src = payload.recording;
    const shade = root.querySelector('.gh-shade'), bg = root.querySelector('.gh-bg');
    if (shade) shade.before(video); else if (bg) bg.after(video); else root.prepend(video);
    playVideo();
  }
  let rail;
  if (payload.rail) {
    rail = own(doc.createElement('img'));
    rail.className = 'continue-owner-rail';
    rail.alt = ''; rail.setAttribute('aria-hidden', 'true'); rail.src = payload.rail;
    rail.style.cssText = 'display:block;position:absolute;top:2px;bottom:auto;width:auto;height:auto;';
    rail.onerror = () => {
      if (!rail) return;
      rail.remove(); owned.delete(rail); rail = null;
      for (const [el, rec] of records) if (el.classList.contains('gh-rule')) { restore(el, rec); records.delete(el); }
    };
  }
  function tick() {
    if (!alive) return;
    if (video && !root.contains(video)) { unload(); return; }
    // The hub may render its own background video after injection; stay above it.
    const shade = video && root.querySelector(':scope > .gh-shade');
    if (shade && video.nextElementSibling !== shade) shade.before(video);
    if (video?.paused && !doc.hidden) playVideo();
    if (Date.now() > until || window.__ghPC !== owner || window.__ghBridge !== bridge ||
        path() !== '/library/app/' + payload.app || !root.isConnected || doc.querySelector('.gh-root') !== root) { unload(); return; }
    for (const [el, rec] of records) if (!root.contains(el)) { restore(el, rec); records.delete(el); }
    const panel = root.querySelector('.gh-panel');
    if (rail && panel) {
      if (rail.parentNode !== panel) panel.appendChild(rail);
      const rule = panel.querySelector('.gh-rule');
      if (rule && !records.has(rule)) hide(rule);
      const r = root.getBoundingClientRect(), p = panel.getBoundingClientRect();
      const scale = panel.offsetWidth ? p.width / panel.offsetWidth : 1;
      const rootScale = root.offsetHeight ? r.height / root.offsetHeight : 1;
      const facts = root.querySelector('.gh-factbar')?.getBoundingClientRect();
      const end = Math.min(r.bottom - 8 * rootScale, facts ? facts.top - 16 * rootScale : r.bottom - 92 * rootScale);
      const width = Math.max(0, Math.min(24, 48 / scale, (p.left - r.left) / scale - 4));
      rail.style.maxWidth = width + 'px';
      rail.style.maxHeight = Math.max(0, (end - p.top) / scale - 2) + 'px';
      rail.style.left = (-width - 4) + 'px';
    }
    for (const fact of root.querySelectorAll('.gh-fact')) {
      const label = fact.querySelector('.gh-fl')?.textContent.trim();
      const src = payload.icons[label];
      const original = fact.querySelector('svg.gh-glyph,img.gh-icon-own');
      if (!original) continue;
      const rec = records.get(original);
      if (rec && (!src || rec.inserted?.getAttribute('src') !== src ||
          rec.inserted?.parentNode !== original.parentNode || !original.classList.contains('continue-owner-original'))) { restore(original, rec); records.delete(original); }
      if (!src || records.has(original)) continue;
      const img = own(doc.createElement('img'));
      img.className = 'continue-owner-icon'; img.alt = ''; img.setAttribute('aria-hidden', 'true'); img.src = src;
      original.before(img); hide(original, img);
    }
  }
  const api = {app:payload.app, version, renew:() => { until = Date.now() + leaseMs; tick(); return alive; }, unload};
  window.__continueOwnerTheme = api;
  timer = setInterval(tick, 250);
  tick();
  return alive;
})()
