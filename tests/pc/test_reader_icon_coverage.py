"""All working readers: fixture-derived icon contracts must resolve to files.

The inventory was read from 423 explicit fixture stages (golden stage paths and
the preserved audit copies for the two readers without positive golden files).
Reader hashes make a stale inventory fail when a reader changes.
"""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import types

import pytest

PC = Path(__file__).resolve().parents[2] / 'pc'
TARGET = Path(os.environ.get('CONTINUE_R14_ROOT', PC.parent))
PLUGIN = TARGET / 'plugin' if (TARGET / 'plugin').is_dir() else TARGET
MODULES = PLUGIN / 'py_modules'
sys.path[:0] = [str(MODULES), str(PC)]
INVENTORY = json.loads(Path(__file__).with_name('r14_reader_icons.json').read_text(encoding='utf-8'))

# No authored game set exists for these facts. These six common SVGs are explicit
# semantic fallbacks, shipped as files too; no generic checkmark is permitted.
COMMON_FALLBACKS = {
    ('1659420', 'completion_percent'): 'pie.svg',
    ('1659420', 'treasures_collected'): 'gem.svg',
    ('1659420', 'play_time_minutes'): 'clock.svg',
    ('2322010', 'silver'): 'coins.svg',
    ('2322010', 'play_time'): 'clock.svg',
    ('2420110', 'play_time_seconds'): 'clock.svg',
}


@pytest.mark.parametrize('appid', sorted(INVENTORY))
def test_all_fixture_reader_icons_and_portraits_have_packaged_files(tmp_path, appid):
    from public_game_assets import seed_game_icons
    row = INVENTORY[appid]
    reader = MODULES / 'ddsaves' / (row['slug'] + '.py')
    assert hashlib.sha256(reader.read_bytes()).hexdigest() == row['reader_sha256'], 'Regenerate inventory from explicit fixtures after reader changes'
    assets = PLUGIN / 'assets/game_icons'
    seed_game_icons(assets, tmp_path)
    manifest = json.loads((tmp_path / 'icons/manifest.json').read_text(encoding='utf-8'))
    tree = ast.parse((PLUGIN / 'main.py').read_text(encoding='utf-8'))
    method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_apply_icons')
    ns = {'os': os, 'DATA': str(tmp_path)}
    exec(compile(ast.Module(body=[method], type_ignores=[]), 'shipped_main._apply_icons', 'exec'), ns)
    plugin = types.SimpleNamespace(_icon_map=lambda: manifest)
    card = {'facts': copy.deepcopy(row['facts'])}
    ids = [int(appid), 424840] if appid == '2149010' else [int(appid)]
    ns['_apply_icons'](plugin, card, ids)
    for fact in card['facts']:
        values = [fact.get('icon')] + [p.get('icon') for p in fact.get('people') or []]
        for value in values:
            assert value and value.startswith('img:icons/'), (appid, fact['id'], value)
            path = tmp_path / value[4:].split('?')[0]
            assert path.is_file(), (appid, fact['id'], path.name)
            assert path.suffix.lower() in {'.png', '.svg', '.webp', '.jpg', '.jpeg'}
            if path.suffix == '.svg':
                assert COMMON_FALLBACKS.get((appid, fact['id'])) == path.name
                assert 'M2 11l4-3' not in path.read_text(encoding='utf-8'), 'checkmark forbidden'
    assert len(INVENTORY) == 23
