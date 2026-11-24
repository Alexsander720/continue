const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),pack=path.join(root,'pc/assets/controller_glyphs');
const manifest=JSON.parse(fs.readFileSync(path.join(pack,'manifest.json'),'utf8'));
const glyphs=Object.fromEntries(Object.entries(manifest.sets).map(([family,buttons])=>[family,Object.fromEntries(Object.entries(buttons).map(([key,file])=>[key,'data:image/svg+xml,'+encodeURIComponent(fs.readFileSync(path.join(pack,file),'utf8'))]))]));
const c=vm.createContext({console,URL,Map,Set,encodeURIComponent,__PC_CONTROLLER_GLYPHS__:glyphs,
  I18N:{en:{},ru:{},uk:{}},Icon(){},fitBar(){},useAchievements(){},useStandaloneMusic(){},HubAppButtons(){},__PC_ICON_NAMES__:[],
  React:{Fragment:'fragment'},DFL:{Focusable:'focus',ModalRoot:'modal'},LANGUAGE:'en',DATA:'/',h:(type,props,...children)=>({type,props:{...props,children}})});
for(const name of ['bp_public_controls.js','bp_public_settings.js'])vm.runInContext(fs.readFileSync(path.join(root,'pc',name),'utf8'),c);
const run=s=>vm.runInContext(s,c),source=key=>'https://steamloopback.host/steaminputglyphs/xbox_'+(key.startsWith('dpad_')?'':'button_')+key+'.svg';
let count=0;
for(const family of Object.keys(glyphs)){
  for(const key of ['a','b','x','y','back','start','lb','rb','lt','rt','dpad_up','dpad_down','dpad_left','dpad_right']){
    c.source=source(key);c.family=family;
    assert.equal(run('pcControllerGlyph(source,family)'),glyphs[family][key.replace('dpad_','')]);count++;
  }
  for(const [a,b]of [['a','x'],['b','circle'],['x','square'],['y','triangle']]){
    c.source=source(a);c.ps='https://steamloopback.host/steaminputglyphs/ps5_button_'+b+'.svg';
    assert.equal(run('pcControllerGlyph(source,family)'),run('pcControllerGlyph(ps,family)'));
  }
}
for(const url of ['https://example.org/steaminputglyphs/xbox_button_a.svg','https://steamloopback.host/steaminputglyphs/xbox_button_logo.svg','https://user@steamloopback.host/steaminputglyphs/xbox_button_a.svg','file://steamloopback.host/steaminputglyphs/xbox_button_a.svg']){
  c.source=url;assert.equal(run('pcControllerGlyph(source,"xbox")'),null);
}
const original=source('a');let attr=null;
const img={src:original,isConnected:true,getAttribute(){return attr;},setAttribute(_,v){attr=v;}};
c.uiDocument=()=>({querySelectorAll:()=>[img]});c.pluginSettings={pc_glyphs:'xbox'};
for(const family of [...Object.keys(glyphs),'native','owner']){
  c.pluginSettings.pc_glyphs=family;run('pcRefreshControllerGlyphs()');
  assert.equal(img.src,glyphs[family]?.a||original);
}
// JSX provenance survives switching before the fallback map's first tick.
attr=original;img.src=glyphs.dualshock.a;c.pluginSettings.pc_glyphs='steam_controller';run('pcRefreshControllerGlyphs()');assert.equal(img.src,glyphs.steam_controller.a);
run('pcRefreshControllerGlyphs(true)');assert.equal(img.src,original);
for(const lang of ['en','ru','uk']){
  c.LANGUAGE=lang;const choices=run('pcControllerChoices()');
  assert.deepEqual(Array.from(choices,x=>x[0]),['owner','native','xbox','playstation','dualshock','steam','steam_controller']);
  assert.ok(choices[3][1].includes('DualSense'));assert.ok(choices[4][1].includes('DualShock'));
  assert.notEqual(choices[3][1],choices[4][1]);
}
// Render the actual settings component, preserving its 32px preview sizing.
const walk=x=>Array.isArray(x)?x.flatMap(walk):x?.props?[x,...walk(x.props.children)]:[];
let selected='xbox',index=0;c.LANGUAGE='en';c.useLanguage=()=>{};c.useEffect=()=>{};c.useRef=()=>({current:true});
c.currentAppId=()=>42;c.window={appStore:{GetAppOverviewByAppID:()=>({display_name:'Fixture'})}};c.startupMovieOn=()=>false;c.setStartupMovie=()=>{};c.openThemes=()=>{};c.t=k=>k;c.psSection=()=> 'appearance';
c.useState=()=>{const values=['appearance','global',{pc_glyphs:selected},{global:{},effective:{}},[],null,[],null,'',false,null,false];return [values[index++],()=>{}];};
for(const family of Object.keys(glyphs)){
  selected=family;index=0;const nodes=walk(run('PcSettings({closeModal(){}})'));
  const preview=nodes.filter(x=>x.type==='img'&&/^(A|B|X|Y|BACK|START|LB|RB|LT|RT)$/.test(x.props.alt));
  assert.equal(preview.length,10);
  for(const img of preview){assert.equal(img.props.src,glyphs[family][img.props.alt.toLowerCase()]);assert.equal(img.props.style.width,32);assert.equal(img.props.style.height,32);}
}
const suffix=fs.readFileSync(path.join(root,'pc/bp_suffix.js'),'utf8');
vm.runInContext(suffix.slice(suffix.indexOf('const PAD_PS'),suffix.indexOf('// Страница игры')),c);
c.kids=[{type:{prototype:{render(){return 'actual support';}}},props:{feature:16}}];
for(const family of Object.keys(glyphs)){
  c.family=family;
  assert.equal(run('pcPadIcons(kids,family)[0].props.children[1].type'),'img',family+' support glyph is rendered, with actual Steam support preserved');
}
console.log(`PASS controller glyphs: ${count} set/path mappings; 20 physical PS correspondences; 7 settings; EN/RU/UK; actual preview/support render; restoration; no remote asset URLs`);
