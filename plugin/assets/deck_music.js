// Standalone Deck additions. The export inserts this inside the existing bundle.
const DM_TEXT = {
  en:{music:'Music',enable:'Enable automatic music',detail:'Set up once. Themes are prepared when you open games. Short audio downloads can run on battery; video preparation waits for charging.',consent:'Download optional media tools (about 174 MiB plus yt-dlp) into Continue?, then find themes on YouTube. No account is needed. Continue? does not change SteamOS.',card:'On the game page',home:'On Home',volume:'Music volume',game:'This game',auto:'Automatic theme',none:'No music',retry:'Try again',update:'Update music downloader',rollback:'Restore previous downloader',setup_required:'Music needs setup',preparing:'Preparing music…',waiting:'The theme will be prepared when you open a game',ready:'Theme ready',disabled:'Music disabled',error:'Could not prepare the theme. Try again or update the downloader.',busy:'Preparation is already running',deferred:'Waiting: close the game or charge the battery above 15%.',failed:'Setup failed. Try again when your connection is available.',version:'Downloader',note:'Global settings. “This game” changes only the open game.'},
  ru:{music:'Музыка',enable:'Включить автоматическую музыку',detail:'Настрой один раз. Темы готовятся при открытии игр. Короткое аудио загружается и на батарее; видео готовится при зарядке.',consent:'Скачать инструменты медиа (около 174 МиБ плюс yt-dlp) в папку Continue?, затем искать темы на YouTube. Аккаунт не нужен. SteamOS не изменяется.',card:'На странице игры',home:'На главной',volume:'Громкость музыки',game:'Эта игра',auto:'Автоматическая тема',none:'Без музыки',retry:'Попробовать ещё раз',update:'Обновить загрузчик музыки',rollback:'Вернуть прежний загрузчик',setup_required:'Музыку нужно настроить',preparing:'Готовлю музыку…',waiting:'Тема подготовится при открытии игры',ready:'Тема готова',disabled:'Музыка выключена',error:'Не удалось подготовить тему. Повтори попытку или обнови загрузчик.',busy:'Подготовка уже идёт',deferred:'Ожидание: закрой игру или заряди батарею выше 15%.',failed:'Настройка не завершилась. Повтори при доступном интернете.',version:'Загрузчик',note:'Общие настройки. «Эта игра» меняет только открытую игру.'},
  uk:{music:'Музика',enable:'Увімкнути автоматичну музику',detail:'Налаштуй один раз. Теми готуються під час відкриття ігор. Коротке аудіо завантажується й від батареї; відео готується під час заряджання.',consent:'Завантажити інструменти медіа (близько 174 МіБ плюс yt-dlp) у папку Continue?, потім шукати теми на YouTube. Обліковий запис не потрібен. SteamOS не змінюється.',card:'На сторінці гри',home:'На головній',volume:'Гучність музики',game:'Ця гра',auto:'Автоматична тема',none:'Без музики',retry:'Спробувати ще раз',update:'Оновити завантажувач музики',rollback:'Повернути попередній завантажувач',setup_required:'Музику потрібно налаштувати',preparing:'Готую музику…',waiting:'Тема підготується під час відкриття гри',ready:'Тема готова',disabled:'Музику вимкнено',error:'Не вдалося підготувати тему. Повтори спробу або онови завантажувач.',busy:'Підготовка вже триває',deferred:'Очікування: закрий гру або заряди батарею вище 15%.',failed:'Налаштування не завершено. Повтори за доступного інтернету.',version:'Завантажувач',note:'Загальні налаштування. «Ця гра» змінює лише відкриту гру.'}
};
function dm(key) { return DM_TEXT[LANGUAGE]?.[key] || DM_TEXT.en[key] || key; }
DM_TEXT.en.disable='Disable automatic music';DM_TEXT.ru.disable='Выключить автоматическую музыку';DM_TEXT.uk.disable='Вимкнути автоматичну музику';
DM_TEXT.en.detail='First setup: ~180 MB, about half a minute; connect the charger at 30% battery or below. Themes download on battery; video preparation needs charging.';
DM_TEXT.ru.detail='Первая настройка ~180 МБ, около полуминуты; при заряде 30% и ниже подключи зарядку. Темы загружаются на батарее; видео готовится при зарядке.';
DM_TEXT.uk.detail='Перше налаштування ~180 МБ, близько пів хвилини; за заряду 30% і нижче підключи зарядку. Теми завантажуються від батареї; відео готується під час заряджання.';
DM_TEXT.en.consent=DM_TEXT.en.detail+' Download optional media tools into Continue?, then find themes on YouTube. No account is needed. SteamOS stays unchanged.';
DM_TEXT.ru.consent=DM_TEXT.ru.detail+' Скачать инструменты медиа в папку Continue?, затем искать темы на YouTube. Аккаунт не нужен. SteamOS не изменяется.';
DM_TEXT.uk.consent=DM_TEXT.uk.detail+' Завантажити інструменти медіа у папку Continue?, потім шукати теми на YouTube. Обліковий запис не потрібен. SteamOS не змінюється.';
DM_TEXT.en.charging_required='Music setup needs more than 30% battery or a connected charger. Close the game first.';
DM_TEXT.ru.charging_required='Для настройки музыки нужен заряд выше 30% или подключённая зарядка. Сначала закрой игру.';
DM_TEXT.uk.charging_required='Для налаштування музики потрібен заряд вище 30% або підключена зарядка. Спочатку закрий гру.';
DM_TEXT.en.python3_required='Music needs system Python 3. Restore Python 3 in SteamOS, then try again.';
DM_TEXT.ru.python3_required='Для музыки нужен системный Python 3. Восстанови Python 3 в SteamOS и повтори попытку.';
DM_TEXT.uk.python3_required='Для музики потрібен системний Python 3. Віднови Python 3 у SteamOS і повтори спробу.';

