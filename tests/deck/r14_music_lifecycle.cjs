// Execute shipped polling, card subscription and Audio hook with a tiny fake DOM.
const fs=require('fs'),assert=require('assert');
const [pc,plugin]=process.argv.slice(2);
const settingsSource=fs.readFileSync(pc+'/bp_public_settings.js','utf8');
const controls=fs.readFileSync(pc+'/bp_public_controls.js','utf8');
const bundle=fs.readFileSync(plugin+'/dist/index.js','utf8');
const music=fs.readFileSync(plugin+'/assets/deck_music.js','utf8');
function section(s,a,b){assert(s.includes(a),a);return s.slice(s.indexOf(a),s.indexOf(b,s.indexOf(a)+a.length));}
let ready=false,mounted=true,plays=0,cardUpdates=0,cleanups=[];
let useStandaloneMusic,refreshMediaLatest,LANGUAGE='en',IS_LINUX=false;
const settingsListeners=new Set(),useRef=v=>({current:v});
const sourceListeners=new Set(),DATA='http://fixture/',window={SteamUIStore:{WindowStore:{GamepadUIMainWindowInstance:{BrowserWindow:{document:{
  createElement(){return {dataset:{},volume:0,paused:true,play(){this.paused=false;plays++;return Promise.resolve();},pause(){this.paused=true;},removeAttribute(){},remove(){},load(){}};},body:{appendChild(){}}
}}}}}};
const continueMusicAllowed=()=>true,pcBusy=()=>false,uiBusy=()=>false,homeLiveRefresh=()=>{},seekResume=()=>{},notePos=()=>{};
const uiDocument=()=>window.SteamUIStore.WindowStore.GamepadUIMainWindowInstance.BrowserWindow.document;
const settings={standalone:true,theme_music_consent:true,hub_music:true},appid=42,name='Fixture',language='en';
function useEffect(fn){const cleanup=fn();if(cleanup)cleanups.push(cleanup);}
function setCard(card){cardUpdates++;cleanups.splice(1).forEach(f=>f());useStandaloneMusic(appid,settings,card.media);}
async function localizedCall(){return {media:ready?{theme:'42_theme.m4a'}:{}};}
async function call(method){
  if(method==='media_job_status')return ready?{done:true,result:{ok:true}}:{done:false};
  if(method==='get_pc_media_status')return {music:{file:ready?'42_theme.m4a':null}};
  if(method==='get_music_files')return ready?{'42':'media/42_theme.m4a'}:{};
  throw Error(method);
}
const nativeTimeout=setTimeout,nativeInterval=setInterval;
setTimeout=(fn,ms)=>nativeTimeout(()=>{mounted=false;ready=true;fn();},1);
setInterval=(fn,ms)=>nativeInterval(fn,1);
eval(section(music,'function createDeckMusicPlayer','\nif(IS_LINUX)useStandaloneMusic=useDeckMusic;'));
eval(section(controls,'useStandaloneMusic = function','\nfunction '));
eval(section(settingsSource,'async function resolvePcMediaJob','\nfunction PcSettings'));
const start=bundle.indexOf('useEffect(() => {  // автономный источник');
assert(start>=0,'real card listener');
eval(bundle.slice(start,bundle.indexOf('\n\n',start)));
useStandaloneMusic(appid,settings,{});
(async()=>{
  await resolvePcMediaJob({pending:true,job:'fixture'},()=>mounted,appid);
  await new Promise(resolve=>nativeTimeout(resolve,30));
  assert(!mounted,'settings closed');assert(cardUpdates>0,'card notified after close');assert(plays>0,'audio plays without navigation');
  cleanups.reverse().forEach(f=>f());
  console.log('closed-modal playback PASS',JSON.stringify({plays,cardUpdates}));
  // Check actual labels lookup: every reason must resolve in all UI languages.
  eval(section(settingsSource,'const PC_SETTINGS_TEXT','\nfunction PcSettingsButton').replace('const PC_SETTINGS_TEXT','var PC_SETTINGS_TEXT'));
  for(const lang of ['en','ru','uk'])for(const key of ['youtube_blocked','theme_no_candidate','theme_title_filtered','theme_timeout','theme_encode_failed','theme_format_unavailable','theme_network_error','theme_download_failed','theme_file_busy']){
    assert(PC_SETTINGS_TEXT[lang]?.[key],lang+': '+key);
    const render=new Function('status','s','psText','h','PC_SETTINGS_TEXT',
      section(settingsSource,'  const mediaState=kind=>','  let content=null;')+'\nreturn mediaState("music");');
    const element=render({music:{state:key,reason:key}},{theme_music_consent:true,hub_music:true},
      k=>PC_SETTINGS_TEXT[lang][k],(tag,props,...children)=>({tag,props,children}),PC_SETTINGS_TEXT);
    assert.equal(element.children[0],PC_SETTINGS_TEXT[lang][key],lang+': rendered '+key);
  }
  assert(settingsSource.includes('labels[info.reason]')||settingsSource.includes('PC_SETTINGS_TEXT.en[info.state]'),'status reason rendered');
  console.log('localized status reasons PASS');
})().catch(e=>{console.error(e);process.exitCode=1;cleanups.reverse().forEach(f=>f());});
