// Continue? для Steam Deck — фронтенд. Без сборщика: SP_REACT и DFL — глобальные объекты Decky.
// «Где остановился» на странице игры (как в Continue? на ПК), главная с установленными играми,
// темы хаба в Game Theme Music. Живой фон — только на зарядке (Дек — для игр без света).

const manifest = { "name": "Continue", "author": "Doctor_Nerd", "flags": [], "api_version": 1 };
const API_VERSION = 2;
const internalAPIConnection = window.__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit;
if (!internalAPIConnection) throw new Error("[Continue?] Decky loader API is not initialized");
let api;
try { api = internalAPIConnection.connect(API_VERSION, manifest.name); }
catch { api = internalAPIConnection.connect(1, manifest.name); }
const call = api.call;
const routerHook = api.routerHook;

const React = window.SP_REACT;
const DFL = window.DFL;
const h = React.createElement;
const { useState, useEffect, useRef, useLayoutEffect } = React;
// имя плагина меняется при сборке Continue? — адрес данных берём из манифеста (ПК подменяет эту строку целиком)
const DATA = "http://127.0.0.1:1337/plugins/" + encodeURIComponent(manifest.name) + "/data/";
const log = (...a) => console.log("%c Continue? ", "background:#c8a96a;color:#111", ...a);

// ───────────── мелочи ─────────────

const I18N = {
  "ru": {
    "months": [
      "января",
      "февраля",
      "марта",
      "апреля",
      "мая",
      "июня",
      "июля",
      "августа",
      "сентября",
      "октября",
      "ноября",
      "декабря"
    ],
    "today": "сегодня",
    "yesterday": "вчера",
    "days": [
      "день",
      "дня",
      "дней"
    ],
    "weeks": [
      "неделю",
      "недели",
      "недель"
    ],
    "months_ago": [
      "месяц",
      "месяца",
      "месяцев"
    ],
    "years": [
      "год",
      "года",
      "лет"
    ],
    "ago": "назад",
    "hour_short": "ч",
    "bg_auto": "Авто",
    "bg_trailer": "Трейлер",
    "bg_gameplay": "Мой геймплей",
    "bg_image": "Картинка хаба",
    "bg_steam": "Обложка Steam",
    "steam_stats": [
      "Вы играли",
      "Последний запуск",
      "Требуется места",
      "Запуск",
      "Наиграно",
      "Размер"
    ],
    "last_played": "Запуск",
    "played": "Наиграно",
    "space": "Размер",
    "pdb_native": "Нативная Linux",
    "pdb_platinum": "Платина",
    "pdb_gold": "Золото",
    "pdb_silver": "Серебро",
    "pdb_bronze": "Бронза",
    "pdb_borked": "Не работает",
    "pdb_pending": "Мало отчётов",
    "pdb_none": "Нет отчётов",
    "pdb_reports": " · отчётов {0}",
    "stream": "Играть с ПК (трансляция)",
    "store": "Магазин и отзывы",
    "save_prefix": "Сохранение от ",
    "save_word": "сейв",
    "story": "Сюжет",
    "completionist": "На 100%",
    "not_started": "Ещё не начата",
    "achievements": "Достижения",
    "save_frame": "кадр сохранения",
    "last_achievement": "Последнее достижение",
    "pc_tab": "С ПК",
    "now": "Сейчас: {0}",
    "background": "Фон: {0}",
    "game_live": "Живой фон этой игры",
    "no_video": "Для этой игры нет видео — только картинка",
    "version_now": "Сейчас {0}",
    "update_to": "Обновить до {0}",
    "version_latest": "Последняя версия: {0}",
    "update_offline": "Не удалось проверить — нет сети?",
    "version_check": "Версия {0} · проверить",
    "charging": "Только на зарядке",
    "always": "Всегда",
    "off": "Выключен",
    "hub_status": "Из хаба: {0} игр",
    "synced": " · обновлено {0} ({1})",
    "not_synced": " · ещё не синхронизировано",
    "reader_status": "\nСейвы читаются на Деке: {0} игр · HLTB в кэше: {1}",
    "brightness": "Полоса яркости",
    "brightness_other": "Стоит плагин Brightness Bar — показывает он",
    "brightness_desc": "Как полоса громкости, при смене яркости (и в игре)",
    "home_live": "Главная: живой фон игры",
    "home_live_desc": "Видео и логотип выбранной игры на фоне главной",
    "home_music": "Главная: музыка игры",
    "home_music_desc": "Тема выбранной игры играет, пока листаешь обложки",
    "installed_first": "Главная: сначала установленные",
    "live_policy": "Живой фон (общий)",
    "live_policy_desc": "По умолчанию для игр без своего выбора (~0,4 Вт, во время игры на паузе)",
    "pdb_page": "ProtonDB на странице игры",
    "pdb_page_desc": "Совместимость с Linux; нажатие — отзывы",
    "pdb_tiles": "ProtonDB на обложках",
    "pdb_tiles_desc": "Рядом со значком Steam Deck в библиотеке",
    "hub_music": "Музыка из хаба",
    "hub_music_desc": "Темы игр, выбранные в Continue?, для Game Theme Music",
    "startup_movie": "Видеозаставка Steam",
    "startup_movie_desc": "Ролик при включении и входе в Big Picture",
    "media_deferred": "Подготовка продолжится на зарядке, когда игра закрыта.",
    "media_setup_failed": "Не удалось подготовить YouTube. Можно оставить фон из Steam.",
    "standalone_status": "Игр с сейвом: {0} · фонов в кэше: {1}",
    "preset": "Пресет расхода батареи",
    "preset_light": "Лёгкий",
    "preset_balanced": "Сбалансированный",
    "preset_maximum": "Максимум",
    "preset_desc": "Лёгкий: стоп-кадр от батареи и без видео на главной; Максимум: 1080p и видео везде",
    "bg_source": "Источник живого фона",
    "source_for_game": "Источник для этой игры",
    "source_steam": "Магазин Steam",
    "source_youtube": "YouTube (экспериментально)",
    "source_recording": "Записи моей игры",
    "youtube_optin": "Разрешить YouTube и скачать yt-dlp",
    "youtube_desc": "Явное согласие на загрузку официального yt-dlp; без Node обход YouTube может не работать",
    "recording_optin": "Использовать Steam Background Recording",
    "recording_desc": "По умолчанию выключено; обработка идёт только на зарядке и вне игры",
    "theme_optin": "Искать музыку темы",
    "theme_desc": "По умолчанию выключено: возможны авторские ограничения; используется yt-dlp",
    "disk_limit": "Лимит кэша видео",
    "clear_cache": "Очистить кэш фонов",
    "cache_cleared": "Кэш фонов очищен",
    "original_description": "Описание показано на языке Steam без перевода"
  },
  "en": {
    "months": [
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December"
    ],
    "today": "today",
    "yesterday": "yesterday",
    "days": [
      "day",
      "days",
      "days"
    ],
    "weeks": [
      "week",
      "weeks",
      "weeks"
    ],
    "months_ago": [
      "month",
      "months",
      "months"
    ],
    "years": [
      "year",
      "years",
      "years"
    ],
    "ago": "ago",
    "hour_short": "h",
    "bg_auto": "Auto",
    "bg_trailer": "Trailer",
    "bg_gameplay": "My gameplay",
    "bg_image": "Hub image",
    "bg_steam": "Steam artwork",
    "steam_stats": [
      "You've played",
      "Last played",
      "Space required",
      "Last played",
      "Played",
      "Size"
    ],
    "last_played": "Last played",
    "played": "Played",
    "space": "Size",
    "pdb_native": "Native Linux",
    "pdb_platinum": "Platinum",
    "pdb_gold": "Gold",
    "pdb_silver": "Silver",
    "pdb_bronze": "Bronze",
    "pdb_borked": "Does not work",
    "pdb_pending": "Few reports",
    "pdb_none": "No reports",
    "pdb_reports": " · {0} reports",
    "stream": "Stream from PC",
    "store": "Store and reviews",
    "save_prefix": "Saved on ",
    "save_word": "save",
    "story": "Main story",
    "completionist": "Completionist",
    "not_started": "Not started yet",
    "achievements": "Achievements",
    "save_frame": "save screenshot",
    "last_achievement": "Latest achievement",
    "pc_tab": "From PC",
    "now": "Now playing: {0}",
    "background": "Background: {0}",
    "game_live": "Live background for this game",
    "no_video": "This game has an image only; no video is available",
    "version_now": "Current version: {0}",
    "update_to": "Update to {0}",
    "version_latest": "Latest version: {0}",
    "update_offline": "Could not check. Are you offline?",
    "version_check": "Version {0} · check for updates",
    "charging": "Only while charging",
    "always": "Always",
    "off": "Off",
    "hub_status": "From the hub: {0} games",
    "synced": " · updated {0} ({1})",
    "not_synced": " · not synced yet",
    "reader_status": "\nSave readers on Deck: {0} games · Cached HLTB entries: {1}",
    "brightness": "Brightness bar",
    "brightness_other": "The Brightness Bar plugin is handling this",
    "brightness_desc": "Shown when brightness changes, including in games",
    "home_live": "Home: live game background",
    "home_live_desc": "Show the selected game's video and logo on Home",
    "home_music": "Home: game music",
    "home_music_desc": "Play the selected game's theme as you browse your Library",
    "installed_first": "Home: installed games first",
    "live_policy": "Live background (default)",
    "live_policy_desc": "Default for games without an override (~0.4 W; paused while playing)",
    "pdb_page": "ProtonDB on game pages",
    "pdb_page_desc": "Linux compatibility; select to read reports",
    "pdb_tiles": "ProtonDB on Library artwork",
    "pdb_tiles_desc": "Beside the Steam Deck badge in your Library",
    "hub_music": "Music from the hub",
    "hub_music_desc": "Use themes selected in Continue? with Game Theme Music",
    "startup_movie": "Steam startup movie",
    "startup_movie_desc": "Play a movie at startup and when entering Big Picture",
    "media_deferred": "Setup will continue on AC power when no game is running.",
    "media_setup_failed": "YouTube setup failed. Steam backgrounds remain available.",
    "standalone_status": "Games with saves: {0} · cached backgrounds: {1}",
    "preset": "Battery-use preset",
    "preset_light": "Light",
    "preset_balanced": "Balanced",
    "preset_maximum": "Maximum",
    "preset_desc": "Light: still image on battery and no Home video; Maximum: 1080p video everywhere",
    "bg_source": "Live-background source",
    "source_for_game": "Source for this game",
    "source_steam": "Steam Store",
    "source_youtube": "YouTube (experimental)",
    "source_recording": "My gameplay recordings",
    "youtube_optin": "Allow YouTube and download yt-dlp",
    "youtube_desc": "Explicit consent to download official yt-dlp; YouTube may fail without Node",
    "recording_optin": "Use Steam Background Recording",
    "recording_desc": "Off by default; processing runs only while charging and outside games",
    "theme_optin": "Find theme music",
    "theme_desc": "Off by default due to copyright; uses yt-dlp",
    "disk_limit": "Video cache limit",
    "clear_cache": "Clear background cache",
    "cache_cleared": "Background cache cleared",
    "original_description": "Description is shown in Steam's original language"
  },
  "uk": {
    "months": [
      "січня",
      "лютого",
      "березня",
      "квітня",
      "травня",
      "червня",
      "липня",
      "серпня",
      "вересня",
      "жовтня",
      "листопада",
      "грудня"
    ],
    "today": "сьогодні",
    "yesterday": "вчора",
    "days": [
      "день",
      "дні",
      "днів"
    ],
    "weeks": [
      "тиждень",
      "тижні",
      "тижнів"
    ],
    "months_ago": [
      "місяць",
      "місяці",
      "місяців"
    ],
    "years": [
      "рік",
      "роки",
      "років"
    ],
    "ago": "тому",
    "hour_short": "год",
    "bg_auto": "Авто",
    "bg_trailer": "Трейлер",
    "bg_gameplay": "Мій ігровий процес",
    "bg_image": "Зображення хаба",
    "bg_steam": "Обкладинка Steam",
    "steam_stats": [
      "Ви грали",
      "Востаннє запущено",
      "Потрібне місце",
      "Запуск",
      "Зіграно",
      "Розмір"
    ],
    "last_played": "Запуск",
    "played": "Зіграно",
    "space": "Розмір",
    "pdb_native": "Версія для Linux",
    "pdb_platinum": "Платина",
    "pdb_gold": "Золото",
    "pdb_silver": "Срібло",
    "pdb_bronze": "Бронза",
    "pdb_borked": "Не працює",
    "pdb_pending": "Мало звітів",
    "pdb_none": "Немає звітів",
    "pdb_reports": " · звітів: {0}",
    "stream": "Транслювати з ПК",
    "store": "Крамниця й огляди",
    "save_prefix": "Збереження від ",
    "save_word": "збереження",
    "story": "Основний сюжет",
    "completionist": "На 100%",
    "not_started": "Ще не розпочато",
    "achievements": "Досягнення",
    "save_frame": "знімок збереження",
    "last_achievement": "Останнє досягнення",
    "pc_tab": "З ПК",
    "now": "Зараз у грі: {0}",
    "background": "Тло: {0}",
    "game_live": "Живе тло цієї гри",
    "no_video": "Для цієї гри є лише зображення — відео немає",
    "version_now": "Поточна версія: {0}",
    "update_to": "Оновити до {0}",
    "version_latest": "Остання версія: {0}",
    "update_offline": "Не вдалося перевірити — немає мережі?",
    "version_check": "Версія {0} · перевірити оновлення",
    "charging": "Лише під час заряджання",
    "always": "Завжди",
    "off": "Вимкнено",
    "hub_status": "Із хаба: {0} ігор",
    "synced": " · оновлено {0} ({1})",
    "not_synced": " · ще не синхронізовано",
    "reader_status": "\nЗбереження на Deck: {0} ігор · HLTB у кеші: {1}",
    "brightness": "Індикатор яскравості",
    "brightness_other": "Це показує встановлений плагін Brightness Bar",
    "brightness_desc": "Показується при зміні яскравості, зокрема й у грі",
    "home_live": "Головна: живе тло гри",
    "home_live_desc": "Відео й логотип вибраної гри на тлі головної сторінки",
    "home_music": "Головна: музика гри",
    "home_music_desc": "Тема вибраної гри звучить, поки ви переглядаєте обкладинки",
    "installed_first": "Головна: спочатку встановлені ігри",
    "live_policy": "Живе тло (загальне)",
    "live_policy_desc": "Для ігор без окремого налаштування (~0,4 Вт; під час гри призупинено)",
    "pdb_page": "ProtonDB на сторінці гри",
    "pdb_page_desc": "Сумісність із Linux; натисніть, щоб прочитати звіти",
    "pdb_tiles": "ProtonDB на обкладинках",
    "pdb_tiles_desc": "Поруч зі значком Steam Deck у бібліотеці",
    "hub_music": "Музика з хаба",
    "hub_music_desc": "Теми ігор, вибрані в Continue?, для Game Theme Music",
    "startup_movie": "Відеозаставка Steam",
    "startup_movie_desc": "Відео під час увімкнення й переходу в Big Picture",
    "media_deferred": "Підготовка продовжиться на зарядці, коли гру закрито.",
    "media_setup_failed": "Не вдалося підготувати YouTube. Тло зі Steam доступне.",
    "standalone_status": "Ігор зі збереженням: {0} · тло в кеші: {1}",
    "preset": "Режим витрати батареї",
    "preset_light": "Легкий",
    "preset_balanced": "Збалансований",
    "preset_maximum": "Максимум",
    "preset_desc": "Легкий: нерухоме тло від батареї й без відео на головній; Максимум: 1080p і відео всюди",
    "bg_source": "Джерело живого тла",
    "source_for_game": "Джерело для цієї гри",
    "source_steam": "Крамниця Steam",
    "source_youtube": "YouTube (експериментально)",
    "source_recording": "Записи моєї гри",
    "youtube_optin": "Дозволити YouTube і завантажити yt-dlp",
    "youtube_desc": "Явна згода на завантаження офіційного yt-dlp; без Node YouTube може не працювати",
    "recording_optin": "Використовувати Steam Background Recording",
    "recording_desc": "Типово вимкнено; обробка лише під час заряджання й поза грою",
    "theme_optin": "Шукати музику теми",
    "theme_desc": "Типово вимкнено через авторські обмеження; використовується yt-dlp",
    "disk_limit": "Ліміт кешу відео",
    "clear_cache": "Очистити кеш тла",
    "cache_cleared": "Кеш тла очищено",
    "original_description": "Опис показано мовою Steam без перекладу"
  }
};