DM_TEXT.en.youtube_blocked='YouTube temporarily declined the request; try again later.';
DM_TEXT.ru.youtube_blocked='YouTube временно отклонил запрос; повтори позже.';
DM_TEXT.uk.youtube_blocked='YouTube тимчасово відхилив запит; спробуй пізніше.';
Object.assign(DM_TEXT.en,{"youtube_blocked": "YouTube temporarily declined the request; try again later.", "theme_no_candidate": "No theme found. Try again later.", "theme_title_filtered": "Search results did not match this game. Try again later.", "theme_timeout": "Theme preparation timed out. Try again.", "theme_encode_failed": "Could not process the audio. Try again or repair the media tools.", "theme_format_unavailable": "No compatible audio format is available. Try again later or update the downloader.", "theme_network_error": "Could not connect to the music source. Check your connection and try again.", "theme_download_failed": "The music source returned an unknown download error. Try again later."});
Object.assign(DM_TEXT.ru,{"youtube_blocked": "YouTube временно отклонил запрос; повтори позже.", "theme_no_candidate": "Тема не найдена. Повтори позже.", "theme_title_filtered": "Результаты поиска не совпали с игрой. Повтори позже.", "theme_timeout": "Время подготовки музыки истекло. Повтори попытку.", "theme_encode_failed": "Не удалось обработать аудио. Повтори попытку или восстанови инструменты медиа.", "theme_format_unavailable": "Совместимый формат аудио недоступен. Повтори позже или обнови загрузчик.", "theme_network_error": "Не удалось подключиться к источнику музыки. Проверь интернет и повтори попытку.", "theme_download_failed": "Источник музыки вернул неизвестную ошибку загрузки. Повтори позже."});
Object.assign(DM_TEXT.uk,{"youtube_blocked": "YouTube тимчасово відхилив запит; спробуй пізніше.", "theme_no_candidate": "Тему не знайдено. Спробуй пізніше.", "theme_title_filtered": "Результати пошуку не відповідають грі. Спробуй пізніше.", "theme_timeout": "Час підготовки музики минув. Спробуй знову.", "theme_encode_failed": "Не вдалося обробити аудіо. Спробуй знову або віднови інструменти медіа.", "theme_format_unavailable": "Сумісний формат аудіо недоступний. Спробуй пізніше або онови завантажувач.", "theme_network_error": "Не вдалося підключитися до джерела музики. Перевір інтернет і спробуй знову.", "theme_download_failed": "Джерело музики повернуло невідому помилку завантаження. Спробуй пізніше."});

