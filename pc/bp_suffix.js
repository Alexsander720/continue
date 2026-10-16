// Public PC adapter: the shared production panel and Home; native controller glyphs.
const PC = { deckH: 534, footer: 0, playBar: 80, barGap: 12 };
Object.assign(I18N.en, { pc_continue: 'Continue', preset: 'Appearance mode', preset_desc: 'Light: no Home video. Balanced: backgrounds up to 720p. Maximum: up to 1080p.' });
Object.assign(I18N.ru, { pc_continue: 'Продолжить', preset: 'Режим оформления', preset_desc: 'Лёгкий: без видео на главной. Сбалансированный: фоны до 720p. Максимум: до 1080p.' });
Object.assign(I18N.uk, { pc_continue: 'Продовжити', preset: 'Режим оформлення', preset_desc: 'Легкий: без відео на головній. Збалансований: тло до 720p. Максимум: до 1080p.' });
function pcGeometry(win) {
  const s = win.innerHeight / PC.deckH;
  return { s, rootH: win.innerHeight / s, barBottom: (PC.playBar + PC.barGap) / s, barRight: win.innerWidth / s - 28 };
}
function pcCss(g) {
  const hd = DFL.appDetailsHeaderClasses || {}, bs = DFL.basicAppDetailsSectionStylerClasses || {};
  const c = k => "." + (hd[k] || "gh-none");
  const play = `${PC.playBar}px`, foot = `${PC.footer}px`;
  // «Clean Gameview» (SuchMeme, как на Деке: прозрачная строка, логотип закреплён) — шапка игры на весь экран
  let css = `
.BasicUI ${c("TopCapsule")}{height:calc(100vh - ${play} - ${foot})}
${c("HeaderBackgroundImage")}{height:calc(100vh - ${foot})}
.BasicUI ${c("TopCapsule")}${c("FullscreenEnterStart")}{animation-name:gh-godown;animation-duration:1s}
.BasicUI ${c("TopCapsule")}${c("FullscreenEnterDone")}{height:58vw}
${c("TitleSection")}{padding:0}
${c("SVGTitle")}{background:rgba(14,20,27,.5);padding:10px 0 16px 24px;margin-bottom:-6px;width:100%}
@keyframes gh-godown{from{height:calc(100vh - ${play} - ${foot})}to{height:58vw}}
${c("TitleSection")}{background:rgba(14,20,27,.33)}
/* полоса «Играть» прозрачная — playBarCss() в index.js (общая с Декой) */
${c("BoxSizer")}{--logo-max-height:120px;top:calc(100vh - var(--logo-max-height) * 1.3 - ${play} - ${foot})!important;max-height:var(--logo-max-height)}
.${DFL.playSectionClasses?.MenuButton || "gh-none"}{border-radius:10px}
${HUB_LOOK_CSS}
/* полоса фактов как в хабе: залитые значки, подписи светлее, тонкие разделители между ячейками */
.gh-fact{position:relative}
.gh-fact svg.gh-glyph{color:rgba(215,224,234,.72)}
.gh-fact .gh-icon-img{flex:none;object-fit:cover;border-radius:4px;filter:drop-shadow(0 2px 8px rgba(0,0,0,.6))}
.gh-fact .gh-icon-raven{object-fit:contain;border-radius:0}
.gh-fact .gh-icon-own{object-fit:contain;border-radius:0;filter:drop-shadow(0 2px 8px rgba(0,0,0,.75))}
.gh-fl{color:rgb(214,224,234)!important}
.gh-fact:not(.gh-rowstart)::before{content:"";position:absolute;left:-15px;top:50%;width:1px;height:38px;transform:translateY(-50%);
 background:linear-gradient(to bottom,transparent,rgba(214,224,234,.38),transparent)}
`;
  if (g) css += `
.gh-root{zoom:${g.s};height:${g.rootH}px!important}
.gh-factbar,.gh-shot{bottom:${g.barBottom}px!important}
`;
  return css;
}


