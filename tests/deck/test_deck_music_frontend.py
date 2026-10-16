"""Run the production audio controller against a DOM/audio boundary fixture."""
from pathlib import Path
import subprocess


def test_audio_obeys_volume_visibility_game_suspend_and_cleans_up(tmp_path):
    source=(Path(__file__).resolve().parents[2]/'plugin/assets/deck_music.js').read_text(encoding='utf-8')
    start=source.index('function createDeckMusicPlayer(')
    end=source.index('\nfunction useDeckMusic(',start)
    script=source[start:end]+r'''
const assert=require('node:assert/strict');
let busy=false,suspended=false,playing=0,paused=0,removed=0;
const events={};const doc={visibilityState:'visible',addEventListener:(k,f)=>events[k]=f,removeEventListener:k=>delete events[k],body:{appendChild:()=>{}},createElement:()=>({volume:0,paused:true,play(){playing++;this.paused=false;return Promise.resolve()},pause(){paused++;this.paused=true},removeAttribute(){},load(){},remove(){removed++}})};
let tick;let resume,suspend;let regs=0;
global.setInterval=f=>(tick=f,1);global.clearInterval=()=>{};
const api={RegisterForPrepareForSystemSuspendProgress:f=>(suspend=f,regs++,{unregister(){regs--}}),RegisterForResumeSuspendedGamesProgress:f=>(resume=f,regs++,{unregister(){regs--}})};
const p=createDeckMusicPlayer(doc,'fixture.m4a',.2,()=>busy,api);
assert.equal(playing,1);assert.equal(p.audio.volume,.2);
busy=true;tick();assert.equal(p.audio.paused,true);
busy=false;tick();assert.equal(p.audio.paused,false);
doc.visibilityState='hidden';events.visibilitychange();assert.equal(p.audio.paused,true);
doc.visibilityState='visible';events.visibilitychange();assert.equal(p.audio.paused,false);
suspend();assert.equal(p.audio.paused,true);resume();assert.equal(p.audio.paused,false);
p.close();assert.equal(removed,1);assert.equal(regs,0);assert.equal(events.visibilitychange,undefined);
'''
    path=tmp_path/'audio.cjs';path.write_text(script,encoding='utf-8')
    result=subprocess.run(['node',str(path)],capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stderr


def test_volume_does_not_restart_track_and_late_play_cannot_escape_cleanup(tmp_path):
    text=(Path(__file__).resolve().parents[2]/'plugin/assets/deck_music.js').read_text(encoding='utf-8')
    source=text[text.index('function createDeckMusicPlayer('):text.index('if(IS_LINUX)useStandaloneMusic=useDeckMusic;')]
    script=source+r'''
const assert=require('node:assert/strict');let now=0,ri=0,ei=0;const refs=[],effects=[],audios=[],pending=[],timers=new Map();let tid=0;
Date.now=()=>now;global.setInterval=f=>(timers.set(++tid,f),tid);global.clearInterval=id=>timers.delete(id);
const useRef=v=>refs[ri++]||(refs[ri-1]={current:v});
function useEffect(f,deps){const i=ei++,old=effects[i];if(!old||deps.some((v,j)=>v!==old.deps[j])){old?.cleanup?.();effects[i]={deps,cleanup:f()};}}
const doc={visibilityState:'visible',addEventListener(){},removeEventListener(){},body:{appendChild(){}},createElement(){const a={volume:0,paused:true,currentTime:0,play(){return new Promise(resolve=>pending.push(()=>{a.paused=false;resolve()}))},pause(){a.paused=true},removeAttribute(){},load(){},remove(){a.removed=true}};audios.push(a);return a;}};
const window={},DATA='fixture/',uiBusy=()=>false,uiDocument=()=>doc,continueMusicAllowed=()=>true,seekResume=()=>{},call=async()=>({'1':'theme.m4a'});
const sourceListeners=new Set(),settingsListeners=new Set();
const flush=()=>new Promise(r=>setImmediate(r));function render(volume){ri=ei=0;useDeckMusic(1,{standalone:true,hub_music:true,theme_music_consent:true,music_volume:volume},{loop:'same-file.mp4'});}
(async()=>{render(.4);await flush();pending.shift()();await flush();audios[0].currentTime=17;render(.8);now+=250;for(const f of [...timers.values()])f();
assert.equal(audios.length,1);assert.equal(audios[0].currentTime,17);assert.equal(audios[0].volume,.8);
effects[0].cleanup();now+=700;for(const f of [...timers.values()])f();assert.ok(audios[0].removed);assert.equal(timers.size,0);
const p=createDeckMusicPlayer(doc,'late',.4,()=>false);p.close();pending.shift()();await flush();assert.ok(p.audio.paused&&p.audio.removed);assert.equal(timers.size,0);})();
'''
    path=tmp_path/'volume.cjs';path.write_text(script,encoding='utf-8')
    result=subprocess.run(['node',str(path)],capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stderr
