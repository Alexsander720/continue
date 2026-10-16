// Executes ZIP code, real UI handlers and player hooks. No browser/network/device.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const [root,platform,scenario]=process.argv.slice(2);
const plugin=fs.existsSync(root+'/plugin')?root+'/plugin':root;
const bundle=fs.readFileSync(plugin+'/dist/index.js','utf8');
const controls=platform==='pc'?fs.readFileSync(root+'/pc/bp_public_controls.js','utf8'):'';
const settingsSource=platform==='pc'?fs.readFileSync(root+'/pc/bp_public_settings.js','utf8'):'';
function slice(text,a,b){const i=text.indexOf(a),end=text.indexOf(b,i+a.length),j=end<0?text.length:end;assert(i>=0&&j>i,a);return text.slice(i,j);}
let now=0,seq=0,host=null,busy=false,deferFiles=false,filesReady=true,prepares=0;
const timers=new Map(),audios=[],pendingFiles=[],events=new Map();
const clone=x=>JSON.parse(JSON.stringify(x));
const store={standalone:true,theme_music_consent:true,hub_music:true,home_music:true,music_volume:.4,music_choices:{}};
const files=()=>filesReady&&store.music_choices['42']!=='none'?{'42':'media/42_theme.m4a'}:{};
class Host {
  constructor(fn){this.fn=fn;this.slots=[];this.effects=[];}
  render(){host=this;this.i=0;this.todo=[];this.tree=this.fn();host=null;for(const f of this.todo)f();return this.tree;}
  unmount(){for(const e of this.effects)e?.cleanup?.();this.effects=[];}
}
const useRef=v=>{const i=host.i++;return host.slots[i]||(host.slots[i]={current:v});};
const useState=v=>{const owner=host,i=host.i++;if(!(i in owner.slots))owner.slots[i]=typeof v==='function'?v():v;return[owner.slots[i],next=>owner.slots[i]=typeof next==='function'?next(owner.slots[i]):next];};
function useEffect(fn,deps){const owner=host,i=host.i++,old=owner.effects[i];if(!old||deps.some((v,j)=>!Object.is(v,old.deps[j])))owner.todo.push(()=>{old?.cleanup?.();owner.effects[i]={deps,cleanup:fn()};});}
const doc={visibilityState:'visible',body:{appendChild(){}},addEventListener(k,f){events.set(f,k);},removeEventListener(k,f){events.delete(f);},
 createElement(){const a={volume:0,paused:true,currentTime:17,dataset:{},play(){this.paused=false;return Promise.resolve();},pause(){this.paused=true;},load(){},removeAttribute(){this.src='';},remove(){this.removed=true;}};audios.push(a);return a;}};
