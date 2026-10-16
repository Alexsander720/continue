// One native Steam entry for Continue?; global defaults and explicit game overrides.
const PC_SETTINGS_TEXT = {
  en: {
    intro:'Your library, ready to continue.', intro_detail:'Progress comes from supported local saves. Backgrounds prepare when you open a game. Accounts are optional.',
    start:'Start here', library:'Library', card:'Game card', backgrounds:'Backgrounds', music:'Music', appearance:'Appearance', connections:'Connections',
    settings:'Settings', defaults:'All games', this_game:'This game', inherit:'Use global settings', reset:'Reset this section', back:'Close',
    card_detail:'Choose what appears on the card. Changes here never alter your saves.', game_detail:'Only this game changes. Everything else inherits your global settings.',
    story:'Where I stopped', description:'Game description', facts:'Save details', characters:'Characters and survival', achievements:'Achievement count', latest_achievement:'Latest achievement', playtime:'Playtime and completion estimates',
    individual:'Details in this save', no_facts:'No supported save details are available for this game yet.', no_game:'Open a game page to configure individual details.',
    live:'Live backgrounds', live_detail:'Muted video behind the game card. A still image stays visible while a video prepares or when no suitable video is available.',
    quality:'Video quality limit', quality_detail:'A maximum, not a promise: Steam often supplies up to 1080p. 4K needs a 4K source and a compatible downloader; Continue? does not upscale video.',
    cache:'Media storage limit', cache_detail:'Shared by downloaded backgrounds and music. Older unused files are removed when space is needed. Games and saves are untouched.',
    fallback:'Find missing backgrounds on YouTube', fallback_detail:'Optional. Searches and downloads only for games you open, after you allow it. Steam trailers remain the first source.',
    allow_fallback:'Allow YouTube backgrounds', consent_video:'Allow Continue? to search YouTube and download background videos for games I open. This uses the internet and the media cache.',
    consent_music:'Allow Continue? to search YouTube and download theme music for games I open. This uses the internet and the media cache. No YouTube account is needed.',
    enable_music:'Enable automatic music', music_detail:'One setup for the library. A theme is selected when you open a game; use the music button only to change a particular track.',
    music_card:'On game pages', music_home:'On Home', volume:'Volume', choose_track:'Choose a track for this game', music_off:'Automatic music is off', music_ready:'Automatic music is enabled',
    music_preparing:'Preparing music…', music_missing:'No suitable track is available yet', refresh:'Try again', consent_title:'Optional download', allow:'Allow and enable', cancel:'Cancel', preparing:'Preparing…',
    ready:'Ready', waiting:'Waiting for download', unavailable:'No suitable video found', disabled:'Disabled in settings', paused:'Downloads pause while a game runs or on battery', error:'Could not finish. Try again.',
    clear:'Clear downloaded media', clear_detail:'Removes cached backgrounds and music. They can be downloaded again as you open games.',
    mode:'Background for this game', automatic:'Automatic', still:'Still image', native:'Steam artwork',
    tabs:'Continue? library tabs', tabs_detail:'Adds native tabs for installed games and supported progress. Leave off if another tab plugin manages your library.',
    installed:'Show installed games first on Home', rounded:'Rounded Steam controls', glyphs:'Controller symbols', custom:'Continue? style', steam:'Steam default', pads:'Controller support icons',
    advanced:'More appearance options', advanced_detail:'Optional CSS Loader themes and detailed visual tweaks.', movie:'Steam startup video',
    artwork:'Custom covers and logos', artwork_detail:'Optional SteamGridDB connection. Create an account, open its API page, generate your personal key, then paste it in the artwork picker. The key stays on this PC.',
    api_page:'Open SteamGridDB API page', art_picker:'Set up artwork', key_ready:'Your SteamGridDB key is saved', key_missing:'No SteamGridDB key is set',
    translation:'Description language', translation_detail:'Continue? uses the Steam description in your Steam language. If Steam has no translation, the original is marked. No Google account is required.',
    gemini_detail:'The owner’s Continue? used a private Gemini/Vertex connection. Google sign-in and AI translation are not included in this public build.',
    core_ready:'Game cards work without an account', setup_optional:'Optional: enable music', art_optional:'Optional: change artwork', version:'Check for updates',
    info:'Settings apply immediately. B / Esc closes this window.', on:'On', off:'Off', inherited:'Inherited', home_video:'Live background on Home', home_video_detail:'Uses the prepared background of the selected game.',
    storage:'Downloaded', request:'Prepare this game now', no_manual:'Automatic selection is enough; individual search is optional.'
  },
  ru: {
    intro:'Твоя библиотека. Можно продолжать.', intro_detail:'Прогресс берём из поддерживаемых локальных сейвов. Фон готовится при открытии игры. Аккаунты — по желанию.',
    start:'Начало', library:'Библиотека', card:'Карточка игры', backgrounds:'Фоны', music:'Музыка', appearance:'Оформление', connections:'Подключения',
    settings:'Настройки', defaults:'Все игры', this_game:'Эта игра', inherit:'Как в общих настройках', reset:'Сбросить этот раздел', back:'Закрыть',
    card_detail:'Выбери, что показывать на карточке. Сохранения игры от этого не меняются.', game_detail:'Меняется только эта игра. Остальное берётся из общих настроек.',
    story:'Где остановился', description:'Описание игры', facts:'Данные сохранения', characters:'Персонажи и кто жив', achievements:'Количество достижений', latest_achievement:'Последнее достижение', playtime:'Наиграно и время прохождения',
    individual:'Детали этого сохранения', no_facts:'В этой игре пока нет доступных данных поддерживаемого сейва.', no_game:'Открой страницу игры, чтобы настроить её отдельные детали.',
    live:'Живые фоны', live_detail:'Видео без звука за карточкой игры. Пока оно готовится или подходящего ролика нет, остаётся обычная картинка.',
    quality:'Максимальное качество видео', quality_detail:'Это верхняя граница: Steam часто отдаёт ролики до 1080p. Для 4K нужны исходник в 4K и подходящий загрузчик. Видео не растягиваем до «4K».',
    cache:'Место для фонов и музыки', cache_detail:'Общий предел загрузок. При нехватке места удаляем старые неиспользуемые файлы. Игры и сейвы не затрагиваем.',
    fallback:'Искать недостающие фоны на YouTube', fallback_detail:'По желанию. Только для открываемых игр и после разрешения. Сначала ищем официальный ролик Steam.',
    allow_fallback:'Разрешить фоны с YouTube', consent_video:'Разрешаю Continue? искать на YouTube и скачивать фоновые видео для открываемых игр. Нужен интернет, файлы займут место в кэше.',
    consent_music:'Разрешаю Continue? искать на YouTube и скачивать музыку для открываемых игр. Нужен интернет, файлы займут место в кэше. Аккаунт YouTube не нужен.',
    enable_music:'Включить автоматическую музыку', music_detail:'Настраивается один раз для всей библиотеки. Тема подбирается при открытии игры. Кнопка музыки нужна, только если захочешь другой трек.',
    music_card:'На страницах игр', music_home:'На главной', volume:'Громкость', choose_track:'Выбрать трек для этой игры', music_off:'Автоматическая музыка выключена', music_ready:'Автоматическая музыка включена',
    music_preparing:'Готовим музыку…', music_missing:'Подходящий трек пока не найден', refresh:'Попробовать ещё раз', consent_title:'Загрузка по желанию', allow:'Разрешить и включить', cancel:'Отмена', preparing:'Готовим…',
    ready:'Готово', waiting:'Ожидает загрузки', unavailable:'Подходящее видео не найдено', disabled:'Выключено в настройках', paused:'Загрузки на паузе во время игры или при работе от батареи', error:'Не получилось завершить. Попробуй ещё раз.',
    clear:'Очистить загруженные фоны и музыку', clear_detail:'Удаляет только кэш. Файлы можно загрузить заново при открытии игр.',
    mode:'Фон для этой игры', automatic:'Автоматически', still:'Обычная картинка', native:'Обложка Steam',
    tabs:'Вкладки Continue? в библиотеке', tabs_detail:'Добавляет вкладки установленных игр и поддерживаемого прогресса. Оставь выключенным, если вкладками управляет другой плагин.',
    installed:'Установленные игры первыми на главной', rounded:'Скруглённые элементы Steam', glyphs:'Символы контроллера', custom:'Стиль Continue?', steam:'Стандарт Steam', pads:'Значки поддержки контроллера',
    advanced:'Больше настроек оформления', advanced_detail:'Дополнительные темы CSS Loader и подробные визуальные настройки.', movie:'Видеозаставка Steam',
    artwork:'Свои обложки и логотипы', artwork_detail:'Необязательное подключение SteamGridDB. Создай аккаунт, открой страницу API, сгенерируй личный ключ и вставь его в окне картинок. Ключ хранится на этом ПК.',
    api_page:'Открыть страницу API SteamGridDB', art_picker:'Настроить картинки', key_ready:'Твой ключ SteamGridDB сохранён', key_missing:'Ключ SteamGridDB ещё не задан',
    translation:'Язык описания', translation_detail:'Берём описание Steam на языке твоего Steam. Если перевода нет, помечаем оригинал. Google-аккаунт для этого не нужен.',
    gemini_detail:'В личном Continue? владельца было приватное подключение Gemini/Vertex. В этой публичной сборке вход через Google и AI-перевод пока не подключены.',
    core_ready:'Карточки работают без аккаунта', setup_optional:'По желанию: включи музыку', art_optional:'По желанию: замени картинки', version:'Проверить обновления',
    info:'Изменения применяются сразу. B / Esc закрывает окно.', on:'Вкл', off:'Выкл', inherited:'Из общих настроек', home_video:'Живой фон на главной', home_video_detail:'Использует готовый фон выбранной игры.',
    storage:'Загружено', request:'Подготовить эту игру сейчас', no_manual:'Автоматического подбора достаточно; искать трек вручную необязательно.'
  },
  uk: {
    intro:'Твоя бібліотека. Можна продовжувати.', intro_detail:'Прогрес беремо з підтримуваних локальних збережень. Тло готується під час відкриття гри. Облікові записи — за бажанням.',
    start:'Початок', library:'Бібліотека', card:'Картка гри', backgrounds:'Тло', music:'Музика', appearance:'Оформлення', connections:'Підключення',
    settings:'Налаштування', defaults:'Усі ігри', this_game:'Ця гра', inherit:'Як у загальних налаштуваннях', reset:'Скинути цей розділ', back:'Закрити',
    card_detail:'Обери, що показувати на картці. Збереження гри від цього не змінюються.', game_detail:'Змінюється лише ця гра. Решта успадковує загальні налаштування.',
    story:'Де зупинився', description:'Опис гри', facts:'Дані збереження', characters:'Персонажі та хто живий', achievements:'Кількість досягнень', latest_achievement:'Останнє досягнення', playtime:'Зіграно та час проходження',
    individual:'Деталі цього збереження', no_facts:'У цій грі поки немає доступних даних підтримуваного збереження.', no_game:'Відкрий сторінку гри, щоб налаштувати її окремі деталі.',
    live:'Живе тло', live_detail:'Відео без звуку за карткою гри. Поки воно готується або відповідного ролика немає, залишається звичайне зображення.',
    quality:'Максимальна якість відео', quality_detail:'Це верхня межа: Steam часто надає ролики до 1080p. Для 4K потрібні джерело в 4K та відповідний завантажувач. Відео не розтягуємо до «4K».',
    cache:'Місце для тла та музики', cache_detail:'Спільний ліміт завантажень. За браком місця видаляємо старі невикористовувані файли. Ігри та збереження не змінюємо.',
    fallback:'Шукати відсутнє тло на YouTube', fallback_detail:'За бажанням. Лише для відкритих ігор та після дозволу. Спочатку шукаємо офіційний ролик Steam.',
    allow_fallback:'Дозволити тло з YouTube', consent_video:'Дозволяю Continue? шукати на YouTube та завантажувати фонові відео для відкритих ігор. Потрібен інтернет, файли займатимуть місце в кеші.',
    consent_music:'Дозволяю Continue? шукати на YouTube та завантажувати музику для відкритих ігор. Потрібен інтернет, файли займатимуть місце в кеші. Обліковий запис YouTube не потрібен.',
    enable_music:'Увімкнути автоматичну музику', music_detail:'Одне налаштування для всієї бібліотеки. Тему підбираємо під час відкриття гри. Кнопка музики потрібна лише для вибору іншого треку.',
    music_card:'На сторінках ігор', music_home:'На головній', volume:'Гучність', choose_track:'Обрати трек для цієї гри', music_off:'Автоматична музика вимкнена', music_ready:'Автоматична музика ввімкнена',
    music_preparing:'Готуємо музику…', music_missing:'Відповідний трек поки не знайдено', refresh:'Спробувати знову', consent_title:'Завантаження за бажанням', allow:'Дозволити й увімкнути', cancel:'Скасувати', preparing:'Готуємо…',
    ready:'Готово', waiting:'Очікує завантаження', unavailable:'Відповідне відео не знайдено', disabled:'Вимкнено в налаштуваннях', paused:'Завантаження призупинено під час гри або роботи від батареї', error:'Не вдалося завершити. Спробуй знову.',
    clear:'Очистити завантажене тло та музику', clear_detail:'Видаляє лише кеш. Файли можна завантажити знову під час відкриття ігор.',
    mode:'Тло цієї гри', automatic:'Автоматично', still:'Звичайне зображення', native:'Обкладинка Steam',
    tabs:'Вкладки Continue? у бібліотеці', tabs_detail:'Додає вкладки встановлених ігор та підтримуваного прогресу. Залиш вимкненим, якщо вкладками керує інший плагін.',
    installed:'Встановлені ігри першими на головній', rounded:'Заокруглені елементи Steam', glyphs:'Символи контролера', custom:'Стиль Continue?', steam:'Стандарт Steam', pads:'Значки підтримки контролера',
    advanced:'Більше налаштувань оформлення', advanced_detail:'Додаткові теми CSS Loader та докладні візуальні налаштування.', movie:'Відеозаставка Steam',
    artwork:'Власні обкладинки й логотипи', artwork_detail:'Необов’язкове підключення SteamGridDB. Створи обліковий запис, відкрий сторінку API, згенеруй особистий ключ і встав його у вікні зображень. Ключ зберігається на цьому ПК.',
    api_page:'Відкрити сторінку API SteamGridDB', art_picker:'Налаштувати зображення', key_ready:'Твій ключ SteamGridDB збережено', key_missing:'Ключ SteamGridDB ще не задано',
    translation:'Мова опису', translation_detail:'Беремо опис Steam мовою твого Steam. Якщо перекладу немає, позначаємо оригінал. Обліковий запис Google не потрібен.',
    gemini_detail:'В особистому Continue? власника було приватне підключення Gemini/Vertex. У цій публічній збірці вхід через Google та AI-переклад поки не підключені.',
    core_ready:'Картки працюють без облікового запису', setup_optional:'За бажанням: увімкни музику', art_optional:'За бажанням: заміни зображення', version:'Перевірити оновлення',
    info:'Зміни застосовуються одразу. B / Esc закриває вікно.', on:'Увімк.', off:'Вимк.', inherited:'Із загальних налаштувань', home_video:'Живе тло на головній', home_video_detail:'Використовує готове тло обраної гри.',
    storage:'Завантажено', request:'Підготувати цю гру зараз', no_manual:'Автоматичного підбору достатньо; шукати трек вручну необов’язково.'
  }
};
for (const [code,labels] of Object.entries({en:['Update music downloader','Restore previous downloader','Previous downloader kept; update failed. Try again later.'],ru:['Обновить загрузчик музыки','Вернуть прежний загрузчик','Обновление не удалось; сохранён прежний загрузчик. Повтори позже.'],uk:['Оновити завантажувач музики','Повернути попередній завантажувач','Оновлення не вдалося; збережено попередній завантажувач. Повтори пізніше.']})) Object.assign(PC_SETTINGS_TEXT[code],{loader_update:labels[0],loader_rollback:labels[1],loader_old:labels[2]});
Object.assign(PC_SETTINGS_TEXT.en,{"youtube_blocked": "YouTube temporarily declined the request; try again later.", "theme_no_candidate": "No theme found. Try again later.", "theme_title_filtered": "Search results did not match this game. Try again later.", "theme_timeout": "Theme preparation timed out. Try again.", "theme_encode_failed": "Could not process the audio. Try again or repair the media tools.", "theme_format_unavailable": "No compatible audio format is available. Try again later or update the downloader.", "theme_network_error": "Could not connect to the music source. Check your connection and try again.", "theme_download_failed": "The music source returned an unknown download error. Try again later."});
Object.assign(PC_SETTINGS_TEXT.ru,{"youtube_blocked": "YouTube временно отклонил запрос; повтори позже.", "theme_no_candidate": "Тема не найдена. Повтори позже.", "theme_title_filtered": "Результаты поиска не совпали с игрой. Повтори позже.", "theme_timeout": "Время подготовки музыки истекло. Повтори попытку.", "theme_encode_failed": "Не удалось обработать аудио. Повтори попытку или восстанови инструменты медиа.", "theme_format_unavailable": "Совместимый формат аудио недоступен. Повтори позже или обнови загрузчик.", "theme_network_error": "Не удалось подключиться к источнику музыки. Проверь интернет и повтори попытку.", "theme_download_failed": "Источник музыки вернул неизвестную ошибку загрузки. Повтори позже."});
Object.assign(PC_SETTINGS_TEXT.uk,{"youtube_blocked": "YouTube тимчасово відхилив запит; спробуй пізніше.", "theme_no_candidate": "Тему не знайдено. Спробуй пізніше.", "theme_title_filtered": "Результати пошуку не відповідають грі. Спробуй пізніше.", "theme_timeout": "Час підготовки музики минув. Спробуй знову.", "theme_encode_failed": "Не вдалося обробити аудіо. Спробуй знову або віднови інструменти медіа.", "theme_format_unavailable": "Сумісний формат аудіо недоступний. Спробуй пізніше або онови завантажувач.", "theme_network_error": "Не вдалося підключитися до джерела музики. Перевір інтернет і спробуй знову.", "theme_download_failed": "Джерело музики повернуло невідому помилку завантаження. Спробуй пізніше."});

