"""Keep established game ornaments when adding rails for unstyled games."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEGACY = {'1689620', '1903340', '2322010', '990080', '1092790',
          '2129530', '2124490', '2651280', '2531310'}


def test_existing_themes_keep_their_own_rails():
    pc = json.loads((ROOT / 'pc/assets/game_styles.json').read_text('utf-8'))
    deck = json.loads((ROOT / 'plugin/assets/game_styles.json').read_text('utf-8'))
    assert pc == deck
    for appid in LEGACY:
        assert not pc[appid].get('rail'), f'{appid}: generated rail replaces an existing ornament'
        assert '#cardCopyFrame' in pc[appid]['css']
    assert all(row.get('rail') for appid, row in pc.items()
               if appid not in LEGACY and row.get('source') == 'rails')


def test_legacy_background_does_not_target_loaded_images():
    result = subprocess.run(['node', str(Path(__file__).with_name('rails_preservation.cjs'))],
                            capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stdout + result.stderr