DM_TEXT.en.theme_file_busy='The audio file is in use. Close its other player and try again.';
DM_TEXT.ru.theme_file_busy='Аудиофайл занят. Закрой другой плеер и повтори попытку.';
DM_TEXT.uk.theme_file_busy='Аудіофайл зайнятий. Закрий інший програвач і спробуй знову.';
function createDeckMusicPlayer(doc,url,volume,busy,userApi) {
  let closed=false,sleeping=false,pending=false,generation=0,ramp=null,removed=false;
  const audio=doc.createElement('audio');audio.src=url;audio.loop=true;audio.preload='auto';audio.hidden=true;
  audio.volume=Math.max(0,Math.min(1,Number.isFinite(volume)?volume:.4));
  doc.body.appendChild(audio);
  const remove=()=>{audio.pause();if(removed)return;removed=true;clearInterval(ramp);audio.removeAttribute('src');audio.load?.();audio.remove();};
  const setVolume=(value,ms=0,done)=>{
    value=Math.max(0,Math.min(1,Number.isFinite(value)?value:.4));clearInterval(ramp);
    if(!ms){audio.volume=value;done?.();return;}
    const from=audio.volume,at=Date.now();ramp=setInterval(()=>{
      const k=Math.min(1,(Date.now()-at)/ms);audio.volume=from+(value-from)*k;
      if(k===1){clearInterval(ramp);done?.();}
    },40);
  };
  const tick=()=>{
    if(closed)return;
    if(sleeping || doc.visibilityState==='hidden' || busy()) { ++generation;pending=false;if(!audio.paused)audio.pause(); }
    else if(audio.paused&&!pending){
      pending=true;const attempt=++generation;
      audio.play().then(()=>{
        if(closed){remove();return;}
        if(attempt!==generation||sleeping||doc.visibilityState==='hidden'||busy())audio.pause();
      }).catch(()=>{}).finally(()=>{if(attempt===generation)pending=false;});
    }
  };
  const registrations=[];
  try { const r=userApi?.RegisterForPrepareForSystemSuspendProgress?.(()=>{sleeping=true;tick();});if(r)registrations.push(r); }catch{}
  try { const r=userApi?.RegisterForResumeSuspendedGamesProgress?.(()=>{sleeping=false;tick();});if(r)registrations.push(r); }catch{}
  doc.addEventListener?.('visibilitychange',tick);const interval=setInterval(tick,500);tick();
  return {audio,setVolume,close(fadeMs=0){if(closed)return;closed=true;++generation;clearInterval(interval);doc.removeEventListener?.('visibilitychange',tick);
    for(const r of registrations)try{if(typeof r==='function')r();else r.unregister?.();}catch{}
    if(fadeMs&&!audio.paused)setVolume(0,fadeMs,remove);else remove();}};
}
// Steam popups share an origin, but may host independent plugin realms. Settings
// are persisted before publishing; this event path adds no backend polling.
const CONTINUE_MUSIC_CHANNEL='continue-music-settings-v1';
const musicSettingsSender=Math.random().toString(36).slice(2);
let musicSettingsSequence=0;
function publishContinueMusicSettings(settings) {
  if(!settings?.standalone || typeof BroadcastChannel!=='function')return;
  try {
    const channel=new BroadcastChannel(CONTINUE_MUSIC_CHANNEL);
    channel.postMessage({type:'settings',sender:musicSettingsSender,seq:++musicSettingsSequence,settings});
    channel.close();
  }catch{}
}
function subscribeContinueMusicSettings(apply) {
  if(typeof BroadcastChannel!=='function')return ()=>{};
  try {
    const channel=new BroadcastChannel(CONTINUE_MUSIC_CHANNEL),seen=new Map();
    channel.onmessage=event=>{
      const msg=event.data;
      // Local Set listeners already received this sender's snapshot. Reject
      // duplicates and stale deliveries without restarting volume ramps.
      if(msg?.type!=='settings'||msg.sender===musicSettingsSender||typeof msg.sender!=='string'||
         !Number.isSafeInteger(msg.seq)||msg.seq<1||msg.seq<=(seen.get(msg.sender)||0)||!msg.settings?.standalone)return;
      if(seen.size>=24&&!seen.has(msg.sender))seen.delete(seen.keys().next().value);
      seen.set(msg.sender,msg.seq);apply(msg.settings);
    };
    return ()=>channel.close();
  }catch{return ()=>{};}
}
function useDeckMusic(appid,settings,media,busy=uiBusy) {
  const settingsRef=useRef(settings),applyRef=useRef(null);
  useEffect(()=>{
    let alive=true,player=null,file=null,generation=0,enabled=false;
    const allowed=()=>!!settingsRef.current?.standalone && settingsRef.current.hub_music!==false &&
      !!settingsRef.current.theme_music_consent && continueMusicAllowed(settingsRef.current) &&
      settingsRef.current.music_choices?.[appid]!=='none';
    const refresh=async(id=appid,prepare=false)=>{
      if(Number(id)!==Number(appid)||!alive||!allowed())return;
      const request=++generation,valid=()=>alive&&request===generation&&allowed();
      try {
        const files=await call('get_music_files');
        if(!valid())return;
        const next=files?.[appid]||null;
        if(!next&&prepare){
          const name=window.appStore?.GetAppOverviewByAppID?.(Number(appid))?.display_name||'';
          if(IS_LINUX)await prepareDeckTheme(appid,name,false,valid);
          else await refreshMediaLatest(appid,name,null,valid);
          if(valid())return refresh(appid);
          return;
        }
        if(next===file&&(player||!next))return;
        player?.close();player=null;file=next;
        const doc=uiDocument();if(!file||!doc?.body)return;
        const volume=settingsRef.current.music_volume??.4;
        player=createDeckMusicPlayer(doc,DATA+file,volume,()=>busy(doc)||!allowed(),window.SteamClient?.User);
        if(player.audio.dataset)player.audio.dataset.continueTheme=String(appid);
        const audio=player.audio;
        audio.ontimeupdate=()=>{if(!audio.paused)notePos('music:'+appid,audio.currentTime);};
        if(!IS_LINUX){player.setVolume(0);player.setVolume(volume,1500);}
        seekResume(player.audio,'music:'+appid);
      }catch{}
    };
    // UI callbacks, cross-context events and React props share one lifecycle.
    const apply=next=>{
      settingsRef.current=next;
      const wasEnabled=enabled;enabled=allowed();
      if(!enabled){++generation;player?.close();player=null;file=null;return;}
      if(player)player.setVolume(next.music_volume??.4,200);
      else if(!wasEnabled)refresh(appid,true);
    };
    applyRef.current=apply;settingsListeners.add(apply);sourceListeners.add(refresh);
    const unsubscribe=subscribeContinueMusicSettings(apply);
    apply(settingsRef.current);
    return ()=>{alive=false;++generation;unsubscribe();settingsListeners.delete(apply);sourceListeners.delete(refresh);
      if(applyRef.current===apply)applyRef.current=null;player?.close(600);};
  },[appid]);
  useEffect(()=>{applyRef.current?.(settings);},[appid,settings?.standalone,settings?.hub_music,settings?.theme_music_consent,settings?.music_provider,settings?.music_choices?.[appid],settings?.music_volume]);
}
if(IS_LINUX)useStandaloneMusic=useDeckMusic;