PC_SETTINGS_TEXT.en.theme_file_busy='The audio file is in use. Close its other player and try again.';
PC_SETTINGS_TEXT.ru.theme_file_busy='Аудиофайл занят. Закрой другой плеер и повтори попытку.';
PC_SETTINGS_TEXT.uk.theme_file_busy='Аудіофайл зайнятий. Закрий інший програвач і спробуй знову.';
const psText = key => (PC_SETTINGS_TEXT[LANGUAGE] || PC_SETTINGS_TEXT.en)[key] || key;
const PC_SETTINGS_CSS = `
.DialogContent:has(.cps){width:min(1040px,92vw)!important;max-height:90vh!important;padding:0!important}
.cps{width:100%;color:#e8edf3;font:15px/1.45 "Motiva Sans",Arial,sans-serif;background:linear-gradient(140deg,#1c2a38,#131e29);border:1px solid #394957;border-radius:8px;overflow:hidden}
.cps-header{display:flex;align-items:center;gap:20px;padding:22px 28px;border-bottom:1px solid #34414d}.cps-brand{font:700 25px Georgia,serif;letter-spacing:.04em;flex:1}.cps-sub{color:#9fb0c2;font-size:13px}
.cps-layout{display:grid;grid-template-columns:200px minmax(0,1fr);height:min(620px,66vh)}.cps-nav{padding:18px 12px;border-right:1px solid #34414d;overflow-y:auto}.cps-content{padding:26px 30px;overflow:auto;min-width:0;scroll-padding:12px}
.cps h2{font:400 27px Georgia,serif;margin:0 0 10px}.cps h3{font-size:15px;letter-spacing:.02em;margin:24px 0 10px}.cps p{color:#aebfd0;margin:0 0 18px}.cps small{display:block;color:#9fb0c2;font-size:13px;margin-top:4px}
.cps-btn{display:inline-flex;justify-content:center;align-items:center;gap:8px;padding:10px 16px;background:rgba(255,255,255,.08);color:#e8edf3!important;border:1px solid transparent;border-radius:5px;cursor:pointer;min-height:22px;box-sizing:content-box}
.cps-btn[aria-disabled=true]{opacity:.5;cursor:default}.cps-btn.gpfocus,.cps-btn:focus,.cps-btn:focus-within,.cps-btn:hover{outline:2px solid #fff;outline-offset:-2px;background:#e8edf3!important;color:#101820!important}.cps-btn.selected{background:#334c63;border-color:#64839d}.cps-btn.primary{background:linear-gradient(135deg,#eef4fb,#cadbf0);color:#101820!important;font-weight:600}
.cps-nav .cps-btn{display:flex;justify-content:flex-start;margin-bottom:6px}.cps-nav .cps-btn.selected{border-left:3px solid #dae8f7}
.cps-row{display:flex;gap:20px;align-items:center;padding:16px 0;border-bottom:1px solid rgba(255,255,255,.08)}.cps-label{flex:1;min-width:0}.cps-row .cps-btn{flex-shrink:0}.cps-row.choices{display:block}.cps-choices{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}.cps-choices .cps-btn{min-width:60px}.cps-scope{margin-bottom:20px}.cps-scope .cps-btn{flex:1}.cps-pill{padding:7px 11px;border:1px solid #45627b;border-radius:4px;font-size:13px;color:#c8dbed}.cps-status{margin:16px 0;padding:12px 16px;background:#223448;border-left:3px solid #83a7c8;color:#d4e2ef}.cps-status.error{border-color:#dda78d}.cps-footer{padding:14px 28px;border-top:1px solid #34414d;display:flex;align-items:center;gap:20px}.cps-footer small{flex:1;margin:0}
@media(max-width:800px){.cps-layout{grid-template-columns:160px minmax(0,1fr)}.cps-content{padding:18px}.cps-header{padding:18px}.cps-row{gap:10px}.cps-choices .cps-btn{min-width:40px}}
`;
Object.assign(PC_SETTINGS_TEXT.en,{gb:'GB',glyph_detail:'Choose the button symbols manually. Steam default follows Steam Input.',glyph_preview:'Button symbols preview',pads_detail:'Changes the icon style. Support information still comes from Steam.'});
Object.assign(PC_SETTINGS_TEXT.ru,{gb:'ГБ',glyph_detail:'Выберите символы кнопок вручную. Стандарт Steam следует Steam Input.',glyph_preview:'Образцы символов кнопок',pads_detail:'Меняется вид значков. Сведения о поддержке по-прежнему берём из Steam.'});
Object.assign(PC_SETTINGS_TEXT.uk,{gb:'ГБ',glyph_detail:'Оберіть символи кнопок вручну. Стандарт Steam відповідає Steam Input.',glyph_preview:'Зразки символів кнопок',pads_detail:'Змінюється вигляд значків. Відомості про підтримку й надалі беремо зі Steam.'});
PC_SETTINGS_TEXT.en.cache_detail+=' This is a ceiling, not reserved disk space. Downloads stop while free space is low.';
PC_SETTINGS_TEXT.ru.cache_detail+=' Это предел, место заранее не резервируется. При нехватке свободного места загрузки останавливаются.';
PC_SETTINGS_TEXT.uk.cache_detail+=' Це межа, місце заздалегідь не резервується. Якщо вільного місця замало, завантаження зупиняються.';
function pcControllerChoices() {
  return [['owner',psText('custom')],['native',psText('steam')],['xbox','Xbox'],['playstation','PlayStation'],['steam','Steam Deck / Steam Controller']];
}
function PcSettingsButton({ children, onClick, selected, disabled, primary, label }) {
  const activate = disabled ? undefined : onClick;
  return h(DFL.Focusable, {className:'cps-btn'+(selected?' selected':'')+(primary?' primary':''), role:'button', tabIndex:0,
    'aria-label':label || (typeof children === 'string' ? children : undefined), 'aria-disabled':!!disabled,
    onClick:activate,onActivate:activate}, children);
}
function usePcPlaytimeVisibility(rootRef, hidden) {
  useEffect(()=>{
    if(!hidden)return;
    const changed=new Map();
    const names=new Set(Object.values(I18N).flatMap(d=>[d.steam_stats?.[0],d.played]).filter(Boolean).map(x=>x.trim().toLowerCase()));
    const update=()=>{
      const doc=rootRef.current?.ownerDocument;
      if(!doc)return;
      for(const label of playBarStat(doc)?.labels||[]){
        if(!names.has(label.textContent.trim().toLowerCase()))continue;
        const cls=DFL.playSectionClasses?.GameStat;
        let node=(cls?label.closest('.'+cls):null)||label.parentElement?.parentElement;
        if(node?.parentElement?.classList.contains('tool-tip-source'))node=node.parentElement;
        if(node){if(!changed.has(node))changed.set(node,node.style.display);node.style.display='none';}
      }
    };
    const stop=activeInterval(update,800,()=>rootRef.current?.ownerDocument||uiDocument());
    return()=>{stop();for(const[node,value]of changed)if(node.style.display==='none')node.style.display=value;};
  },[hidden]);
}
async function publishPcSettings(settings) {
  pluginSettings = settings || {};
  publishContinueMusicSettings(pluginSettings);
  settingsListeners.forEach(f => { try { f(pluginSettings); } catch {} });
  applyLaunchNoticeSetting(!!pluginSettings.hide_launch_notice);
  applyHomeSetting(!!pluginSettings.home_installed_first);
  applyHomeLiveSetting(true); homeLiveRefresh();
}
async function enablePcMusic() {
  const installed = await resolvePcMediaJob(await call('install_ytdlp', true, false, 'theme'));
  if (!installed?.ok) return installed;
  await call('set_setting','hub_music',true);
  const settings = await call('set_setting','home_music',true);
  await publishPcSettings(settings);
  if (viewing) { const target=viewing; refreshMediaLatest(target.appid,target.name || '',null,()=>true).then(() => sourceListeners.forEach(f=>f(target.appid))).catch(()=>{}); }
  return {ok:true,settings};
}
livePolicy = function(settings,power,home=false) {
  if (settings?.live_bg==='off' || (home&&settings?.home_live===false)) return 'off';
  return settings?.live_bg==='ac'&&!power?.ac?'off':'always';
};
refreshMediaLatest = async function(appid,name,source=null,alive=()=>true,force=false) {
  if (!alive() || uiBusy()) return {ok:false,deferred:'running'};
  return resolvePcMediaJob(await call('refresh_media',appid,name,false,source,force),alive,appid);
};
async function resolvePcMediaJob(result,alive=()=>true,appid=null) {
  if (!result?.pending || !result.job) return result;
  let mediaSignature='';
  for (let attempt=0;attempt<600;attempt++) {
    const state=await call('media_job_status',result.job);
    if (state?.done) { if(appid){sourceListeners.forEach(f=>f(appid));homeLiveRefresh();} return state.result; }
    if (appid && attempt%2===0) {
      const media=await call('get_pc_media_status',appid).catch(()=>null);
      const next=JSON.stringify([media?.background?.file,media?.music?.file]);
      if(next!==mediaSignature){mediaSignature=next;sourceListeners.forEach(f=>f(appid));homeLiveRefresh();}
    }
    await new Promise(resolve=>setTimeout(resolve,1500));
  }
  return {ok:false,deferred:alive()?'timeout':'superseded'};
}
function PcSettings({closeModal, initialSection='start', initialScope='global'}) {
  useLanguage();
  const appid = currentAppId();
  const name = appid ? window.appStore?.GetAppOverviewByAppID?.(appid)?.display_name || String(appid) : '';
  const [section,setSection]=useState(initialSection),[scope,setScope]=useState(initialScope);
  const [s,setS]=useState(null),[prefs,setPrefs]=useState(null),[fields,setFields]=useState([]),[status,setStatus]=useState(null),[themes,setThemes]=useState([]),[keyState,setKeyState]=useState(null);
  const [notice,setNotice]=useState(''),[busy,setBusy]=useState(false),[consent,setConsent]=useState(null),[movie,setMovie]=useState(startupMovieOn());
  const mounted=useRef(true);
  const refresh=async()=>{
    const jobs=[call('get_settings'),call('get_card_preferences',appid || null),appid?localizedCall('get_card_fields',appid,name):Promise.resolve([]),call('get_pc_media_status',appid || null),call('themes_list'),call('sgdb_status')];
    const results=await Promise.allSettled(jobs); if(!mounted.current)return;
    const setters=[setS,setPrefs,setFields,setStatus,setThemes,setKeyState];
    results.forEach((r,i)=>{if(r.status==='fulfilled')setters[i](r.value);else setNotice(psText('error'));});
  };
  useEffect(()=>{mounted.current=true;refresh();return()=>{mounted.current=false;};},[appid,LANGUAGE]);
  useEffect(()=>{if(!['music','backgrounds'].includes(section))return;const timer=setInterval(()=>call('get_pc_media_status',appid||null).then(r=>mounted.current&&setStatus(r)).catch(()=>{}),3000);return()=>clearInterval(timer);},[section,appid]);
  const run=async(fn)=>{if(busy)return;setBusy(true);setNotice('');try{const r=await fn();if(r?.status==='usable_old')throw new Error(psText('loader_old'));if(r?.ok===false)throw new Error(r.deferred?psText('paused'):psText('error'));await refresh();}catch(e){if(mounted.current)setNotice(String(e.message||e));}finally{if(mounted.current)setBusy(false);}};
  const update=(key,value)=>run(async()=>{const ns=await call('set_setting',key,value);await publishPcSettings(ns);if(mounted.current)setS(ns);});
  const pref=(key,value)=>run(async()=>{setPrefs(await call('set_card_preference',scope==='game'?appid:null,key,value));await publishPcSettings(await call('get_settings'));});
  const B=(label,fn,options={})=>h(PcSettingsButton,{onClick:fn,disabled:busy,...options},label);
  const note=text=>h('p',null,text);
  const toggle=(label,checked,fn,detail,disabled=false)=>h('div',{className:'cps-row'},h('div',{className:'cps-label'},label,detail?h('small',null,detail):null),B(psText(checked?'on':'off'),()=>fn(!checked),{selected:checked,disabled:disabled||busy,label:label+': '+psText(checked?'on':'off')}));
  const choices=(label,value,options,fn,detail)=>h('div',{className:'cps-row choices'},h('div',{className:'cps-label'},label,detail?h('small',null,detail):null),h(DFL.Focusable,{className:'cps-choices','flow-children':'row'},...options.map(([v,text])=>B(text,()=>fn(v),{key:String(v),selected:value===v}))));
  const selected=scope==='game'?prefs?.effective:prefs?.global;
  const scopePicker=()=>h(React.Fragment,null,h(DFL.Focusable,{className:'cps-choices cps-scope','flow-children':'row'},B(psText('defaults'),()=>setScope('global'),{selected:scope==='global'}),B(psText('this_game')+(name?' · '+name:''),()=>setScope('game'),{selected:scope==='game',disabled:!appid})),note(psText(scope==='game'?'game_detail':'card_detail')));
  const mediaState=kind=>{
    const info=status?.[kind] || {};
    const fallback=kind==='music'?(!s?.theme_music_consent||!s?.hub_music?'disabled':info.file?'ready':'waiting'):s?.live_bg==='off'?'disabled':info.file?'ready':'waiting';
    const labels={ready:'ready',downloading:kind==='music'?'music_preparing':'preparing',unavailable:kind==='music'?'music_missing':'unavailable',disabled:'disabled',setup_required:'music_off',deferred:'paused',waiting:'waiting',error:'error'};
    return h('div',{className:'cps-status',role:'status'},psText(labels[info.reason] || (PC_SETTINGS_TEXT.en[info.state] ? info.state : labels[info.state||fallback]) || 'waiting'),info.source?h('small',null,(info.source==='youtube'?'YouTube':'Steam')+(info.effective_quality?' · '+info.effective_quality+'p':'')):null);
  };
  let content=null;
  if(consent)content=h(React.Fragment,null,h('h2',null,psText('consent_title')),note(psText(consent==='music'?'consent_music':'consent_video')),
    status?.runtime?.download_bytes>0?note(({en:'Initial setup also downloads the media tools: ',ru:'При первой настройке также загрузим инструменты обработки: ',uk:'Під час першого налаштування також завантажимо інструменти обробки: '}[LANGUAGE]||'')+Math.ceil(status.runtime.download_bytes/1048576)+' MB.'):null,
    h(DFL.Focusable,{className:'cps-choices','flow-children':'row'},B(psText('allow'),()=>run(async()=>{
    const purpose=consent;setConsent(null);
    if(purpose==='music')return enablePcMusic();
    const r=await resolvePcMediaJob(await call('install_ytdlp',true,false,'youtube'),()=>mounted.current);if(r?.ok){await call('set_setting','media_fallback',true);await publishPcSettings(await call('get_settings'));}return r;
  }),{primary:true}),B(psText('cancel'),()=>setConsent(null))));
  else if(!s)content=note(t('pc_loading'));
  else if(section==='start')content=h(React.Fragment,null,h('h2',null,psText('intro')),note(psText('intro_detail')),
    h('div',{className:'cps-status'},'✓ '+psText('core_ready')),
    h('div',{className:'cps-row'},h('div',{className:'cps-label'},psText(s.theme_music_consent&&s.hub_music?'music_ready':'setup_optional'),h('small',null,psText('no_manual'))),B(psText('music'),()=>setSection('music'),{primary:true})),
    h('div',{className:'cps-row'},h('div',{className:'cps-label'},psText('art_optional'),h('small',null,'SteamGridDB')),B(psText('connections'),()=>setSection('connections'))));
  else if(section==='card')content=h(React.Fragment,null,h('h2',null,psText('card')),scopePicker(),
    ...['story','description','facts','characters','achievements','latest_achievement','playtime'].filter(k=>k!=='characters'||fields.some(f=>f.has_characters)).map(k=>toggle(psText(k),selected?.[k]!==false,v=>pref(k,v),scope==='game'&&prefs?.game?.[k]===undefined?psText('inherited'):null)),
    appid?h(React.Fragment,null,h('h3',null,psText('individual')),fields.length?fields.map(f=>toggle(f.label,!selected?.hidden_fact_ids?.includes(f.id),v=>pref('hidden_fact_ids',v?(selected?.hidden_fact_ids||[]).filter(x=>x!==f.id):[...new Set([...(selected?.hidden_fact_ids||[]),f.id])]))):note(psText('no_facts'))):note(psText('no_game')),
    h('div',{className:'cps-choices'},B(psText(scope==='game'?'inherit':'reset'),()=>run(async()=>{await call('reset_card_preferences',scope==='game'?appid:null);await publishPcSettings(await call('get_settings'));}))));
  else if(section==='backgrounds')content=h(React.Fragment,null,h('h2',null,psText('backgrounds')),
    toggle(psText('live'),s.live_bg!=='off',v=>update('live_bg',v?'always':'off'),psText('live_detail')),
    toggle(psText('home_video'),s.home_live!==false,v=>update('home_live',v),psText('home_video_detail'),s.live_bg==='off'),
    choices(psText('quality'),s.media_quality||1080,[[720,'720p'],[1080,'1080p'],[2160,'4K']],v=>update('media_quality',v),psText('quality_detail')),
    choices(psText('cache'),s.disk_limit_gb||2,[2,4,8,16,64].map(v=>[v,v+' '+psText('gb')]),v=>update('disk_limit_gb',v),psText('cache_detail')),
    toggle(psText('fallback'),!!s.media_fallback&&!!s.youtube_consent,v=>v&&!s.youtube_consent?setConsent('video'):update('media_fallback',v),psText('fallback_detail')),
    appid?h(React.Fragment,null,h('h3',null,name),choices(psText('mode'),s.game_bg?.[appid]||'auto',[['auto',psText('automatic')],['image',psText('still')],['steam',psText('native')]],v=>run(async()=>{await call('set_game_bg',appid,v);bgListeners.forEach(f=>f(appid,v));})),mediaState('background'),B(psText('request'),()=>run(async()=>{const r=await refreshMediaLatest(appid,name,null,()=>mounted.current);sourceListeners.forEach(f=>f(appid));return r;}))):null,
    h('div',{className:'cps-row'},h('div',{className:'cps-label'},psText('storage')+': '+Math.round((status?.bytes||0)/1048576)+' MB'),B(psText('clear'),()=>run(async()=>{const r=await call('clear_media_cache');homeLiveRefresh();sourceListeners.forEach(f=>f(appid));return r;}))));
  else if(section==='music')content=h(React.Fragment,null,h('h2',null,psText('music')),note(psText('music_detail')),
    !s.theme_music_consent?B(psText('enable_music'),()=>setConsent('music'),{primary:true}):h(React.Fragment,null,
      toggle(psText('music_card'),s.hub_music!==false,v=>update('hub_music',v)),toggle(psText('music_home'),s.home_music!==false,v=>update('home_music',v)),
      choices(psText('volume'),Math.round((s.music_volume??.4)*100),[0,20,40,60,80,100].map(v=>[v,v+'%']),v=>update('music_volume',v/100))),
    s.theme_music_consent?h('div',{className:'cps-choices'},B(psText('loader_update'),()=>run(async()=>resolvePcMediaJob(await call('update_music_loader',true,false)))),status?.rollback_available?B(psText('loader_rollback'),()=>run(async()=>resolvePcMediaJob(await call('update_music_loader',true,true)))):null):null,
    appid?h(React.Fragment,null,h('h3',null,name),mediaState('music'),h('div',{className:'cps-choices'},B(psText('choose_track'),()=>openMusicPicker(appid)),B(psText('refresh'),()=>run(async()=>{const r=await refreshMediaLatest(appid,name,null,()=>mounted.current,true);sourceListeners.forEach(f=>f(appid));return r;})))):null);
  else if(section==='library')content=h(React.Fragment,null,h('h2',null,psText('library')),
    toggle(psText('tabs'),s.library_tabs===true,v=>update('library_tabs',v),psText('tabs_detail'),otherTabMaster()),
    toggle(psText('installed'),!!s.home_installed_first,v=>update('home_installed_first',v)),h('div',{className:'cps-row'},h(UpdateRow)));
  else if(section==='appearance')content=h(React.Fragment,null,h('h2',null,psText('appearance')),
    toggle(psText('rounded'),!!themes.find(x=>x.name==='Round')?.active,v=>run(async()=>setThemes(await call('themes_set','Round',null,v)))),
    choices(psText('glyphs'),s.pc_glyphs||'owner',pcControllerChoices(),v=>update('pc_glyphs',v),psText('glyph_detail')),
    ['xbox','playstation','steam'].includes(s.pc_glyphs)?h('div',{className:'cps-choices','aria-label':psText('glyph_preview')},...['a','b','x','y','back','start','lb','rb','lt','rt'].map(k=>h('img',{key:k,alt:k.toUpperCase(),src:pcControllerGlyph('https://steamloopback.host/steaminputglyphs/xbox_button_'+k+'.svg',s.pc_glyphs),style:{width:32,height:32}}))):null,
    choices(psText('pads'),s.pc_pads||'owner',pcControllerChoices(),v=>update('pc_pads',v),psText('pads_detail')),
    toggle(psText('movie'),movie,v=>run(async()=>setMovie(await setStartupMovie(v)))),
    h('div',{className:'cps-row'},h('div',{className:'cps-label'},psText('advanced'),h('small',null,psText('advanced_detail'))),B(psText('settings'),openThemes)));
  else if(section==='connections')content=h(React.Fragment,null,h('h2',null,psText('connections')),
    h('h3',null,psText('artwork')),note(psText('artwork_detail')),h('div',{className:'cps-status'},psText(keyState?.configured?'key_ready':'key_missing')),
    h('div',{className:'cps-choices'},B(psText('api_page'),()=>DFL.Navigation.NavigateToExternalWeb('https://www.steamgriddb.com/profile/preferences/api')),
      B(psText('art_picker'),()=>openArtPicker(appid||0),{disabled:!appid})),
    h('h3',null,psText('translation')),note(psText('translation_detail')),h('small',null,psText('gemini_detail')));
  return h(DFL.ModalRoot,{closeModal,onCancel:closeModal,bAllowFullSize:true},h('style',null,PC_SETTINGS_CSS),
    h(DFL.Focusable,{className:'cps','flow-children':'column',onCancelButton:closeModal},
      h('div',{className:'cps-header'},h('div',{className:'cps-brand'},'Continue?'),h('div',{className:'cps-sub'},psText('settings'))),
      h(DFL.Focusable,{className:'cps-layout','flow-children':'row'},
        h(DFL.Focusable,{className:'cps-nav','flow-children':'column'},...['start','library','card','backgrounds','music','appearance','connections'].map(k=>B(psText(k),()=>{setSection(k);setConsent(null);setNotice('');},{key:k,selected:section===k}))),
        h(DFL.Focusable,{className:'cps-content','flow-children':'column'},content,notice?h('div',{className:'cps-status error',role:'alert'},notice):null,busy?h('div',{className:'cps-status',role:'status'},psText('preparing')):null)),
      h('div',{className:'cps-footer'},h('small',null,psText('info'),h('br'),'Continue? by Doctor_Nerd — github.com/Alexsander720/continue'),B(psText('back'),closeModal,{disabled:false}))));
}
