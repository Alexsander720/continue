// Execute the shipped standalone PC controls with native UI stubs and no Steam.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const pc=path.resolve(__dirname,'../../pc');
let modal;
const manager={fixture:true},win={BrowserWindow:{document:{}},m_ModalManager:manager};
const h=(type,props,...children)=>({type,props:{...props,children}});
const context=vm.createContext({URL,Map,Set,Date,console,
  I18N:{en:{},ru:{},uk:{}},LANGUAGE:'en',React:{Fragment:'fragment'},h,
  t(key){return context.I18N[context.LANGUAGE][key]||key;},
  Icon:()=>null,fitBar:()=>42,useAchievements:()=>({got:1,total:2}),useStandaloneMusic:()=>{},HubAppButtons:()=>null,
  __PC_ICON_NAMES__:fs.readdirSync(path.resolve(__dirname,'../../plugin/assets/icons')).filter(n=>n.endsWith('.svg')).map(n=>n.slice(0,-4)),
  currentAppId:()=>42,DFL:{Focusable:'NativeFocus',ModalRoot:'NativeModal',showModalRaw(...args){modal=args;}},
  window:{SteamUIStore:{WindowStore:{GamepadUIMainWindowInstance:win}},appStore:{GetAppOverviewByAppID:()=>({display_name:'Fixture'})}},
  __PC_GLYPHS__:JSON.parse(fs.readFileSync(path.join(pc,'assets/glyphs.json'),'utf8')),__PC_GAME_STYLES__:{},
  setTimeout(fn){fn();},clearTimeout(){},log(){},DATA:'http://127.0.0.1/',
});
vm.runInContext(fs.readFileSync(path.join(pc,'bp_public_controls.js'),'utf8'),context);
for(const name of ['openArtPicker','openMusicPicker','openThemes']) {
  vm.runInContext(name+'(42)',context);
  assert.equal(modal[6],manager,'Control must use the native Big Picture modal manager');
}
const walk=x=>Array.isArray(x)?x.flatMap(walk):x?.props?[x,...walk(x.props.children)]:[];
const buttons=walk(vm.runInContext('HubAppButtons()',context)).filter(x=>x.props.role==='button');
assert.equal(buttons.length,2);assert.ok(buttons.every(x=>typeof x.props.onActivate==='function'&&x.props.onActivate===x.props.onClick));
context.summary={nAchieved:1,vecHighlight:[{strID:'A',strName:'Fixture',bAchieved:true,rtUnlocked:100}]};
assert.equal(vm.runInContext('pcLatestAchievement(summary).name',context),'Fixture');
context.summary.nAchieved=2;assert.equal(vm.runInContext('pcLatestAchievement(summary)',context),null);
for(const lang of ['en','ru','uk']) {
  context.LANGUAGE=lang;
  for(const key of ['pc_art','pc_music','pc_themes','pc_key_setup','pc_music_setup']) assert.ok(context.t(key)!==key);
}
console.log('Public PC native controls and conservative achievement history passed');