async function resolveDeckMusicJob(result,alive=()=>true,appid=null,cancelled=()=>false) {
  if(!result?.pending||!result.job)return result;
  for(let attempt=0;attempt<400&&!cancelled();attempt++){
    const state=await call('music_job_status',result.job);
    if(cancelled())return {ok:false,cancelled:true};
    if(state?.done){if(appid){sourceListeners.forEach(f=>f(Number(appid)));homeLiveRefresh();}return state.result;}
    await new Promise(resolve=>setTimeout(resolve,1000));
  }
  return {ok:false,error:cancelled()?'cancelled':'timeout'};
}
async function prepareDeckTheme(appid,name,force=false,alive=()=>true) {
  // A different game may still own the single download worker. Keep only the
  // current view interested; an obsolete Home/card request never retries.
  for(let attempt=0;attempt<240&&alive();attempt++) {
    const result=await resolveDeckMusicJob(await call('refresh_music',Number(appid),name||'',force),alive,appid,()=>!alive());
    if(!alive())return {ok:false,cancelled:true};
    if(result?.deferred!=='busy') {
      if(result?.ok)sourceListeners.forEach(f=>f(Number(appid)));
      return result;
    }
    await new Promise(resolve=>setTimeout(resolve,1500));
  }
  return {ok:false,error:alive()?'timeout':'cancelled'};
}
function DeckMusicSection() {
  useLanguage();
  const [settings,setSettings]=useState(null),[status,setStatus]=useState(null),[busy,setBusy]=useState(false),[notice,setNotice]=useState(''),[consent,setConsent]=useState(false);
  const mounted=useRef(true);const target=viewing?.appid;
  const refresh=async()=>{
    const [s,st]=await Promise.all([call('get_settings'),call('get_deck_music_status',target||null)]);
    if(mounted.current){setSettings(s);setStatus(st);}
  };
  useEffect(()=>{mounted.current=true;refresh().catch(()=>{});const timer=setInterval(()=>refresh().catch(()=>{}),2500);
    return ()=>{mounted.current=false;clearInterval(timer);};},[target]);
  // Decky's dropdown trampoline may unmount this section before onChange's RPC
  // resolves. Only local React state belongs behind the mounted guard.
  const publish=(s,restartHome=true)=>{pluginSettings=s;publishContinueMusicSettings(s);settingsListeners.forEach(f=>{try{f(s);}catch{}});if(restartHome){homeLiveRefresh();sourceListeners.forEach(f=>target&&f(target));}if(mounted.current)setSettings(s);};
  const change=async(k,v)=>publish(await call('set_setting',k,v),k!=='music_volume');
  const run=async action=>{setBusy(true);setNotice('');try{
    const r=await resolveDeckMusicJob(await action(),()=>mounted.current,target);
    if(!mounted.current)return;
    if(!r?.ok || r.status==='usable_old')setNotice(dm(!!DM_TEXT.en[r?.reason]?r.reason:r?.deferred==='busy'?'busy':r?.deferred==='charging_required'?'charging_required':r?.deferred?'deferred':'failed'));
    publish(await call('get_settings'));await refresh();
    if(r?.ok&&target)prepareDeckTheme(target,viewing?.name||'',false,()=>mounted.current).catch(()=>{});
  }catch{if(mounted.current)setNotice(dm('failed'));}finally{if(mounted.current)setBusy(false);}};
  if(consent)return h(ReviewDialog,{title:dm('enable'),description:dm('consent'),busy,cancel:()=>setConsent(false),accept:()=>{setConsent(false);run(()=>call('setup_deck_music',true,false));}});
  const row=content=>h(DFL.PanelSectionRow,null,content);
  return h(DFL.PanelSection,{title:dm('music')},
    row(h('div',{style:{fontSize:12,lineHeight:1.5,color:'#b8c2cc'}},dm('detail'))),
    notice?row(h('div',{role:'status'},notice)):null,
    row(h('div',{role:'status',style:{fontSize:12}},dm(busy?'preparing':status?.state||'setup_required'))),
    !settings?.theme_music_consent||!status?.runtime?.ready?row(h(DFL.ButtonItem,{disabled:busy,onClick:()=>setConsent(true)},dm('enable'))):h(React.Fragment,null,
      row(h(DFL.ToggleField,{label:dm('card'),checked:settings.hub_music!==false,onChange:v=>change('hub_music',v)})),
      row(h(DFL.ToggleField,{label:dm('home'),checked:settings.home_music!==false,onChange:v=>change('home_music',v)})),
      row(h(DFL.DropdownItem,{label:dm('volume'),rgOptions:[0,20,40,60,80,100].map(v=>({data:v,label:v+'%'})),selectedOption:Math.round((settings.music_volume??.4)*100),onChange:o=>change('music_volume',o.data/100)})),
      target?row(h(DFL.DropdownItem,{label:dm('game'),rgOptions:[{data:'auto',label:dm('auto')},{data:'none',label:dm('none')}],selectedOption:settings.music_choices?.[target]||'auto',onChange:async o=>{const r=await call('set_music_choice',target,o.data);if(r?.ok)publish(r.settings);if(o.data==='auto')run(()=>call('refresh_music',target,viewing?.name||'',true));}})):null,
      target?row(h(DFL.ButtonItem,{disabled:busy,onClick:()=>run(()=>call('refresh_music',target,viewing?.name||'',true))},dm('retry'))):null,
      row(h(DFL.ButtonItem,{disabled:busy,onClick:()=>run(()=>call('update_music_loader',true,false))},dm('update'))),
      status?.rollback_available?row(h(DFL.ButtonItem,{disabled:busy,onClick:()=>run(()=>call('update_music_loader',true,true))},dm('rollback'))):null,
      row(h(DFL.ButtonItem,{disabled:busy,onClick:()=>run(async()=>{await call('set_setting','hub_music',false);await call('set_setting','home_music',false);await call('set_setting','theme_music_consent',false);return {ok:true};})},dm('disable'))),
      status?.loader?.version?row(h('div',{style:{fontSize:11,color:'#8b99a6'}},dm('version')+': '+status.loader.version)):null));
}