function PC_HOME_CSS() { return ""; }
function pcGlobalCss() {
  const ab = DFL.appActionButtonClasses || {}, ft = DFL.footerClasses || {};
  const c = k => "." + (ab[k] || "gh-none");
  return `
${ft.BasicFooter ? `.${ft.BasicFooter}{display:none!important}` : ""}
${c("PlayButtonContainer")} ${c("ButtonChild")}{background:linear-gradient(135deg,rgba(238,244,251,.94) 0%,rgba(202,219,240,.9) 100%)!important;
 color:#0b1016!important;border-radius:3px!important;box-shadow:0 4px 16px rgba(0,0,0,.55),0 0 14px rgba(142,180,227,.25)!important;
 transition:background .18s,box-shadow .18s,transform .18s}
${c("PlayButtonContainer")} ${c("ButtonChild")} svg{color:#0b1016!important;fill:currentColor}
${c("PlayButtonContainer")} ${c("ButtonText")}{font-family:Georgia,"Noto Serif",serif!important;font-weight:700!important;
 letter-spacing:.22em!important;text-transform:uppercase!important;color:#0b1016!important}
${c("PlayButtonContainer")} ${c("ButtonChild")}.gpfocus,${c("PlayButtonContainer")} ${c("ButtonChild")}:hover{background:#fff!important;
 transform:translateY(-1px);box-shadow:0 6px 22px rgba(0,0,0,.6),0 0 24px rgba(142,180,227,.5)!important}
${c("PlayButtonContainer")}${c("Disabled")} ${c("ButtonChild")}{opacity:.55}
${PC_HOME_CSS()}
`;
}
let __ghGlobalStyle = null;
function ensureGlobalStyle() {
  try {
    const d = window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance?.BrowserWindow?.document;
    if (!d || !d.head) return;
    let st = d.getElementById("gh-pc-global");
    if (!st) { st = d.createElement("style"); st.id = "gh-pc-global"; d.head.appendChild(st); }
    const css = pcGlobalCss();
    if (st.textContent !== css) st.textContent = css;
    __ghGlobalStyle = st;
  } catch (e) { log("стиль", e); }
}


const __deckFitPanel = fitPanel;
fitPanel = function (el, bar, logo, width, shot, video) {
  __deckFitPanel(el, bar, logo, width, shot, video);
  const detail = el && video ? el.querySelector('.gh-detail') : null;
  if (!detail || detail.scrollHeight <= detail.clientHeight + 1) return;
  const available = fitBar(bar, width) - FIT.top - FIT.gap;
  const fits = () => el.getBoundingClientRect().height <= available;
  const scale = Number((el.style.transform.match(/scale\(([\d.]+)\)/) || [])[1]) || 1;
  const setLogo = height => { if (logo) { logo.style.maxHeight = height / scale + 'px'; logo.style.maxWidth = FIT.logoW / scale + 'px'; } };
  setLogo(FIT.logoMin);
  let lines = Number(detail.style.webkitLineClamp) || 4;
  while (detail.scrollHeight > detail.clientHeight + 1 && lines < 20) {
    detail.style.webkitLineClamp = String(lines + 1);
    if (!fits()) { detail.style.webkitLineClamp = String(lines); break; }
    lines++;
  }
  for (const height of FIT.logoH) { setLogo(height); if (fits()) return; }
  setLogo(FIT.logoMin);
};

const __ghBlur = new WeakMap();
function pcBusy(doc) {
  if (gameRunning() || doc.visibilityState === 'hidden') return true;
  if (doc.hasFocus()) { __ghBlur.delete(doc); return false; }
  if (!__ghBlur.has(doc)) __ghBlur.set(doc, Date.now());
  return Date.now() - __ghBlur.get(doc) > 3000;
}
usePlaybackGate = function (videoRef, enabled) {
  useEffect(() => {
    if (!enabled) return;
    const tick = () => {
      const video = videoRef.current;
      if (!video) return;
      if (pcBusy(video.ownerDocument)) { if (!video.paused) video.pause(); }
      else if (video.paused) video.play().catch(() => {});
    };
    const timer = setInterval(tick, 1000); tick();
    return () => clearInterval(timer);
  }, [enabled]);
};

// Reuse the production settings component through Steam's controller focusables.
// Startup-movie control lives in the Themes window on PC.
StartupMovieToggle = () => null;
UpdateRow = function () {
  useLanguage();
  const [update, setUpdate] = useState(null);
  useEffect(() => { call('check_update', false).then(setUpdate).catch(() => {}); }, []);
  return h(DFL.PanelSectionRow, null, h(DFL.ButtonItem, {
    onClick: () => call('check_update', true).then(setUpdate).catch(() => {}),
    description: update?.available ? t('update_to', update.latest) : t('update_offline')
  }, t('version_check', update?.current || '…')));
};