Object.assign(I18N.ru, {
  report_collect: "Собрать отчёт для разработчика", report_description: "Сначала просмотрите обезличенные данные; затем сохраните ZIP и приложите его к Issue вручную.",
  report_title: "Проверка отчёта", report_privacy: "В ZIP войдёт только показанный ниже JSON: версии, язык, настройки, хвост лога, установленные игры и результаты читателей, состояние кеша. Сейвы и медиа не включаются. Имена, пути профиля и Steam ID скрыты. Проверьте текст перед сохранением.",
  report_save: "Сохранить ZIP", report_saved: "Сохранено: {0}/{1}", report_failed: "Не удалось собрать или сохранить отчёт: {0}",
  report_busy: "Собираем отчёт…", dialog_cancel: "Отмена", dialog_accept: "Разрешить", consent_title: "Разрешить yt-dlp?",
  consent_youtube: "Continue? скачает yt-dlp с проверкой SHA256. Поиск и загрузка трейлеров YouTube требуют сети; без JS-рантайма источник экспериментальный. Разрешение можно выключить в меню.",
  consent_theme: "Continue? скачает yt-dlp с проверкой SHA256 для поиска музыки тем. Музыка загружается только по вашему согласию; права принадлежат авторам. Это отдельное разрешение от трейлеров YouTube."
});
Object.assign(I18N.en, {
  report_collect: "Collect a developer report", report_description: "Review the sanitized data first, then save a ZIP and attach it to an Issue manually.",
  report_title: "Review the report", report_privacy: "The ZIP contains only the JSON shown below: versions, language, settings, a log tail, installed games and reader results, and cache status. Saves and media are excluded. Names, profile paths and Steam IDs are redacted. Review the text before saving.",
  report_save: "Save ZIP", report_saved: "Saved: {0}/{1}", report_failed: "Could not collect or save the report: {0}",
  report_busy: "Collecting report…", dialog_cancel: "Cancel", dialog_accept: "Allow", consent_title: "Allow yt-dlp?",
  consent_youtube: "Continue? will download yt-dlp and verify its SHA256. YouTube trailer search and downloads use the network; this source is experimental without a JS runtime. You can withdraw permission in the menu.",
  consent_theme: "Continue? will download yt-dlp and verify its SHA256 to search for theme music. Music downloads require your consent; rights belong to their authors. This permission is separate from YouTube trailers."
});
Object.assign(I18N.uk, {
  report_collect: "Зібрати звіт для розробника", report_description: "Спершу перегляньте знеособлені дані, потім збережіть ZIP і додайте його до Issue вручну.",
  report_title: "Перевірка звіту", report_privacy: "ZIP міститиме лише показаний нижче JSON: версії, мову, налаштування, кінець журналу, встановлені ігри й результати читачів, стан кешу. Збереження та медіа не додаються. Імена, шляхи профілю й Steam ID приховано. Перевірте текст перед збереженням.",
  report_save: "Зберегти ZIP", report_saved: "Збережено: {0}/{1}", report_failed: "Не вдалося зібрати або зберегти звіт: {0}",
  report_busy: "Збираємо звіт…", dialog_cancel: "Скасувати", dialog_accept: "Дозволити", consent_title: "Дозволити yt-dlp?",
  consent_youtube: "Continue? завантажить yt-dlp і перевірить SHA256. Пошук і завантаження трейлерів YouTube потребують мережі; без JS-рантайму джерело експериментальне. Дозвіл можна відкликати в меню.",
  consent_theme: "Continue? завантажить yt-dlp і перевірить SHA256 для пошуку музичних тем. Музика завантажується лише за вашою згодою; права належать авторам. Цей дозвіл окремий від трейлерів YouTube."
});
let LANGUAGE = "ru";
function steamLang(value) {
  const v = String(value || "").trim().toLowerCase();
  return ({ russian: "ru", ukrainian: "uk", english: "en" })[v]
    || (/^(ru|uk|en)(?:-|$)/.exec(v)?.[1]) || "en";
}
function t(key, ...args) {
  const value = I18N[LANGUAGE][key];
  if (value === undefined) throw new Error("Unknown interface key: " + key);
  return typeof value === "string" ? value.replace(/\{(\d+)\}/g, (_, i) => String(args[i] ?? "")) : value;
}
function plural(n, one, few, many) {
  if (LANGUAGE === "en") return n === 1 ? one : many;
  const m10 = n % 10, m100 = n % 100;
  return m10 === 1 && m100 !== 11 ? one : (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20) ? few : many);
}
const MONTHS = { ru: I18N.ru.months, en: I18N.en.months, uk: I18N.uk.months };
function dateRu(ts) {
  const d = new Date(ts * 1000), now = new Date();
  return `${d.getDate()} ${MONTHS[LANGUAGE][d.getMonth()]}${d.getFullYear() !== now.getFullYear() ? " " + d.getFullYear() : ""}`;
}
function ago(ts) {
  const days = Math.floor((Date.now() / 1000 - ts) / 86400);
  if (days <= 0) return t("today");
  if (days === 1) return t("yesterday");
  const shown = (n, key) => `${n} ${plural(n, ...t(key))} ${t("ago")}`;
  if (days < 14) return shown(days, "days");
  if (days < 60) return shown(Math.round(days / 7), "weeks");
  if (days < 365) return shown(Math.round(days / 30), "months_ago");
  return shown(Math.round(days / 365), "years");
}
const hours = v => (Math.round(v * 10) / 10).toLocaleString({ ru: "ru-RU", en: "en-US", uk: "uk-UA" }[LANGUAGE]);
// I18N_END

// Initialize in the shared body: the PC bundler drops only the Decky wrapper.
const languageListeners = new Set();
const languageReady = Promise.resolve().then(() => window.SteamClient?.Settings?.GetCurrentLanguage?.()).catch(() => null)
  .then(value => {
    LANGUAGE = steamLang(value || navigator.language || "english");
    return call("set_lang", LANGUAGE);
  }).catch(e => log("language", e)).then(() => { languageListeners.forEach(f => f(LANGUAGE)); return LANGUAGE; });
function useLanguage() {
  const [code, setCode] = useState(LANGUAGE);
  useEffect(() => { languageListeners.add(setCode); languageReady.then(setCode); return () => languageListeners.delete(setCode); }, []);
  return code;
}
async function localizedCall(...args) { await languageReady; return call(...args); }

// ───────────── иконки (линейные, 24×24) ─────────────

const ICONS = {
  trophy: ["M8 21h8", "M12 17v4", "M7 4h10v5a5 5 0 0 1-10 0V4z", "M17 5h3v2a3 3 0 0 1-3 3", "M7 5H4v2a3 3 0 0 0 3 3"],
  bolt: ["M13 2 4 14h7l-1 8 9-12h-7l1-8z"],
  level: ["M3 17l6-6 4 4 8-8", "M15 7h6v6"],
  shield: ["M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z"],
  coins: ["M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3z", "M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6", "M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"],
  gem: ["M6 3h12l4 6-10 12L2 9l4-6z", "M2 9h20", "M12 21 8 9l4-6 4 6-4 12"],
  clock: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z", "M12 7v5l3 2"],
  scroll: ["M4 4h11a3 3 0 0 1 3 3v13H7a3 3 0 0 1-3-3V4z", "M8 8h6", "M8 12h6"],
  book: ["M4 4h11a3 3 0 0 1 3 3v13H7a3 3 0 0 1-3-3V4z", "M8 8h6", "M8 12h6"],
  heart: ["M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8z"],
  pie: ["M21 12A9 9 0 1 1 12 3v9h9z", "M15 3.5A9 9 0 0 1 20.5 9H15V3.5z"],
  check: ["M20 6 9 17l-5-5"],
  cards: ["M7 3h10a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z", "M9 8h6"],
  signpost: ["M12 3v18", "M5 6h11l3 3-3 3H5z"],
  hourglass: ["M6 2h12", "M6 22h12", "M7 2v3l5 7-5 7v3", "M17 2v3l-5 7 5 7v3"],
  mask: ["M12 2c4 0 7 3 7 8 0 6-3 11-7 12-4-1-7-6-7-12 0-5 3-8 7-8z", "M9 10h.01", "M15 10h.01"],
  shrine: ["M3 21h18", "M5 21V10l7-6 7 6v11", "M10 21v-5h4v5"],
  beast: ["M4 20l4-10 4 5 4-9 4 14z"],
  tooth: ["M7 3C5 3 4 5 4 7c0 3 2 5 2 9 0 3 1 5 2 5s2-3 2-5 1-2 2-2 2 0 2 2 1 5 2 5 2-2 2-5c0-4 2-6 2-9 0-2-1-4-3-4-2 0-3 1-5 1S9 3 7 3z"],
  raven: ["M3 14c2 0 4-1 6-4 1.5-2 3-3 5-3 1.5 0 2.5.7 3 1.5L21 8l-2.5 2.5c0 4-3 7.5-8 7.5l-2 3-.5-3.5L4 16z", "M15 9.5h.01"],
  wheel: ["M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z", "M12 6v6l4 2"],
  leaf: ["M11 20A7 7 0 0 1 4 13c0-4 3.5-7.5 8-11 4.5 3.5 8 7 8 11a7 7 0 0 1-7 7z", "M12 2v18"],
  moon: ["M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"],
  jump: ["M12 4a2 2 0 1 0 0-4 2 2 0 0 0 0 4z", "M4 14l5-3 3 2 4-4 4 2", "M9 11v6l-3 4", "M14 13v4l4 4"],
  hanger: ["M12 4a2 2 0 0 0-2 2c0 1.1.9 2 2 2h.5l-8 7.5A2 2 0 0 0 6 18h12a2 2 0 0 0 1.5-3.3L12 8"],
  sun: ["M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10z", "M12 1v2", "M12 21v2", "M4.2 4.2l1.4 1.4", "M18.4 18.4l1.4 1.4", "M1 12h2", "M21 12h2", "M4.2 19.8l1.4-1.4", "M18.4 5.6l1.4-1.4"],
  bag: ["M6 7h12l-1 13H7L6 7z", "M9 7V6a3 3 0 0 1 6 0v1"],
  camera: ["M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z", "M12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z"],
  eye: ["M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12z", "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"],
  flag: ["M5 22V3", "M5 4h12l-2 4 2 4H5"],
  gamepad: ["M7 8h10a5 5 0 0 1 4.7 6.7l-1 3A2 2 0 0 1 17.5 19L15 17H9l-2.5 2a2 2 0 0 1-3.2-1.3l-1-3A5 5 0 0 1 7 8z", "M7 12v4", "M5 14h4", "M16 13h.01", "M19 15h.01"],
  key: ["M21 2l-9.6 9.6", "M15 5l4 4", "M7 21a5 5 0 1 1 0-10 5 5 0 0 1 0 10z"],
  map: ["M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3V6z", "M9 3v15", "M15 6v15"],
  "map-pin": ["M12 22s7-6.2 7-13a7 7 0 1 0-14 0c0 6.8 7 13 7 13z", "M12 12a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"],
  potion: ["M9 2h6", "M10 2v6l-5 9a3 3 0 0 0 3 4h8a3 3 0 0 0 3-4l-5-9V2", "M7 15h10"],
  puzzle: ["M8 3h4a3 3 0 1 1 3 3h6v6a3 3 0 1 0 0 6v3h-6a3 3 0 1 0-6 0H3v-6a3 3 0 1 1 0-6V3h5z"],
  skull: ["M5 11a7 7 0 1 1 14 0v5l-3 2v3H8v-3l-3-2v-5z", "M9 12h.01", "M15 12h.01", "M10 17h4"],
  smile: ["M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z", "M8 9h.01", "M16 9h.01", "M8 14s1.5 3 4 3 4-3 4-3"],
  star: ["M12 2l3 6 6.5 1-4.7 4.6 1.1 6.4-5.9-3-5.9 3 1.1-6.4L2.5 9 9 8l3-6z"],
  sword: ["M14 4l6-2-2 6-9 9-4 1 1-4 9-9z", "M5 13l6 6", "M4 20l2-2"],
};
Object.assign(ICONS, {
  activity: ICONS.level, award: ICONS.trophy, badge: ICONS.shield, bookmark: ICONS.book,
  "check-circle": ICONS.check, coin: ICONS.coins, disc: ICONS.wheel, "help-circle": ICONS.check,
  orb: ICONS.gem, percent: ICONS.pie, target: ICONS.level, trend: ICONS.level, zap: ICONS.bolt,
});
const BUILTIN_ICONS = {"flag":"M3 2h2v20H3z M5 3h15l-4 5 4 5H5z","gem":"M5 3h14l4 6-11 14L1 9z","clock":"M12 1a11 11 0 1 0 0 22 11 11 0 0 0 0-22z M11 5h2v6l4 2-1 2-5-3z","trophy":"M6 2h12v3h4v4c0 4-3 6-6 6l-2 2v3h5v2H5v-2h5v-3l-2-2c-4 0-6-3-6-6V5h4z M4 7v2c0 2 1 3 3 4L6 7z M18 7l-1 6c2-1 3-2 3-4V7z","sword":"M20 1l3 1-2 7-10 9 3 3-2 2-4-4-4 4-3-3 4-4-3-3 2-2 3 3 9-10z","star":"M12 1l3.4 7 7.6 1-5.5 5.5 1.3 7.5-6.8-3.5-6.8 3.5 1.3-7.5L1 9l7.6-1z","shield":"M12 1l10 4v6c0 6-5 10-10 12C7 21 2 17 2 11V5z","level":"M2 17h5v6H2z M9 11h5v12H9z M16 3h6v20h-6z","sun":"M11 0h2v4h-2z M11 20h2v4h-2z M0 11h4v2H0z M20 11h4v2h-4z M3 2l3 3-1 2-3-3z M18 5l3-3 1 2-3 3z M2 21l3-3 2 1-3 3z M18 19l1-1 3 3-2 1z M12 5a7 7 0 1 0 0 14 7 7 0 0 0 0-14z","scroll":"M5 1h14a3 3 0 0 1 3 3v3h-5v13a3 3 0 0 1-3 3H5a3 3 0 0 1-3-3v-3h5V4a3 3 0 0 0-2-3z M17 4v1h3V4z M4 19v1a1 1 0 0 0 2 0v-1z","pie":"M13 1v10h10A11 11 0 0 0 13 1z M11 3A10 10 0 1 0 21 13H11z","moon":"M16 1A11 11 0 1 0 23 17 10 10 0 0 1 16 1z","heart":"M12 22L2 12C-4 5 6-3 12 4c6-7 16 1 10 8z","eye":"M1 12c5-10 17-10 22 0-5 10-17 10-22 0z M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10z M12 9a3 3 0 1 1 0 6 3 3 0 0 1 0-6z","book":"M2 2h8l2 2 2-2h8v19h-8l-2 2-2-2H2z M11 5v14h2V5z","wheel":"M12 1a11 11 0 1 0 0 22 11 11 0 0 0 0-22z M11 3v6L7 5a8 8 0 0 1 4-2z M13 3a8 8 0 0 1 4 2l-4 4z M19 7a8 8 0 0 1 2 4h-6z M21 13a8 8 0 0 1-2 4l-4-4z M17 19a8 8 0 0 1-4 2v-6z M11 21a8 8 0 0 1-4-2l4-4z M5 17a8 8 0 0 1-2-4h6z M3 11a8 8 0 0 1 2-4l4 4z","coins":"M11 2a8 4 0 1 0 0 8 8 4 0 0 0 0-8z M3 8v4c3 4 13 4 16 0V8c-4 4-12 4-16 0z M3 14v4c3 4 13 4 16 0v-4c-4 4-12 4-16 0z","raven":"M2 20l6-8-5-7 9 4 2-5 4-2 3 4-3 2-1 6-4 3-2 6-2-1 1-5z","check":"M2 11l4-3 4 5L19 2l4 3-13 17z","coin":"M11 2a8 4 0 1 0 0 8 8 4 0 0 0 0-8z M3 8v4c3 4 13 4 16 0V8c-4 4-12 4-16 0z M3 14v4c3 4 13 4 16 0v-4c-4 4-12 4-16 0z","orb":"M5 3h14l4 6-11 14L1 9z","trend":"M2 17h5v6H2z M9 11h5v12H9z M16 3h6v20h-6z","activity":"M2 17h5v6H2z M9 11h5v12H9z M16 3h6v20h-6z","award":"M6 2h12v3h4v4c0 4-3 6-6 6l-2 2v3h5v2H5v-2h5v-3l-2-2c-4 0-6-3-6-6V5h4z M4 7v2c0 2 1 3 3 4L6 7z M18 7l-1 6c2-1 3-2 3-4V7z","badge":"M12 1l10 4v6c0 6-5 10-10 12C7 21 2 17 2 11V5z","bookmark":"M2 2h8l2 2 2-2h8v19h-8l-2 2-2-2H2z M11 5v14h2V5z","check-circle":"M2 11l4-3 4 5L19 2l4 3-13 17z","bolt":"M11 0h2v4h-2z M11 20h2v4h-2z M0 11h4v2H0z M20 11h4v2h-4z M3 2l3 3-1 2-3-3z M18 5l3-3 1 2-3 3z M2 21l3-3 2 1-3 3z M18 19l1-1 3 3-2 1z M12 5a7 7 0 1 0 0 14 7 7 0 0 0 0-14z","zap":"M11 0h2v4h-2z M11 20h2v4h-2z M0 11h4v2H0z M20 11h4v2h-4z M3 2l3 3-1 2-3-3z M18 5l3-3 1 2-3 3z M2 21l3-3 2 1-3 3z M18 19l1-1 3 3-2 1z M12 5a7 7 0 1 0 0 14 7 7 0 0 0 0-14z"};
function Icon({ name }) {
  // свой значок игры (icons/<appid>/<id>.png, ставит бэкенд _apply_icons) — как на ПК (bp_suffix: «img:»)
  if (typeof name === "string" && name.startsWith("img:")) return h("img", { className: "gh-icon-img gh-icon-own", src: DATA + name.slice(4) });
  if (standaloneIcons) return h("svg", { viewBox: "0 0 24 24", fill: "currentColor" }, h("path", { fillRule: "evenodd", d: BUILTIN_ICONS[name] || BUILTIN_ICONS.check }));
  const d = ICONS[name] || ICONS.check;
  return h("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round", strokeLinejoin: "round" },
    ...d.map((p, i) => h("path", { key: i, d: p })));
}

