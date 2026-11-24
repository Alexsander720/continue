"""Offline contracts for the shipped, CC0 controller prompt subsets."""
import asyncio
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / 'pc/assets/controller_glyphs'
FAMILIES = ('xbox', 'playstation', 'dualshock', 'steam', 'steam_controller')


def test_subset_provenance_and_passive_vectors():
    manifest = json.loads((PACK/'manifest.json').read_text(encoding='utf-8'))
    assert set(manifest['sets']) == set(FAMILIES)
    assert manifest['license'] == 'CC0-1.0'
    for family, buttons in manifest['sets'].items():
        assert set(buttons) == {'a','b','x','y','back','start','lb','rb','lt','rt','up','down','left','right'}
        for key, relative in buttons.items():
            path = PACK/relative
            assert path.resolve().is_relative_to(PACK.resolve())
            text = path.read_text(encoding='utf-8')
            svg = ET.fromstring(text)
            assert svg.get('viewBox') == '4 4 56 56'
            assert not re.search(r'<(?:script|image|text|foreignObject)\b|(?:href|url\(|@import)', text)
            assert all(e.tag.rsplit('}',1)[-1] in ('svg','defs','g','path') for e in svg.iter())
            if key in 'abxy' and family in ('playstation','steam','steam_controller'):
                assert '#FFFFFF' in text
    # Cross is blue, circle red, square pink and triangle green.
    for key, color in {'a':'#559CFF','b':'#F15B64','x':'#EB83C5','y':'#57D9A3'}.items():
        assert color in (PACK/manifest['sets']['dualshock'][key]).read_text()
    license_text = (ROOT/'pc/assets/licenses/kenney-input-prompts.txt').read_text(encoding='utf-8')
    assert 'Creative Commons Zero, CC0' in license_text
    assert 'Kenney' in (ROOT/'NOTICE.md').read_text(encoding='utf-8')


def test_frontend_mapping_restoration_and_localization():
    r = subprocess.run(['node',str(Path(__file__).with_name('controller_glyphs.cjs'))],capture_output=True,text=True,encoding='utf-8')
    assert r.returncode == 0, r.stdout+r.stderr


@pytest.mark.parametrize('value', FAMILIES)
def test_settings_roundtrip_and_r19_compatibility(tmp_path,value):
    spec=importlib.util.spec_from_file_location('glyphs_r19_helpers', Path(__file__).with_name('test_r19_features.py'))
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    plugin=helper.settings_plugin(tmp_path)
    for key in ('pc_glyphs','pc_pads'):
        result=asyncio.run(plugin().set_setting(key,value))
        assert result[key] == value
        assert asyncio.run(plugin().get_settings())[key] == value


def test_actual_bundle_embeds_every_shipped_vector():
    import types
    spec=importlib.util.spec_from_file_location('glyph_bundle',ROOT/'pc/gamehub_bp.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    bundle,_=module.build_bundle(types.SimpleNamespace(app=ROOT,plugin=ROOT/'plugin',media_url='http://127.0.0.1:8793/'))
    assert '__PC_CONTROLLER_GLYPHS__' not in bundle
    assert 'data:image/svg+xml,' in bundle
    assert 'kenney.nl' not in bundle
    assert 'thoseawesomeguys.com' not in bundle
