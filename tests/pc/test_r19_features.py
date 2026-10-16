"""R19 contracts exercised offline; no real Steam, scheduler or media writes."""
import ast
import asyncio
import importlib.util
import json
import shutil
import subprocess
import types
from pathlib import Path

import pytest
import standalone_media as sm

ROOT = Path(__file__).resolve().parents[2]
# Deck and PC ship different modules with this name. A combined collection can
# prepend Deck's directory before importing this test, so select the PC file.
_policy_spec = importlib.util.spec_from_file_location('r19_shipped_pc_policy', ROOT/'pc/public_media_policy.py')
_policy = importlib.util.module_from_spec(_policy_spec)
_policy_spec.loader.exec_module(_policy)
PCMediaManager = _policy.PCMediaManager


def settings_plugin(tmp_path):
    # Compile the shipped nested PC class's two settings overrides, avoiding
    # Backend's threads, Steam discovery and network-capable plugin lifecycle.
    path = tmp_path / 'settings.json'
    class Base:
        async def get_settings(self):
            return json.loads(path.read_text()) if path.exists() else {}
        def _is_standalone(self): return True
        def _write_settings(self, value): path.write_text(json.dumps(value))
        @staticmethod
        def _valid_setting(*args): return False
    tree = ast.parse((ROOT/'plugin/main.py').read_text(encoding='utf-8'))
    base_class = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Plugin')
    setter = next(n for n in base_class.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'set_setting')
    namespace = {}
    exec(compile(ast.Module(body=[setter], type_ignores=[]), '<shipped setter>', 'exec'), namespace)
    Base.set_setting = namespace['set_setting']
    tree = ast.parse((ROOT/'pc/gamehub_bp.py').read_text(encoding='utf-8'))
    pc = next(n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == 'PCPlugin')
    pc.body = [n for n in pc.body if getattr(n, 'name', '') in ('_valid_setting', 'get_settings')]
    env = {'main':types.SimpleNamespace(Plugin=Base),'config':types.SimpleNamespace(root=tmp_path),
           'read_json':lambda p:json.loads(p.read_text()) if p.exists() else {}}
    exec(compile(ast.Module(body=[pc], type_ignores=[]), '<shipped PC overrides>', 'exec'), env)
    return env['PCPlugin']


@pytest.mark.parametrize('key,value', [('disk_limit_gb',64)] + [(key,v) for key in ('pc_glyphs','pc_pads') for v in ('owner','native','xbox','playstation','steam')])
def test_selected_setting_survives_new_instance(tmp_path,key,value):
    plugin = settings_plugin(tmp_path)
    result = asyncio.run(plugin().set_setting(key,value))
    assert result.get(key) == value
    assert asyncio.run(plugin().get_settings())[key] == value
    assert json.loads((tmp_path/'settings.json').read_text())[key] == value


@pytest.mark.parametrize('value', [True,64.0,'64',0,-1,65,None])
def test_cache_invalid_values_rejected(tmp_path,value):
    plugin = settings_plugin(tmp_path)
    assert not plugin._valid_setting('disk_limit_gb',value,True)


def test_64gb_is_a_ceiling_and_keeps_free_space_guard(tmp_path,monkeypatch):
    manager = PCMediaManager(tmp_path)
    manager._configure({'disk_limit_gb':64,'media_quality':1080})
    assert manager._limit_bytes == 64 * 1024**3
    # A 64 GB ceiling works on a disk with only 3 GB free; no preallocation.
    monkeypatch.setattr(sm.shutil,'disk_usage',lambda _:types.SimpleNamespace(free=3*1024**3))
    manager._check_space(1024)
    monkeypatch.setattr(sm.shutil,'disk_usage',lambda _:types.SimpleNamespace(free=manager._min_free_bytes+100))
    with pytest.raises(RuntimeError,match='insufficient free disk space'):
        manager._check_space(101)


def test_r19_frontend_contract():
    node=shutil.which('node')
    if not node: pytest.skip('Node required for frontend VM')
    r=subprocess.run([node,str(Path(__file__).with_name('r19_features.cjs'))],capture_output=True,text=True,encoding='utf-8')
    assert r.returncode == 0,r.stdout+r.stderr


def test_pc_bundle_compiles_with_r19_controls(tmp_path):
    import importlib.util
    spec=importlib.util.spec_from_file_location('r19_public_service',ROOT/'pc/gamehub_bp.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    bundle,version=module.build_bundle(types.SimpleNamespace(app=ROOT,plugin=ROOT/'plugin',media_url='http://127.0.0.1:8793/'))
    assert 'pcControllerGlyph' in bundle and 'PcSupportFeatures' in bundle
    assert len(version)==12
    node=shutil.which('node')
    if not node: pytest.skip('Node required for actual shipped bundle syntax')
    target=tmp_path/'bundle.js';target.write_text(bundle,encoding='utf-8')
    result=subprocess.run([node,'--check',str(target)],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
