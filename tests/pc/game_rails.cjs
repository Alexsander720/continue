const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(path.resolve(__dirname,'../../plugin/dist/index.js'),'utf8');
const start=source.indexOf('// Shared game visuals start'),end=source.indexOf('// Shared game visuals end');
assert.ok(start>=0&&end>start,'Shared rail/button renderer missing');
let state=false;const c=vm.createContext({console,DFL:{appActionButtonClasses:{PlayButtonContainer:'play',ButtonChild:'child',ButtonText:'text',Disabled:'disabled'}},
 h:(type,props,...children)=>({type,props:{...props,children}}),useState:()=>[state,v=>state=v]});
vm.runInContext(source.slice(start,end),c);const run=s=>vm.runInContext(s,c);
for(const accent of ['#d8dfe6','#e2c47e','#c3161b','#ef4444','#000000','#ffffff','bad','red;display:none']){
 c.accent=accent;const p=run('gamePlayPalette(accent)');c.bg=p.background;c.fg=p.foreground;
 assert.ok(run('gameColorContrast(bg,fg)')>=4.5,accent);assert.equal(p.foreground,'#0b1016');
 assert.equal(run('gameColorContrast(accent,"#0b1016")')>=4.5?p.background:'#ffffff',p.background);
 const css=run('gamePlayCss(accent,"108710")');assert.ok(css.includes(':hover')&&css.includes('.gpfocus')&&css.includes(':focus-visible'));
 assert.ok(css.includes('outline:2px solid #fff'));assert.ok(!css.includes('undefined'));
}
c.visual={rail:'data:image/png;base64,eA==',rail_sha256:'a'.repeat(64)};
let tree=run('GameRail({visual})');assert.equal(tree.props.className,'gh-rule');
const img=tree.props.children[0];assert.equal(img.props.alt,'');assert.equal(img.props['aria-hidden'],true);
img.props.onLoad({currentTarget:{naturalWidth:20}});tree=run('GameRail({visual})');assert.ok(tree.props.className.includes('gh-has-rail'));
tree.props.children[0].props.onError();tree=run('GameRail({visual})');assert.equal(tree.props.className,'gh-rule');
assert.ok(run('GAME_RAIL_CSS').includes('.gh-has-rail::before'));
const attrs=new Map(),root={setAttribute:(k,v)=>attrs.set(k,v),removeAttribute:k=>attrs.delete(k)};
c.anchor={current:{ownerDocument:{documentElement:root}}};c.cleanups=[];
c.useLayoutEffect=fn=>c.cleanups.push(fn());
run('useGameVisualDocument(108710,anchor,true)');run('useGameVisualDocument(2322010,anchor,true)');
c.cleanups[0]();assert.equal(attrs.get('data-continue-visual'),'2322010');
c.cleanups[1]();assert.equal(attrs.size,0);
run('useGameVisualDocument(108710,anchor,true)');run('useGameVisualDocument(108710,anchor,true)');
c.cleanups[2]();assert.equal(attrs.get('data-continue-visual'),'108710');c.cleanups[3]();assert.equal(attrs.size,0);
console.log('PASS shared native button: valid/invalid accents, WCAG >=4.5, hover/focus; rail load/error fallback');
