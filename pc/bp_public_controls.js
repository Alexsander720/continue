// Standalone PC controls retain the existing Big Picture presentation.
Object.assign(I18N.en, {"pc_art": "Artwork", "pc_music": "Music", "pc_themes": "Themes", "pc_grid": "Cover", "pc_hero": "Background", "pc_logo": "Logo", "pc_wide": "Wide", "pc_reset_art": "Restore default", "pc_art_loading": "Loading from SteamGridDB…", "pc_applying": "Applying…", "pc_empty": "Nothing found", "pc_auto": "Auto", "pc_no_music": "No music", "pc_search": "Search", "pc_search_for": "Search: ", "pc_menu_music": "Main menu", "pc_song_query": "Your song or search query", "pc_youtube_search": "Searching YouTube…", "pc_downloading": " — downloading…", "pc_on": "On", "pc_off": "Off", "pc_collapse": "Collapse", "pc_configure": "Configure", "pc_loading": "Loading…", "pc_required": "Required by: ", "pc_builtin": "Already provided by Continue? on PC", "pc_themes_desc": "The same CSS Loader themes as on Deck. Changes apply immediately; PC has its own settings.", "pc_key_setup": "Enter your SteamGridDB API key", "pc_key_save": "Save key", "pc_music_setup": "Allow YouTube theme music and install yt-dlp", "pc_music_consent": "Music search and download use YouTube. Enable only if you agree.", "pc_wait_game": "Available after the game closes"});
Object.assign(I18N.ru, {"pc_art": "Картинки", "pc_music": "Музыка", "pc_themes": "Темы", "pc_grid": "Обложка", "pc_hero": "Фон", "pc_logo": "Логотип", "pc_wide": "Широкая", "pc_reset_art": "Вернуть стандартную", "pc_art_loading": "Загружаю из SteamGridDB…", "pc_applying": "Ставлю…", "pc_empty": "Ничего не нашлось", "pc_auto": "Авто", "pc_no_music": "Без музыки", "pc_search": "Найти", "pc_search_for": "Искать: ", "pc_menu_music": "Главное меню", "pc_song_query": "Своя песня или запрос", "pc_youtube_search": "Ищу на YouTube…", "pc_downloading": " — скачиваю…", "pc_on": "Вкл", "pc_off": "Выкл", "pc_collapse": "Свернуть", "pc_configure": "Настроить", "pc_loading": "Загружаю…", "pc_required": "Нужна для: ", "pc_builtin": "На ПК это уже делает Continue?", "pc_themes_desc": "Те же темы, что в CSS Loader на Деке. Меняются сразу, настройки ПК свои.", "pc_key_setup": "Введите свой API-ключ SteamGridDB", "pc_key_save": "Сохранить ключ", "pc_music_setup": "Разрешить музыку из YouTube и установить yt-dlp", "pc_music_consent": "Поиск и загрузка музыки используют YouTube. Включайте, если согласны.", "pc_wait_game": "Доступно после закрытия игры"});
Object.assign(I18N.uk, {"pc_art": "Зображення", "pc_music": "Музика", "pc_themes": "Теми", "pc_grid": "Обкладинка", "pc_hero": "Тло", "pc_logo": "Логотип", "pc_wide": "Широка", "pc_reset_art": "Відновити стандартну", "pc_art_loading": "Завантажую зі SteamGridDB…", "pc_applying": "Застосовую…", "pc_empty": "Нічого не знайдено", "pc_auto": "Авто", "pc_no_music": "Без музики", "pc_search": "Знайти", "pc_search_for": "Шукати: ", "pc_menu_music": "Головне меню", "pc_song_query": "Власна пісня або запит", "pc_youtube_search": "Шукаю на YouTube…", "pc_downloading": " — завантажую…", "pc_on": "Увімк", "pc_off": "Вимк", "pc_collapse": "Згорнути", "pc_configure": "Налаштувати", "pc_loading": "Завантажую…", "pc_required": "Потрібна для: ", "pc_builtin": "На ПК це вже робить Continue?", "pc_themes_desc": "Ті самі теми, що в CSS Loader на Деці. Зміни одразу, налаштування ПК окремі.", "pc_key_setup": "Введіть власний API-ключ SteamGridDB", "pc_key_save": "Зберегти ключ", "pc_music_setup": "Дозволити музику з YouTube та встановити yt-dlp", "pc_music_consent": "Пошук і завантаження музики використовують YouTube. Увімкніть, якщо згодні.", "pc_wait_game": "Доступно після закриття гри"});
const HUB_GLYPHS = (typeof __PC_GLYPHS__ === 'undefined' ? {} : __PC_GLYPHS__);
// Original geometric SVGs: white paths, no fonts, downloaded art or backgrounds.
const PC_BUTTON_PATHS = {
  a:'M10 23L16 9L22 23M12 19H20', b:'M11 9V23H17C24 23 24 16 17 16H11M17 16C23 16 23 9 17 9H11',
  x:'M10 10L22 22M22 10L10 22', y:'M10 9L16 16L22 9M16 16V23',
  cross:'M10 10L22 22M22 10L10 22',circle:'M24 16A8 8 0 1 0 8 16A8 8 0 1 0 24 16',
  square:'M9 9H23V23H9Z',triangle:'M16 8L25 24H7Z',
  menu:'M9 10H23M9 16H23M9 22H23',view:'M8 8H19V19H8ZM19 13H24V24H13V19',
  options:'M10 11H22M10 16H22M10 21H22',share:'M16 23V9M11 14L16 9L21 14M10 20V24H22V20',
  steam_menu:'M10 11H22M10 16H22M10 21H22',steam_view:'M10 16H10.1M16 16H16.1M22 16H22.1',
  l:'M5 11V22H11',r:'M5 22V11H9C15 11 15 17 9 17H5M9 17L13 22',
  bumper:'M19 11V22H23C29 22 29 16 23 16H19M23 16C28 16 28 11 23 11H19',
  one:'M20 13L23 11V22M20 22H26',two:'M19 13C20 9 27 10 26 14L19 22H27',
  trigger:'M18 11H28M23 11V22',
};
function pcControllerSvg(paths,frame=true) {
  return 'data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'+(frame?'<circle cx="16" cy="16" r="14"/>':'')+'<path d="'+paths+'"/></svg>');
}
function pcControllerGlyph(source,family) {
  if(!['xbox','playstation','steam'].includes(family)||typeof source!=='string')return null;
  let file;
  try { const u=new URL(source);if(u.hostname!=='steamloopback.host'||!u.pathname.startsWith('/steaminputglyphs/'))return null;file=u.pathname.split('/').pop().replace(/\.svg$/,''); }catch{return null;}
  const match=/^(?:xbox|ps|ps4|ps5|shared|steam|steamdeck|steam_controller)_button_(a|b|x|y|cross|circle|square|triangle|start|back|menu|view|options|share|lb|rb|lt|rt|l1|r1|l2|r2)$/.exec(file);
  if(!match)return null;
  let key=match[1];
  if(/^ps/.test(file)&&key==='x')key='a';
  key=({cross:'a',circle:'b',square:'x',triangle:'y',menu:'start',view:'back',options:'start',share:'back',l1:'lb',r1:'rb',l2:'lt',r2:'rt'})[key]||key;
  if(['lb','rb','lt','rt'].includes(key))return pcControllerSvg(PC_BUTTON_PATHS[key[0]]+PC_BUTTON_PATHS[family==='playstation'?(key[1]==='t'?'two':'one'):(key[1]==='t'?'trigger':'bumper')]);
  if(key==='start'||key==='back')key=family==='playstation'?(key==='start'?'options':'share'):family==='steam'?(key==='start'?'steam_menu':'steam_view'):(key==='start'?'menu':'view');
  else if(family==='playstation')key=({a:'cross',b:'circle',x:'square',y:'triangle'})[key]||key;
  return PC_BUTTON_PATHS[key]?pcControllerSvg(PC_BUTTON_PATHS[key]):null;
}
const pcGlyphOriginals=new Map();
function pcRefreshControllerGlyphs(restore=false) {
  const doc=typeof uiDocument==='function'?uiDocument():null;
  if(doc)for(const img of doc.querySelectorAll('img')){
    const record=pcGlyphOriginals.get(img);
    const attribute=img.getAttribute('data-continue-glyph-source');
    const fromJsx=attribute&&['xbox','playstation','steam'].some(family=>img.src===pcControllerGlyph(attribute,family));
    const original=fromJsx?attribute:record&&img.src===record.injected?record.original:img.src;
    if(attribute&&attribute!==original)img.setAttribute('data-continue-glyph-source',original);
    const src=restore?null:pcControllerGlyph(original,pluginSettings.pc_glyphs);
    if(src){pcGlyphOriginals.set(img,{original,injected:src});if(img.src!==src)img.src=src;}
    else if(record||attribute){if(img.src!==original)img.src=original;pcGlyphOriginals.delete(img);}
  }
  for(const [img,record]of pcGlyphOriginals)if(restore||!img.isConnected){if(restore&&img.src===record.injected)img.src=record.original;pcGlyphOriginals.delete(img);}
}
function pcSupportGlyph(family) {
  const shape=family==='playstation'?'M6 11Q8 8 12 11H20Q24 8 26 11L29 24Q28 28 24 24L21 21H11L8 24Q4 28 3 24Z':family==='steam'?'M4 7H28V25H4ZM12 10H20V22H12M7 13V19M25 13V19':'M7 10Q10 8 13 11H19Q22 8 25 10L29 24Q28 28 24 24L21 20H11L8 24Q4 28 3 24Z';
  return pcControllerSvg(shape+'M7 15H11M9 13V17M23 14H23.1M25 17H25.1',false);
}
const HUB_ICON = { trophy: "ach", camera: "cam", sun: "star", moon: "star", shrine: "target", beast: "shield", leaf: "bookmark",
  mask: "heart", wheel: "bolt", hourglass: "stopwatch", jump: "trend", bag: "backpack", tooth: "sword" };