const __pcSettingsStyle = `
.DialogContent:has(.continue-pc-settings){width:min(700px,90vw)!important;max-height:90vh!important}
.continue-pc-settings{width:100%;max-height:78vh;overflow:auto;color:#e8edf3;padding:12px;font-family:Arial,sans-serif}
.continue-pc-row{margin:8px 0;padding:8px;border-bottom:1px solid #34414d;overflow-wrap:anywhere}
.continue-pc-control{display:block;width:100%;padding:10px;background:#354454;border-radius:5px;cursor:pointer;color:#fff}
.continue-pc-control.gpfocus,.continue-pc-control:focus{outline:3px solid #fff;background:#526e85}
.continue-pc-description{font-size:12px;line-height:1.5;color:#bac7d4;margin-top:5px}
`;
const F = DFL.Focusable;
const control = (props, text, activate) => h(F, { className: 'continue-pc-control', role: 'button', tabIndex: 0,
  'aria-label': props.label, onActivate: activate, onClick: activate, onCancelButton: props.onCancelButton }, text);
DFL.PanelSection = p => h('section', null, p.title ? h('h3', null, p.title) : null, p.children);
DFL.PanelSectionRow = p => h('div', { className: 'continue-pc-row' }, p.children);
DFL.ButtonItem = p => h('div', null, control(p, p.children, p.disabled ? undefined : p.onClick), p.description ? h('div', { className: 'continue-pc-description' }, p.description) : null);
DFL.ToggleField = p => h('div', null, control(p, p.label + ': ' + (p.checked ? '✓' : '○'), p.disabled ? undefined : () => p.onChange?.(!p.checked)), p.description ? h('div', { className: 'continue-pc-description' }, p.description) : null);
DFL.DropdownItem = p => {
  const index = Math.max(0, p.rgOptions.findIndex(o => o.data === p.selectedOption));
  return h('div', null, control(p, p.label + ': ' + p.rgOptions[index]?.label + ' ›', () => p.onChange?.(p.rgOptions[(index + 1) % p.rgOptions.length])), p.description ? h('div', { className: 'continue-pc-description' }, p.description) : null);
};
function openPcSettings(section='start') {
  const win = window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance;
  if (!DFL.showModalRaw || !DFL.ModalRoot || !win) return;
  const initialSection=['start','library','card','backgrounds','music','appearance','connections'].includes(section)?section:'start';
  DFL.showModalRaw(h(PcSettings,{initialSection}), win.BrowserWindow, 'Continue?', { strTitle: 'Continue?' }, undefined, { bHideActions: false }, win.m_ModalManager);
}
const __sharedButtons = HubAppButtons;
HubAppButtons = function () {
  const cls = DFL.playSectionClasses?.MenuButton || '';
  return h(React.Fragment, null, h(__sharedButtons), h(F, { className: cls, role: 'button', 'aria-label': 'Continue?',
    onActivate: openPcSettings, onClick: openPcSettings }, h('span', { style: { fontSize: 23 } }, '…')));
};

const PAD_PS = new Set([16, 18]), PAD_FULL = 1;
function isPadFeature(c) { return c && c.props && typeof c.props.feature === "number" && "minimode" in c.props && "overview" in c.props; }
function padShown(c) {   // компонент Steam сам решает, поддерживает ли игра признак: render() → null, если нет
  try { return c.type?.prototype?.render ? c.type.prototype.render.call({ props: c.props }) != null : true; } catch (e) { return true; }
}
function pcPadIcons(kids) {
  const ps = kids.filter(c => PAD_PS.has(c.props.feature) && padShown(c));
  return ps.length ? ps : kids.filter(c => c.props.feature === PAD_FULL && padShown(c)).slice(0, 1);
}

