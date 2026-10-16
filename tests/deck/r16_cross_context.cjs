// Actual native BroadcastChannel is the only frontend transport between two VMs.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {BroadcastChannel:NativeChannel}=require('node:worker_threads');
const [root,platform,scenario]=process.argv.slice(2),channels=new Set();
const base=fs.readFileSync(__dirname+'/r15_live_settings.cjs','utf8').split('async function main(){')[0];
const shared={standalone:true,theme_music_consent:true,hub_music:true,home_music:true,music_volume:.4,music_choices:{}};
const clone=x=>JSON.parse(JSON.stringify(x));
let settingsReads=0;
function fixture(stale=false){
 const outer={require,console,process:{argv:['node','fixture',root,platform,stale||'fixture']},globalThis:null};outer.globalThis=outer;
 vm.createContext(outer);
 const source=base.replace('await n.props.onChange({data:v*100});',"if(scenario==='stale_qam')ui.unmount();await n.props.onChange({data:v*100});")
  .replace("await n.props.onChange({data:v});","if(scenario==='stale_qam')ui.unmount();await n.props.onChange({data:v});")
  .replaceAll('await n.props.onClick();',"const pending=n.props.onClick();if(scenario==='stale_picker')picker.unmount();await pending;");
 vm.runInContext(source+'\nglobalThis.fixture={context,player,ui,picker,advance,volume,choice,audios,timers,events,flush};',outer);
 const f=outer.fixture,original=f.context.call;
 f.context.BroadcastChannel=class extends NativeChannel{
  constructor(name){super(name);channels.add(this);}
  close(){channels.delete(this);return super.close();}
 };
 f.context.call=async(method,...args)=>{
  if(method==='get_settings'){settingsReads++;return clone(shared);}
  if(method==='set_setting'){shared[args[0]]=args[1];return clone(shared);}
  if(method==='set_music_choice'||method==='music_choose'){shared.music_choices={...shared.music_choices};if(args[1]==='auto')delete shared.music_choices[args[0]];else shared.music_choices[args[0]]=args[1];return {ok:true,settings:clone(shared)};}
  if(method==='get_music_files')return shared.music_choices['42']==='none'?{}:{'42':'media/42_theme.m4a'};
  return original(method,...args);
 };
 return f;
}
const turn=()=>new Promise(r=>setImmediate(r));
async function delivered(){for(let i=0;i<8;i++)await turn();}
async function main(){
 const sameRealm=scenario==='stale_qam'||scenario==='stale_picker';
 const publisher=fixture(sameRealm?scenario:false),receiver=sameRealm?publisher:fixture();
 if(!sameRealm){assert.notEqual(publisher.context.settingsListeners,receiver.context.settingsListeners,'separate VMs cannot share listeners');assert.notEqual(publisher.context.window,receiver.context.window);}
 receiver.player.render();await receiver.flush();await receiver.advance(1800);
 const first=receiver.audios[0];assert(first&&!first.paused);
 if(scenario==='volume'||scenario==='stale_qam'){
  for(const v of [0,1,.2,.4]){
   await publisher.volume(v);await delivered();await receiver.advance(240);
   assert(Math.abs(first.volume-v)<1e-10,'persisted setting must reach same audio from '+scenario+'; actual='+first.volume+' expected='+v);
   assert.equal(receiver.audios.length,1,'volume must retain the audio element');
  }
 }else if(scenario==='none_auto'||scenario==='stale_picker'){
  await publisher.choice('none');await delivered();await receiver.advance(240);assert(first.paused&&first.removed,'None stops/removes remote audio');
  await publisher.choice('auto');await delivered();await receiver.advance(800);assert(receiver.audios.some(a=>!a.paused&&!a.removed),'Auto starts open remote card');
 }else if(scenario==='remount'){
  for(let i=0;i<20;i++){receiver.player.unmount();await receiver.advance(700);receiver.player.render();await receiver.flush();}
  assert.equal(channels.size,1,'one receiver channel after remounts');
  const reads=settingsReads;await receiver.advance(10000);assert.equal(settingsReads,reads,'event transport must not poll backend');
 }else throw Error(scenario);
 receiver.player.unmount();receiver.ui.unmount();publisher.ui.unmount();publisher.picker.unmount();await receiver.advance(700);
 assert.equal(channels.size,0,'all channels close on unmount');
 assert.equal(receiver.context.settingsListeners.size,0);assert.equal(receiver.context.sourceListeners.size,0);assert.equal(receiver.timers.size,0);
 console.log(JSON.stringify({platform,scenario,status:'PASS',isolated_vms:sameRealm?1:2,transport:'native BroadcastChannel',settings_reads:settingsReads,polling_reads:0,channels_remaining:channels.size}));
}
main().catch(e=>{console.error(e);for(const c of channels)c.close();process.exitCode=1;});
