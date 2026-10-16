const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
const context=vm.createContext({console,URL,encodeURIComponent,Map,Set,
  I18N:{en:{},ru:{},uk:{}},Icon:()=>null,fitBar:()=>{},useAchievements:()=>{},useStandaloneMusic:()=>{},HubAppButtons:()=>{},
  __PC_ICON_NAMES__:[],DATA:'/',h:(type,props,...children)=>({type,props:{...props,children}}),
  React:{Fragment:'fragment'},DFL:{Focusable:'focus',ModalRoot:'modal'},LANGUAGE:'en',
  livePolicy:()=>{},refreshMediaLatest:()=>{},startupMovieOn:()=>false,currentAppId:()=>42,
  window:{appStore:{GetAppOverviewByAppID:()=>({display_name:'Fixture'})}},
});
vm.runInContext(fs.readFileSync(path.join(root,'pc/bp_public_controls.js'),'utf8'),context);
vm.runInContext(fs.readFileSync(process.env.R19_SETTINGS_SOURCE||path.join(root,'pc/bp_public_settings.js'),'utf8'),context);
for(const family of ['xbox','playstation','steam']) {
  for(const source of ['xbox_button_a','xbox_button_b','xbox_button_x','xbox_button_y','ps_button_x','ps_button_circle','ps_button_square','ps_button_triangle','xbox_button_start','xbox_button_back','xbox_button_lb','xbox_button_rb','xbox_button_lt','xbox_button_rt']) {
    context.source='https://steamloopback.host/steaminputglyphs/'+source+'.svg';context.family=family;
    const data=vm.runInContext('pcControllerGlyph(source,family)',context);
    assert.ok(data?.startsWith('data:image/svg+xml,'),family+' '+source);
    const svg=decodeURIComponent(data.split(',')[1]);assert.ok(svg.includes('<svg'));assert.ok(!/<text|<image|font|https?:/.test(svg.replace('http://www.w3.org/2000/svg','')));
  }
}
assert.notEqual(vm.runInContext('pcControllerGlyph(source,"xbox")',context),vm.runInContext('pcControllerGlyph(source,"playstation")',context));
assert.equal(vm.runInContext('pcControllerGlyph("https://example.org/art/a.svg","xbox")',context),null);
assert.equal(vm.runInContext('pcControllerGlyph(source,"native")',context),null);
for(const [xbox,ps]of [['a','x'],['b','circle'],['x','square'],['y','triangle']]){
  context.xboxSource='https://steamloopback.host/steaminputglyphs/xbox_button_'+xbox+'.svg';context.psSource='https://steamloopback.host/steaminputglyphs/ps_button_'+ps+'.svg';
  assert.equal(vm.runInContext('pcControllerGlyph(xboxSource,"playstation")',context),vm.runInContext('pcControllerGlyph(psSource,"playstation")',context),'Physical face-button correspondence');
}
const original='https://steamloopback.host/steaminputglyphs/xbox_button_a.svg';
const img={src:original,isConnected:true,getAttribute(){return null;}};
context.uiDocument=()=>({querySelectorAll:()=>[img]});context.pluginSettings={pc_glyphs:'xbox'};
vm.runInContext('pcRefreshControllerGlyphs()',context);assert.ok(img.src.startsWith('data:'));
const xbox=img.src;context.pluginSettings.pc_glyphs='playstation';vm.runInContext('pcRefreshControllerGlyphs()',context);assert.notEqual(img.src,xbox);
context.pluginSettings.pc_glyphs='native';vm.runInContext('pcRefreshControllerGlyphs()',context);assert.equal(img.src,original);
context.pluginSettings.pc_glyphs='steam';vm.runInContext('pcRefreshControllerGlyphs();pcRefreshControllerGlyphs(true)',context);assert.equal(img.src,original);
// A JSX-replaced image may precede the first timer tick. Switching back to
// Steam must restore it even though it has not entered the DOM fallback map.
img.src=xbox;img.getAttribute=()=>original;context.pluginSettings.pc_glyphs='native';
vm.runInContext('pcRefreshControllerGlyphs()',context);assert.equal(img.src,original);
img.src=xbox;vm.runInContext('pcRefreshControllerGlyphs(true)',context);assert.equal(img.src,original,'Unload restores a glyph before the first timer tick');
// Steam reuses an img when the footer's action changes from A to B.
img.getAttribute=()=>null;img.src=original;context.pluginSettings.pc_glyphs='playstation';
vm.runInContext('pcRefreshControllerGlyphs()',context);
const buttonB='https://steamloopback.host/steaminputglyphs/xbox_button_b.svg';
img.src=buttonB;context.source=buttonB;vm.runInContext('pcRefreshControllerGlyphs()',context);
assert.equal(img.src,vm.runInContext('pcControllerGlyph(source,"playstation")',context),'Reused native image updates its button');
context.pluginSettings.pc_glyphs='native';vm.runInContext('pcRefreshControllerGlyphs()',context);assert.equal(img.src,buttonB);
img.getAttribute=()=>null;img.src=original;context.pluginSettings.pc_glyphs='playstation';
vm.runInContext('pcRefreshControllerGlyphs()',context);
const unmapped='https://steamloopback.host/steaminputglyphs/xbox_button_logo.svg';img.src=unmapped;
vm.runInContext('pcRefreshControllerGlyphs()',context);assert.equal(img.src,unmapped,'An unmapped Steam replacement must stay untouched');
context.pluginSettings.pc_glyphs='native';vm.runInContext('pcRefreshControllerGlyphs()',context);assert.equal(img.src,unmapped);
let marked=original;img.getAttribute=()=>marked;img.setAttribute=(_,value)=>{marked=value;};
img.src=original;context.pluginSettings.pc_glyphs='playstation';vm.runInContext('pcRefreshControllerGlyphs()',context);
img.src=buttonB;vm.runInContext('pcRefreshControllerGlyphs();pcRefreshControllerGlyphs()',context);
assert.equal(img.src,vm.runInContext('pcControllerGlyph(source,"playstation")',context),'Stale JSX provenance is updated, including the next timer tick');
context.pluginSettings.pc_glyphs='native';vm.runInContext('pcRefreshControllerGlyphs()',context);assert.equal(img.src,buttonB);
// Render the shipped settings component with deterministic hooks, using source
// fields even when a preference has hidden the row from the final game card.
const walk=x=>Array.isArray(x)?x.flatMap(walk):x?.props?[x,...walk(x.props.children)]:[];
let section='card',fields=[],settings={disk_limit_gb:64,pc_glyphs:'playstation'},index=0;
context.useLanguage=()=>{};context.useEffect=()=>{};context.useRef=()=>({current:true});
context.useState=()=>{const values=[section,'global',settings,{global:{},effective:{}},fields,null,[],null,'',false,null,false];return [values[index++],()=>{}];};
context.startupMovieOn=()=>false;context.t=k=>k;context.psSection=()=>section;
function render(){index=0;return walk(vm.runInContext('PcSettings({closeModal(){}})',context));}
function hasText(nodes,text){return nodes.some(n=>n.props.children.includes(text));}
assert.equal(hasText(render(),'Characters and survival'),false);
fields=[{id:'people',label:'Alive',has_characters:true,visible:false}];
assert.equal(hasText(render(),'Characters and survival'),true);
section='backgrounds';fields=[];
assert.ok(hasText(render(),'64 GB'));
section='appearance';context.setStartupMovie=()=>{};context.openThemes=()=>{};
const nodes=render();for(const name of ['Xbox','PlayStation','Steam Deck / Steam Controller','Continue? style','Steam default'])assert.ok(hasText(nodes,name),name);
for(const lang of ['ru','uk']){context.LANGUAGE=lang;section='backgrounds';assert.ok(hasText(render(),'64 ГБ'));}context.LANGUAGE='en';
const suffix=fs.readFileSync(path.join(root,'pc/bp_suffix.js'),'utf8');
vm.runInContext(suffix.slice(suffix.indexOf('const PAD_PS'),suffix.indexOf('// Страница игры')),context);
vm.runInContext(suffix.slice(suffix.indexOf('const PS_TYPES'),suffix.indexOf('const HOME_TABS')),context);
context.originalGlyph={controllerType:1,controllerSource:2,controllerModeInput:3};
for(const [family,expected]of [['owner',45],['playstation',1],['native',1],['owner',45],['native',1]]){
  context.useState=()=>[{pc_glyphs:family},()=>{}];
  assert.equal(vm.runInContext('PcControllerSymbols({component:"NativeGlyph",original:originalGlyph}).props.controllerType',context),expected,'Mode changes rerender from true original controller props');
  assert.equal(context.originalGlyph.controllerType,1);
}
context.pluginSettings={pc_pads:'steam'};context.kids=[{type:{prototype:{render(){return null;}}},props:{feature:1}},{type:{prototype:{render(){return 'actual support';}}},props:{feature:16}}];
assert.equal(vm.runInContext('pcPadIcons(kids).length',context),1,'Unsupported facts stay absent');
// The actual Steam support component remains the child, preserving its tooltip.
assert.equal(vm.runInContext('pcPadIcons(kids)[0].props.children[0].props.children[0]===kids[1]',context),true);
context.useState=()=>[{pc_pads:'native'},()=>{}];
assert.equal(vm.runInContext('PcSupportFeatures({kids}).props.children.length',context),2,'Steam default retains every native support fact');
context.useState=()=>[{pc_pads:'xbox'},()=>{}];
assert.equal(vm.runInContext('PcSupportFeatures({kids}).props.children.length',context),1,'Manual style respects actual support');
context.settingsListeners=new Set();context.visualStates=[];
context.visualListener=value=>context.visualStates.push(value);
vm.runInContext('pcSubscribeVisualSettings(visualListener);pcRestoreVisualSettings()',context);
assert.equal(context.settingsListeners.size,0,'Unload detaches mounted visual subscribers without host unmount');
assert.equal(context.visualStates[0].pc_glyphs,'native');assert.equal(context.visualStates[0].pc_pads,'native');
console.log('PASS R19 frontend: 42 glyph mappings; source-field visibility; 64 GB; five choices');
