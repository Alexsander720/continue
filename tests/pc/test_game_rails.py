"""Shared PC/Deck visuals: offline, isolated fixtures, no owner state."""
import importlib.util
import json
import struct
import subprocess
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_visuals():
    path = ROOT / 'plugin/py_modules/game_visuals.py'
    assert path.exists(), 'Shared game visual metadata loader is missing'
    spec = importlib.util.spec_from_file_location('rails_test_visuals', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def png(width=20, height=400):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress((b'\0' + b'\xff\0\0\xff' * width) * height)) + chunk(b'IEND', b''))


def fixture(tmp_path, entry):
    (tmp_path / 'rails').mkdir(exist_ok=True)
    (tmp_path / 'rails/108710.png').write_bytes(png())
    (tmp_path / 'game_styles.json').write_text(json.dumps({'108710': entry}), 'utf-8')
    return tmp_path


def test_shared_metadata_and_asset_bounds(tmp_path):
    mod = load_visuals()
    root = fixture(tmp_path, {'accent': '#d8dfe6', 'rail': 'rails/108710.png'})
    value = mod.game_visual(root, 108710)
    assert value['accent'] == '#d8dfe6'
    assert value['rail'].startswith('data:image/png;base64,') and len(value['rail_sha256']) == 64
    assert value['rail_width'] <= 48
    assert mod.game_visual(root, 1) == {}


def test_bad_assets_keep_accent_and_explicit_fallback(tmp_path):
    mod = load_visuals()
    root = fixture(tmp_path, {'accent': '#ffffff', 'rail': '../outside.png'})
    assert mod.game_visual(root, 108710) == {'accent': '#ffffff', 'fallback': 'legacy'}
    root.joinpath('game_styles.json').write_text('{bad', 'utf-8')
    assert mod.game_visual(root, 108710) == {}
    fixture(tmp_path, {'accent': 'red; background:url(https://bad)', 'rail': 'rails/108710.png'})
    assert 'accent' not in mod.game_visual(root, 108710)
    root.joinpath('rails/108710.png').write_bytes(png(49, 400))
    assert mod.game_visual(root, 108710)['fallback'] == 'legacy'
    root.joinpath('rails/108710.png').write_bytes(b'x' * 30721)
    assert 'rail' not in mod.game_visual(root, 108710)


def test_shared_native_button_and_image_lifecycle():
    result = subprocess.run(['node', str(Path(__file__).with_name('game_rails.cjs'))], capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stdout + result.stderr


def test_candidate_archives_exclude_backups_and_preserve_semver(tmp_path):
    spec = importlib.util.spec_from_file_location('rails_build_fixture', ROOT / 'tests/test_pc_build.py')
    fixture_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture_module)
    fixture_module.create_fixture(tmp_path)
    (tmp_path / 'plugin/main.py.bak-rails').write_text('# backup must stay local', 'utf-8')
    assets = tmp_path / 'pc/assets'
    assets.mkdir()
    (assets / 'game_styles.json.bak-rails').write_text('{}', 'utf-8')
    (assets / 'game_styles.json').write_text('{}', 'utf-8')
    import zipfile
    for name in ['pc', 'deck']:
        spec = importlib.util.spec_from_file_location('rails_builder_' + name, ROOT / f'tools/build_{name}_zip.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        archive, checksum = builder.build(tmp_path, '0.1.5', 'r2')
        assert archive.name == f'continue-{name}-0.1.5-r2.zip'
        assert checksum.exists()
        with zipfile.ZipFile(archive) as z:
            assert not any(n.endswith('.bak-rails') for n in z.namelist())
            assert json.loads(z.read('Continue/RELEASE.json'))['version'] == '0.1.5'