// ───────────── выбор фона: общее состояние панели страницы и меню «…» ─────────────
// Меню «…» живёт в другом окне, но JS-модуль один: панель страницы сообщает, какая игра открыта,
// меню меняет режим её фона, панель перерисовывается.

let viewing = null;                       // { appid, name, media, mode, source, standalone }
const viewListeners = new Set();
const bgListeners = new Set();
const sourceListeners = new Set();
const settingsListeners = new Set();
let standaloneIcons = false;
function setViewing(v) { viewing = v; viewListeners.forEach(f => f(v)); }
function useViewing() {
  const [v, setV] = useState(viewing);
  useEffect(() => { viewListeners.add(setV); setV(viewing); return () => viewListeners.delete(setV); }, []);
  return v;
}
const BG_LABELS = Object.fromEntries(["auto", "trailer", "gameplay", "image", "steam"].map(key => [key, { get label() { return t(`bg_${key}`); } }]));
const SOURCE_LABELS = Object.fromEntries(["steam", "youtube", "recording"].map(key => [key, { get label() { return t(`source_${key}`); } }]));

// ───────────── стиль ─────────────
// Блок рисуется в «базовом» размере и растягивается scale() под свободное место (см. fitPanel).
// Размеры — в CSS-px: экран Steam на Деке 854×534 при DPR 1,5 (скриншот 1280×800).
// С 02.10 нижней полосы Steam («Выбрать / Назад», 40px) нет — тема No-Whats-New + Clean Gameview «Ignore Footer»:
// блок на всю высоту 534, строка «Играть» у самого низа.

const CSS = (accent, hideSteamLogo) => `
.gh-root{position:absolute;left:0;top:0;right:0;height:534px;z-index:0;pointer-events:none;overflow:hidden}
.gh-bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;animation:gh-fade .8s ease}
@keyframes gh-fade{from{opacity:0}to{opacity:1}}
.gh-shade{position:absolute;inset:0;background:
 linear-gradient(90deg,rgba(6,8,12,.92) 0%,rgba(6,8,12,.8) 36%,rgba(6,8,12,.38) 62%,rgba(6,8,12,0) 80%),
 linear-gradient(180deg,rgba(6,8,12,.45) 0%,rgba(6,8,12,0) 18%,rgba(6,8,12,.15) 60%,rgba(6,8,12,.85) 100%)}
.gh-panel{position:absolute;left:36px;top:40px;width:440px;color:#f1f4f7;transform-origin:0 0;animation:gh-in .5s ease}
@keyframes gh-in{from{opacity:0}to{opacity:1}}
.gh-rule{position:absolute;left:-14px;top:2px;bottom:4px;width:2px;border-radius:1px;background:linear-gradient(180deg,rgba(255,255,255,.32),rgba(255,255,255,.04))}
.gh-logo{display:block;max-height:62px;max-width:290px;margin:0 0 14px;filter:drop-shadow(0 2px 10px rgba(0,0,0,.65))}
.gh-logo.gh-logo-dark{filter:invert(1) hue-rotate(180deg) drop-shadow(0 2px 10px rgba(0,0,0,.65))}
.gh-logo-text{font-family:"Noto Serif","DejaVu Serif",Georgia,serif;font-size:26px;letter-spacing:.08em;text-transform:uppercase;margin:0 0 14px;text-shadow:0 2px 12px rgba(0,0,0,.7)}
.gh-kicker{font:700 11.5px/1 "Motiva Sans",Arial,sans-serif;letter-spacing:.18em;text-transform:uppercase;color:${accent};margin-bottom:8px}
.gh-title{font-family:"Noto Serif","DejaVu Serif","Liberation Serif",Georgia,serif;font-size:33px;line-height:1.08;font-weight:400;text-shadow:0 2px 12px rgba(0,0,0,.75)}
.gh-sub{font-family:"Noto Serif","DejaVu Serif","Liberation Serif",Georgia,serif;font-style:italic;font-size:21px;line-height:1.2;color:#e2e7ee;margin-top:5px;text-shadow:0 2px 10px rgba(0,0,0,.75)}
.gh-detail{font-family:"Noto Serif","DejaVu Serif","Liberation Serif",Georgia,serif;font-style:italic;font-size:14px;line-height:1.42;color:#d6dde6;margin-top:7px;display:-webkit-box;-webkit-line-clamp:20;-webkit-box-orient:vertical;overflow:hidden;text-shadow:0 1px 8px rgba(0,0,0,.8)}
.gh-lead{font-size:16px;line-height:1.45;margin-top:4px;color:#e4e9ef}
.gh-factbar{position:absolute;left:36px;bottom:92px;display:grid;column-gap:30px;row-gap:12px;align-items:center;color:#f1f4f7;transform-origin:0 100%;animation:gh-in .5s ease}
.gh-fact{display:flex;align-items:center;gap:9px;white-space:nowrap}
.gh-fact svg{width:24px;height:24px;color:#eef2f6;flex:none}
.gh-fact.gh-people{grid-column:1/-1;flex-direction:column;align-items:flex-start;gap:7px;width:0;min-width:100%}
.gh-people .gh-hd{display:flex;gap:14px;align-items:baseline}
.gh-fact.gh-wide{grid-column:1/-1;width:0;min-width:100%}   /* длинная строка — своим рядом, колонки не раздвигает */   /* свой ряд; ширину колонок остальных не раздвигает */
.gh-pp-row{display:flex;gap:16px;align-items:flex-end}
.gh-pp{display:flex;flex-direction:column;align-items:center;gap:3px;position:relative}
.gh-pp img{width:58px;height:58px;object-fit:contain;filter:drop-shadow(0 2px 6px rgba(0,0,0,.8))}
.gh-pp span{font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#dfe5ec}
.gh-pp.dead img{opacity:.22;filter:grayscale(1)}.gh-pp.dead span{opacity:.4;text-decoration:line-through}
.gh-pp-ph{width:58px;height:58px;border-radius:50%;background:rgba(255,255,255,.15)}

.gh-fact img.gh-icon-own{width:34px;height:34px;flex:none;object-fit:contain;filter:drop-shadow(0 2px 6px rgba(0,0,0,.8))}
.gh-fl{font:700 9.5px/1.15 "Motiva Sans",Arial,sans-serif;letter-spacing:.12em;text-transform:uppercase;color:#b4bfcc}
.gh-fv{font-family:"Noto Serif","DejaVu Serif","Liberation Serif",Georgia,serif;font-weight:700;font-size:16px;color:#fff;margin-top:2px}
.gh-fact,.gh-fv,.gh-fl{text-shadow:0 1px 8px rgba(0,0,0,.9)}
.gh-shot{position:absolute;right:28px;bottom:92px;border-radius:8px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.7),0 0 0 1px rgba(255,255,255,.18);animation:gh-in .5s ease}
.gh-shot img{display:block;width:100%;height:100%;object-fit:cover}
.gh-shot div{position:absolute;left:0;right:0;bottom:0;padding:12px 9px 4px;background:linear-gradient(180deg,rgba(6,8,12,0),rgba(6,8,12,.9));display:flex;align-items:center;gap:5px;font:700 8.5px/1.2 "Motiva Sans",Arial,sans-serif;letter-spacing:.12em;text-transform:uppercase;color:#d0d8e2}
.gh-shot svg{width:12px;height:12px;color:${accent};flex:none}
${hideSteamLogo ? `.${DFL.appDetailsHeaderClasses.BoxSizerContainer}{opacity:0!important}` : ""}
.hltb-info{display:none!important}
${playBarCss()}
`;

// Полоса «Играть / Запуск / кнопки» прозрачная (просьба владельца 02.10, Дека и ПК): под ней два слоя —
// сама полоса (тема Clean Gameview на Деке, .33) и подложка нижней части страницы Steam AppDetailsRoot (.25).
// Тему не трогаем — перекрываем на странице игры; тексту полосы — тень, чтобы читался на светлом кадре.
function playBarCss() {
  const bs = DFL.basicAppDetailsSectionStylerClasses || {};
  if (!bs.PlaySection || !bs.AppDetailsRoot) return "";
  return `.${bs.PlaySection},.${bs.AppDetailsRoot}{background:transparent!important;box-shadow:none!important}
.${bs.PlaySection} *{text-shadow:0 1px 6px rgba(0,0,0,.9),0 0 18px rgba(0,0,0,.6)}`;
}

// Подбор размеров. Полоса фактов — сетка (значок под значком), прижата книзу над кнопкой «Играть»:
// крупнее всего в ОДИН ряд, иначе в два ряда столбцами; не влезает — отпадает последний факт.
// Текст над полосой: важнее всего, чтобы описание поместилось ЦЕЛИКОМ; при нехватке места сначала
// убирается необязательная строка («Сохранение от …»), затем мельчает шрифт, и только в самом конце
// описание обрезается. Логотип растёт лишь на оставшееся место.
const FIT = { width: 560, barRight: 826, top: 40, gap: 16, rootH: 534, barBottom: 92,
  scales: [1.45, 1.35, 1.25, 1.15, 1.07, 1.0], oneRow: [1.45, 1.35, 1.25, 1.15, 1.07, 1.0], twoRows: [1.25, 1.15, 1.07, 1.0],
  logoH: [130, 112, 96, 84], logoMin: 66, logoW: 480 };

// Вид «как в хабе» для большого экрана (ПК/телевизор, внешний монитор Деки). Хаб — эталон владельца (02.10: «в хабе
// размеры лучше, меньше»). Размеры сняты с хаба на ТВ (1280×720 CSS, research/hub_measure.py) и переведены в единицы
// панели (×534/720). Подбор масштаба не раздувает текст (на большом экране места много, и ×1.45 делало всё крупным,
// а факты GoW уходили в два ряда) — только ужимает, если не влезает.
const FIT_DECK = { scales: FIT.scales, oneRow: FIT.oneRow, twoRows: FIT.twoRows, logoH: FIT.logoH, logoMin: FIT.logoMin, logoW: FIT.logoW };
const FIT_HUB = { scales: [1.0, 0.94, 0.88, 0.82], oneRow: [1.0, 0.94, 0.88], twoRows: [1.0, 0.94], logoH: [85, 76, 68], logoMin: 52, logoW: 342 };
function useHubLook(on) { Object.assign(FIT, on ? FIT_HUB : FIT_DECK); }
const HUB_LOOK_CSS = `
.gh-kicker{font:400 12px/1.3 Georgia,"Times New Roman",serif!important;letter-spacing:.16em}
.gh-title{font-family:Georgia,"Times New Roman",serif;font-size:33.6px;line-height:1.08}
.gh-sub{font-family:Georgia,serif;font-size:22.7px;line-height:1.12}
.gh-detail{font-family:Georgia,serif;font-size:12.3px;line-height:1.55}
.gh-detail.gh-lead{font-size:14px;line-height:1.5}
.gh-fl{font:400 9.1px/1.18 Georgia,serif!important;letter-spacing:.12em}
.gh-fv{font-family:Georgia,serif;font-size:12.65px;line-height:1.24;font-weight:700;letter-spacing:.01em}
.gh-fact svg.gh-glyph{width:29px;height:29px}
.gh-fact .gh-icon-img,.gh-fact .gh-icon-raven{width:36px;height:36px}
`;

function fitBar(bar, width) {
  if (!bar) return FIT.rootH - FIT.barBottom;
  const facts = [...bar.querySelectorAll(".gh-fact")];
  const place = (cols, sc) => {
    bar.style.gridTemplateColumns = `repeat(${cols}, max-content)`;
    bar.style.transform = `scale(${sc})`;
    return bar.scrollWidth * sc <= width;
  };
  for (let hide = 0; hide < Math.max(1, facts.length); hide++) {
    facts.forEach((f, i) => { f.style.display = i >= facts.length - hide ? "none" : ""; });
    const n = facts.length - hide;
    for (const sc of FIT.oneRow) if (place(n, sc)) return FIT.rootH - FIT.barBottom - bar.offsetHeight * sc;
    if (n > 2) for (const sc of FIT.twoRows) if (place(Math.ceil(n / 2), sc)) return FIT.rootH - FIT.barBottom - bar.offsetHeight * sc;
  }
  return FIT.rootH - FIT.barBottom - bar.offsetHeight;
}

function fitPanel(el, bar, logo, barWidth, shot, video) {
  if (!el) return;
  const barTop = fitBar(bar, barWidth);
  if (shot && bar) {   // кадр сохранения — той же высоты, что полоса фактов, и на той же линии
    const hgt = Math.max(70, Math.min(130, FIT.rootH - FIT.barBottom - barTop));
    shot.style.height = hgt + "px"; shot.style.width = Math.round(hgt * 16 / 9) + "px";
  }
  const avail = barTop - FIT.top - FIT.gap;
  const det = el.querySelector(".gh-detail");
  const optional = [...el.querySelectorAll(".gh-optional")];
  const fits = () => el.getBoundingClientRect().height <= avail;
  const setLogo = (hv, sc) => { if (logo) { logo.style.maxHeight = (hv / sc) + "px"; logo.style.maxWidth = (FIT.logoW / sc) + "px"; } };
  const grow = sc => {   // уместилось — даём логотипу остаток места
    for (const hv of FIT.logoH) { setLogo(hv, sc); if (fits()) return; }
    setLogo(FIT.logoMin, sc);
  };
  // Живой фон играет — описание скромнее (уже, мельче, до 4 строк), чтобы видео было видно.
  // Нет видео (картинка, игра не скачана) — описание крупное и целиком: так удобнее читать.
  const width = video ? 470 : FIT.width;
  const scales = video ? FIT.scales.filter(x => x <= 1.15) : FIT.scales;
  if (det) det.style.webkitLineClamp = video ? "4" : "20";
  for (const dropOptional of [false, true]) {
    optional.forEach(o => { o.style.display = dropOptional ? "none" : ""; });
    for (const sc of scales) {
      el.style.width = (width / sc) + "px";
      el.style.transform = `scale(${sc})`;
      setLogo(FIT.logoMin, sc);
      if (fits()) { grow(sc); return; }
    }
  }
  for (const clamp of [6, 5, 4, 3, 2]) {   // крайний случай: описание не влезает и в мелком шрифте
    if (det) det.style.webkitLineClamp = String(clamp);
    if (fits()) return;
  }
}

// ───────────── строка Steam внизу: время прохождения рядом с «Запуск» / «Наиграно» ─────────────
// Строку рисует Steam; добавляем к ней пункты-клоны её же пунктов (тот же вид). Длинные подписи Steam
// укорачиваем («Последний запуск» → «Запуск», «Вы играли» → «Наиграно»), чтобы всё влезло до кнопок справа.

const PB_LABELS = new RegExp("^(" + [...new Set(Object.values(I18N).flatMap(d => d.steam_stats))].join("|") + ")$", "i");
const PB_SHORT = Object.fromEntries(Object.values(I18N).flatMap(d => d.steam_stats.slice(0, 3).map((label, i) => [label, { get label() { return t(["played", "last_played", "space"][i]); } }])));
function playBarStat(doc) {
  const labels = [...doc.querySelectorAll("div")].filter(d => d.childElementCount === 0 && PB_LABELS.test(d.textContent.trim()));
  const items = labels.map(l => l.parentElement?.parentElement).filter(Boolean);
  if (!items.length) {   // не-Steam игры: Steam оставляет пустой блок статистики — заполняем его сами
    const cls = DFL.playSectionClasses || {};
    const row = cls.GameStatsSection && doc.querySelector("." + cls.GameStatsSection);
    return row ? { row, template: null, labels: [] } : null;
  }
  const wrapped = it => it.parentElement?.classList.contains("tool-tip-source");
  const outer = it => wrapped(it) ? it.parentElement : it;
  return { row: outer(items[0]).parentElement, template: items.find(it => !wrapped(it)) || items[items.length - 1], labels };
}
function makeStat(doc, label, value) {   // пункт строки по классам самого Steam (когда клонировать нечего)
  const cls = DFL.playSectionClasses || {};
  const el = (c, t) => { const d = doc.createElement("div"); d.className = c || ""; if (t != null) d.textContent = t; return d; };
  const stat = el(cls.GameStat), right = el(cls.GameStatRight);
  right.append(el(cls.PlayBarLabel, label), el(cls.PlayBarDetailLabel, value));
  stat.append(right);
  return stat;
}
// Правило владельца (02.10): время прохождения — только в строке Steam. Что не влезает до кнопок справа,
// не показываем вовсе (в ряд значков игры не переносим и не ужимаем).
function usePlayBarHltb(rootRef, items) {
  const key = JSON.stringify(items);
  useEffect(() => {
    const ensure = () => {
      const doc = rootRef.current?.ownerDocument;
      const found = doc && playBarStat(doc);
      if (!found) return;
      for (const l of found.labels) { const s = PB_SHORT[l.textContent.trim()]; if (s) l.textContent = s.label; }
      if (!items.length || found.row.dataset.ghHltbDone === key) return;
      const { row, template: stat } = found;
      row.querySelectorAll("[data-gh-hltb]").forEach(n => n.remove());
      for (const it of items) {
        let c;
        if (stat) {
          c = stat.cloneNode(true);
          c.removeAttribute("tabindex");
          c.classList.remove("Focusable");
          const leafs = [...c.querySelectorAll("div")].filter(d => d.childElementCount === 0);
          if (leafs.length >= 2) { leafs[0].textContent = it.label; leafs[1].textContent = it.value; }
        } else c = makeStat(doc, it.label, it.value);
        c.setAttribute("data-gh-hltb", "1");
        row.appendChild(c);
      }
      const rr = row.getBoundingClientRect(), cy = rr.top + rr.height / 2;
      const right = [...doc.querySelectorAll(".Focusable")].map(b => b.getBoundingClientRect())
        .filter(r => r.width >= 40 && r.width <= 64 && Math.abs(r.top + r.height / 2 - cy) < 40 && r.left > rr.left + 60)
        .map(r => r.left);
      const limit = right.length ? Math.min(...right) - 12 : 840;
      const mine = [...row.querySelectorAll("[data-gh-hltb]")];
      const first = row.firstElementChild?.getBoundingClientRect().top ?? mine[0].getBoundingClientRect().top;
      const bad = n => { const r = n.getBoundingClientRect(); return r.right > limit || Math.abs(r.top - first) > 6; };
      while (mine.length && bad(mine[mine.length - 1])) mine.pop().remove();   // сначала уходит «На 100%», потом «Сюжет»
      row.dataset.ghHltbDone = key;
    };
    ensure();
    const t = setInterval(ensure, 800);
    return () => {
      clearInterval(t);
      const doc = rootRef.current?.ownerDocument;
      doc?.querySelectorAll("[data-gh-hltb]").forEach(n => n.remove());
      doc?.querySelectorAll("[data-gh-hltb-done]").forEach(n => { delete n.dataset.ghHltbDone; });
    };
  }, [key]);
}