const __deckIcon = Icon;
const PC_ICON_NAMES = typeof __PC_ICON_NAMES__ === 'undefined' ? Object.keys(ICONS) : __PC_ICON_NAMES__;
Icon = function ({ name }) {
  if (typeof name === 'string' && name.startsWith('img:')) return __deckIcon({name});
  if (typeof name === 'string' && name.startsWith('steamimg:') && pcSteamImage(name.slice(9)))
    return h('img', {className:'gh-icon-img',src:name.slice(9)});
  if (typeof name === 'string' && PC_ICON_NAMES.includes(name))
    return h('img', {className:'gh-icon-img gh-icon-own',src:DATA+'icons/'+name+'.svg',onError:e=>{e.currentTarget.style.display='none';}});
  return __deckIcon({ name });
};

function pcSteamImage(value) {
  try { const u = new URL(value); return u.protocol === 'https:' && !u.username && !u.password &&
    ['shared.steamstatic.com','cdn.steamstatic.com','cdn.akamai.steamstatic.com','steamcdn-a.akamaihd.net','cdn.cloudflare.steamstatic.com'].includes(u.hostname); }
  catch (_) { return false; }
}
function pcLatestAchievement(value) {
  if (!value || !Number.isInteger(value.nAchieved) || value.nAchieved < 1) return null;
  const achieved = new Map();
  for (const item of [...(value.vecHighlight || []), ...(value.vecAchievedHidden || [])]) {
    if (item?.bAchieved !== true || typeof item.strID !== 'string' || typeof item.strName !== 'string'
        || !Number.isFinite(item.rtUnlocked) || item.rtUnlocked <= 0) continue;
    achieved.set(item.strID, item);
  }
  // Steam can expose only highlights. Claim latest only if the full achieved
  // count is accounted for in the supplied native history.
  if (achieved.size !== value.nAchieved) return null;
  const item = [...achieved.values()].sort((a,b) => b.rtUnlocked - a.rtUnlocked)[0];
  return {name:item.strName,icon:pcSteamImage(item.strImage) ? 'steamimg:' + item.strImage : 'trophy'};
}
const pcBaseAchievements = useAchievements;
useAchievements = function(appid) {
  const summary = pcBaseAchievements(appid);
  let latest = null;
  try { latest = pcLatestAchievement(window.appDetailsStore?.GetAchievements?.(appid)); } catch (_) {}
  return summary ? {...summary, latest} : null;
};