const h=(type,props,...children)=>({type,props:{...props,children},children});
const noop=()=>{};
const context={console,Promise,Map,Set,Math,Number,JSON,Error,Date:{now:()=>now},useRef,useState,useEffect,h,
 setInterval(fn,ms){timers.set(++seq,{fn,at:now+ms,ms});return seq;},clearInterval:id=>timers.delete(id),
 setTimeout(fn,ms){timers.set(++seq,{fn,at:now+ms,ms:0});return seq;},clearTimeout:id=>timers.delete(id),
 DATA:'http://fixture/',IS_LINUX:platform==='deck',LANGUAGE:'en',useStandaloneMusic:null,
 sourceListeners:new Set(),settingsListeners:new Set(),pluginSettings:clone(store),viewing:{appid:42,name:'Fixture'},
 React:{Fragment:'Fragment'},DFL:new Proxy({}, {get:(_,k)=>k}),uiDocument:()=>doc,uiBusy:()=>busy,pcBusy:()=>busy,
 continueMusicAllowed:()=>true,seekResume:noop,notePos:noop,homeLiveRefresh:noop,useLanguage:noop,
 applyLaunchNoticeSetting:noop,applyHomeSetting:noop,applyHomeLiveSetting:noop,
 startupMovieOn:()=>true,currentAppId:()=>42,refreshMediaLatest:async()=>{prepares++;filesReady=true;return {ok:true};},
 resolveCustomizationJob:async x=>x,openMusicPicker:noop,log:noop,t:k=>k,I18N:{en:{}},UpdateRow:noop,
 window:{appStore:{GetAppOverviewByAppID:()=>({display_name:'Fixture'})},SteamUIStore:{WindowStore:{GamepadUIMainWindowInstance:{BrowserWindow:{document:doc}}}}},
 call:async(method,...args)=>{
   if(method==='get_settings')return clone(store);
   if(method==='set_setting'){store[args[0]]=args[1];return clone(store);}
   if(method==='set_music_choice'||method==='music_choose'){store.music_choices={...store.music_choices,'42':args[1]};return {ok:true,settings:clone(store)};}
   if(method==='music_current')return store.music_choices['42']||'auto';
   if(method==='music_search')return [];
   if(method==='get_music_files'){const snapshot=files();return deferFiles?new Promise(r=>pendingFiles.push(()=>r(snapshot))):snapshot;}
   if(method==='refresh_music'||method==='refresh_media'){prepares++;filesReady=true;return {ok:true};}
   if(method==='get_deck_music_status')return {state:'ready',runtime:{ready:true}};
   if(method==='get_card_preferences')return {};
   if(method==='get_pc_media_status')return {music:{file:'media/42_theme.m4a'}};
   if(method==='themes_list')return [];
   if(method==='sgdb_status')return {};
   if(method==='get_card_fields')return [];
   throw Error('Unexpected fixture call: '+method);
 },localizedCall:async()=>[]};
