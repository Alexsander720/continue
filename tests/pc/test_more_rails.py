"""Decorative-only games must work without widening the save/icon allowlist."""
import base64
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
APPS = ['1030300','19680','1778820','2592160','1671210','1585220','1569580','2582320','2215430','2358720','2138710','2461850','2428980','374320','405640','731490','587620','701160','702670','10150','2990600','2741360','434170','814380','391220']

def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_decorative_games_deliver_identical_static_vectors_on_pc_deck_and_owner():
    sys.path.insert(0, str(ROOT / 'pc'))
    owner = load('more_owner', 'pc/public_owner_theme.py')
    shared = load('more_visuals', 'plugin/py_modules/game_visuals.py')
    pc = json.loads((ROOT / 'pc/assets/game_styles.json').read_text('utf-8'))
    deck = json.loads((ROOT / 'plugin/assets/game_styles.json').read_text('utf-8'))
    for app in APPS:
        assert app in pc and app in deck, f'Missing decorative style {app}'
        assert pc[app] == deck[app]
        assert pc[app]['rail'] == f'rails/{app}.svg'
        images = [shared.game_visual(ROOT / platform / 'assets', app) for platform in ['pc','plugin']]
        assert images[0] == images[1] and images[0]['rail_width'] == 48
        assert images[0]['rail'].startswith('data:image/svg+xml;base64,')
        raw = base64.b64decode(images[0]['rail'].split(',', 1)[1])
        assert shared._static_svg(raw)
        assert b'<text' not in raw and b'<image' not in raw
        result = owner.payload(ROOT, app)
        assert result and result['rail'] == images[0]['rail']
        assert result['accent'] == pc[app]['accent'] and result['icons'] == {}

def test_owner_visual_metadata_does_not_enable_unpublished_icons_or_readers(tmp_path):
    sys.path.insert(0, str(ROOT / 'pc'))
    owner = load('more_owner_isolation', 'pc/public_owner_theme.py')
    assets = tmp_path / 'pc/assets'
    (assets / 'game_icons/1030300').mkdir(parents=True)
    (assets / 'game_styles.json').write_text(json.dumps({'1030300': {'accent':'#abcdef'}}))
    (assets / 'game_icons/manifest.json').write_text(json.dumps({'1030300':{'invented':'1030300/x.png'}}))
    (assets / 'game_icons/1030300/x.png').write_bytes(b'\x89PNG\r\n\x1a\nmalformed')
    result = owner.payload(tmp_path, '1030300')
    assert result and result['accent'] == '#abcdef' and result['icons'] == {}
    assert owner.payload(tmp_path, '9999999') is None
    assert owner.payload(tmp_path, '../1030300') is None
