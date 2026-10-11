// Public PC adapter: the shared production panel and Home; native controller glyphs.
const PC = { deckH: 534, footer: 0, playBar: 80, barGap: 12 };
function pcGeometry(win) {
  const s = win.innerHeight / PC.deckH;
  return { s, rootH: win.innerHeight / s, barBottom: (PC.playBar + PC.barGap) / s, barRight: win.innerWidth / s - 28 };
}
function pcCss(g) {
  const hd = DFL.appDetailsHeaderClasses, c = k => '.' + (hd[k] || 'gh-none');
  return `
.BasicUI ${c('TopCapsule')}{height:calc(100vh - 80px)}
${c('HeaderBackgroundImage')}{height:100vh}
${c('TitleSection')}{padding:0;background:rgba(14,20,27,.33)}
${c('SVGTitle')}{background:rgba(14,20,27,.5);padding:10px 0 16px 24px;width:100%}
${c('BoxSizer')}{--logo-max-height:120px;top:calc(100vh - var(--logo-max-height)*1.3 - 80px)!important;max-height:var(--logo-max-height)}
${HUB_LOOK_CSS}
${g ? `.gh-root{zoom:${g.s};height:${g.rootH}px!important}.gh-factbar,.gh-shot{bottom:${g.barBottom}px!important}` : ''}`;
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
// No startup movie file or Linux display setting is installed on Windows.
StartupMovieToggle = () => null;
UpdateRow = function () {
  useLanguage();
  const [update, setUpdate] = useState(null);
  useEffect(() => { call('check_update', false).then(setUpdate).catch(() => {}); }, []);
  return h(DFL.PanelSectionRow, null, h(DFL.ButtonItem, {
    onClick: () => call('check_update', true).then(setUpdate).catch(() => {}),
    description: update?.available ? t('update_to', update.latest) : t('update_offline')
  }, t('version_check', update?.current || '0.1.0')));
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
function openPcSettings() {
  const win = window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance;
  if (!DFL.showModalRaw || !DFL.ModalRoot || !win) return;
  const Settings = ({ closeModal }) => h(DFL.ModalRoot, { closeModal, onCancel: closeModal, bAllowFullSize: true },
    h('style', null, __pcSettingsStyle), h(F, { className: 'continue-pc-settings', 'flow-children': 'column', onCancelButton: closeModal }, h(QamContent)));
  DFL.showModalRaw(h(Settings), win.BrowserWindow, 'Continue?', { strTitle: 'Continue?' }, undefined, { bHideActions: false });
}
const __sharedButtons = HubAppButtons;
HubAppButtons = function () {
  const cls = DFL.playSectionClasses?.MenuButton || '';
  return h(React.Fragment, null, h(__sharedButtons), h(F, { className: cls, role: 'button', 'aria-label': 'Continue?',
    onActivate: openPcSettings, onClick: openPcSettings }, h('span', { style: { fontSize: 23 } }, '…')));
};

function PcPageInner({ appid }) {
  const ref = useRef(null), [geometry, setGeometry] = useState(null);
  useLayoutEffect(() => {
    const win = ref.current?.ownerDocument?.defaultView;
    if (!win) return;
    const update = () => setGeometry(pcGeometry(win)); update();
    win.addEventListener('resize', update);
    return () => win.removeEventListener('resize', update);
  }, []);
  if (geometry) { FIT.rootH = geometry.rootH; FIT.barBottom = geometry.barBottom; FIT.barRight = geometry.barRight; useHubLook(true); }
  return h(React.Fragment, null, h('style', { ref }, pcCss(geometry)), geometry ? h(GameHubPanel, { appid }) : null);
}
const __ghSwap = new Set();
function PcPage({ appid }) {
  const [next, setNext] = useState(null);
  useEffect(() => { const update = page => setNext(() => page); __ghSwap.add(update); return () => __ghSwap.delete(update); }, []);
  return next ? h(next, { appid }) : h(PcPageInner, { appid });
}
function patchAppPagePC() {
  const jsx = window.SP_JSX, inner = DFL.appDetailsClasses?.InnerContainer;
  if (!jsx || !inner || jsx.__ghPage) return () => {};
  const orig = { jsx: jsx.jsx, jsxs: jsx.jsxs };
  const wrap = fn => function (type, props, key) {
    if (props && Array.isArray(props.children) && typeof props.className === 'string' && props.className.split(' ').includes(inner)) {
      const appid = currentAppId();
      if (appid && !props.children.some(child => child?.key === 'continue-panel')) {
        const children = props.children.slice(); children.splice(1, 0, h(PcPage, { key: 'continue-panel', appid }));
        props = { ...props, children };
      }
    }
    return fn.call(this, type, props, key);
  };
  jsx.jsx = wrap(orig.jsx); jsx.jsxs = wrap(orig.jsxs); jsx.__ghPage = true;
  return () => { jsx.jsx = orig.jsx; jsx.jsxs = orig.jsxs; delete jsx.__ghPage; };
}
try { window.__ghPC?.unload?.(PcPage); } catch (error) { log('unload', error); }
const __stopTab = patchLibraryDefaultTab(), __stopPage = patchAppPagePC(), __stopButtons = patchAppButtons(), __stopBattery = patchPadBattery();
applyHomeLiveSetting(true);
window.__ghPC = {
  ver: __GH_VER__,
  reply(id, ok, value) { const pending = __ghPending.get(id); if (!pending) return; __ghPending.delete(id); ok ? pending.resolve(value) : pending.reject(new Error(value)); },
  debug: { FIT, settings: openPcSettings },
  unload(next) {
    if (unpatchHomeLive) { unpatchHomeLive(); unpatchHomeLive = null; }
    __stopBattery(); __stopButtons(); __stopPage(); __stopTab();
    if (next) __ghSwap.forEach(update => update(next));
    __ghPending.forEach(p => p.reject(new Error('Continue? unloaded'))); __ghPending.clear();
  }
};
