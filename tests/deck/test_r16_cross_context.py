"""Independent JS realms communicate only through native BroadcastChannel."""
from pathlib import Path
import os
import subprocess
import pytest

ROOT=Path(os.environ.get('CONTINUE_R16_ROOT',Path(__file__).resolve().parents[2]))
if os.environ.get('CONTINUE_R16_ROOT'):
    assert (ROOT/'plugin/dist/index.js').is_file() or (ROOT/'dist/index.js').is_file()
if not (ROOT/'plugin/dist/index.js').is_file() and not (ROOT/'dist/index.js').is_file():
    ROOT=Path(__file__).resolve().parents[4]/'continue-public'

@pytest.mark.parametrize('platform',['deck','pc'])
@pytest.mark.parametrize('scenario',['stale_qam','stale_picker','volume','none_auto','remount'])
def test_cross_context_settings(platform,scenario):
    if platform=='pc' and not (ROOT/'pc').is_dir():
        pytest.skip('Deck ZIP contains no PC UI')
    if scenario=='stale_qam' and platform=='pc':
        pytest.skip('Decky dropdown unmount is specific to QAM')
    if scenario=='stale_picker' and platform=='deck':
        pytest.skip('The MusicPicker modal belongs to PC')
    r=subprocess.run(['node',str(Path(__file__).with_name('r16_cross_context.cjs')),str(ROOT),platform,scenario],capture_output=True,text=True,encoding='utf-8',timeout=20)
    assert r.returncode==0,r.stdout+r.stderr
    assert '"status":"PASS"' in r.stdout