// Разделители рисуются слева от ячейки, кроме первой в ряду (в два ряда — у каждого ряда своя первая).
const __deckFitBar = fitBar;
fitBar = function (bar, width) {
  const r = __deckFitBar(bar, width);
  if (bar) {
    const cols = Number((/repeat\((\d+)/.exec(bar.style.gridTemplateColumns) || [])[1]) || 1;
    [...bar.querySelectorAll(".gh-fact")].filter(f => f.style.display !== "none")
      .forEach((f, i) => f.classList.toggle("gh-rowstart", i % cols === 0));
  }
  return r;
};

function translateHubTheme(cls, css, winH) {
  const ab = DFL.appActionButtonClasses;
  const btn = `.${ab.PlayButtonContainer} .${ab.ButtonChild}`, btnText = `${btn} .${ab.ButtonText}`;
  const remPanel = 13.33 * 534 / 720, remSteam = 13.33 * winH / 720;
  const MAP = [
    [/^\.continue \.tri$/, [`${btn} svg`], "steam"],
    [/^\.continue:hover$/, [`${btn}:hover`], "steam", [`${btn}:hover .${ab.ButtonText}`]],
    [/^\.continue:focus-visible$/, [`${btn}.gpfocus`], "steam", [`${btn}.gpfocus .${ab.ButtonText}`]],
    [/^\.continue$/, [btn], "steam", [btnText]],
    [/^\.label$/, [".gh-kicker"]], [/^\.objective-sub$/, [".gh-sub"]], [/^\.objective$/, [".gh-title"]],
    [/^\.desc$/, [".gh-detail"]], [/^\.fact-lbl$/, [".gh-fl"]], [/^\.fact-val$/, [".gh-fv"]],
    [/^\.fact-glyph$/, [".gh-fact svg.gh-glyph"]], [/^\.fact-icon$/, [".gh-fact .gh-icon-img"]],
    [/^\.fact-sep$/, [".gh-fact:not(.gh-rowstart)::before"]],
    [/^\.scrim$/, [".gh-shade"]], [/^\.scrim::after$/, [".gh-shade::after"]],
    [/^#cardCopyFrame::before$/, [".gh-rule::before"]],
    [/^#cardCopyFrame$/, [".gh-rule"], "rail"],
  ];
  const out = [];
  const body = css.replace(/\/\*[\s\S]*?\*\//g, "");
  for (const m of body.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const sels = m[1].split(",").map(x => x.trim());
    let decl = m[2];
    for (const sel of sels) {
      const prefix = `body.${cls} `;
      if (!sel.startsWith(prefix)) continue;
      const rest = sel.slice(prefix.length).trim();
      const hit = MAP.find(([re]) => re.test(rest));
      if (!hit) continue;
      const [, targets, kind, textTargets] = hit;   // textTargets — подпись кнопки: только шрифт и цвет, без фона
      let d = decl;
      if (kind === "rail") {   // полоска хаба — border-left у колонки; у нас — отдельная линия .gh-rule: берём только цвет
        const c = /border-left(?:-color)?\s*:\s*(?:[\d.]+(?:px|rem)\s+solid\s+)?([^;]+)/.exec(d);
        if (!c) continue;
        d = `background:${c[1].trim()}`;
      }
      const rem = kind === "steam" ? remSteam : remPanel;
      d = d.replace(/(-?\d*\.?\d+)rem\b/g, (_, n) => `${(parseFloat(n) * rem).toFixed(2)}px`)
        .split(";").map(x => x.trim()).filter(Boolean)
        .map(x => /!important$/.test(x) ? x : x + "!important").join(";");
      out.push(`${targets.map(t => `html.gh-hub-${cls} ${t}`).join(",")}{${d}}`);
      const textD = d.split(";").filter(x => /^(font|color|letter-spacing|text-)/.test(x)).join(";");
      if (textTargets && textD) out.push(`${textTargets.map(t => `html.gh-hub-${cls} ${t}`).join(",")}{${textD}}`);
    }
  }
  return out.join("\n");
}
const PC_GAME_STYLES = typeof __PC_GAME_STYLES__ === 'undefined' ? {} : __PC_GAME_STYLES__;
const HERO_RE = /\/assets\/(\d+)\/(?:[0-9a-f]+\/)?library_hero\.jpg/;
const pcHeroCache = new Map(), pcHeroTimers = new Set(), pcHeroOriginals = new Map();
function hero4k(src) {
  const match = HERO_RE.exec(src); if (!match) return null;
  const appid = Number(match[1]);
  if (pcHeroCache.has(appid)) return pcHeroCache.get(appid) || null;
  pcHeroCache.set(appid, false);
  const probe = async remaining => {
    try {
      const result = await call('get_hero4k', appid);
      if (result?.file && __pcMounted) {
        const url = DATA + result.file; pcHeroCache.set(appid, url);
        const doc = window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance?.BrowserWindow?.document;
        doc?.querySelectorAll('img').forEach(img => {if (HERO_RE.exec(img.src)?.[1] == appid) {if (!pcHeroOriginals.has(img)) pcHeroOriginals.set(img,img.src);img.src = url;}});
      } else if (result?.pending && remaining > 0 && __pcMounted) {
        const timer = setTimeout(() => {pcHeroTimers.delete(timer); probe(remaining - 1);}, 2000); pcHeroTimers.add(timer);
      }
    } catch (_) {}
  };
  probe(12); return null;
}
function useHubThemeCss(appid, anchorRef, winH) {
  const theme = PC_GAME_STYLES[String(appid)];
  useEffect(() => {
    const root = anchorRef.current?.ownerDocument?.documentElement;
    if (!theme || !root) return;
    root.classList.add('gh-hub-' + theme.cls);
    return () => root.classList.remove('gh-hub-' + theme.cls);
  }, [appid]);
  return theme && winH ? translateHubTheme(theme.cls, theme.css, winH) : '';
}
async function resolveCustomizationJob(value, alive=()=>true) {
  if (!value?.job) return value;
  for (let n = 0; n < 600 && alive(); n++) {
    const state = await call('customization_job', value.job);
    if (state.done) { if (state.error) throw new Error(state.error); return state.result; }
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  throw new Error('Timed out waiting for media');
}
const ART_TABS = [   // вкладка, подпись, тип Steam (SetCustomArtworkForApp), превью ш×в, в ряд
  ["grid", "pc_grid", 0, 116, 174, 7], ["hero", "pc_hero", 1, 330, 106, 3], ["logo", "pc_logo", 2, 240, 110, 4], ["wide", "pc_wide", 3, 240, 112, 4]];
const ART_SVG = h("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round", style: { width: "26px", height: "26px" } },
  h("rect", { x: 3, y: 4, width: 18, height: 16, rx: 2, style: { fill: "none" } }), h("circle", { cx: 8.5, cy: 9.5, r: 1.6 }),
  h("path", { d: "M21 16l-5-5-8 8", style: { fill: "none" } }));   // Steam заливает фигуры в кнопках — рамку держим контуром

function ArtPicker({ appid, name, closeModal }) {
  useLanguage();
  const [key, setKey] = useState('');
  const keyRef = useRef(null);
  const [reload, setReload] = useState(0);
  const [tab, setTab] = useState(0);
  const [st, setSt] = useState({ items: null, error: null });
  const [busy, setBusy] = useState(null);
  const [kind, label, asset, tw, th, per] = ART_TABS[tab];
  useEffect(() => {
    let alive = true;
    setSt({ items: null, error: null });
    call("sgdb_list", appid, name, kind).then(r => alive && setSt(r || { items: [], error: t('pc_empty') }))
      .catch(e => alive && setSt({ items: [], error: String(e.message || e) }));
    return () => { alive = false; };
  }, [tab, reload]);
  const saveKey = async () => {
    try { await call('sgdb_set_key', key); setKey(''); setReload(n => n + 1); }
    catch (error) { setSt(s => ({...s, error: String(error.message || error)})); }
  };
  const apply = async it => {
    if (busy) return;
    setBusy(it.id);
    try {
      const r = await call("sgdb_image", it.id);
      await SteamClient.Apps.SetCustomArtworkForApp(appid, r.b64, r.fmt, asset);
      closeModal?.();
    } catch (e) { setBusy(null); setSt(s => ({ ...s, error: "не поставилось: " + (e.message || e) })); }
  };
  const reset = async () => {
    try { await SteamClient.Apps.ClearCustomArtworkForApp(appid, asset); closeModal?.(); } catch (e) { log("сброс картинки", e); }
  };
  const F = DFL.Focusable;
  const tabBtn = (t, i) => h(F, { key: t[0], className: "gh-art-tab" + (i === tab ? " on" : ""), onActivate: () => setTab(i), onClick: () => setTab(i) }, I18N[LANGUAGE][t[1]]);
  const items = st.items || [];
  const rows = [];
  for (let i = 0; i < items.length; i += per) rows.push(items.slice(i, i + per));
  return h(DFL.ModalRoot, { closeModal, onCancel: closeModal, bAllowFullSize: true },
    h("style", null, `
.DialogContent:has(.gh-art){width:auto!important;max-width:94vw!important}
.gh-art{width:min(1180px,88vw);font-family:"Motiva Sans",Arial,sans-serif;color:#e8edf3}
.gh-art h2{font:400 24px Georgia,serif;margin:0 0 14px}
.gh-art-tabs{display:flex;gap:10px;margin-bottom:14px}
.gh-art-tab,.gh-art-reset{padding:8px 18px;border-radius:6px;background:rgba(255,255,255,.08);font-size:15px;letter-spacing:.04em}
.gh-art-tab.on{background:rgba(255,255,255,.22);color:#fff}
.gh-art-tab.gpfocus,.gh-art-reset.gpfocus,.gh-art-tab:hover,.gh-art-reset:hover{background:#fff;color:#0b1016}
.gh-art-grid{max-height:62vh;overflow-y:auto;padding:6px}
.gh-art-row{display:flex;gap:12px;margin-bottom:12px}
.gh-art-it{position:relative;border-radius:6px;outline:2px solid transparent;outline-offset:3px;background:#0b1016 repeating-conic-gradient(#1a222c 0 25%,#0f151c 0 50%) 0 0/16px 16px;overflow:hidden;flex:none}
.gh-art-it img{width:100%;height:100%;object-fit:cover;display:block}
.gh-art-it.logo img{object-fit:contain}
.gh-art-it.gpfocus,.gh-art-it:hover{outline-color:#fff}
.gh-art-it.busy::after{content:"${t('pc_applying')}";position:absolute;inset:0;display:grid;place-items:center;background:rgba(0,0,0,.6);font-size:15px}
.gh-art-msg{padding:24px 6px;color:#aeb9c6;font-size:16px}
`),
    h("div", { className: "gh-art" },
      h("h2", null, t('pc_art') + ': ' + (name || appid)),
      st.setup_required ? h(F, { className: 'gh-mu-row', 'flow-children': 'row' },
        h(F, { onActivate: () => keyRef.current?.focus(), onClick: () => keyRef.current?.focus() },
          h('input', { ref: keyRef, type: 'password', autoComplete: 'off', value: key, placeholder: t('pc_key_setup'), 'aria-label': t('pc_key_setup'), onChange: e => setKey(e.target.value) })),
        h(F, { className: 'gh-art-reset', onActivate: () => saveKey(), onClick: () => saveKey() }, t('pc_key_save'))) : null,
      h(F, { className: "gh-art-tabs", "flow-children": "row" },
        ...ART_TABS.map(tabBtn),
        h(F, { key: "reset", className: "gh-art-reset", style: { marginLeft: "auto" }, onActivate: reset, onClick: reset }, t('pc_reset_art'))),
      h(F, { className: "gh-art-grid", "flow-children": "column" },
        st.items === null ? h("div", { className: "gh-art-msg" }, t('pc_art_loading')) : null,
        st.error && !st.setup_required ? h("div", { className: "gh-art-msg" }, st.error) : null,
        ...rows.map((row, ri) => h(F, { key: ri, className: "gh-art-row", "flow-children": "row" },
          ...row.map(it => h(F, { key: it.id, className: "gh-art-it " + kind + (busy === it.id ? " busy" : ""),
            style: { width: tw + "px", height: th + "px" }, onActivate: () => apply(it), onClick: () => apply(it) },
            h("img", { src: DATA + it.thumb, loading: "lazy" }))))))));
}

function openArtPicker(appid) {
  const win = window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance?.BrowserWindow;
  if (!DFL.showModalRaw || !DFL.ModalRoot || !win) return log("картинки: модальное окно Steam не найдено");
  const name = window.appStore?.GetAppOverviewByAppID?.(appid)?.display_name || "";
  DFL.showModalRaw(h(ArtPicker, { appid, name }), win, t('pc_art'), { strTitle: t('pc_art'), bHideMainWindowForPopouts: false },
    undefined, { bHideActions: false }, window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance?.m_ModalManager);
}

// ───────────── выбор фоновой музыки (на Деке — Game Theme Music, на ПК — своё окно) ─────────────
const MUSIC_SVG = h("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round", style: { width: "26px", height: "26px" } },
  h("path", { d: "M9 18V5l11-2v13", style: { fill: "none" } }), h("circle", { cx: 6, cy: 18, r: 3 }), h("circle", { cx: 17, cy: 16, r: 3 }));
const MUSIC_KINDS = [["theme", "Theme Music"], ["ost", "OST"], ["menu", "pc_menu_music"]];
const fmtDur = d => d ? `${Math.floor(d / 60)}:${String(d % 60).padStart(2, "0")}` : "";

function MusicPicker({ appid, name, closeModal }) {
  useLanguage();
  const [gate, setGate] = useState(null);
  const [kind, setKind] = useState("theme");
  const [q, setQ] = useState("");        // свой запрос: конкретная песня («Bleach Number One»)
  const [qGo, setQGo] = useState(0);
  const inRef = useRef(null);
  const [list, setList] = useState(null);
  const [cur, setCur] = useState(null);
  const [busy, setBusy] = useState(null);
  const [err, setErr] = useState(null);
  const mounted = useRef(true);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
  useEffect(() => { call("music_current", appid).then(setCur).catch(() => {}); }, []);
  useEffect(() => {
    let alive = true;
    if (kind === "query" && !q.trim()) { setList([]); return; }
    setList(null);
    call("music_search", kind === "query" ? q.trim() : name, kind).then(r=>resolveCustomizationJob(r,()=>alive)).then(r => { if (!alive) return; setGate(Array.isArray(r) ? null : r); setList(Array.isArray(r) ? r : []); }).catch(e => alive && (setList([]), setErr(String(e.message || e))));
    return () => { alive = false; };
  }, [kind, qGo]);
  const pick = async v => {
    if (busy) return;
    setBusy(v); setErr(null);
    try {
      const result = await resolveCustomizationJob(await call("music_choose", appid, v),()=>mounted.current);
      if (!result?.ok) { if (mounted.current) { setGate(result); setBusy(null); } return; }
      // Publish persisted choices before source refresh; the active player must
      // stop for None even if card rendering or the file-list RPC is delayed.
      await publishPcSettings(await call('get_settings'));
      sourceListeners.forEach(listener => listener(appid));
      if (v === 'auto' && pluginSettings?.theme_music_consent) {
        refreshMediaLatest(appid,name,null,()=>true).then(()=>sourceListeners.forEach(listener=>listener(appid))).catch(()=>{});
      }
      if (mounted.current) closeModal?.();
    } catch (e) { setBusy(null); setErr("не получилось: " + (e.message || e)); }
  };
  const F = DFL.Focusable;
  const btn = (key, label, onAct, extra) => h(F, { key, className: "gh-mu-btn" + (extra || ""), onActivate: onAct, onClick: onAct }, label);
  if (gate?.consent_required || gate?.setup_required) return h(DFL.ModalRoot,{closeModal,onCancel:closeModal,bAllowFullSize:true},
    h('style',null,PC_SETTINGS_CSS+'\n.DialogContent:has(.gh-mu-setup){width:min(760px,88vw)!important}.gh-mu-setup{padding:28px}'),
    h(F,{className:'cps gh-mu-setup','flow-children':'column'},h('h2',null,t('pc_music')),h('p',null,psText('music_detail')),
      h(PcSettingsButton,{primary:true,onClick:()=>{closeModal?.();setTimeout(()=>openPcSettings('music'),350);}},psText('enable_music'))));
  return h(DFL.ModalRoot, { closeModal, onCancel: closeModal, bAllowFullSize: true },
    h("style", null, `
.DialogContent:has(.gh-mu){width:auto!important;max-width:94vw!important}
.gh-mu{width:min(860px,86vw);font-family:"Motiva Sans",Arial,sans-serif;color:#e8edf3}
.gh-mu h2{font:400 24px Georgia,serif;margin:0 0 12px}
.gh-mu-row{display:flex;gap:10px;margin-bottom:12px;flex-wrap:wrap}
.gh-mu-btn{padding:8px 16px;border-radius:6px;background:rgba(255,255,255,.08);font-size:15px}
.gh-mu-btn.on{background:rgba(255,255,255,.24);color:#fff}
.gh-mu-inw{flex:1;min-width:320px;border-radius:6px}
.gh-mu-inw.gpfocus{outline:2px solid #fff}
.gh-mu-in{width:100%;box-sizing:border-box;padding:8px 12px;border-radius:6px;border:1px solid rgba(255,255,255,.25);background:rgba(0,0,0,.35);color:#fff;font-size:15px}
.gh-mu-btn.gpfocus,.gh-mu-btn:hover,.gh-mu-it.gpfocus,.gh-mu-it:hover{background:#fff!important;color:#0b1016!important}
.gh-mu-list{max-height:56vh;overflow-y:auto;padding:4px}
.gh-mu-it{display:flex;gap:14px;align-items:center;padding:9px 12px;border-radius:6px;margin-bottom:4px;background:rgba(255,255,255,.04)}
.gh-mu-it b{flex:1;font-weight:400;font-size:15px}
.gh-mu-it small{opacity:.65;font-size:13px;white-space:nowrap}
.gh-mu-it.busy{opacity:.6}
.gh-mu p{color:#9fb0c2;font-size:14px;margin:6px 0}
`),
    h("div", { className: "gh-mu" },
      h("h2", null, t('pc_music') + ': ' + (name || appid)),
      h(F, { className: "gh-mu-row", "flow-children": "row" },
        btn("auto", t('pc_auto') + (cur === "auto" || !cur ? " ✓" : ""), () => pick("auto")),
        btn("none", t('pc_no_music') + (cur === "none" ? " ✓" : ""), () => pick("none")),
        ...MUSIC_KINDS.map(([k, l]) => btn("k-" + k, t('pc_search_for') + (I18N[LANGUAGE][l] || l), () => setKind(k), k === kind ? " on" : ""))),
      h(F, { className: "gh-mu-row", "flow-children": "row" },
        h(F, { className: "gh-mu-inw", onActivate: () => inRef.current?.focus(), onClick: () => inRef.current?.focus() },
          h("input", { ref: inRef, className: "gh-mu-in", type: "text", value: q, placeholder: t('pc_song_query'), spellCheck: false,
            onChange: e => setQ(e.target.value), onKeyDown: e => { if (e.key === "Enter") { setKind("query"); setQGo(n => n + 1); } } })),
        btn("go", t('pc_search'), () => { setKind("query"); setQGo(n => n + 1); }, kind === "query" ? " on" : "")),
      gate?.consent_required || gate?.setup_required ? h(F, { className: 'gh-mu-row', 'flow-children': 'column' },
        h('p', null, t('pc_music_consent')),
        btn('setup', t('pc_music_setup'), async () => {
          setBusy('setup'); setErr(null);
          try { const installed = await enablePcMusic();
            if (!installed?.ok) throw new Error(installed?.error || t('pc_wait_game'));
            setGate(null); setQGo(n => n + 1);
          } catch (e) { setErr(String(e.message || e)); } finally { setBusy(null); }
        })) : null,
      gate?.deferred ? h('p', null, t('pc_wait_game')) : null,
      err ? h("p", null, err) : null,
      list === null ? h("p", null, t('pc_youtube_search')) : (list.length ? null : h("p", null, t('pc_empty'))),
      h(F, { className: "gh-mu-list", "flow-children": "column" },
        ...(list || []).map(it => h(F, { key: it.id, className: "gh-mu-it" + (busy === it.id ? " busy" : ""), onActivate: () => pick(it.id), onClick: () => pick(it.id) },
          h("b", null, (cur === it.id ? "✓ " : "") + it.title + (busy === it.id ? t('pc_downloading') : "")),
          h("small", null, [it.channel, fmtDur(it.duration)].filter(Boolean).join(" · ")))))));
}

function openMusicPicker(appid) {
  const win = window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance?.BrowserWindow;
  if (!DFL.showModalRaw || !DFL.ModalRoot || !win) return log("музыка: модальное окно Steam не найдено");
  const name = window.appStore?.GetAppOverviewByAppID?.(appid)?.display_name || "";
  DFL.showModalRaw(h(MusicPicker, { appid, name }), win, t('pc_music'), { strTitle: t('pc_music'), bHideMainWindowForPopouts: false },
    undefined, { bHideActions: false }, window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance?.m_ModalManager);
}

// Кнопка «Картинки» — в тот же ряд, что «Магазин» (кнопки Деки рисует HubAppButtons из index.js).
const __deckAppButtons = HubAppButtons;
HubAppButtons = function () {
  const deck = __deckAppButtons();
  const appid = currentAppId();
  if (!appid || !DFL.Focusable || !DFL.showModalRaw) return deck;
  const go = () => openArtPicker(appid);
  const art = h(DFL.Focusable, { key: "gh-art", className: DFL.playSectionClasses?.MenuButton || "", role: "button",
    "aria-label": t('pc_art') + ' (SteamGridDB)', onActivate: go, onClick: go, title: t('pc_art'), style: { marginRight: "10px" } }, ART_SVG);
  const mgo = () => openMusicPicker(appid);
  const mus = h(DFL.Focusable, { key: "gh-music", className: DFL.playSectionClasses?.MenuButton || "", role: "button",
    "aria-label": t('pc_music'), onActivate: mgo, onClick: mgo, title: t('pc_music'), style: { marginRight: "10px" } }, MUSIC_SVG);
  return h(React.Fragment, null, deck, art, mus);
};

// ───────────── темы CSS Loader на ПК (на Деке — сам CSS Loader в быстром меню) ─────────────
// Пункт «Темы» в главном меню Steam (после «Настроек») → окно: тема вкл/выкл, у включённой — её варианты
// (A — следующее значение). CSS в окна Steam вставляет служба (themes_pc.py + ThemeInjector), как CSS Loader.
const THEMES_SVG = h("svg", { viewBox: "0 0 24 24", fill: "currentColor", style: { width: "20px", height: "20px" } },
  h("path", { d: "M12 3a9 9 0 0 0 0 18c1.1 0 1.8-.8 1.8-1.8 0-.5-.2-.9-.5-1.2-.3-.3-.5-.7-.5-1.2 0-1 .8-1.8 1.8-1.8H17a4 4 0 0 0 4-4C21 6.6 17 3 12 3zm-5.5 9a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm3-4a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm5 0a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm3 4a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3z" }));

function ThemePicker({ closeModal }) {
  useLanguage();
  const [list, setList] = useState(null);
  const [open, setOpen] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => { call("themes_list").then(setList).catch(e => setErr(String(e.message || e))); }, []);
  const set = (name, patch, value) => call("themes_set", name, patch, value).then(setList).catch(e => setErr(String(e.message || e)));
  const F = DFL.Focusable;
  const [movie, setMovie] = useState(startupMovieOn());   // видеозаставка Steam (index.js: setStartupMovie)
  const toggleMovie = () => setStartupMovie(!movie).then(setMovie).catch(e => setErr(String(e.message || e)));
  const rows = [h(F, { key: "gh-movie", className: "gh-th-row", "flow-children": "row" },
    h(F, { className: "gh-th-btn gh-th-on" + (movie ? " on" : ""), onActivate: toggleMovie, onClick: toggleMovie }, movie ? t('pc_on') : t('pc_off')),
    h("div", { className: "gh-th-name" }, I18N[LANGUAGE].startup_movie, h("small", null, I18N[LANGUAGE].startup_movie_desc)))];
  for (const t of (list || []).filter(x=>!x.pc_note)) {
    const toggle = () => set(t.name, null, !t.active);
    const more = () => setOpen(open === t.name ? null : t.name);
    const sub = t.required_by.length ? I18N[LANGUAGE].pc_required + t.required_by.join(", ") : t.pc_note ? I18N[LANGUAGE].pc_builtin : '';
    rows.push(h(F, { key: t.name, className: "gh-th-row", "flow-children": "row" },
      h(F, { className: "gh-th-btn gh-th-on" + (t.active ? " on" : ""), onActivate: toggle, onClick: toggle }, t.active ? I18N[LANGUAGE].pc_on : I18N[LANGUAGE].pc_off),
      h("div", { className: "gh-th-name" }, t.name, sub ? h("small", null, sub) : null),
      t.patches.length && t.active ? h(F, { className: "gh-th-btn", onActivate: more, onClick: more }, open === t.name ? I18N[LANGUAGE].pc_collapse : `${I18N[LANGUAGE].pc_configure} (${t.patches.length})`) : null));
    if (open === t.name && t.active) for (const p of t.patches) {
      const next = () => set(t.name, p.name, p.values[(p.values.indexOf(p.value) + 1) % p.values.length]);
      rows.push(h(F, { key: t.name + "/" + p.name, className: "gh-th-row gh-th-patch", "flow-children": "row" },
        h("div", { className: "gh-th-name" }, p.name),
        h(F, { className: "gh-th-btn gh-th-val", onActivate: next, onClick: next }, p.value + "  ›")));
    }
  }
  return h(DFL.ModalRoot, { closeModal, onCancel: closeModal, bAllowFullSize: true },
    h("style", null, `
.DialogContent:has(.gh-th){width:auto!important;max-width:94vw!important}
.gh-th{width:min(900px,86vw);font-family:"Motiva Sans",Arial,sans-serif;color:#e8edf3}
.gh-th h2{font:400 24px Georgia,serif;margin:0 0 6px}
.gh-th p{margin:0 0 14px;color:#9fb0c2;font-size:14px}
.gh-th-list{max-height:64vh;overflow-y:auto;padding:4px}
.gh-th-row{display:flex;align-items:center;gap:14px;padding:6px 4px;border-bottom:1px solid rgba(255,255,255,.06)}
.gh-th-patch{padding-left:96px}
.gh-th-name{flex:1;font-size:16px}
.gh-th-name small{display:block;color:#8d9db0;font-size:12.5px;margin-top:2px}
.gh-th-btn{padding:7px 14px;border-radius:6px;background:rgba(255,255,255,.08);font-size:14px;white-space:nowrap}
.gh-th-on{min-width:56px;text-align:center}
.gh-th-on.on{background:#4c9a5f;color:#fff}
.gh-th-val{min-width:150px;text-align:right}
.gh-th-btn.gpfocus,.gh-th-btn:hover{background:#fff!important;color:#0b1016!important}
`),
    h("div", { className: "gh-th" },
      h("h2", null, t('pc_themes')),
      h("p", null, I18N[LANGUAGE].pc_themes_desc),
      err ? h("p", null, err) : null,
      list === null && !err ? h("p", null, I18N[LANGUAGE].pc_loading) : null,
      h(F, { className: "gh-th-list", "flow-children": "column" }, ...rows)));
}

function openThemes() {
  const w = window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance;
  if (!DFL.showModalRaw || !DFL.ModalRoot || !w) return log("темы: модальное окно Steam не найдено");
  try { w.MenuStore?.CloseSideMenus?.(); } catch (e) {}
  // меню закрывается анимацией и уносит с собой окно, открытое в тот же миг — открываем чуть позже
  setTimeout(() => DFL.showModalRaw(h(ThemePicker, {}), w.BrowserWindow, t('pc_themes'), { strTitle: t('pc_themes'), bHideMainWindowForPopouts: false },
    undefined, { bHideActions: false }, w.m_ModalManager), 350);
}

// Пункты главного меню — элементы с key (home, library, …, settings, power) одним массивом; добавляем «Темы» после «Настроек»
// компонентом пункта «Друзья и чат»: он принимает action (компонент «Настроек» превращает пункт в переход по route).
function withThemesItem(arr) {
  const i = arr.findIndex(e => e && e.key === "settings" && e.props?.route === "/settings");
  if (i < 0 || arr.some(e => e && e.key === "continue-themes")) return null;
  const s = arr[i];
  const chat = arr.find(e => e && e.key === "chat" && typeof e.props?.action === "function");   // пункт с action (у «Настроек» — route)
  if (!chat) return null;
  const item = h(chat.type, { key: "continue-themes", label: 'Continue?', icon: THEMES_SVG, action: () => {
    try {window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance?.MenuStore?.CloseSideMenus?.();} catch (_) {}
    setTimeout(openPcSettings,350);
  }, active: false,
    onGamepadFocus: s.props.onGamepadFocus });
  return [...arr.slice(0, i + 1), item, ...arr.slice(i + 1)];
}


// PC uses its own startup-movie name and remembers the previous native choice.
const PC_NO_MOVIE = '/uioverrides/movies/continue_no_startup.webm';
let pcMoviePrevious = null;
function startupMovieOn() {
  const api = steamSettingsApi();
  return !api || api.store.m_ClientSettings?.startup_movie_local_path !== PC_NO_MOVIE;
}
async function setStartupMovie(on) {
  const api = steamSettingsApi();
  if (!api) throw new Error('Steam settings API was not found');
  const current = api.store.m_ClientSettings || {};
  if (!on) {
    if (!await call('ensure_blank_movie')) throw new Error('Startup movie could not be prepared');
    if (current.startup_movie_local_path !== PC_NO_MOVIE) {
      pcMoviePrevious = {id:String(current.startup_movie_id ?? '0'), path:current.startup_movie_local_path || '', shuffle:!!current.startup_movie_shuffle};
      await call('set_setting', 'startup_movie_prev', pcMoviePrevious);
    }
    await api.set('startup_movie_shuffle', false);
    await api.set('startup_movie_id', '0');
    await api.set('startup_movie_local_path', PC_NO_MOVIE);
  } else if (current.startup_movie_local_path === PC_NO_MOVIE) {
    const prev = (await call('get_settings'))?.startup_movie_prev || {};
    await api.set('startup_movie_id', prev.id || '0');
    await api.set('startup_movie_local_path', prev.path || '');
    await api.set('startup_movie_shuffle', !!prev.shuffle);
  }
  return startupMovieOn();
}
async function restorePcStartupMovie() {
  try {
    const api = steamSettingsApi();
    if (!api || api.store.m_ClientSettings?.startup_movie_local_path !== PC_NO_MOVIE) return true;
    if (!pcMoviePrevious) return false;
    await api.set('startup_movie_id', pcMoviePrevious.id || '0');
    await api.set('startup_movie_local_path', pcMoviePrevious.path || '');
    await api.set('startup_movie_shuffle', !!pcMoviePrevious.shuffle);
    return true;
  } catch (_) { return false; }
}
// Public cards on both platforms share settings, cancellation and Audio lifecycle.
useStandaloneMusic = function(appid, settings, media) {
  useDeckMusic(appid, settings, media, pcBusy);
};
