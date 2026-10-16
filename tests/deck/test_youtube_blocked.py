"""Provider refusals stay distinct from connection failures, without network I/O."""
import asyncio
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULES = ROOT / 'py_modules'
if MODULES.is_dir():
    PC = ROOT.parents[1] / 'pc_bp'
else:
    ROOT = Path(__file__).resolve().parents[2]
    MODULES = ROOT / 'plugin/py_modules'
    PC = ROOT / 'pc'
sys.path.insert(0, str(MODULES))
sys.path.insert(0, str(PC))


@pytest.mark.parametrize('platform', ['pc', 'deck'])
@pytest.mark.parametrize('phase', ['search', 'download'])
@pytest.mark.parametrize('message', ["Sign in to confirm you're not a bot", 'HTTP Error 403: Forbidden', 'Connection timed out'])
def test_youtube_refusal_survives_worker_and_cooldown(tmp_path, monkeypatch, platform, phase, message):
    from public_media_policy import PCMediaManager
    from deck_music_media import DeckMediaManager
    manager = (PCMediaManager if platform == 'pc' else DeckMediaManager)(tmp_path)
    monkeypatch.setattr(manager, '_own_ytdlp', lambda: None)
    monkeypatch.setattr(manager, 'locate_ytdlp', lambda: Path('fixture-loader'))
    monkeypatch.setattr(manager, '_ytdlp_command', lambda: ['fixture-never-executed'])
    monkeypatch.setattr(manager, 'store_data', lambda *args: {'name': 'Fixture'})
    if phase == 'download':
        monkeypatch.setattr(manager, 'youtube_candidates', lambda *args, **kw: [{'url': 'https://www.youtube.com/watch?v=abcdefghijk'}])
    def run(command, **kw):
        error = message if kw.get('text') else message.encode()
        return subprocess.CompletedProcess(command, 1, stdout='', stderr=error)
    monkeypatch.setattr(manager, 'run', run)
    settings = {'theme_music_consent': True, 'hub_music': True}
    result = manager._maybe_theme(42, 'Fixture', settings)
    blocked = 'timed out' not in message
    assert result.get('reason') == ('youtube_blocked' if blocked else 'theme_timeout')
    attempt = manager._state()['theme_attempts']['42']
    assert attempt.get('reason') == result.get('reason')
    retry = manager._maybe_theme(42, 'Fixture', settings)
    assert retry.get('reason') == result.get('reason')
    assert not result['ok']


def test_deck_status_exposes_localizable_provider_reason(tmp_path):
    from deck_music_backend import with_music
    class Base:
        def _is_standalone(self): return True
        async def get_settings(self):
            return {'theme_music_consent': True, 'hub_music': True}
    class Runtime:
        def status(self): return {'ready': True}
    class Manager:
        runtime = Runtime()
        def _state(self): return {'theme_attempts': {'42': {'ok': False, 'reason': 'youtube_blocked'}}}
        def music_files(self, settings): return {}
    plugin = with_music(Base, str(tmp_path))()
    plugin._media = lambda: Manager()
    status = asyncio.run(plugin.get_deck_music_status(42))
    assert status['state'] == 'youtube_blocked'
    assert status['error'] == 'youtube_blocked'


def test_deck_refusal_text_in_three_languages():
    import json
    import shutil
    node = shutil.which('node')
    if not node: pytest.skip('Node is required for the shipped UI text')
    source = (MODULES.parent / 'assets/deck_music.js').read_text(encoding='utf-8')
    prefix = source.split('function createDeckMusicPlayer', 1)[0]
    result = subprocess.run([node, '-e', "let LANGUAGE='en';\n" + prefix + "\nconsole.log(JSON.stringify(['en','ru','uk'].map(lang=>{LANGUAGE=lang;return dm('youtube_blocked')})));"], capture_output=True, text=True, encoding='utf-8', check=True)
    values = json.loads(result.stdout)
    assert all('YouTube' in text and text != 'youtube_blocked' for text in values)
    assert len(set(values)) == 3
