"""Palette inputs cannot inject CSS, icon seeding remains separate from reader admission."""
import importlib.util
import json
from pathlib import Path
import subprocess
import zipfile
import ast
import os
import types

ROOT=Path(__file__).resolve().parents[2]
def load(path):
    spec=importlib.util.spec_from_file_location('thematic_'+path.stem,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

def test_palette_accepts_only_fixed_names(tmp_path):
    mod=load(ROOT/'plugin/py_modules/game_visuals.py')
    for i,value in enumerate(('courier-blue','courier-black','red;}body{display:none',{},[],None)):
        asset=tmp_path/str(i);asset.mkdir()
        (asset/'game_styles.json').write_text(json.dumps({'1850570':{'palette':value,'accent':'#f1b54a'}}),'utf-8')
        result=mod.game_visual(asset,1850570)
        assert result['accent']=='#f1b54a'
        assert result.get('palette')==(value if isinstance(value,str) and value.startswith('courier-') else None)

def test_ds_icons_seed_without_registering_readers(tmp_path):
    mod=load(ROOT/'pc/public_game_assets.py')
    result=mod.seed_game_icons(ROOT/'pc/assets/game_icons',tmp_path)
    manifest=json.loads((tmp_path/'icons/manifest.json').read_text('utf-8'))
    for app in ('1850570','3280350'):
        assert {'order_id','order_name','order_status','playtime_seconds','current_task','episode_number','main_goal'} <= set(manifest[app])
        for path in manifest[app].values():assert (tmp_path/'icons'/path).is_file()
    readers=(ROOT/'plugin/py_modules/deck_saves.py').read_text('utf-8')
    assert 'death_stranding_dc' not in readers and 'death_stranding_2' not in readers
    tree=ast.parse((ROOT/'plugin/main.py').read_text('utf-8'))
    method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_apply_icons')
    namespace={'os':os,'DATA':str(tmp_path)}
    exec(compile(ast.Module(body=[method],type_ignores=[]),'shipped_icon_lookup','exec'),namespace)
    plugin=types.SimpleNamespace(_icon_map=lambda:manifest)
    for app in ('1850570','3280350'):
        card={'facts':[{'id':key,'label':key,'value':'1'} for key in manifest[app]]}
        namespace['_apply_icons'](plugin,card,[int(app)])
        assert all(f['icon'].startswith('img:icons/'+app+'/') for f in card['facts'])

def test_design_backups_excluded_from_actual_builders(tmp_path):
    load(ROOT/'tests/test_pc_build.py').create_fixture(tmp_path)
    assets=tmp_path/'pc/assets';assets.mkdir()
    (assets/'game_styles.json').write_text('{}','utf-8')
    (assets/'game_styles.json.bak-design').write_text('old visual data','utf-8')
    (tmp_path/'plugin/main.py.bak-design').write_text('old runtime data','utf-8')
    for platform in ('pc','deck'):
        archive,_=load(ROOT/f'tools/build_{platform}_zip.py').build(tmp_path,'0.1.5','r4')
        with zipfile.ZipFile(archive) as z:assert not any('.bak-design' in n for n in z.namelist())