vm.createContext(context);
vm.runInContext(slice(bundle,'// Standalone Deck additions.','\nfunction QamContent()'),context);
if(platform==='pc'){
 vm.runInContext(slice(controls,'useStandaloneMusic = function','\nfunction '),context);
 vm.runInContext(slice(settingsSource,'const PC_SETTINGS_TEXT','\nfunction usePcPlaytimeVisibility'),context);
 vm.runInContext(slice(settingsSource,'async function publishPcSettings','\nasync function enablePcMusic'),context);
 vm.runInContext(settingsSource.slice(settingsSource.indexOf('function PcSettings({')),context);
 vm.runInContext(slice(controls,'const MUSIC_KINDS','\nfunction openMusicPicker'),context);
}
const flush=async()=>{for(let i=0;i<30;i++)await Promise.resolve();};
async function advance(ms){const end=now+ms;while(true){let id=null,at=Infinity;for(const[k,t]of timers)if(t.at<at){id=k;at=t.at;}if(at>end)break;now=at;const t=timers.get(id);if(t.ms)t.at+=t.ms;else timers.delete(id);t.fn();await flush();}now=end;await flush();}
function nodes(tree,predicate){const out=[];function visit(n){if(!n||typeof n!=='object')return;if(predicate(n))out.push(n);for(const c of n.children||[])if(Array.isArray(c))c.forEach(visit);else visit(c);}visit(tree);return out;}
let props=clone(store);
const player=new Host(()=>context.useStandaloneMusic(42,props,{}));
const ui=new Host(()=>platform==='deck'?context.DeckMusicSection():context.PcSettings({initialSection:'music'}));
let picker=new Host(()=>context.MusicPicker({appid:42,name:'Fixture',closeModal:noop}));
async function uiReady(){ui.render();await flush();ui.render();}
async function volume(v){await uiReady();let n;
 if(platform==='deck'){n=nodes(ui.tree,n=>n.props?.label==='Music volume')[0];assert(n,'QAM volume');await n.props.onChange({data:v*100});}
 else {n=nodes(ui.tree,n=>n.children?.[0]===v*100+'%'&&typeof n.props?.onClick==='function')[0];assert(n,'PC volume');await n.props.onClick();}
 await flush();
}
async function choice(v){
 if(platform==='deck'){await uiReady();const n=nodes(ui.tree,n=>n.props?.label==='This game')[0];assert(n,'QAM choice');await n.props.onChange({data:v});}
 else {picker.unmount();picker=new Host(()=>context.MusicPicker({appid:42,name:'Fixture',closeModal:noop}));picker.render();await flush();picker.render();const n=nodes(picker.tree,n=>n.props?.key===v)[0];assert(n,'PC choice');await n.props.onClick();}
 await flush();
}
async function main(){
 if(scenario==='pending_job'){
  let interested=true,polls=0;const original=context.call;
  context.call=async(method,...args)=>method==='refresh_music'?{pending:true,job:'fixture'}:method==='music_job_status'?(polls++,{done:false}):original(method,...args);
  const task=context.prepareDeckTheme(42,'Fixture',false,()=>interested);await flush();assert.equal(polls,1);
  interested=false;await advance(2200);assert.equal(polls,1,'cancelled preparation must stop polling');
  const result=await task;assert(result.cancelled||result.error==='cancelled');assert.equal(context.sourceListeners.size,0);
  console.log(JSON.stringify({platform,scenario,status:'PASS',polls}));return;
 }
 player.render();await flush();await advance(1800);
 const first=audios[0];assert(first&&!first.paused,'initial audio plays');
 if(scenario==='volume'){
  await volume(0);await advance(240);assert.equal(store.music_volume,0);assert.equal(first.volume,0,'live QAM/PC volume must become zero within 1s');
  await volume(.4);await advance(240);assert.equal(first.volume,.4);assert.equal(audios.length,1,'volume keeps same element');assert.equal(first.currentTime,17);
 } else if(scenario==='none_auto'){
  deferFiles=true;await choice('none');assert(first.paused,'none pauses current audio without waiting for another file-list RPC');deferFiles=false;pendingFiles.splice(0).forEach(f=>f());await advance(2500);assert(first.paused);
  await choice('auto');await advance(800);assert(audios.some(a=>!a.paused&&!a.removed),'auto resumes open card');
 } else if(scenario==='pending'){
  player.unmount();await advance(700);deferFiles=true;player.render();await flush();assert(pendingFiles.length);
  await choice('none');deferFiles=false;pendingFiles.splice(0).forEach(f=>f());await flush();await advance(2000);
  assert(audios.every(a=>a.paused),'late get_music_files must not revive disabled player');
 } else if(scenario==='remount'){
  for(let i=0;i<20;i++){player.unmount();await advance(700);player.render();await flush();assert.equal(context.settingsListeners.size,1,'exactly one player settings listener');assert.equal(context.sourceListeners.size,1,'one source listener');}
  player.unmount();await advance(700);assert.equal(context.settingsListeners.size,0);assert.equal(context.sourceListeners.size,0);assert.equal(timers.size,0);
 } else if(scenario==='auto_prepare'){
  await choice('none');filesReady=false;const n=prepares;await choice('auto');await advance(800);
  assert(prepares>n,'auto prepares missing theme');assert(audios.some(a=>!a.paused&&!a.removed),'prepared theme starts without navigation');
 } else if(scenario==='stale_props'){
  await volume(0);player.render();await advance(240);assert.equal(first.volume,0,'unrelated render must not overwrite bus settings');
  props=clone(store);props.music_volume=.8;player.render();await advance(240);assert.equal(first.volume,.8,'props use same apply callback');assert.equal(audios.length,1);
 } else if(scenario==='source'){
  context.sourceListeners.forEach(f=>f(42));await flush();assert.equal(audios.length,1,'same source keeps player');await choice('none');context.sourceListeners.forEach(f=>f(42));await flush();assert(audios.every(a=>a.paused));
 } else throw Error(scenario);
 player.unmount();ui.unmount();picker.unmount();await advance(700);
 assert.equal(context.settingsListeners.size,0);assert.equal(context.sourceListeners.size,0);assert.equal(events.size,0);
 console.log(JSON.stringify({platform,scenario,status:'PASS',audio_elements:audios.length,settings_listeners:context.settingsListeners.size,virtual_ms:now}));
}
main().catch(e=>{console.error(e);process.exitCode=1;});