// ───────────── кнопки в ряду Steam справа: магазин (и трансляция с ПК для ярлыков не из Steam) ─────────────
// Вставляем в сам ряд кнопок Steam (рядом с геймпадом и настройками), поэтому крестовина ходит по ним
// как по родным: перехват SP_JSX для элемента с классом AppButtons.

let aliasMap = {};   // свой ярлык → копия той же игры с ПК (трансляция)
const STORE_SVG = h("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round", style: { width: "26px", height: "26px" } },
  h("path", { d: "M3 4h2.2l2.3 11h10.6l2-8H6.4" }), h("circle", { cx: 9.5, cy: 19.5, r: 1.4 }), h("circle", { cx: 17, cy: 19.5, r: 1.4 }));
const STREAM_SVG = h("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round", style: { width: "26px", height: "26px" } },
  h("rect", { x: 3, y: 4, width: 18, height: 12, rx: 1.5 }), h("path", { d: "M8 20h8" }), h("path", { d: "M12 16v4" }), h("path", { d: "M10 8.5l4 1.5-4 1.5z" }));

function currentAppId() {
  try {
    const p = window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance?.m_history?.location?.pathname || "";
    const m = p.match(/^\/library\/app\/(\d+)/);
    return m ? Number(m[1]) : null;
  } catch (e) { return null; }
}

// Тёмный логотип на тёмном фоне не виден (Death Stranding 2 и т.п., просьба владельца 02.10): меряем среднюю яркость
// непрозрачных пикселей; почти чёрный — CSS инвертирует светлоту с сохранением оттенков (.gh-logo-dark).
// Мерим отдельной копией картинки: логотип с другого адреса (Decky :1337, служба ПК :8793) без CORS «портит» canvas,
// а crossOrigin на самой картинке без CORS-заголовка не дал бы ей загрузиться вовсе.
const __ghLogoDark = new Map();
function logoIsDark(src) {
  if (__ghLogoDark.has(src)) return Promise.resolve(__ghLogoDark.get(src));
  const measure = img => {
    const w = 96, hgt = Math.max(1, Math.round(w * img.naturalHeight / img.naturalWidth));
    const c = document.createElement("canvas"); c.width = w; c.height = hgt;
    const g = c.getContext("2d"); g.drawImage(img, 0, 0, w, hgt);
    const d = g.getImageData(0, 0, w, hgt).data;
    let sum = 0, n = 0;
    for (let i = 0; i < d.length; i += 4) if (d[i + 3] > 60) { sum += 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2]; n++; }
    return n > 30 && sum / n < 70;   // средняя яркость < 70 из 255 — тёмный
  };
  return new Promise(res => {
    const img = new Image();
    if (!src.startsWith(location.origin)) img.crossOrigin = "anonymous";
    img.onload = () => { let v = false; try { v = measure(img); } catch (e) {} __ghLogoDark.set(src, v); res(v); };
    img.onerror = () => { __ghLogoDark.set(src, false); res(false); };
    img.src = src;
  });
}

// ───────────── ProtonDB (04.10, вместо плагина ProtonDB Badges, который ронял страницу игры) ─────────────
// Оценка совместимости с Linux: кнопка в ряду справа (нажатие — отзывы на protondb.com) и значок на обложке
// в библиотеке рядом с родным значком Деки. На ПК (Big Picture под Windows) не показываем — там это не нужно.
// Выключается в панели «…» (pdb_button / pdb_tiles).
const IS_LINUX = /linux/i.test(navigator.userAgent || "") && !/windows/i.test(navigator.userAgent || "");
const PDB = {
  native: { c: "#62c462", get ru() { return t("pdb_native"); } }, platinum: { c: "#b4c7dc", get ru() { return t("pdb_platinum"); } },
  gold: { c: "#cfb53b", get ru() { return t("pdb_gold"); } }, silver: { c: "#a8a8a8", get ru() { return t("pdb_silver"); } }, bronze: { c: "#cd7f32", get ru() { return t("pdb_bronze"); } },
  borked: { c: "#ff5c5c", get ru() { return t("pdb_borked"); } }, pending: { c: "#8a96a3", get ru() { return t("pdb_pending"); } }, none: { c: "#6b7682", get ru() { return t("pdb_none"); } },
};
let pdbPrefs = { pdb_button: true, pdb_tiles: true };
const pdbCache = new Map();
function pdbGet(appid) {
  if (!pdbCache.has(appid)) pdbCache.set(appid, call("get_protondb", appid).catch(() => null));
  return pdbCache.get(appid);
}
function pdbKey(v) { return v ? (PDB[v.tier] ? v.tier : (v.tier ? "pending" : "none")) : null; }
// Атом ProtonDB в цвете оценки; форма-пометка у особых состояний: платина — искра, нативная — галочка,
// «не работает» — перечёркнут, мало/нет отчётов — пунктир.
function pdbSvg(tier, px) {
  const c = (PDB[tier] || PDB.none).c, dash = tier === "pending" || tier === "none" ? ' stroke-dasharray="2.2 2"' : "";
  const orb = a => `<ellipse cx="12" cy="12" rx="9.5" ry="3.6" transform="rotate(${a} 12 12)" fill="none" stroke="${c}" stroke-width="1.6"${dash}/>`;
  let extra = "";
  if (tier === "platinum") extra = `<path d="M19.5 1.5l.9 2 2 .9-2 .9-.9 2-.9-2-2-.9 2-.9z" fill="${c}"/>`;
  if (tier === "native") extra = `<path d="M15.5 19.5l2.2 2.2 4.3-4.6" fill="none" stroke="${c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`;
  if (tier === "borked") extra = `<path d="M4 20L20 4" stroke="#14181d" stroke-width="4" stroke-linecap="round"/><path d="M4 20L20 4" stroke="${c}" stroke-width="2" stroke-linecap="round"/>`;
  return `<svg viewBox="0 0 24 24" width="${px}" height="${px}" style="display:block">${orb(0)}${orb(60)}${orb(120)}<circle cx="12" cy="12" r="2.1" fill="${c}"/>${extra}</svg>`;
}
function pdbOpen(appid) {
  const url = `https://www.protondb.com/app/${appid}`;
  try { DFL.Navigation.NavigateToExternalWeb(url); } catch (e) { try { SteamClient.URL.ExecuteSteamURL("steam://openurl/" + url); } catch (e2) { log("pdb", e2); } }
}

function patchLibraryPdb() {
  if (!IS_LINUX || !DFL.findClassModule) return () => {};
  // классы в разных модулях Steam: значок совместимости отдельно, плитка библиотеки отдельно
  const m = DFL.findClassModule(x => x.SteamDeckCompatInfo && x.SteamDeckCompatLogo);
  if (!m) return () => {};
  const mb = DFL.findClassModule(x => x.LibraryItemBox) || {};
  const info = String(m.SteamDeckCompatInfo).split(" ")[0], box = mb.LibraryItemBox ? String(mb.LibraryItemBox).split(" ")[0] : null;
  let obs = null, doc = null, w = null, raf = 0, langReady = false;
  languageReady.then(() => { langReady = true; scan(); });
  const appidOf = el => {   // appid плитки — из пропсов React вверх по дереву
    const tile = (box && el.closest("." + box)) || el;   // на главной своя плитка — идём от самого значка
    const k = Object.keys(tile).find(x => x.startsWith("__reactFiber"));
    let f = k ? tile[k] : null;
    for (let i = 0; f && i < 40; i++, f = f.return) {
      const p = f.memoizedProps || {};
      const a = p.app?.appid ?? p.appid ?? p.appOverview?.appid ?? p.overview?.appid;
      if (a) return Number(a);
    }
    return null;
  };
  const scan = () => {
    raf = 0;
    if (!doc || !langReady) return;
    if (!pdbPrefs.pdb_tiles) { doc.querySelectorAll(".gh-pdb-tile").forEach(e => e.remove()); return; }
    doc.querySelectorAll("." + info).forEach(el => {
      if (el.querySelector(":scope > .gh-pdb-tile")) return;
      const appid = appidOf(el);
      if (!appid || appid >= 0x80000000) return;
      const span = doc.createElement("span");
      span.className = "gh-pdb-tile";
      span.style.cssText = "display:inline-flex;align-items:center;margin:0 5px 0 2px";
      el.insertBefore(span, el.firstChild);
      pdbGet(appid).then(v => {
        const t = pdbKey(v);
        if (!t || t === "none") { span.remove(); return; }
        span.innerHTML = pdbSvg(t, 19);
        span.title = "ProtonDB: " + PDB[t].ru;
      });
    });
  };
  const start = () => {
    w = window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance?.BrowserWindow;
    if (!w?.document?.body) return false;
    doc = w.document;
    obs = new w.MutationObserver(() => { if (!raf) raf = w.requestAnimationFrame(scan); });
    obs.observe(doc.body, { childList: true, subtree: true });
    if (langReady) scan();
    return true;
  };
  const t = setInterval(() => { if (start()) clearInterval(t); }, 1000);
  return () => { clearInterval(t); obs?.disconnect(); doc?.querySelectorAll(".gh-pdb-tile").forEach(e => e.remove()); };
}

function HubAppButtons() {
  useLanguage();
  const appid = currentAppId();
  const showPdb = IS_LINUX && pdbPrefs.pdb_button && appid && appid < 0x80000000;
  const [pdb, setPdb] = useState(null);
  useEffect(() => { setPdb(null); if (showPdb) pdbGet(appid).then(setPdb); }, [appid, showPdb]);
  if (!appid || !DFL.Focusable) return null;
  const cls = DFL.playSectionClasses?.MenuButton || "";
  // отступ — как у родных кнопок между собой (раньше «Магазин» стоял дальше от геймпада на лишние 10px)
  const btn = (key, label, svg, go) => h(DFL.Focusable, { key, className: cls, role: "button", "aria-label": label,
    onActivate: go, onClick: go }, svg);
  const out = [];
  const tier = showPdb ? pdbKey(pdb) : null;
  if (tier) out.push(btn("gh-pdb", "ProtonDB: " + PDB[tier].ru + (pdb?.total ? t("pdb_reports", pdb.total) : ""),
    h("span", { style: { display: "flex" }, dangerouslySetInnerHTML: { __html: pdbSvg(tier, 26) } }), () => pdbOpen(appid)));
  const pc = aliasMap[String(appid)];
  if (pc) out.push(btn("gh-stream", t("stream"), STREAM_SVG, () => {
    // сразу поток с ПК (как «Транслировать» у игр Steam); нет ПК в сети — страница копии с её кнопкой
    try {
      const cd = (window.appStore?.GetAppOverviewByAppID?.(pc)?.per_client_data || []).find(c => c.clientid && c.clientid !== "0" && c.installed);
      if (cd) SteamClient.Apps.StreamGame(pc, cd.clientid, -1);
      else DFL.Navigation.Navigate(`/library/app/${pc}`);
    } catch (e) { log("stream", e); }
  }));
  if (appid < 0x80000000) out.push(btn("gh-store", t("store"), STORE_SVG, () => {
    try { SteamClient.URL.ExecuteSteamURL(`steam://store/${appid}`); } catch (e) { log("store", e); }
  }));
  return out.length ? h(React.Fragment, null, ...out) : null;
}

function patchAppButtons() {
  // 04.10: перехват ставится ОДИН раз на всю жизнь Steam и при каждом показе берёт актуальный компонент из
  // window.__ghButtonsImpl. Раньше после перевыкатки плагина старый перехват оставался с флагом «уже сделано» —
  // новая версия пропускала свой, а старый (код выгруженного плагина) кнопок не рисовал: «пропали магазин и ProtonDB».
  const J = window.SP_JSX;
  const cls = DFL.basicAppDetailsSectionStylerClasses?.AppButtons;
  if (!J || !cls) return () => {};
  window.__ghButtonsImpl = HubAppButtons;
  window.__ghButtonsCls = cls;   // имя класса ряда — из window при каждом показе (перехват живёт дольше версии плагина)
  const install = () => {
    const orig = { jsx: J.jsx, jsxs: J.jsxs };
    const wrap = fn => function (type, props, key) {
      const Impl = window.__ghButtonsImpl;
      const rowCls = window.__ghButtonsCls;
      if (Impl && rowCls && props && typeof props.className === "string" && props.className.split(" ").includes(rowCls)) {
        try {
          const kids = Array.isArray(props.children) ? props.children : [props.children];
          // элемент с этим классом создаётся дважды (обёртка и вложенный Panel) — вставляем один раз
          if (!kids.some(k => k && k.key === "gh-buttons"))
            props = { ...props, children: [window.SP_REACT.createElement(Impl, { key: "gh-buttons" }), ...kids] };
        } catch (e) {}
      }
      return fn.call(this, type, props, key);
    };
    J.jsx = wrap(orig.jsx); J.jsxs = wrap(orig.jsxs);
  };
  // 06.10: другие перехваты SP_JSX при снятии откатывают цепочку к своему «до» и срезают наш слой (флаг «уже стоит» это не видел —
  // кнопки пропадали после каждой перевыкатки). Теперь раз в 2 с проверяем пробным вызовом, вставляются ли кнопки, и ставим слой заново.
  const works = () => {
    try {
      if (!window.__ghButtonsImpl || !window.__ghButtonsCls) return true;
      const el = J.jsxs("div", { className: window.__ghButtonsCls, children: [] });
      const ch = el?.props?.children;
      return Array.isArray(ch) && ch.some(k => k && k.key === "gh-buttons");
    } catch (e) { return true; }
  };
  if (!works()) install();
  clearInterval(window.__ghBtnTimer);
  window.__ghBtnTimer = setInterval(() => { if (!works()) install(); }, 2000);
  return () => { clearInterval(window.__ghBtnTimer); if (window.__ghButtonsImpl === HubAppButtons) window.__ghButtonsImpl = null; };
}

// ───────────── панель «Где остановился» ─────────────

function useAchievements(appid) {
  const [a, setA] = useState(null);
  useEffect(() => {
    setA(null);
    let alive = true, tries = 0;
    try { window.appDetailsStore?.RequestAchievements?.(appid); } catch (e) {}
    const read = () => {
      try {
        const x = window.appDetailsStore?.GetAchievements?.(appid);
        if (x && x.nTotal > 0) { if (alive) setA({ got: x.nAchieved, total: x.nTotal }); return true; }
      } catch (e) {}
      return false;
    };
    if (!read()) {
      const t = setInterval(() => { if (read() || ++tries > 45) clearInterval(t); }, 700);   // Steam грузит достижения до ~30 с
      return () => { alive = false; clearInterval(t); };
    }
    return () => { alive = false; };
  }, [appid]);
  return a;
}

function usePlaybackGate(videoRef, enabled) {
  // видео не крутится, пока запущена игра или окно Steam скрыто/экран погас — батарею не жжём
  useEffect(() => {
    if (!enabled) return;
    const tick = () => {
      const v = videoRef.current;
      if (!v) return;
      const doc = v.ownerDocument;
      const busy = gameRunning() || doc?.visibilityState === "hidden";
      if (busy && !v.paused) v.pause();
      else if (!busy && v.paused) v.play().catch(() => {});
    };
    const t = setInterval(tick, 1500);
    tick();
    return () => clearInterval(t);
  }, [enabled]);
}

// Какое видео играть: явный выбор владельца для этой игры сильнее общего переключателя.
function pickVideo(media, mode, liveBg, ac, standalone = false) {
  const m = media || {};
  if (standalone && (liveBg === "off" || (liveBg === "ac" && !ac))) return null;
  if (mode === "image" || mode === "steam") return null;
  if (mode === "gameplay") return m.rec || null;
  if (mode === "trailer") return m.trl || null;
  return m.loop && (liveBg === "always" || (liveBg === "ac" && ac)) ? m.loop : null;
}