// Страница игры открывается сверху. Steam помнит прокрутку каждой страницы: один раз ушли вниз (к «Активности»,
// которой на ПК почти нет) — игра потом всегда открывается на пустом месте. Первые 1,5 с после открытия
// возвращаем наверх, если фокус на кнопках шапки (владелец сам ещё никуда не ушёл).
function useScrollTop(appid, anchorRef) {
  useEffect(() => {
    const el = anchorRef.current;
    const w = el?.ownerDocument?.defaultView;
    if (!w) return;
    let sc = el.parentElement;
    while (sc && !(sc.scrollHeight > sc.clientHeight + 40 && /auto|scroll/.test(w.getComputedStyle(sc).overflowY))) sc = sc.parentElement;
    if (!sc) return;
    const ps = DFL.basicAppDetailsSectionStylerClasses?.PlaySection;
    const top = () => {
      const a = el.ownerDocument.activeElement;
      const inHead = !a || a === el.ownerDocument.body || (ps && a.closest?.("." + ps));
      if (sc.scrollTop > 0 && inHead) sc.scrollTop = 0;
    };
    const ts = [0, 80, 250, 600, 1000, 1500].map(ms => setTimeout(top, ms));
    return () => ts.forEach(clearTimeout);
  }, [appid]);
}


function PcPageInner({ appid }) {
  const ref = useRef(null), [geometry, setGeometry] = useState(null);
  useScrollTop(appid, ref);
  useContinueLabel(appid, ref);
  const themeCss = useHubThemeCss(appid, ref, geometry ? geometry.s * PC.deckH : 0);
  useLayoutEffect(() => {
    const win = ref.current?.ownerDocument?.defaultView;
    if (!win) return;
    const update = () => setGeometry(pcGeometry(win)); update();
    win.addEventListener('resize', update);
    return () => win.removeEventListener('resize', update);
  }, []);
  if (geometry) { FIT.rootH = geometry.rootH; FIT.barBottom = geometry.barBottom; FIT.barRight = geometry.barRight; useHubLook(true); }
  return h(React.Fragment, null, h('style', { ref }, pcCss(geometry)), geometry ? h(GameHubPanel, { appid }) : null, themeCss ? h('style', null, themeCss) : null);
}
const __ghSwap = new Set();
function PcPage({ appid }) {
  const [next, setNext] = useState(null);
  useEffect(() => { const update = page => setNext(() => page); __ghSwap.add(update); return () => __ghSwap.delete(update); }, []);
  return next ? h(next, { appid }) : h(PcPageInner, { appid });
}
const PC_PLAY_LABELS = new Set(['Play', 'Играть', 'Грати']);
const __ghContinue = new Set(), __pcOriginalLabels = new Map();
function playLabelFix(doc, appid) {
  const cls = DFL.appActionButtonClasses?.ButtonText;
  if (!cls || !__ghContinue.has(appid)) return;
  doc.querySelectorAll('.' + cls).forEach(node => {
    if (!PC_PLAY_LABELS.has(node.textContent.trim())) return;
    if (!__pcOriginalLabels.has(node)) __pcOriginalLabels.set(node, node.textContent);
    node.textContent = t('pc_continue');
  });
}
function useContinueLabel(appid, anchorRef) {
  useEffect(() => {
    let alive = true;
    __ghContinue.delete(appid);
    call('get_card', appid).then(card => {
      if (!alive || !(card?.continue_available ?? !!card?.block?.title)) return;
      __ghContinue.add(appid);
      const doc = anchorRef.current?.ownerDocument;
      if (doc) playLabelFix(doc, appid);
    }).catch(() => {});
    return () => { alive = false; };
  }, [appid]);
}
function patchAppPagePC() {
  return keepJsxLayer('pc-page', (fn, type, props, key) => {
    const inner = DFL.appDetailsClasses?.InnerContainer, text = DFL.appActionButtonClasses?.ButtonText;
    if (props && Array.isArray(props.children) && props.children.length > 1 && props.children.every(isPadFeature)
        && pluginSettings.pc_pads !== 'native') {
      props = { ...props, children: pcPadIcons(props.children) };
    } else if (props && PC_PLAY_LABELS.has(props.children) && text && typeof props.className === 'string'
        && props.className.split(' ').includes(text) && __ghContinue.has(currentAppId())) {
      props = { ...props, children: t('pc_continue') };
    } else if (inner && props && Array.isArray(props.children) && typeof props.className === 'string'
        && props.className.split(' ').includes(inner)) {
      const appid = currentAppId();
      if (appid && !props.children.some(child => child?.key === 'continue-panel')) {
        const children = props.children.slice(); children.splice(1, 0, h(PcPage, { key: 'continue-panel', appid }));
        props = { ...props, children };
      }
    }
    return fn.call(this, type, props, key);
  });
}
const PS_TYPES = new Set([33, 34, 45, 48]), PS5 = 45;
const HOME_TABS = new Set(['WhatsNew', 'Friends', 'Recommended']);
function patchPcVisuals() {
  return keepJsxLayer('pc-visuals', (fn, type, props, key) => {
    if (props && pluginSettings.pc_glyphs !== 'native') {
      try {
        const find = typeof __ghBoot !== 'undefined' && __ghBoot.glyphFind;
        if (typeof props.controllerType === 'number' && props.controllerSource !== undefined && props.controllerModeInput !== undefined
            && !PS_TYPES.has(props.controllerType) && (!find || find(props.controllerSource, props.controllerModeInput, PS5, props.controllerStyle, props.knockout)))
          props = { ...props, controllerType: PS5 };
        else if (type === 'img' && typeof props.src === 'string' && props.src.includes('/steaminputglyphs/xbox_button_logo.svg'))
          props = { ...props, src: props.src.replace('xbox_button_logo.svg', 'ps4_button_logo.svg') };
      } catch (error) { log('glyph', error); }
    }
    if (Array.isArray(props?.children)) { const menu = withThemesItem(props.children); if (menu) props = { ...props, children: menu }; }
    if (Array.isArray(props?.children) && !props.children.some(child => child?.key === 'continue-themes')) {
      const nested = props.children.findIndex(Array.isArray);
      const menu = nested >= 0 ? withThemesItem(props.children[nested]) : null;
      if (menu) props = { ...props, children: props.children.map((child, i) => i === nested ? menu : child) };
    }
    if (pluginSettings.pc_home !== 'native' && type === 'img' && typeof props?.src === 'string') {
      const large = hero4k(props.src); if (large) props = { ...props, src: large };
    }
    if (pluginSettings.pc_home !== 'native' && Array.isArray(props?.tabs) && props.tabs.some(tab => HOME_TABS.has(tab.id))) return null;
    return fn.call(this, type, props, key);
  });
}
try { window.__ghPC?.unload?.(PcPage); } catch (error) { log('unload', error); }
const __stopTab = patchLibraryDefaultTab(), __stopPage = patchAppPagePC(), __stopButtons = patchAppButtons(), __stopVisuals = patchPcVisuals(), __stopBattery = patchPadBattery(), __stopLaunchNotice = ensureLaunchNoticeHidden();
ensureGlobalStyle();
const __globalStyleTimer = setInterval(ensureGlobalStyle, 2000);
let __pcMounted = true;
call('get_settings').then(settings => {
  if (!__pcMounted) return;
  pluginSettings = settings || {};
  pcMoviePrevious = settings?.startup_movie_prev || null;
  settingsListeners.forEach(listener => listener(pluginSettings));
}).catch(error => log('settings', error));
applyHomeLiveSetting(true);
window.__ghPC = {
  ver: __GH_VER__,
  reply(id, ok, value) { const pending = __ghPending.get(id); if (!pending) return; __ghPending.delete(id); ok ? pending.resolve(value) : pending.reject(new Error(value)); },
  debug: { FIT, settings: openPcSettings, art: openArtPicker, music: openMusicPicker, themes: openThemes,
    movie: setStartupMovie, movieState: () => { const s = steamSettingsApi()?.store.m_ClientSettings || {}; return {id:String(s.startup_movie_id ?? '0'),path:s.startup_movie_local_path || '',shuffle:!!s.startup_movie_shuffle}; } },
  unload(next) {
    __pcMounted = false;
    if (unpatchHomeLive) { unpatchHomeLive(); unpatchHomeLive = null; }
    clearInterval(__globalStyleTimer);
    pcHeroTimers.forEach(clearTimeout); pcHeroTimers.clear();
    for (const [img, original] of pcHeroOriginals) { if ([...pcHeroCache.values()].includes(img.src)) img.src = original; }
    pcHeroOriginals.clear();
    __ghGlobalStyle?.remove();
    for (const [node, original] of __pcOriginalLabels) { if (node.textContent === t('pc_continue')) node.textContent = original; }
    __pcOriginalLabels.clear();
    __stopLaunchNotice(); __stopBattery(); __stopVisuals(); __stopButtons(); __stopPage(); __stopTab();
    if (next) __ghSwap.forEach(update => update(next));
    __ghPending.forEach(p => p.reject(new Error('Continue? unloaded'))); __ghPending.clear();
    return next ? Promise.resolve(true) : restorePcStartupMovie();
  }
};
