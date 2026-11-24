"""Alan Wake must render a static vector in both public delivery modes."""
import base64
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_aw_packaged_style_and_both_payloads_use_only_static_vector():
    shared = load('plugin/py_modules/game_visuals.py', 'aw_visuals')
    sys.path.insert(0, str(ROOT / 'pc'))
    owner = load('pc/public_owner_theme.py', 'aw_owner')
    for platform in ['pc', 'plugin']:
        assets = ROOT / platform / 'assets'
        style = json.loads((assets / 'game_styles.json').read_text('utf-8'))['108710']
        assert style['rail'] == 'rails/108710.svg', 'Alan Wake still uses the raster rail'
        visual = shared.game_visual(assets, 108710)
        assert visual['rail'].startswith('data:image/svg+xml;base64,')
        data = base64.b64decode(visual['rail'].split(',', 1)[1])
        svg = ET.fromstring(data)
        assert svg.attrib['viewBox'] == '0 0 48 768'
        assert svg.attrib['preserveAspectRatio'] == 'xMidYMid meet'
        assert not any(x in data.lower() for x in [b'<image', b'<script', b'<filter', b'<animate', b'<style'])
        assert visual['rail_width'] == 48
        if platform == 'pc':
            assert owner.payload(ROOT, '108710')['rail'] == visual['rail']


def test_vector_loader_rejects_active_external_raster_and_invalid_geometry(tmp_path):
    shared = load('plugin/py_modules/game_visuals.py', 'aw_bad_visuals')
    root = tmp_path
    (root / 'rails').mkdir()
    path = root / 'rails/108710.svg'
    (root / 'game_styles.json').write_text(json.dumps({'108710': {'accent': '#eee0b9', 'rail': 'rails/108710.svg'}}))
    safe = '<svg xmlns="http://www.w3.org/2000/svg" width="48" height="768" viewBox="0 0 48 768" preserveAspectRatio="xMidYMid meet"><path d="M0 0L48 768" fill="#fff"/></svg>'
    path.write_text(safe)
    assert shared.game_visual(root, 108710).get('rail', '').startswith('data:image/svg+xml;base64,')
    for i, bad in enumerate([
        safe.replace('<path', '<script'),
        safe.replace('<path', '<image href="data:image/png;base64,AAAA"'),
        safe.replace('<path', '<path onload="alert(1)"'),
        safe.replace('fill="#fff"', 'fill="url(https://example.invalid/x)"'),
        safe.replace('width="48"', 'width="49"'),
        safe.replace('0 0 48 768', '0 0 480 768'),
        '<!DOCTYPE svg [<!ENTITY x "bad">]>' + safe,
        safe.replace('<path', '<animate'),
    ]):
        folder = root / str(i)
        (folder / 'rails').mkdir(parents=True)
        (folder / 'game_styles.json').write_bytes((root / 'game_styles.json').read_bytes())
        (folder / 'rails/108710.svg').write_text(bad)
        assert 'rail' not in shared.game_visual(folder, 108710), bad