function livePolicy(settings, power, home = false) {
  if (!settings?.standalone) return settings?.live_bg || "off";
  const preset = settings.preset || "light";
  if (preset === "maximum") return "always";
  if (home && preset === "light") return "off";
  return power?.ac ? "always" : "off";
}

function limitVideoWindow(video, media, relative, standalone) {
  if (!standalone || !video || !Number.isFinite(video.duration)) return;
  const window = media?.video_windows?.[relative] || {};
  const start = Math.max(0, Number(window.start) || 0);
  const end = Math.min(video.duration, start + Math.min(20, Number(window.seconds) || 20));
  if (end > start && (video.currentTime < start || video.currentTime >= end - 0.05)) {
    try { video.currentTime = start; } catch (e) {}
  }
}

function useStandaloneMusic(appid, settings, media) {
  useEffect(() => {
    if (!settings?.standalone || !settings.theme_music_consent) return;
    let alive = true, audio = null;
    call("get_music_files").then(files => {
      if (!alive || !files?.[appid]) return;
      audio = new Audio(DATA + files[appid]); audio.loop = true; audio.volume = 0.5;
      const tick = () => { if (gameRunning() || document.visibilityState === "hidden") audio.pause(); else audio.play().catch(() => {}); };
      audio._ghTick = setInterval(tick, 1500); tick();
    }).catch(() => {});
    return () => { alive = false; if (audio) { clearInterval(audio._ghTick); audio.pause(); audio.removeAttribute("src"); } };
  }, [appid, settings?.standalone, settings?.theme_music_consent, media]);
}

const SAVE_DATE = new RegExp("^(" + Object.values(I18N).map(d => d.save_prefix).join("|") + ")");

