from pathlib import Path
import importlib.util
import shutil
import subprocess

BASE=Path(__file__).resolve().parents[2]

def run_js(tmp_path, source, test):
    path=tmp_path/'test.cjs'
    path.write_text(source+'\n'+test,encoding='utf-8')
    result=subprocess.run(['node',str(path)],capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stdout+result.stderr

def test_busy_retries_only_while_current(tmp_path):
    source=(BASE/'plugin/assets/deck_music.js').read_text(encoding='utf-8')
    source=source[source.index('async function resolveDeckMusicJob('):source.index('function DeckMusicSection(')]
    run_js(tmp_path,source,r'''
const assert=require('node:assert/strict');let calls=0,current=true,notified=0;
const sourceListeners=[()=>notified++];global.setTimeout=f=>(f(),1);
async function call(){calls++;return calls===1?{ok:false,deferred:'busy'}:{ok:true};}
(async()=>{assert.equal((await prepareDeckTheme(2,'B',false,()=>current)).ok,true);assert.equal(calls,2);assert.equal(notified,1);
calls=0;current=false;await prepareDeckTheme(3,'C',false,()=>current);assert.equal(calls,0);})();
''')

def test_home_aba_disposes_every_audio(tmp_path):
    text=(BASE/'plugin/dist/index.js').read_text(encoding='utf-8')
    source=text[text.index('function patchHomeLive() {'):text.index('let unpatchHomeLive = null;')]
    # Execute the production closure with its actual timers and async boundaries.
    source=source.replace('  window.__ghHomeLive =', '  window.testHome={playMusic,stopMusic,setCurrent:id=>cur=id,setDoc:d=>doc=d,setSettings:s=>settings=s};\n  window.__ghHomeLive =')
    run_js(tmp_path,source,r'''
const assert=require('node:assert/strict');const window={};const settingsListeners=new Set();const IS_LINUX=true,DATA='fixture/',pending=[],audios=[];
const continueMusicAllowed=()=>true,uiBusy=()=>false,seekResume=()=>{},log=()=>{};
function createDeckMusicPlayer(doc,url){const audio={volume:0,pause(){},removeAttribute(){},remove(){this.removed=true}};audios.push(audio);return {audio,close(){audio.removed=true}};}
const timers=new Map();let seq=0;global.setTimeout=f=>{timers.set(++seq,f);return seq};global.clearTimeout=id=>timers.delete(id);global.setInterval=()=>1;global.clearInterval=()=>{};
const prepareDeckTheme=(id,n,f,alive)=>new Promise(resolve=>pending.push({resolve,alive}));
const call=async()=>({'1':'one.m4a','2':'two.m4a'});
const flush=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{const unload=patchHomeLive(),h=window.testHome;h.setDoc({body:{}});h.setSettings({standalone:true});
h.setCurrent('1');h.playMusic('1');await [...timers.values()].pop()();
})();
'''.replace("await [...timers.values()].pop()();", "const a=[...timers.values()].pop()(); h.setCurrent('2');h.playMusic('2'); const b=[...timers.values()].pop()(); h.setCurrent('1');h.playMusic('1'); const c=[...timers.values()].pop()(); pending[2].resolve();await c;pending[0].resolve();await a;pending[1].resolve();await b;assert.equal(audios.length,1);for(const f of settingsListeners)f({standalone:true,home_music:true,theme_music_consent:true,music_volume:.8});assert.equal(audios.length,1);assert.ok(!audios[0].removed);unload();assert.ok(audios.every(a=>a.removed));assert.equal(settingsListeners.size,0);"))

def test_pc_late_play_cleanup_and_busy(tmp_path):
    text=(BASE/'pc/bp_public_controls.js').read_text(encoding='utf-8');source=text[text.index('useStandaloneMusic = function('):]
    shared=(BASE/'plugin/assets/deck_music.js').read_text(encoding='utf-8')
    source=shared[shared.index('function createDeckMusicPlayer('):shared.index('if(IS_LINUX)useStandaloneMusic=useDeckMusic;')]+source
    run_js(tmp_path,source,r'''
const assert=require('node:assert/strict');let cleanup,busy=false;const pending=[],audios=[],timers=new Map();let seq=0,now=0;
global.setInterval=f=>(timers.set(++seq,f),seq);global.clearInterval=id=>timers.delete(id);Date.now=()=>now;
var useStandaloneMusic;const cleanups=[];function useEffect(f){const c=f();if(c)cleanups.push(c);cleanup=()=>{cleanups.splice(0).forEach(x=>x());};}const useRef=v=>({current:v}),settingsListeners=new Set(),sourceListeners=new Set(),IS_LINUX=false;const continueMusicAllowed=()=>true,pcBusy=()=>busy,uiBusy=()=>busy,seekResume=()=>{},notePos=()=>{},DATA='fixture/';
const doc={body:{appendChild(){}},createElement(){const a={volume:0,paused:true,dataset:{},play(){return new Promise(resolve=>pending.push(()=>{this.paused=false;resolve()}))},pause(){this.paused=true},removeAttribute(){},load(){},remove(){this.removed=true}};audios.push(a);return a;}};
const window={SteamUIStore:{WindowStore:{GamepadUIMainWindowInstance:{BrowserWindow:{document:doc}}}}};const uiDocument=()=>doc,call=async()=>({'1':'one.m4a'});const flush=()=>new Promise(resolve=>setImmediate(resolve));
const advance=()=>{now+=3000;for(const f of [...timers.values()])f();};
(async()=>{useStandaloneMusic(1,{standalone:true,theme_music_consent:true},0);await flush();cleanup();pending.shift()();await flush();advance();assert.ok(audios[0].paused&&audios[0].removed,'late play must not cancel disposal');
useStandaloneMusic(1,{standalone:true,theme_music_consent:true},0);await flush();busy=true;advance();pending.shift()();await flush();advance();assert.ok(audios[1].paused,'late play must not bypass busy');cleanup();advance();assert.equal(timers.size,0);})();
''')
