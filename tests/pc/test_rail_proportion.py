"""Measure actual replaced-image layout, including the production fitting code."""
import base64
import json
import os
import subprocess
import importlib.util
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
APPS = ['108710', '2420110', '532210', '1850570', '3280350', '424840']


def renderer():
    # Evaluate production declarations rather than duplicating their CSS in a test.
    script = r"""
const fs=require('fs'),vm=require('vm');
const s=fs.readFileSync('plugin/dist/index.js','utf8');
const c=vm.createContext({DFL:{appDetailsHeaderClasses:{},basicAppDetailsSectionStylerClasses:{}}});
vm.runInContext(s.slice(s.indexOf('// Shared game visuals start'),s.indexOf('// Shared game visuals end')),c);
vm.runInContext(s.slice(s.indexOf('const CSS = (accent'),s.indexOf('// Полоса «Играть /')),c);
vm.runInContext('function playBarCss(){return ""}',c);
const fit=s.slice(s.indexOf('const FIT = {'),s.indexOf('const PB_LABELS ='));
vm.runInContext(fit,c);
process.stdout.write(JSON.stringify({css:vm.runInContext('CSS("#fff",false)',c),hub:vm.runInContext('HUB_LOOK_CSS',c),fit}));
"""
    return json.loads(subprocess.check_output(['node', '-e', script], cwd=ROOT, text=True, encoding='utf-8'))


def measure_all():
    code = renderer()
    rows = []
    styles = json.loads((ROOT / 'pc/assets/game_styles.json').read_text('utf-8'))
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            for width, height, hub in [(854, 534, False), (1280, 800, True), (1920, 1080, True), (3840, 2160, True)]:
                page.set_viewport_size({'width': width, 'height': height})
                zoom = height / 534
                page.set_content('<style>' + code['css'] + (code['hub'] if hub else '') +
                                 f'.gh-root{{zoom:{zoom};--gh-rail-limit:{48 / zoom}px}}' +
                                 '</style><div class="gh-root"><div class="gh-panel"><div class="gh-rule gh-has-rail">'
                                 '<img class="gh-rail"></div><img class="gh-logo"><div class="gh-title"></div>'
                                 '<div class="gh-detail"></div></div></div>')
                page.add_script_tag(content=code['fit'])
                page.evaluate('hub=>{useHubLook(hub);FIT.barBottom=92/(innerHeight/534)}', hub)
                for app in APPS:
                    mime = 'svg+xml' if styles[app]['rail'].endswith('.svg') else 'png'
                    image = 'data:image/' + mime + ';base64,' + base64.b64encode((ROOT / 'pc/assets' / styles[app]['rail']).read_bytes()).decode()
                    for words, logo_height in [(0, 30), (80, 85), (900, 500)]:
                        value = page.evaluate('''async args=>{
const [src,words,logoHeight]=args,p=document.querySelector('.gh-panel'),im=p.querySelector('.gh-rail'),logo=p.querySelector('.gh-logo');
im.src=src;await im.decode();logo.src='data:image/svg+xml,'+encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="900" height="${logoHeight}"><rect width="100%" height="100%" fill="white"/></svg>`);await logo.decode();
p.querySelector('.gh-title').textContent='A title '.repeat(words>80?12:1);
p.querySelector('.gh-detail').textContent='description '.repeat(words);
fitPanel(p,null,logo,800,null,false);
const r=im.getBoundingClientRect(),root=document.querySelector('.gh-root').getBoundingClientRect(),style=getComputedStyle(im);
return {width:r.width,height:r.height,natural:[im.naturalWidth,im.naturalHeight],error:Math.abs((r.width/r.height)/(im.naturalWidth/im.naturalHeight)-1)*100,fit:style.objectFit,visible:r.bottom<=root.bottom+1&&r.top>=root.top-1};
}''', [image, words, logo_height])
                        rows.append({'app': app, 'viewport': [width, height], 'words': words, 'logo_height': logo_height, **value})
        finally:
            browser.close()
    target = os.environ.get('RAIL_PROPORTION_RESULT')
    if target:
        Path(target).write_text(json.dumps(rows, indent=2), 'utf-8')
    return rows


def test_original_png_proportions_survive_text_logo_and_fitting():
    rows = measure_all()
    bad = [r for r in rows if r['error'] > 2 or not r['visible'] or not r['height'] or not r['width']]
    assert not bad, json.dumps({'cases': len(rows), 'bad': bad[:8]}, indent=2)


def test_r5_backups_never_enter_either_archive(tmp_path):
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    load('r5_build_fixture', ROOT / 'tests/test_pc_build.py').create_fixture(tmp_path)
    for relative in ['plugin/dist/index.js.bak-r5', 'plugin/assets/old.png.bak-r5', 'pc/assets/old.png.bak-r5']:
        p = tmp_path / relative
        p.parent.mkdir(exist_ok=True, parents=True)
        p.write_bytes(b'LOCAL BACKUP ONLY')
    for platform in ['pc', 'deck']:
        builder = load('r5_' + platform, ROOT / f'tools/build_{platform}_zip.py')
        archive, _ = builder.build(tmp_path, '0.1.5', 'r5')
        with zipfile.ZipFile(archive) as z:
            assert not any(n.endswith('.bak-r5') for n in z.namelist())