function GameHubPanel({ appid }) {
  const language = useLanguage();
  const ov = window.appStore?.GetAppOverviewByAppID?.(appid);
  const name = ov?.display_name || "";
  const [card, setCard] = useState(null);
  const [hltb, setHltb] = useState(null);
  const [about, setAbout] = useState(null);
  const [power, setPower] = useState({ ac: false });
  const [settings, setSettings] = useState({ live_bg: "always" });
  const [steamLogo, setSteamLogo] = useState(null);
  const [logoFailed, setLogoFailed] = useState(false);
  const [, setTick] = useState(0);
  const rootRef = useRef(null), videoRef = useRef(null), panelRef = useRef(null), barRef = useRef(null), logoRef = useRef(null), shotRef = useRef(null);
  const ach = useAchievements(appid);
  useStandaloneMusic(appid, settings, card?.media);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [c, p, s] = await Promise.all([localizedCall("get_card", appid, name), call("get_power"), call("get_settings")]);
        if (!alive) return;
        setCard(c); setPower(p || { ac: false }); setSettings(s || {});
        standaloneIcons = !!c?.standalone;
        if (c?.hltb) setHltb(c.hltb);
        else { const x = await localizedCall("get_hltb", appid, name); if (alive && x) setHltb(x); }
        if (s?.standalone && p?.ac && !gameRunning()) {
          call("refresh_media", appid, name, false, null, false).then(async r => {
            if (alive && r?.ok && (!r.cached || r.theme)) setCard(await localizedCall("get_card", appid, name));
          }).catch(e => log("standalone media", e));
        }
      } catch (e) { log("get_card", e); }
    })();
    localizedCall("get_about", appid).then(x => { if (alive) setAbout(x); }).catch(() => {});
    const t = setInterval(async () => { try { const p = await call("get_power"); if (alive) setPower(p); } catch (e) {} }, 60000);
    return () => { alive = false; clearInterval(t); };
  }, [appid, language]);

  useEffect(() => {  // режим фона поменяли в меню «…»
    const f = (id, mode) => { if (id === appid) setCard(c => c && ({ ...c, bg_mode: mode })); };
    bgListeners.add(f);
    return () => bgListeners.delete(f);
  }, [appid]);

  useEffect(() => {
    const f = async ns => { if (ns.standalone) { setSettings(ns); setCard(await localizedCall("get_card", appid, name)); } };
    settingsListeners.add(f);
    return () => settingsListeners.delete(f);
  }, [appid, name, language]);

  useEffect(() => {
    if (!settings.standalone) return;
    const beat = () => call("set_media_context", gameRunning()).catch(() => {});
    beat(); const timer = setInterval(beat, 1500);
    return () => clearInterval(timer);
  }, [settings.standalone]);

  useEffect(() => {  // автономный источник поменяли в меню «…»
    const f = async (id) => { if (id === appid) setCard(await localizedCall("get_card", appid, name)); };
    sourceListeners.add(f);
    return () => sourceListeners.delete(f);
  }, [appid, name, language]);

  useEffect(() => {  // меню «…» должно знать, какая игра открыта
    if (!card) return;
    setViewing({ appid, name, media: card.media || {}, mode: card.bg_mode || "auto",
      source: card.bg_source || "steam", standalone: !!card.standalone });
    return () => { if (viewing?.appid === appid) setViewing(null); };
  }, [appid, card]);

  useEffect(() => {  // логотип Steam (если у хаба нет своего) — из шапки страницы, когда Steam его выставит
    setSteamLogo(null);
    setLogoFailed(false);
    let tries = 0;
    const t = setInterval(() => {
      const doc = rootRef.current?.ownerDocument;
      const img = doc?.querySelector(`.${DFL.appDetailsHeaderClasses.TitleImageContainer} img`);
      const src = img?.getAttribute("src") || "";
      if (/logo/i.test(src) && (src.includes(String(appid)) || src.includes("customimages"))) {
        setSteamLogo(new URL(src, doc.baseURI).href); clearInterval(t);
      } else if (++tries > 15) clearInterval(t);
    }, 200);
    return () => clearInterval(t);
  }, [appid, card]);

  // время прохождения — в строку Steam внизу (не дублируем его крупно в блоке)
  const pbItems = [];
  if (hltb?.main) pbItems.push({ label: t("story"), value: `~${hours(hltb.main)} ${t("hour_short")}` });
  if (hltb?.complete) pbItems.push({ label: t("completionist"), value: `~${hours(hltb.complete)} ${t("hour_short")}` });
  usePlayBarHltb(rootRef, card ? pbItems : []);

  const mode = card?.bg_mode || "auto";
  const videoRel = card ? pickVideo(card.media, mode, livePolicy(settings, power), power.ac, !!card.standalone) : null;
  const hasShot = !!card?.media?.shot;
  const barWidth = FIT.barRight - 36 - (hasShot ? 250 : 0);
  usePlaybackGate(videoRef, !!videoRel);
  useEffect(() => {  // то же видео, что на главной, — без перезапуска
    const v = videoRef.current;
    if (!v || !videoRel) return;
    const src = DATA + videoRel;
    seekResume(v, src);
    const t = setInterval(() => { if (!v.paused) notePos(src, v.currentTime); }, 400);
    return () => { if (!v.paused) notePos(src, v.currentTime); clearInterval(t); };
  }, [videoRel, !!card]);
  useLayoutEffect(() => {  // подогнать размер блока под экран (после каждой смены содержимого)
    const run = () => fitPanel(panelRef.current, barRef.current, logoRef.current, barWidth, shotRef.current, !!videoRel);
    run();
    const t = setTimeout(run, 500);   // шрифты/логотип доехали
    return () => clearTimeout(t);
  });
  if (!card) return h("div", { ref: rootRef, className: "gh-root" });

  const accent = card.accent || "#c8a96a";
  const mins = ov?.minutes_playtime_forever || 0;
  // Где остановился — только если это действительно известно. Сейв без разобранного места («Есть сохранение»)
  // и игры без данных хаба: крупной надписи нет, место — под описание игры.
  let block = card.block;
  if (block && !block.title && !(card.facts || []).length) block = null;
  if (!block) block = { kicker: mins > 0 || card.block ? "" : t("not_started"), title: "", sub: "", detail: "" };
  const norm = t => String(t || "").toLowerCase().replace(/[«»"().,:·—-]/g, " ").replace(/\s+/g, " ").trim();
  if (block.sub && block.title && norm(block.title).includes(norm(block.sub))) block = { ...block, sub: "" };   // «Хогвартс (Год 1…)» + «Год 1…»
  const saveDate = SAVE_DATE.test(block.detail || "") ? block.detail : (SAVE_DATE.test(card.block?.detail || "") ? card.block.detail : "");
  const originalMark = about?.original_language ? ` · ${t("original_description")}` : "";
  const lead = block.title ? (SAVE_DATE.test(block.detail || "") ? "" : block.detail) : ((about?.short || "") + originalMark);
  const detail = block.title ? (lead || "") : lead;

  // порядок = важность: достижения, факты сейва; «Наиграно» и время прохождения уже есть в строке Steam
  const facts = [];
  if (ach) facts.push({ icon: card.ach_icon || "trophy", label: t("achievements"), value: `${ach.got} / ${ach.total} · ${Math.round(ach.got * 100 / ach.total)}%` });
  facts.push(...(card.facts || []).filter(f => (f.icon !== "clock" || (f.id === "save_time" || Object.values(I18N).some(d => String(f.label).toLowerCase().includes(d.save_word))))
    && !(block.title && String(f.value).length > 6 && norm(block.title).includes(norm(f.value)))));   // факт = повтор заголовка

  // логотип, выбранный владельцем в Steam (SteamGridDB → customimages), важнее логотипа хаба
  const logo = logoFailed ? null : (steamLogo && steamLogo.includes("customimages") ? steamLogo
    : (card.media?.logo ? DATA + card.media.logo : steamLogo));
  const onLogo = e => {  // обложка вместо логотипа (высокая картинка) — не логотип: пишем название текстом
    const im = e.currentTarget;
    if (im.naturalHeight > im.naturalWidth * 0.85) { setLogoFailed(true); return; }
    setTick(t => t + 1);
    logoIsDark(im.src).then(dark => { if (dark) im.classList.add("gh-logo-dark"); }).catch(() => {});
  };
  const bg = videoRel ? h("video", { key: videoRel, ref: videoRef, className: "gh-bg", src: DATA + videoRel, autoPlay: true, muted: true, loop: true, playsInline: true,
      onLoadedMetadata: e => limitVideoWindow(e.currentTarget, card.media, videoRel, !!card.standalone),
      onTimeUpdate: e => limitVideoWindow(e.currentTarget, card.media, videoRel, !!card.standalone) })
    : (mode !== "steam" && card.media?.wall ? h("img", { className: "gh-bg", src: DATA + card.media.wall }) : null);

  return h("div", { ref: rootRef, className: "gh-root" },
    h("style", null, CSS(accent, true)),
    bg,
    h("div", { className: "gh-shade" }),
    h("div", { ref: panelRef, className: "gh-panel" },
      h("div", { className: "gh-rule" }),
      logo ? h("img", { key: logo, ref: logoRef, className: "gh-logo", src: logo, onError: () => setLogoFailed(true), onLoad: onLogo })
        : h("div", { className: "gh-logo-text" }, name),
      block.kicker ? h("div", { className: "gh-kicker" }, block.kicker) : null,
      block.title ? h("div", { className: "gh-title" }, block.title) : null,
      block.sub ? h("div", { className: "gh-sub" }, block.sub) : null,
      detail ? h("div", { className: "gh-detail" + (block.title ? "" : " gh-lead") }, detail) : null,
      null /* «Сохранение от …» убрано по решению владельца 06.10 */),
    hasShot ? h("div", { ref: shotRef, className: "gh-shot" },
      h("img", { src: DATA + card.media.shot }),
      h("div", null, h(Icon, { name: "camera" }), t("save_frame"))) : null,
    facts.length ? h("div", { ref: barRef, className: "gh-factbar" },
      ...facts.map((f, i) => f.people && f.people.length
        ? h("div", { key: i, className: "gh-fact gh-people" },
            h("div", { className: "gh-hd" }, h("div", { className: "gh-fl" }, f.label), h("div", { className: "gh-fv" }, f.value)),
            h("div", { className: "gh-pp-row" }, ...f.people.map(pp => h("div", { key: pp.name, className: "gh-pp" + (pp.alive ? "" : " dead") },
              pp.icon && pp.icon.startsWith("img:") ? h("img", { src: DATA + pp.icon.slice(4) }) : h("div", { className: "gh-pp-ph" }),
              h("span", null, pp.name)))))
        : h("div", { key: i, className: "gh-fact" + (f.label === t("last_achievement") ? " gh-wide" : "") }, h(Icon, { name: f.icon }),
            h("div", null, h("div", { className: "gh-fl" }, f.label), h("div", { className: "gh-fv" }, f.value))))) : null);
}

// Внешний монитор / док (02.10: CFORCE 1920×1080 → Steam рисует 1500×844 CSS при DPR 1.28). Панель посчитана в CSS-px
// экрана Деки (854×534) и стояла фиксированной высоты 534 — на мониторе занимала верх, ниже торчала картинка Steam.
// Как на ПК (bp_suffix pcGeometry): .gh-root растягивается zoom-ом по высоте окна, полоса «Играть» Steam (80 CSS-px) в
// единицах панели — 80/zoom. На своём экране Деки zoom = 1 и всё как было.
const DECK_H = 534, PLAY_BAR = 80, BAR_GAP = 12;
function deckGeometry(win) {
  const W = win.innerWidth, H = win.innerHeight, s = H / DECK_H;
  if (Math.abs(s - 1) < 0.02) return { s: 1, barBottom: PLAY_BAR + BAR_GAP, barRight: W - 28 };
  return { s, barBottom: (PLAY_BAR + BAR_GAP) / s, barRight: W / s - 28 };
}
function DeckPanel({ appid }) {
  const ref = useRef(null);
  const [g, setG] = useState(null);
  useLayoutEffect(() => {
    const w = ref.current?.ownerDocument?.defaultView;
    if (!w) return;
    const upd = () => setG(deckGeometry(w));
    upd();
    w.addEventListener("resize", upd);
    return () => w.removeEventListener("resize", upd);
  }, []);
  if (g) { FIT.rootH = DECK_H; FIT.barBottom = g.barBottom; FIT.barRight = g.barRight; useHubLook(g.s !== 1); }
  // монитор/ТВ — вид и размеры хаба; свой экран Деки — как было (крупно, с подбором масштаба вверх)
  const css = g && g.s !== 1 ? `.gh-root{zoom:${g.s}}.gh-factbar,.gh-shot{bottom:${g.barBottom}px!important}${HUB_LOOK_CSS}` : "";
  return h(React.Fragment, null, h("style", { ref }, css), g ? h(GameHubPanel, { appid }) : null);
}

function patchAppPage() {
  return routerHook.addPatch("/library/app/:appid", (tree) => {
    const routeProps = DFL.findInReactTree(tree, (x) => x?.renderFunc);
    if (routeProps) {
      let appid = null;
      const patchHandler = DFL.createReactTreePatcher([
        (t) => {
          const children = DFL.findInReactTree(t, (x) => x?.props?.children?.props?.overview)?.props?.children;
          appid = children?.props?.overview?.appid ?? null;
          return children;
        },
      ], (_, ret) => {
        const container = DFL.findInReactTree(ret, (x) => Array.isArray(x?.props?.children) &&
          x?.props?.className?.includes(DFL.appDetailsClasses.InnerContainer));
        if (typeof container !== "object" || !appid) return ret;
        if (!container.props.children.some(c => c?.key === "gamehub-panel"))
          container.props.children.splice(1, 0, h(DeckPanel, { key: "gamehub-panel", appid }));
        return ret;
      });
      DFL.afterPatch(routeProps, "renderFunc", patchHandler);
    }
    return tree;
  });
}

// ───────────── библиотека: открывать с ПЕРВОЙ вкладки ─────────────
// Steam помнит последнюю вкладку библиотеки (SteamUIStore.m_LastLibraryTab) и открывает её — владелец ждёт первую
// («Установлено»), а получал «Все игры». Первую вкладку узнаём по самим вкладкам (их может подменить TabMaster или
// версия для ПК) и сбрасываем запомненную при уходе из библиотеки на главную. Из страницы игры назад — та же вкладка.
let firstLibraryTab = null;

// Копии ярлыков не из Steam с ПК (ярлык ПК виден на Деке отдельной игрой) — прячем: на родной карточке есть кнопка трансляции.
// Вкладку «С ПК» не трогаем — там они по смыслу.
const PC_TAB = new RegExp("^(" + Object.values(I18N).map(d => d.pc_tab).join("|") + ")$", "i");
function pcCopies() { return new Set(Object.values(aliasMap).map(Number)); }
function withoutCopies(coll, hide) {
  if (!coll?.allApps || !coll.allApps.some(a => hide.has(a.appid))) return null;
  const apps = coll.allApps.filter(a => !hide.has(a.appid)), vis = (coll.visibleApps || coll.allApps).filter(a => !hide.has(a.appid));
  const c = Object.create(coll);   // методы коллекции Steam/TabMaster остаются, подменяем только списки
  const own = { allApps: apps, visibleApps: vis, apps: new Map(apps.map(a => [a.appid, a])),
    GetAppCountWithToolsFilter: f => vis.filter(a => f.Matches(a)).length };
  // defineProperty, а не присваивание: у коллекций Steam allApps — геттер прототипа, присваивание его не перекроет
  for (const k in own) Object.defineProperty(c, k, { value: own[k], writable: true, configurable: true, enumerable: true });
  return c;
}
function hideCopiesInTab(tab, hide) {
  if (!tab?.content || PC_TAB.test(String(tab.title || ""))) return tab;
  const direct = tab.content.props?.collection, inner = tab.content.props?.children?.props?.collection;
  const c = withoutCopies(direct || inner, hide);
  if (!c) return tab;
  const content = direct ? React.cloneElement(tab.content, { collection: c })
    : React.cloneElement(tab.content, {}, React.cloneElement(tab.content.props.children, { collection: c }));
  // счётчик у вкладки: у вкладок Steam — элемент с collection/count (пересчитываем), у TabMaster — свой, не трогаем
  const addon = tab.renderTabAddon;
  const renderTabAddon = addon && (() => { const el = addon(); return el?.props && "collection" in el.props
    ? React.cloneElement(el, { collection: c, count: c.visibleApps.length }) : el; });
  return { ...tab, content, renderTabAddon };
}
function patchLibraryDefaultTab() {
  const unLayer = keepJsxLayer("libtab", (fn, type, props, key) => {
    if (props && Array.isArray(props.tabs) && props.onShowTab && props.tabs.some(t => t && t.id === "AllGames")) {
      firstLibraryTab = props.tabs[0]?.id || firstLibraryTab;
      const hide = pcCopies();
      if (hide.size && !props.tabs.__ghNoCopies) {
        try { const tabs = props.tabs.map(t => hideCopiesInTab(t, hide)); tabs.__ghNoCopies = true; return fn.call(null, type, { ...props, tabs }, key); } catch (e) {}
      }
    }
  });
  let last = "";
  const t = setInterval(() => {
    try {
      const st = window.SteamUIStore, path = st?.WindowStore?.GamepadUIMainWindowInstance?.m_history?.location?.pathname || "";
      if (path !== last) {
        if (path === "/library/home" && firstLibraryTab && st.m_LastLibraryTab) st.m_LastLibraryTab = { strActiveTab: firstLibraryTab };
        last = path;
      }
    } catch (e) {}
  }, 700);
  return () => { clearInterval(t); unLayer(); };
}

// ───────────── главная: сначала установленные ─────────────
// Главная Steam собирает «Недавние» из сыгранного на этом Деке, покупок и установленного, а с 15-го места
// подмешивает недавнее с других устройств (Jackbox и т.п. с ПК). Коллекции Steam защищены от записи (mobx),
// поэтому перехватываем создание элементов карусели и фона главной: у обоих есть props.games (массив appid)
// и колбэк фокуса. Оставляем установленное в порядке Steam, добираем остальные установленные по свежести.

// Установлено именно на ЭТОМ Деке: ярлыки и игры с ПК (трансляция) тоже приходят с installed=true,
// но без local_per_client_data — их на главной не показываем (для них вкладка «С ПК» в библиотеке).
function isInstalledGame(ov) {
  if (!ov || !(ov.app_type === 1 || ov.app_type === 1073741824)) return false;
  if (/^Proton|Steam Linux Runtime|Steamworks/i.test(ov.display_name || "")) return false;
  const local = ov.local_per_client_data;
  return local ? !!local.installed : (ov.app_type === 1 && !!ov.installed);
}

function installedFirst(games) {
  const as = window.appStore;
  const out = [], seen = new Set(pcCopies());
  for (const id of games) {
    if (id === 0) { out.push(id); continue; }                 // заглушка «текущая игра» — как есть
    const ov = as.GetAppOverviewByAppID(id);
    if (isInstalledGame(ov) && !seen.has(id)) { out.push(id); seen.add(id); }
  }
  const cs = window.collectionStore;
  // «Игры на этом устройстве» не включает ярлыки не из Steam (эмуляторы, другие лаунчеры) — берём их отдельно
  const shortcuts = (cs?.deckDesktopApps?.visibleApps || cs?.deckDesktopApps?.allApps || [])
    .filter(ov => ov.app_type === 1073741824 && !/EmulationStation|Steam ROM Manager|EmuDeck|Decky|Heroic|Lutris/i.test(ov.display_name || ""));
  const favs = new Set((cs?.GetCollection?.("favorite")?.allApps || []).map(ov => ov.appid));
  const recency = ov => Math.max(ov.rt_last_time_locally_played || 0, ov.rt_last_time_played || 0);
  const rest = [...(cs?.localGamesCollection?.visibleApps || []), ...shortcuts]
    .filter(ov => isInstalledGame(ov) && !seen.has(ov.appid))
    .sort((a, b) => (favs.has(b.appid) - favs.has(a.appid)) || (recency(b) - recency(a)));
  for (const ov of rest) if (!seen.has(ov.appid)) { out.push(ov.appid); seen.add(ov.appid); }
  return out.slice(0, 20);
}

function isHomeGamesProps(p) {
  return p && Array.isArray(p.games) && p.games.length && p.games.every(Number.isInteger) &&
    ("onItemFocus" in p || "refOnItemFocus" in p);
}

// 10.10: слой SP_JSX, который сам проверяет, что он ещё в цепочке, и ставится заново. Раньше слои главной/библиотеки/значка
// геймпада ставились один раз с флагом «уже стоит»; когда кто-то откатывал J.jsx к своему «до» (чужой плагин, перевыкатка),
// слой пропадал молча, а флаг оставался — на главной снова показывались ВСЕ игры библиотеки, а не только установленные.
// Проверка — пробным вызовом J.jsx с props.__ghProbe = имя слоя: слой, который в цепочке, считает его и пропускает дальше.
function keepJsxLayer(name, handle) {
  const J = window.SP_JSX;
  if (!J) return () => {};
  const st = { seen: 0, active: true };
  const wrap = fn => function (type, props, key) {
    if (props && props.__ghProbe === name) { st.seen++; return fn.call(this, type, props, key); }
    if (st.active) {
      const r = handle.call(this, fn, type, props, key);
      if (r !== undefined) return r;
    }
    return fn.call(this, type, props, key);
  };
  const install = () => { const orig = { jsx: J.jsx, jsxs: J.jsxs }; J.jsx = wrap(orig.jsx); J.jsxs = wrap(orig.jsxs); };
  const works = () => {
    const before = st.seen;
    try { J.jsx(function GhProbe() { return null; }, { __ghProbe: name }); } catch (e) { return true; }
    return st.seen > before;
  };
  if (!works()) install();
  const timer = setInterval(() => { if (!works()) install(); }, 2000);
  // слой остаётся в цепочке (чужие слои выше него не режем), но выключается
  return () => { clearInterval(timer); st.active = false; };
}

function patchHome() {
  return keepJsxLayer("home", (fn, type, props, key) => {
    if (isHomeGamesProps(props)) {
      try { return fn.call(null, type, { ...props, games: installedFirst(props.games) }, key); } catch (e) {}
    } else if (props && Array.isArray(props.tabs) && props.tabs.some(t => t && t.id === "WhatsNew")) {
      return null;   // «Что нового / Друзья / Рекомендации»: тема прятала блок, а крестовина проваливалась в него
    }
  });
}



// ───────────── бесшовное продолжение видео и музыки между главной и страницей игры ─────────────
// Позиции пишутся каждые ~0,4 с; новый элемент с тем же файлом, если прошло меньше 8 с, стартует с того же места
// (с поправкой на прошедшее время и зацикливанием по длине).
// Приложения-«утилиты» в Steam (DSX — DualSense X, запущен вечно): их запуск НЕ значит «экран занят игрой»
const UTIL_APPS = new Set([1812620]);
function gameRunning() {
  const a = window.SteamUIStore?.MainRunningApp;
  return !!a && !UTIL_APPS.has(Number(a.appid));
}
const mediaPos = new Map();   // ключ (имя файла) -> {t, at}
window.__ghMediaPos = mediaPos;
const mediaKey = src => String(src || "").startsWith("music:") ? src : decodeURIComponent(String(src || "").split("?")[0].split("/").pop() || "");
function notePos(src, t) { const k = mediaKey(src); if (k && t > 0) mediaPos.set(k, { t, at: Date.now() }); }
function resumePos(src) {
  const p = mediaPos.get(mediaKey(src));
  return p && Date.now() - p.at < 8000 ? p.t + (Date.now() - p.at) / 1000 : null;
}
function seekResume(el, src) {   // выставить позицию, когда известна длительность
  const t = resumePos(src);
  if (t == null) return;
  const go = () => { try { const d = el.duration; el.currentTime = d && isFinite(d) ? t % d : t; } catch (e) {} };
  if (el.readyState >= 1) go(); else el.addEventListener("loadedmetadata", go, { once: true });
}
// Game Theme Music создаёт свой Audio в этом же контексте: перед play() подставляем позицию и пишем её, пока играет
function patchMediaResume() {
  const proto = window.HTMLMediaElement?.prototype;
  if (!proto || proto.__ghPlay) return () => {};
  const orig = proto.play;
  proto.__ghPlay = true;
  proto.play = function (...a) {
    try {
      const rawSrc = this.currentSrc || this.src || "";
      const page = window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance?.m_history?.location?.pathname || "";
      const am = /library\/app\/(\d+)/.exec(page);
      const src = /^data:audio\//.test(rawSrc) && am ? "music:" + am[1] : "";
      if (src && !this.__ghSampler) {
        seekResume(this, src);
        let idle = 0;
        this.__ghSampler = setInterval(() => {
          if (!this.paused) { idle = 0; notePos(src, this.currentTime); } else if (++idle > 50) { clearInterval(this.__ghSampler); this.__ghSampler = null; }
        }, 400);
      }
    } catch (e) {}
    return orig.apply(this, a);
  };
  return () => { proto.play = orig; delete proto.__ghPlay; };
}
let unpatchMediaResume = null;

// ───────────── главная: живой фон и описание выбранной игры (переключатель «Главная: живой фон игры») ─────────────
// Steam рисует на главной полноэкранную library_hero.jpg под каруселью. Ставим поверх неё (в тот же родитель, сразу после картинки)
// слой: видео-петля игры из хаба + логотип + короткое описание. Карусель остаётся выше. Видео подчиняется общему «Живому фону»
// (на зарядке/всегда/выкл) и выбору фона у игры; не крутится, пока запущена игра.
const homeLiveCache = new Map();   // appid -> {card, about, t}
async function homeLiveInfo(appid, name) {
  const c = homeLiveCache.get(appid);
  if (c && Date.now() - c.t < 120000) return c;
  let [card, about] = await Promise.all([localizedCall("get_card", Number(appid), name).catch(() => null), localizedCall("get_about", Number(appid)).catch(() => null)]);
  if (card?.standalone && !gameRunning()) {
    const made = await call("refresh_media", Number(appid), name, false, null, false).catch(() => null);
    if (made?.ok && !made.cached) card = await localizedCall("get_card", Number(appid), name).catch(() => card);
  }
  const v = { card, about, t: Date.now() };
  homeLiveCache.set(appid, v);
  return v;
}

function patchHomeLive() {
  let doc = null, alive = true, cur = null, vwrap = null, panel = null, settings = {}, power = { ac: false }, busyTick = 0;
  let audio = null, audioFor = null, musicTimer = null, musicFiles = null;
  const HERO = /(?:\/assets\/(\d+)\/library_hero|\/hero4k\/(\d+)\.)/;
  const heroId = im => { const m = HERO.exec(im.getAttribute("src") || ""); return m ? (m[1] || m[2]) : null; };
  const refreshCfg = async () => { try { settings = (await call("get_settings")) || {}; power = (await call("get_power")) || { ac: false }; if (settings.standalone) call("set_media_context", gameRunning()).catch(() => {}); } catch (e) {} };
  const remove = () => { for (const e of [vwrap, panel]) { try { e && e.remove(); } catch (x) {} } vwrap = null; panel = null; cur = null; };
  // активный фон главной: картинка library_hero с наибольшей прозрачностью (соседняя игра при перелистывании гаснет рядом)
  const findHero = () => {
    const vw = doc.documentElement.clientWidth;
    let best = null, bo = 0.5;
    for (const im of doc.querySelectorAll('img[src*="library_hero"], img[src*="/hero4k/"]')) {
      const r = im.getBoundingClientRect();
      if (r.width < vw * 0.85) continue;
      const o = parseFloat(doc.defaultView.getComputedStyle(im).opacity);
      if (o > bo) { best = im; bo = o; }
    }
    return best;
  };
  const build = (hero) => {
    // видео — рядом с картинкой в том же слое (повторяет её масштаб/параллакс Steam)
    const v = doc.createElement("div");
    v.id = "gh-homelive";
    v.style.cssText = "position:absolute;pointer-events:none;overflow:hidden;opacity:0;transition:opacity .5s";
    v.innerHTML = '<video muted loop playsinline style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;transition:opacity .6s"></video>';
    hero.after(v);
    // текст и затемнение — в слое выше без масштаба, чтобы не ехали вместе с параллаксом
    const host = hero.parentElement?.parentElement || hero.parentElement;
    const t = doc.createElement("div");
    t.id = "gh-homelive-text";
    t.style.cssText = "position:absolute;inset:0;pointer-events:none;opacity:0;transition:opacity .5s";
    t.innerHTML = '<div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.62) 0%,rgba(0,0,0,.18) 42%,rgba(0,0,0,0) 62%,rgba(0,0,0,.4) 100%),linear-gradient(90deg,rgba(0,0,0,.5) 0%,rgba(0,0,0,0) 62%)"></div>'
      + '<div style="position:absolute;left:36px;top:40px;width:560px;font-family:\'Noto Serif\',\'DejaVu Serif\',Georgia,serif;color:#e9eef3;text-shadow:0 1px 8px rgba(0,0,0,.85)">'
      + '<img class="gh-hl-logo" style="display:none;max-width:520px;max-height:150px;object-fit:contain;object-position:left center;margin-bottom:0;filter:drop-shadow(0 2px 8px rgba(0,0,0,.7))">'
      + '<div class="gh-hl-name" style="display:none;font-size:46px;font-weight:600;line-height:1.1"></div>'
      + '</div>';
    host.appendChild(t);
    vwrap = v; panel = t;
  };
  const place = (hero) => {
    vwrap.style.left = hero.offsetLeft + "px"; vwrap.style.top = hero.offsetTop + "px";
    vwrap.style.width = hero.offsetWidth + "px"; vwrap.style.height = hero.offsetHeight + "px";
    const k = Math.max(1, Math.min(2.2, doc.documentElement.clientWidth / 854));   // экран Деки = 854 px; на ПК (≈1348) крупнее
    if (panel && panel.children[1]) panel.children[1].style.zoom = String(k);
  };
  const hide = () => { if (vwrap) vwrap.style.opacity = "0"; if (panel) panel.style.opacity = "0"; };
  const apply = async (appid) => {
    const ov = window.appStore?.GetAppOverviewByAppID?.(Number(appid));
    const name = ov?.display_name || "";
    const info = await homeLiveInfo(appid, name);
    if (!alive || !vwrap || cur !== appid) return;
    const card = info.card;
    const v = vwrap.querySelector("video"), logo = panel.querySelector(".gh-hl-logo"), nm = panel.querySelector(".gh-hl-name");
    const rel = card ? pickVideo(card.media, card.bg_mode || "auto", livePolicy(settings, power, true), power.ac, !!card.standalone) : null;
    if (!card || !rel) { hide(); v.removeAttribute("src"); v.removeAttribute("data-src"); return; }   // нет видео — обычная картинка Steam
    const src = DATA + rel;
    v.ontimeupdate = () => limitVideoWindow(v, card.media, rel, !!card.standalone);
    v.onloadedmetadata = v.ontimeupdate;
    if (v.getAttribute("data-src") !== src) {
      v.style.opacity = "0"; v.setAttribute("data-src", src); v.src = src;
      v.onplaying = () => { v.style.opacity = "1"; };
      seekResume(v, src);
      v.play().catch(() => {});
    }
    const lg = card.media?.logo ? DATA + card.media.logo : null;
    if (lg) { logo.style.display = "block"; nm.style.display = "none"; if (logo.getAttribute("src") !== lg) logo.src = lg; logo.onerror = () => { logo.style.display = "none"; nm.style.display = "block"; nm.textContent = name; }; }
    else { logo.style.display = "none"; nm.style.display = "block"; nm.textContent = name; }
    vwrap.style.opacity = "1"; panel.style.opacity = "1";
  };
  // музыка игры на главной: файл темы из Game Theme Music (data/…/music), плавно входит/выходит, сама не мешает странице игры
  const MUSIC = "http://127.0.0.1:1337/plugins/Game%20Theme%20Music/data/music/";
  const fadeTo = (a, target, done) => {
    const step = (target - a.volume) / 10; let n = 0;
    const iv = setInterval(() => { a.volume = Math.min(1, Math.max(0, a.volume + step)); if (++n >= 10) { clearInterval(iv); a.volume = target; if (done) done(); } }, 50);
  };
  const stopMusic = () => {
    clearTimeout(musicTimer); musicTimer = null;
    const a = audio; audio = null; audioFor = null;
    if (a) fadeTo(a, 0, () => { try { a.pause(); a.remove(); } catch (e) {} });
  };
  const playMusic = (appid) => {
    if (audioFor === appid) return;
    stopMusic();
    audioFor = appid;
    musicTimer = setTimeout(async () => {   // при быстром листании не дёргаем музыку на каждой игре
      try {
        if (!alive || cur !== appid) return;
        let url = null;
        if (typeof pcBusy === "function") {   // ПК: тема из хаба — как на странице игры
          const rel = await call("get_theme", Number(appid), window.appStore?.GetAppOverviewByAppID?.(Number(appid))?.display_name || "");
          url = rel ? DATA + rel : null;
        } else {
          if (!musicFiles) musicFiles = (await call("get_music_files")) || {};
          url = musicFiles[appid] ? (String(musicFiles[appid]).includes("/") ? DATA + musicFiles[appid] : MUSIC + encodeURIComponent(musicFiles[appid])) : null;
        }
        if (!url || cur !== appid) return;
        const a = doc.createElement("audio");
        a.src = url; a.loop = true; a.volume = 0; a.preload = "auto";
        doc.body.appendChild(a);
        audio = a;
        seekResume(a, "music:" + appid);
        await a.play();
        fadeTo(a, 0.5);
      } catch (e) { log("homemusic", e); }
    }, 700);
  };
  const tick = () => {
    try {
      if (!alive) { remove(); stopMusic(); return; }
      // окно Big Picture Steam пересоздаёт (открыли/закрыли BP) — документ берём заново на каждом шаге
      const d2 = window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance?.BrowserWindow?.document;
      if (!d2?.body) { remove(); stopMusic(); return; }
      if (d2 !== doc) { remove(); audio = null; audioFor = null; clearTimeout(musicTimer); musicTimer = null; doc = d2; }
      const path = window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance?.m_history?.location?.pathname || "";
      const hero = /library\/home/.test(path) ? findHero() : null;
      const hid = hero ? heroId(hero) : null;
      if (!hid) { remove(); stopMusic(); return; }
      const busy = typeof pcBusy === "function" ? pcBusy(doc) : (gameRunning() || doc.visibilityState === "hidden");
      const live = settings.home_live !== false && livePolicy(settings, power, true) !== "off";
      if (!live) { if (vwrap) remove(); }
      else {
        if (vwrap && (!vwrap.isConnected || vwrap.parentElement !== hero.parentElement)) remove();
        if (!vwrap) build(hero);
        place(hero);
      }
      if (cur !== hid) { cur = hid; if (vwrap) { hide(); apply(hid); } }
      if (vwrap) {
        const v = vwrap.querySelector("video");
        if (v.getAttribute("src")) {
          if (busy && !v.paused) v.pause(); else if (!busy && v.paused) v.play().catch(() => {});
          if (!v.paused) notePos(v.getAttribute("src"), v.currentTime);
        }
      }
      if (settings.home_music !== false && !busy) playMusic(hid); else if (audio || musicTimer) stopMusic();
      if (audio && !audio.paused && audioFor) notePos("music:" + audioFor, audio.currentTime);
      if (++busyTick % 40 === 0) refreshCfg();
    } catch (e) { log("homelive", e); }
  };
  window.__ghHomeLive = () => ({ cur, audioFor, hasAudio: !!audio, timer: !!musicTimer, files: musicFiles && Object.keys(musicFiles).length, settings, alive });
  let iv = null;
  const start = () => {
    const w = window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance?.BrowserWindow;
    if (!w?.document?.body) return false;
    doc = w.document;
    refreshCfg().then(() => { if (alive) iv = setInterval(tick, 400); });
    return true;
  };
  const t = setInterval(() => { if (start()) clearInterval(t); }, 1000);
  return () => { alive = false; clearInterval(t); if (iv) clearInterval(iv); remove(); stopMusic(); };
}
let unpatchHomeLive = null;
function applyHomeLiveSetting(on) {
  if (on && !unpatchHomeLive) unpatchHomeLive = patchHomeLive();
  else if (!on && unpatchHomeLive) { unpatchHomeLive(); unpatchHomeLive = null; }
}
function homeLiveRefresh() { homeLiveCache.clear(); if (unpatchHomeLive) { unpatchHomeLive(); unpatchHomeLive = patchHomeLive(); } }   // новые настройки читаются сразу

// ───────────── темы хаба -> Game Theme Music ─────────────
// GTM хранит выбор трека в IndexedDB «game-theme-music-cache» (localforage, ключ = appid). Ставим трек хаба,
// если записи нет, если её ставили мы, или это автоподбор (audioUrl пустой) — ручной выбор не трогаем.

async function applyHubMusic() {
  try {
    const map = await call("get_music_map");
    const ids = Object.keys(map || {});
    if (!ids.length) return 0;
    const db = await new Promise((res, rej) => { const q = indexedDB.open("game-theme-music-cache"); q.onsuccess = () => res(q.result); q.onerror = rej; });
    if (!db.objectStoreNames.contains("keyvaluepairs")) { db.close(); return 0; }
    let n = 0;
    for (const appid of ids) {
      const cur = await new Promise(r => { const g = db.transaction("keyvaluepairs").objectStore("keyvaluepairs").get(appid); g.onsuccess = () => r(g.result); g.onerror = () => r(null); });
      if (cur && cur.by !== "gamehub" && cur.audioUrl) continue;  // выбрано вручную
      if (cur && cur.videoId === map[appid]) continue;
      await new Promise(r => { const tx = db.transaction("keyvaluepairs", "readwrite"); tx.objectStore("keyvaluepairs").put({ videoId: map[appid], audioUrl: "", by: "gamehub" }, appid); tx.oncomplete = r; tx.onerror = r; });
      n++;
    }
    db.close();
    return n;
  } catch (e) { log("music", e); return 0; }
}

// ───────────── меню «…» ─────────────

// Карточка текущей игры в меню «…»: посреди игры вспомнить, где остановился и что дальше,
// не выходя на страницу игры. Те же данные, что на странице (сейв на Деке / хаб).
function NowPlaying() {
  useLanguage();
  const [cur, setCur] = useState(null);
  useEffect(() => {
    const app = window.SteamUIStore?.MainRunningApp;
    if (!app?.appid) return;
    localizedCall("get_card", app.appid, app.display_name || "").then(c => setCur({ app, c })).catch(() => {});
  }, []);
  const b = cur?.c?.block;
  if (!b) return null;
  const facts = (cur.c.facts || []).slice(0, 3);
  return h(DFL.PanelSection, { title: t("now", cur.app.display_name || "") },
    h(DFL.PanelSectionRow, null, h("div", { style: { lineHeight: "1.35" } },
      b.kicker ? h("div", { style: { fontSize: "11px", letterSpacing: ".14em", textTransform: "uppercase", color: "#c8a96a", marginBottom: "4px" } }, b.kicker) : null,
      h("div", { style: { fontSize: "18px", color: "#fff", fontFamily: "Noto Serif, DejaVu Serif, serif" } }, b.title),
      b.sub ? h("div", { style: { fontSize: "15px", color: "#dfe5ec", fontStyle: "italic", fontFamily: "Noto Serif, DejaVu Serif, serif", marginTop: "2px" } }, b.sub) : null,
      b.detail ? h("div", { style: { fontSize: "13px", color: "#b8c2cc", fontStyle: "italic", marginTop: "6px" } }, b.detail) : null,
      facts.length ? h("div", { style: { fontSize: "13px", color: "#dfe5ec", marginTop: "8px" } },
        facts.map(f => `${f.label}: ${f.value}`).join(" · ")) : null)));
}

// Фон страницы открытой игры: авто / трейлер / мой геймплей / картинка. Выбор хранится для каждой игры отдельно.
function GameBgPicker() {
  useLanguage();
  const v = useViewing();
  if (!v) return null;
  const m = v.media || {};
  const opts = [{ data: "auto", label: BG_LABELS.auto.label }];
  if (m.trl) opts.push({ data: "trailer", label: BG_LABELS.trailer.label });
  if (m.rec) opts.push({ data: "gameplay", label: BG_LABELS.gameplay.label });
  if (m.wall) opts.push({ data: "image", label: BG_LABELS.image.label });
  opts.push({ data: "steam", label: BG_LABELS.steam.label });
  const pick = async o => {
    await call("set_game_bg", v.appid, o.data);
    setViewing({ ...v, mode: o.data });
    bgListeners.forEach(f => f(v.appid, o.data));
  };
  const sourceOpts = ["steam", "youtube", "recording"].map(key => ({ data: key, label: SOURCE_LABELS[key].label }));
  const pickSource = async o => {
    await call("set_game_source", v.appid, o.data);
    setViewing({ ...v, source: o.data });
    sourceListeners.forEach(f => f(v.appid, o.data));
    call("refresh_media", v.appid, v.name || "", gameRunning(), o.data, false).then(() => sourceListeners.forEach(f => f(v.appid, o.data))).catch(() => {});
  };
  return h(DFL.PanelSection, { title: t("background", v.name || "") },
    h(DFL.PanelSectionRow, null, h(DFL.DropdownItem, {
      label: t("game_live"),
      description: m.trl || m.rec ? undefined : t("no_video"),
      rgOptions: opts, selectedOption: opts.some(o => o.data === v.mode) ? v.mode : "auto", onChange: pick })),
    v.standalone ? h(DFL.PanelSectionRow, null, h(DFL.DropdownItem, {
      label: t("source_for_game"), rgOptions: sourceOpts, selectedOption: v.source || "steam", onChange: pickSource })) : null);
}

// Обновления (08.10): бэкенд раз в сутки смотрит GitHub Releases; ставит сам Decky — свой диалог и проверка sha256.
const firstLine = t => (String(t).split(String.fromCharCode(10)).find(x => x.trim()) || "").trim();
function UpdateRow() {
  useLanguage();
  const [u, setU] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { call("check_update", false).then(setU).catch(() => {}); }, []);
  if (!u || u.dev) return null;   // рабочая копия владельца: обновлений нет
  const install = async () => {
    setBusy(true);
    try { await window.DeckyBackend.call("utilities/install_plugin", u.url, manifest.name, u.latest, u.sha256, 2); }
    catch (e) { log("update", e); }
    setBusy(false);
  };
  const recheck = async () => { setBusy(true); try { setU(await call("check_update", true)); } catch {} setBusy(false); };
  return h(DFL.PanelSectionRow, null, u.available
    ? h(DFL.ButtonItem, { layout: "below", disabled: busy, onClick: install,
        description: t("version_now", u.current) + (u.notes ? " · " + firstLine(u.notes) : "") }, t("update_to", u.latest))
    : h(DFL.ButtonItem, { layout: "below", disabled: busy, onClick: recheck,
        description: u.latest ? t("version_latest", u.latest) : t("update_offline") }, t("version_check", u.current)));
}

