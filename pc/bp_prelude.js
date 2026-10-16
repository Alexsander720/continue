// Continue? для Big Picture на ПК — прослойка вместо Decky. Собирается вместе с фронтендом плагина Деки
// (plugin/GameHubDeck/dist/index.js) службой gamehub_bp.py и вливается в SharedJSContext Steam через его
// отладочный порт. Decky под Windows нет, поэтому то, что он даёт плагину, делаем здесь сами:
//   SP_REACT / SP_JSX — модули React из webpack Steam (как это делает загрузчик Decky);
//   DFL — только то, что использует плагин: классы Steam, Focusable, Navigation;
//   call() — мост к Python через Runtime.addBinding (CSP Steam не пускает fetch к своим серверам).

const __ghBoot = (() => {
  let req;
  window.webpackChunksteamui.push([[Symbol("gamehub-pc")], {}, r => { req = r; }]);
  const mods = [];
  for (const id of Object.keys(req.m)) { try { const m = req(id); if (m) mods.push(m); } catch (e) {} }
  const findModule = f => { for (const m of mods) { if (m.default && f(m.default)) return m.default; if (f(m)) return m; } };
  const findExport = f => {
    for (const m of mods) for (const mod of [m.default, m]) {
      if (!mod || typeof mod !== "object" || mod === window) continue;
      for (const k in mod) { try { if (mod[k] && f(mod[k])) return mod[k]; } catch (e) {} }
    }
  };
  if (!window.SP_REACT) window.SP_REACT = findModule(m => m.Component && m.PureComponent && m.useLayoutEffect);
  if (!window.SP_JSX) window.SP_JSX = findModule(m => m.jsx && m.jsxs);
  const classMods = mods.filter(m => typeof m == "object" && !m.__esModule && Object.keys(m).length > 0 &&
    !(Object.keys(m).length == 1 && m.version) &&
    Object.keys(m).every(k => !Object.getOwnPropertyDescriptor(m, k)?.get && typeof m[k] == "string"));
  const cls = f => classMods.find(f) || {};
  const propList = props => new RegExp("const\\{" + props.map(p => `"?${p}"?:[a-zA-Z_$]{1,2}`).join(","));
  const focusableRe = propList(["flow-children", "onActivate", "onCancel", "focusClassName", "focusWithinClassName"]);
  const Focusable = findExport(e => (typeof e == "function" && focusableRe.test(e.toString())) || (e?.render?.toString && focusableRe.test(e.render.toString())));
  if (!window.SP_REACT || !window.SP_JSX || !Focusable) throw new Error('Steam UI components are not ready');
  const win = () => { try { return window.SteamUIStore.GetFocusedWindowInstance() || window.SteamUIStore.WindowStore.GamepadUIMainWindowInstance; } catch (e) { return null; } };
  // Поиск значка кнопки в таблице Steam (тип контроллера → картинка): нужен, чтобы подменять значки на DualSense
  // только там, где у DualSense такой значок есть (трекпады Steam Controller и т.п. остаются как были).
  const glyphFind = findExport(e => typeof e == "function" && e.length === 5 && /bKnockout/.test(e.toString()) && /eControllerStyle/.test(e.toString()));
  // Модальные окна Steam (как showModal/ModalRoot у Decky): окно выбора картинок SteamGridDB на ПК.
  const src = e => { try { return e.toString(); } catch (x) { return ""; } };
  const showModalRaw = findExport(e => typeof e == "function" && !e.prototype?.setState && /bHideMainWindowForPopouts/.test(src(e)) && /fnOnClose/.test(src(e)));
  const ModalRoot = findExport(e => typeof e == "function" && /Either closeModal or onCancel/.test(src(e)));
  return {
    glyphFind,
    DFL: {
      playSectionClasses: cls(m => m.PlayBarDetailLabel),
      appDetailsHeaderClasses: cls(m => m.TopCapsule),
      appDetailsClasses: cls(m => m.HeaderLoaded),
      basicAppDetailsSectionStylerClasses: cls(m => m.AppDetailsRoot),
      staticClasses: cls(m => m.Title && m.QuickAccessMenu && m.BatteryDetailsLabels),
      appActionButtonClasses: cls(m => m.PlayButton && m.PlayButtonContainer && m.ButtonText),
      footerClasses: cls(m => m.BasicFooter && m.FooterLegend),
      Focusable, showModalRaw, ModalRoot,
      Navigation: { Navigate: p => win()?.Navigate(p), NavigateBack: () => win()?.NavigateBack() },
    },
  };
})();
window.DFL = __ghBoot.DFL;

// мост к службе: window.__ghBridge — привязка CDP, ответ приходит в __ghPC.reply(id, ok, value)
const __ghPending = new Map();
let __ghSeq = 0;
const call = (method, ...args) => new Promise((resolve, reject) => {
  if (typeof window.__ghBridge !== "function") return reject(new Error("служба Continue? не подключена"));
  const id = ++__ghSeq;
  __ghPending.set(id, { resolve, reject });
  setTimeout(() => { if (__ghPending.delete(id)) reject(new Error("таймаут " + method)); }, 60000);
  window.__ghBridge(JSON.stringify({ id, method, args }));
});
const routerHook = null;   // на ПК страницу игры подменяем через SP_JSX (bp_suffix.js), не через роутер Decky
