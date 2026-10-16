"""QAM and Big Picture regressions using actual code from immutable candidate ZIPs."""
from pathlib import Path
import os
import subprocess
import pytest

ROOT = Path(os.environ.get('CONTINUE_R15_ROOT', Path(__file__).resolve().parents[2]))
if os.environ.get('CONTINUE_R15_ROOT'):
    assert (ROOT / 'plugin/dist/index.js').is_file() or (ROOT / 'dist/index.js').is_file(), \
        'Explicit CONTINUE_R15_ROOT must point to an extracted candidate ZIP'
if not (ROOT / 'plugin/dist/index.js').exists() and not (ROOT / 'dist/index.js').exists():
    ROOT = Path(__file__).resolve().parents[4] / 'continue-public'

@pytest.mark.parametrize('platform', ['deck', 'pc'])
@pytest.mark.parametrize('scenario', ['volume', 'none_auto', 'pending', 'remount', 'auto_prepare', 'stale_props', 'source', 'pending_job'])
def test_live_settings(platform, scenario):
    if platform == 'pc' and not (ROOT / 'pc').is_dir():
        pytest.skip('Deck ZIP contains no PC UI')
    result = subprocess.run(['node', str(Path(__file__).with_name('r15_live_settings.cjs')),
                             str(ROOT), platform, scenario], capture_output=True, text=True,
                            encoding='utf-8', timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"status":"PASS"' in result.stdout