// ───────────── полоса яркости (08.10, просьба друга): как громкость, но для яркости ─────────────
// Идея и разметка — по decky-brightness-bar (Raşit Ayaz, BSD-3-Clause; см. NOTICE). Свой код: без настроек цвета,
// включается в «…» плагина. Если стоит сам Brightness Bar — молчим, чтобы не было двух полос.
let brightBarOn = true;
let brightQuietUntil = 0;   // сон/пробуждение Steam меняет яркость сам — полоску в это время не показываем
function otherBrightnessBar() {
  try { return (window.DeckyPluginLoader?.plugins || []).some(p => p?.name === "Brightness Bar"); } catch { return false; }
}
let useComposition;
function compositionHook() {
  if (useComposition !== undefined) return useComposition;
  useComposition = null;
  try {
    const find = DFL.findModuleChild || DFL.findModuleExport;
    useComposition = find(m => {
      if (!m || typeof m !== "object") return undefined;
      for (const k in m) {
        let f; try { f = m[k]; } catch { continue; }
        if (typeof f !== "function") continue;
        let s; try { s = Function.prototype.toString.call(f); } catch { continue; }
        if (s.includes("AddMinimumCompositionStateRequest") && s.includes("ChangeMinimumCompositionStateRequest") &&
            s.includes("RemoveMinimumCompositionStateRequest") && !s.includes("m_mapCompositionStateRequests")) return f;
      }
      return undefined;
    }) || null;
  } catch (e) { log("brightness: composition", e); }
  return useComposition;
}
function CompositionRequest() { const f = compositionHook(); if (f) f(1); return null; }   // 1 = поверх игры, как уведомление
function SunIcon() {
  return h("svg", { viewBox: "0 0 24 24", width: 20, height: 20, fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" },
    h("circle", { cx: 12, cy: 12, r: 4.5 }),
    h("path", { d: "M12 1.5v2.5M12 20v2.5M1.5 12H4M20 12h2.5M4.6 4.6l1.8 1.8M17.6 17.6l1.8 1.8M4.6 19.4l1.8-1.8M17.6 6.4l1.8-1.8" }));
}
function BrightnessBar() {
  const [pct, setPct] = useState(0);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    let hideTimer = null;
    const t0 = Date.now();
    const reg = window.SteamClient?.System?.Display?.RegisterForBrightnessChanges?.(d => {
      setPct(Math.round((d?.flBrightness || 0) * 100));
      // 10.10: Steam вызывает колбэк сразу при подписке (через ~20 мс) с ТЕКУЩЕЙ яркостью — полоска «включалась сама»
      // при каждой перевыкатке плагина и пересборке окна
      if (!brightBarOn || Date.now() - t0 < 600 || Date.now() < brightQuietUntil) return;
      setVisible(true);
      clearTimeout(hideTimer);
      hideTimer = setTimeout(() => setVisible(false), 1000);
    });
    return () => { clearTimeout(hideTimer); try { reg?.unregister(); } catch {} };
  }, []);
  return h("div", { style: {
      position: "fixed", left: 8, top: 8, width: 236, zIndex: 7001,   // полоса громкости Steam — 7000
      display: "flex", alignItems: "center", gap: 12, padding: "7px 16px", borderRadius: 10,
      background: "#0e141b", color: "#dfe3e6", boxShadow: visible ? "0 0 10px rgb(0 0 0 / 50%)" : "none",
      transform: `translateY(${visible ? 0 : -150}%)`, transition: "transform .22s cubic-bezier(0,.73,.48,1)" } },
    visible ? h(CompositionRequest) : null,
    h(SunIcon),
    h("div", { style: { flexGrow: 1, height: 6, borderRadius: 3, background: "#3b4148" } },
      h("span", { style: { display: "block", height: "100%", width: `${pct}%`, borderRadius: 3, background: "#1a9fff" } })));
}
function installBrightnessBar(on) {
  brightBarOn = on !== false && !otherBrightnessBar();
  if (!IS_LINUX || !routerHook?.addGlobalComponent || !window.SteamClient?.System?.Display?.RegisterForBrightnessChanges) return () => {};
  routerHook.addGlobalComponent("ContinueBrightnessBar", BrightnessBar);
  const quiet = () => { brightQuietUntil = Date.now() + 6000; };
  const regs = [];
  try { regs.push(window.SteamClient?.User?.RegisterForPrepareForSystemSuspendProgress?.(quiet)); } catch {}
  try { regs.push(window.SteamClient?.User?.RegisterForResumeSuspendedGamesProgress?.(quiet)); } catch {}
  return () => {
    try { routerHook.removeGlobalComponent("ContinueBrightnessBar"); } catch {}
    for (const r of regs) { try { r?.unregister(); } catch {} }
  };
}

function ReviewDialog({ title, description, preview, accept, cancel, busy }) {
  return h(DFL.PanelSection, null,
    h("div", { role: "dialog", "aria-modal": true, "aria-label": title,
      style: { maxWidth: "100%", minWidth: 0, overflowWrap: "anywhere" } },
      h("h2", { style: { fontSize: 18, lineHeight: 1.3, margin: "8px 0" } }, title),
      h("p", { style: { fontSize: 13, lineHeight: 1.5, margin: "4px 0 8px" } }, description),
      preview ? h(DFL.Focusable, { style: { display: "block", width: "100%", maxHeight: "34vh", overflowY: "auto", overflowX: "hidden", marginBottom: 12 },
        onCancelButton: cancel, onKeyDown: e => { if (["ArrowDown", "ArrowUp"].includes(e.key)) { e.currentTarget.scrollTop += e.key === "ArrowDown" ? 80 : -80; e.preventDefault(); } } },
        h("pre", { style: { margin: 0, fontSize: 11, lineHeight: 1.4, textAlign: "left", whiteSpace: "pre-wrap", overflowWrap: "anywhere" } }, preview)) : null,
      h(DFL.PanelSectionRow, null, h("div", { style: { display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)", gap: 8 } },
        h(DFL.ButtonItem, { onClick: cancel, disabled: busy }, t("dialog_cancel")),
        h(DFL.ButtonItem, { onClick: accept, disabled: busy }, t(preview ? "report_save" : "dialog_accept"))))));
}

function QamContent() {
  useLanguage();
  const [st, setSt] = useState(null);
  const [s, setS] = useState(null);
  const [notice, setNotice] = useState("");
  const [dialog, setDialog] = useState(null);
  const [reportBusy, setReportBusy] = useState(false);
  useEffect(() => { call("get_status").then(setSt).catch(() => {}); call("get_settings").then(setS).catch(() => {}); }, []);
  const upd = async (k, v) => { const ns = await call("set_setting", k, v); setS(ns); if (ns.standalone) { settingsListeners.forEach(f => f(ns)); if (k === "bg_source" && viewing) call("refresh_media", viewing.appid, viewing.name || "", gameRunning(), null, false).then(() => sourceListeners.forEach(f => f(viewing?.appid))).catch(() => {}); } if (k === "home_installed_first") applyHomeSetting(v); if (["home_live", "home_music", "preset", "bg_source"].includes(k)) { applyHomeLiveSetting(true); homeLiveRefresh(); } };
  const opts = [{ data: "ac", label: t("charging") }, { data: "always", label: t("always") }, { data: "off", label: t("off") }];
  const presets = ["light", "balanced", "maximum"].map(x => ({ data: x, label: t(`preset_${x}`) }));
  const sources = ["steam", "youtube", "recording"].map(x => ({ data: x, label: t(`source_${x}`) }));
  const limits = [1, 2, 4, 8].map(x => ({ data: x, label: `${x} GB` }));
  const youtubeConsent = async v => {
    if (v) { const r = await call("install_ytdlp", true, false).catch(() => null); setNotice(r?.ok ? "" : t(r?.deferred ? "media_deferred" : "media_setup_failed"));
      const ns = await call("get_settings"); setS(ns); settingsListeners.forEach(f => f(ns)); }
    else await upd("youtube_consent", false);
  };
  const themeConsent = async v => {
    if (v) { const r = await call("install_ytdlp", true, false, "theme").catch(() => null); setNotice(r?.ok ? "" : t(r?.deferred ? "media_deferred" : "media_setup_failed"));
      const ns = await call("get_settings"); setS(ns); settingsListeners.forEach(f => f(ns)); await upd("home_music", !!ns.theme_music_consent); }
    else { await upd("theme_music_consent", false); await upd("home_music", false); }
    if (v && viewing) call("refresh_media", viewing.appid, viewing.name || "", gameRunning(), null, false).then(() => sourceListeners.forEach(f => viewing && f(viewing.appid))).catch(() => {});
    homeLiveRefresh();
  };
  const clearCache = async () => { await call("clear_media_cache"); setSt(await call("get_status")); homeLiveRefresh(); sourceListeners.forEach(f => viewing && f(viewing.appid)); };
  const collectReport = async () => {
    setReportBusy(true);
    try {
      const result = await call("preview_tester_report");
      if (!result?.ok) throw Error(result?.error || "unavailable");
      setDialog({ title: t("report_title"), description: t("report_privacy"), preview: result.preview,
        accept: async () => { setReportBusy(true); try {
          const saved = await call("save_tester_report", result.token);
          setNotice(saved?.ok ? t("report_saved", saved.folder, saved.filename) : t("report_failed", saved?.error || "unavailable"));
        } catch (e) { setNotice(t("report_failed", String(e))); } finally { setReportBusy(false); setDialog(null); } } });
    } catch (e) { setNotice(t("report_failed", String(e))); } finally { setReportBusy(false); }
  };
  const requestConsent = (kind, value) => {
    const change = kind === "youtube" ? youtubeConsent : themeConsent;
    if (!value) return change(false);
    setDialog({ title: t("consent_title"), description: t(kind === "youtube" ? "consent_youtube" : "consent_theme"),
      accept: async () => { setDialog(null); await change(true); } });
  };
  if (s?.standalone && dialog) return h(ReviewDialog, { ...dialog, busy: reportBusy, cancel: () => setDialog(null) });
  return h(React.Fragment, null, h(NowPlaying), h(GameBgPicker), h(DFL.PanelSection, null,
    h(UpdateRow),
    notice ? h(DFL.PanelSectionRow, null, h("div", { role: "status", style: { fontSize: "12px", lineHeight: "1.4" } }, notice)) : null,
    h(DFL.PanelSectionRow, null, h("div", { style: { fontSize: "13px", lineHeight: "1.5", color: "#b8c2cc", whiteSpace: "pre-line" } },
      st ? (st.standalone ? t("standalone_status", st.save_games || 0, st.cached_backgrounds || 0)
        : t("hub_status", st.hub_cards) + (st.synced_at ? t("synced", dateRu(st.synced_at), ago(st.synced_at)) : t("not_synced")) +
          t("reader_status", st.deck_readers.length, st.hltb_cached)) : "…")),
    h(DFL.PanelSectionRow, null, h(StartupMovieToggle)),
    s && IS_LINUX ? h(DFL.PanelSectionRow, null, h(DFL.ToggleField, { label: t("brightness"), description: otherBrightnessBar()
      ? t("brightness_other") : t("brightness_desc"),
      checked: s.brightness_bar !== false, disabled: otherBrightnessBar(), onChange: v => { brightBarOn = v; upd("brightness_bar", v); } })) : null,
    s && !s.standalone ? h(DFL.PanelSectionRow, null, h(DFL.ToggleField, { label: t("home_live"), description: t("home_live_desc"), checked: s.home_live !== false, onChange: v => upd("home_live", v) })) : null,
    s && !s.standalone ? h(DFL.PanelSectionRow, null, h(DFL.ToggleField, { label: t("home_music"), description: t("home_music_desc"), checked: s.home_music !== false, onChange: v => upd("home_music", v) })) : null,
    s ? h(DFL.PanelSectionRow, null, h(DFL.ToggleField, { label: t("installed_first"), checked: !!s.home_installed_first, onChange: v => upd("home_installed_first", v) })) : null,
    s && !s.standalone ? h(DFL.PanelSectionRow, null, h(DFL.DropdownItem, { label: t("live_policy"), description: t("live_policy_desc"), rgOptions: opts, selectedOption: s.live_bg, onChange: o => upd("live_bg", o.data) })) : null,
    s?.standalone ? h(DFL.PanelSectionRow, null, h(DFL.DropdownItem, { label: t("preset"), description: t("preset_desc"), rgOptions: presets, selectedOption: s.preset || "light", onChange: o => upd("preset", o.data) })) : null,
    s?.standalone ? h(DFL.PanelSectionRow, null, h(DFL.DropdownItem, { label: t("bg_source"), rgOptions: sources, selectedOption: s.bg_source || "steam", onChange: o => upd("bg_source", o.data) })) : null,
    s?.standalone ? h(DFL.PanelSectionRow, null, h(DFL.DropdownItem, { label: t("disk_limit"), rgOptions: limits, selectedOption: Number(s.disk_limit_gb || 2), onChange: o => upd("disk_limit_gb", Number(o.data)) })) : null,
    s?.standalone ? h(DFL.PanelSectionRow, null, h(DFL.ToggleField, { label: t("youtube_optin"), description: t("youtube_desc"), checked: !!s.youtube_consent, onChange: v => requestConsent("youtube", v) })) : null,
    s?.standalone ? h(DFL.PanelSectionRow, null, h(DFL.ToggleField, { label: t("recording_optin"), description: t("recording_desc"), checked: !!s.recording_enabled, onChange: v => upd("recording_enabled", v) })) : null,
    s?.standalone ? h(DFL.PanelSectionRow, null, h(DFL.ToggleField, { label: t("theme_optin"), description: t("theme_desc"), checked: !!s.theme_music_consent, onChange: v => requestConsent("theme", v) })) : null,
    s?.standalone ? h(DFL.PanelSectionRow, null, h(DFL.ButtonItem, { layout: "below", onClick: clearCache }, t("clear_cache"))) : null,
    s?.standalone ? h(DFL.PanelSectionRow, null, h(DFL.ButtonItem, { layout: "below", onClick: collectReport, disabled: reportBusy,
      description: t("report_description") }, t(reportBusy ? "report_busy" : "report_collect"))) : null,
    s && IS_LINUX ? h(DFL.PanelSectionRow, null, h(DFL.ToggleField, { label: t("pdb_page"), description: t("pdb_page_desc"),
      checked: s.pdb_button !== false, onChange: v => { pdbPrefs.pdb_button = v; upd("pdb_button", v); } })) : null,
    s && IS_LINUX ? h(DFL.PanelSectionRow, null, h(DFL.ToggleField, { label: t("pdb_tiles"), description: t("pdb_tiles_desc"),
      checked: s.pdb_tiles !== false, onChange: v => { pdbPrefs.pdb_tiles = v; upd("pdb_tiles", v); } })) : null,
    s && !s.standalone ? h(DFL.PanelSectionRow, null, h(DFL.ToggleField, { label: t("hub_music"), description: t("hub_music_desc"), checked: !!s.hub_music, onChange: v => { upd("hub_music", v); if (v) applyHubMusic(); } })) : null));
}

function HubIcon() {
  return h("svg", { viewBox: "0 0 24 24", width: "1em", height: "1em", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" },
    h("path", { d: "M3 7l9-4 9 4-9 4-9-4z" }), h("path", { d: "M3 12l9 4 9-4" }), h("path", { d: "M3 17l9 4 9-4" }));
}

let unpatchHome = null;
function applyHomeSetting(on) {
  if (on && !unpatchHome) {
    unpatchHome = patchHome();
  } else if (!on && unpatchHome) { unpatchHome(); unpatchHome = null; }
}

// ───────────── заряд геймпада числом в шапке Steam (просьба владельца 02.10; Дека и ПК) ─────────────
// Steam рисует у значка контроллера только полоску (компонент с batteryLevel 0..1). Рядом — проценты.
// Значок системной батареи Деки тот же компонент — его не трогаем: у значка контроллера Steam явно задаёт
// batteryCriticalThreshold 0.1, и в ControllerStore есть беспроводной геймпад с тем же уровнем заряда.
function padBatteryInfo(level) {
  const pads = (window.ControllerStore?.m_controllerList || []).filter(c => c && c.eControllerType !== 4 && (c.bBluetooth || c.bWireless));
  const pct = Math.round(level * 100);
  return pads.find(c => Math.abs((c.ucBatteryLevel ?? -100) - pct) <= 1) || null;
}
function patchPadBattery() {
  return keepJsxLayer("padbat", function (fn, type, props, key) {
    if (typeof type === "function" && props && typeof props.batteryLevel === "number" && "acState" in props
        && props.batteryCriticalThreshold === 0.1) {
      try {
        const pad = padBatteryInfo(props.batteryLevel);
        if (pad) {
          const pct = Math.round(props.batteryLevel * 100);
          // блок значка узкий и фиксированный (батарейка лежит в нём абсолютно) — число справа от него, а сам блок
          // раздвигаем на ширину числа, чтобы не наехать на соседние значки шапки
          return h(React.Fragment, { key }, fn.call(null, type, props),
            h("span", { className: "gh-padpct", style: { position: "absolute", left: "100%", top: "50%", transform: "translateY(-50%)",
              marginLeft: "4px", font: "600 14px/1 \"Motiva Sans\",Arial,sans-serif", whiteSpace: "nowrap",
              color: props.batteryLevel <= 0.1 ? "#E01D79" : "inherit" } }, pct + "%"),
            h("style", null, "div:has(> .gh-padpct){margin-right:38px}"));
        }
      } catch (e) {}
    }
  });
}

// ───────────── видеозаставка Steam вкл/выкл (просьба владельца 03.10; Дека и ПК) ─────────────
// Своего выключателя у Steam нет (только выбор ролика / «перемешать» / «при выходе из сна»). «Выкл» = локальная заставка
// из 0,2 с чёрного (assets/gh_no_startup.webm кладёт бэкенд в config/uioverrides/movies), прежний выбор запоминаем
// в настройках плагина и возвращаем при «Вкл». Настройка — самого Steam, поэтому действует и при включении Деки.
const NO_MOVIE = "/uioverrides/movies/gh_no_startup.webm";
let __ghSettingsApi = null;
function steamSettingsApi() {
  if (__ghSettingsApi) return __ghSettingsApi;
  let req;
  window.webpackChunksteamui.push([[Symbol("gh-settings")], {}, r => { req = r; }]);
  let set = null, store = null;
  for (const id of Object.keys(req.m)) {
    let m; try { m = req(id); } catch (e) { continue; }
    if (!m || typeof m !== "object") continue;
    for (const k of Object.keys(m)) {
      let v; try { v = m[k]; } catch (e) { continue; }
      if (!set && typeof v === "function" && v.length === 2) {
        const src = Function.prototype.toString.call(v);
        if (src.includes("SteamClient.Settings.SetSetting(") && src.includes("serializeBinaryToWriter")) set = v;
      }
      if (!store && v && typeof v === "object" && typeof v.GetClientSetting === "function" && "m_ClientSettings" in v) store = v;
    }
    if (set && store) break;
  }
  if (set && store) __ghSettingsApi = { set, store };
  return __ghSettingsApi;
}
function startupMovieOn() {
  const api = steamSettingsApi();
  return !api || api.store.m_ClientSettings?.startup_movie_local_path !== NO_MOVIE;
}
async function setStartupMovie(on) {
  const api = steamSettingsApi();
  if (!api) throw new Error("Steam settings API was not found");
  const cs = api.store.m_ClientSettings || {};
  if (!on) {
    if (cs.startup_movie_local_path !== NO_MOVIE)
      await call("set_setting", "startup_movie_prev", { id: String(cs.startup_movie_id ?? "0"), path: cs.startup_movie_local_path || "",
        shuffle: !!cs.startup_movie_shuffle });
    await call("ensure_blank_movie");
    await api.set("startup_movie_shuffle", false);
    await api.set("startup_movie_id", "0");
    await api.set("startup_movie_local_path", NO_MOVIE);
  } else {
    const prev = (await call("get_settings"))?.startup_movie_prev || {};
    await api.set("startup_movie_id", prev.id || "0");
    await api.set("startup_movie_local_path", prev.path || "");
    await api.set("startup_movie_shuffle", !!prev.shuffle);
  }
  return startupMovieOn();
}
function StartupMovieToggle() {
  useLanguage();
  const [on, setOn] = useState(startupMovieOn());
  return h(DFL.ToggleField, { label: t("startup_movie"), description: t("startup_movie_desc"),
    checked: on, onChange: v => setStartupMovie(v).then(setOn).catch(e => log("startup movie", e)) });
}

// ───────────── заставка запуска игры без раскладки и разрешения (просьба владельца 03.10; Дека и ПК) ─────────────
// При запуске Steam показывает поверх страницы анимацию контроллера + «В этой игре будет использоваться … раскладка» и
// «Максимальное разрешение игры» — налезает на нашу панель. Скрываем только эти два блока; логотип, статус запуска и
// кнопка «пропустить обработку шейдеров» (Дека) остаются. Классы — из модуля стилей заставки (у ПК и Деки сборки разные).
function launchNoticeCss() {
  try {
    let req;
    window.webpackChunksteamui.push([[Symbol("gh-launch")], {}, r => { req = r; }]);
    for (const id of Object.keys(req.m)) {
      let m; try { m = req(id); } catch (e) { continue; }
      const c = m?.default && typeof m.default === "object" ? m.default : m;
      if (c && typeof c.ControlOverviewContainer === "string" && typeof c.GameResolution === "string" && c.ControllerInterstitialAnimationContainer)
        return `.${c.ControlOverviewContainer},.${c.GameResolution}{display:none!important}`;
    }
  } catch (e) { log("launch notice", e); }
  return "";
}
function ensureLaunchNoticeHidden() {
  const css = launchNoticeCss();
  if (!css) return () => {};
  const put = () => {
    try {
      const d = window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance?.BrowserWindow?.document;
      if (!d?.head || d.getElementById("gh-launch-notice")) return;
      const st = d.createElement("style"); st.id = "gh-launch-notice"; st.textContent = css; d.head.appendChild(st);
    } catch (e) {}
  };
  put();
  const t = setInterval(put, 3000);   // окно Big Picture пересоздаётся — ставим заново
  return () => {
    clearInterval(t);
    try { window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance?.BrowserWindow?.document?.getElementById("gh-launch-notice")?.remove(); } catch (e) {}
  };
}

var index = DFL.definePlugin(() => {
  const unLaunchNotice = ensureLaunchNoticeHidden();
  const appPatch = patchAppPage();
  const unpatchPadBat = patchPadBattery();
  const unpatchButtons = patchAppButtons();
  const unpatchLibTab = patchLibraryDefaultTab();
  const unpatchPdb = patchLibraryPdb();
  let unBright = () => {};
  call("get_aliases").then(m => { aliasMap = m || {}; }).catch(() => {});
  // язык названий из игр = язык Steam (ddsaves: нет строки на нём — английский, потом русский)
  languageReady.catch(e => log("language", e));
  call("get_settings").then(s => {
    pdbPrefs = { pdb_button: s?.pdb_button !== false, pdb_tiles: s?.pdb_tiles !== false };
    unBright = installBrightnessBar(s?.brightness_bar);
    applyHomeSetting(s?.home_installed_first !== false);
    applyHomeLiveSetting(true);
    if (!unpatchMediaResume) unpatchMediaResume = patchMediaResume();
    if (s?.hub_music !== false) applyHubMusic().then(n => n && log(`hub themes enabled: ${n}`));
  }).catch(e => log("settings", e));
  return {
    title: h("div", { className: DFL.staticClasses.Title }, "Continue?"),
    content: h(QamContent),
    icon: h(HubIcon),
    onDismount() {
      routerHook.removePatch("/library/app/:appid", appPatch);
      unpatchLibTab();
      unpatchPdb();
      unBright();
      unpatchButtons();
      unpatchPadBat();
      unLaunchNotice();
      if (unpatchHome) { unpatchHome(); unpatchHome = null; }
      if (unpatchHomeLive) { unpatchHomeLive(); unpatchHomeLive = null; }
      if (unpatchMediaResume) { unpatchMediaResume(); unpatchMediaResume = null; }
    },
  };
});

export { index as default };
