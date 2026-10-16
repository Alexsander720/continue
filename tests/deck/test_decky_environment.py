"""Hardware regressions: frozen Decky, cancellation, setup power and TLS; no network."""
import asyncio
import hashlib
import io
import os
from pathlib import Path
import ssl
import subprocess
import threading
from types import SimpleNamespace
import urllib.request

import pytest


@pytest.mark.parametrize('tool', ['yt-dlp', 'ffmpeg', 'ffprobe', 'node'])
@pytest.mark.parametrize('explicit_env', [False, True])
def test_every_media_child_has_clean_environment(tmp_path, monkeypatch, decky_environment, tool, explicit_env):
    from deck_music_media import DeckMediaManager
    import standalone_media as sm
    manager = DeckMediaManager(tmp_path)
    manager.runtime = SimpleNamespace(tool=lambda name: str(tmp_path / 'private' / name))
    before_env = dict(os.environ)
    seen = []
    def popen(command, **kwargs):
        env = kwargs.get('env')
        assert env is not None, 'Popen inherits frozen Decky libraries'
        assert not any(k.startswith('_PYI') for k in env)
        assert not set(env) & {'LD_LIBRARY_PATH', 'LD_PRELOAD', 'PYTHONHOME', 'PYTHONPATH'}
        assert env['HOME'] == '/home/deck'
        assert env['LANG'] == 'C.UTF-8'
        assert env['PATH'].startswith('/usr/local/bin:/usr/bin:/bin')
        assert env['PATH'].endswith(':' + str(tmp_path / 'private'))
        seen.append(command)
        return SimpleNamespace(poll=lambda: 0, returncode=0)
    monkeypatch.setattr(subprocess, 'Popen', popen)
    kw = {'env': dict(os.environ)} if explicit_env else {}
    assert manager.run([tool, '--version'], **kw).returncode == 0
    assert seen == [[tool, '--version']]
    assert dict(os.environ) == before_env


def test_original_library_path_and_empty_home(tmp_path, monkeypatch, decky_environment):
    import standalone_media as sm
    from deck_music_media import DeckMediaManager
    monkeypatch.setenv('LD_LIBRARY_PATH_ORIG', '/usr/lib/original')
    monkeypatch.setenv('HOME', '')
    def popen(command, **kw):
        assert kw['env']['LD_LIBRARY_PATH'] == '/usr/lib/original'
        assert kw['env']['HOME'] == '/home/deck'
        assert not any(k.startswith('_PYI') for k in kw['env'])
        return SimpleNamespace(poll=lambda: 0, returncode=0)
    monkeypatch.setattr(subprocess, 'Popen', popen)
    DeckMediaManager(tmp_path).run(['ffmpeg', '-version'])


def test_zipapp_uses_system_python_in_frozen_decky(tmp_path, monkeypatch, decky_environment):
    import standalone_media as sm
    manager = sm.MediaManager(tmp_path)
    tool = tmp_path / 'yt-dlp'; tool.write_bytes(b'#!/usr/bin/env python3\nPK')
    monkeypatch.setattr(manager, 'locate_ytdlp', lambda: tool)
    def which(name, path=None):
        assert name == 'python3'
        assert path == '/usr/local/bin:/usr/bin:/bin'
        return '/usr/bin/python3'
    monkeypatch.setattr(sm.shutil, 'which', which)
    assert manager._ytdlp_command() == ['/usr/bin/python3', str(tool)]


def test_missing_python_is_a_typed_localizable_error(tmp_path, monkeypatch, decky_environment):
    import standalone_media as sm
    manager = sm.MediaManager(tmp_path)
    tool = tmp_path / 'yt-dlp'; tool.write_bytes(b'PKzipapp')
    monkeypatch.setattr(manager, 'locate_ytdlp', lambda: tool)
    monkeypatch.setattr(sm.shutil, 'which', lambda *a, **kw: None)
    monkeypatch.setattr(sm.os.path, 'isfile', lambda p: False)
    with pytest.raises(RuntimeError, match='python3_required'):
        manager._ytdlp_command()


def test_native_loader_never_needs_python(tmp_path, monkeypatch, decky_environment):
    import standalone_media as sm
    manager = sm.MediaManager(tmp_path)
    tool = tmp_path / 'yt-dlp'; tool.write_bytes(b'\x7fELF')
    monkeypatch.setattr(manager, 'locate_ytdlp', lambda: tool)
    assert manager._ytdlp_command() == [str(tool)]


def test_runtime_https_handler_has_verified_context(tmp_path, monkeypatch, decky_environment):
    import deck_media_runtime as dm
    body = b'pinned offline archive'
    context = ssl.create_default_context()
    handlers = []
    class Response(io.BytesIO):
        url = 'https://nodejs.org/offline.tar.xz'
        def getheader(self, name): return str(len(body))
    def build(*args):
        handlers.extend(args)
        return SimpleNamespace(open=lambda *a, **kw: Response(body))
    monkeypatch.setattr(urllib.request, 'build_opener', build)
    # Existing shared helper must supply the same verified context to this path.
    import standalone_media as sm
    monkeypatch.setattr(sm, '_ssl_context', lambda: context)
    monkeypatch.setattr(dm, '_ssl_context', lambda: context, raising=False)
    runtime = dm.MediaRuntime(tmp_path)
    runtime._download({'name': 'node', 'url': Response.url, 'size_bytes': len(body),
                       'sha256': hashlib.sha256(body).hexdigest()}, tmp_path / 'archive')
    https = [h for h in handlers if isinstance(h, urllib.request.HTTPSHandler)]
    assert len(https) == 1, 'runtime opener relies on missing embedded CA store'
    assert https[0]._context is context and context.verify_mode == ssl.CERT_REQUIRED
    assert any(isinstance(h, dm.RuntimeRedirectHandler) for h in handlers)


def test_loader_download_also_uses_shared_context(tmp_path, monkeypatch, decky_environment):
    import standalone_media as sm
    from deck_music_media import DeckMediaManager
    context = ssl.create_default_context(); calls = []
    monkeypatch.setattr(sm, '_ssl_context', lambda: context)
    def opener(request, **kw):
        assert kw['context'] is context
        calls.append(request.full_url)
        return io.BytesIO(b'payload')
    manager = DeckMediaManager(tmp_path, urlopen=opener)
    assert manager._bytes('https://github.com/yt-dlp/yt-dlp/releases/download/fixture/SHA2-256SUMS') == b'payload'
    manager._stream('https://github.com/yt-dlp/yt-dlp/releases/download/fixture/yt-dlp', tmp_path / 'loader.part')
    assert len(calls) == 2


def test_allowed_is_cached_for_one_second_and_denial_is_sticky(tmp_path, monkeypatch):
    import deck_media_runtime as dm
    clock = [10.0]; calls = []; permitted = [True]
    monkeypatch.setattr(dm.time, 'monotonic', lambda: clock[0])
    runtime = dm.MediaRuntime(tmp_path, allowed=lambda: calls.append(clock[0]) or permitted[0])
    for _ in range(5000): assert runtime._check_allowed()
    assert calls == [10.0]
    clock[0] = 10.999
    assert runtime._check_allowed() and len(calls) == 1
    clock[0] = 11.0
    assert runtime._check_allowed() and len(calls) == 2
    permitted[0] = False; clock[0] = 12.0
    assert not runtime._check_allowed()
    permitted[0] = True; clock[0] = 100.0
    assert not runtime._check_allowed() and len(calls) == 3


def test_manager_cancel_bypasses_positive_runtime_cache(tmp_path):
    import deck_media_runtime as dm
    from deck_music_media import DeckMediaManager
    manager = DeckMediaManager(tmp_path)
    manager.runtime = dm.MediaRuntime(tmp_path, allowed=lambda: True)
    assert manager.runtime._check_allowed()
    manager.cancel()
    assert not manager.runtime._check_allowed()


class Base:
    def __init__(self):
        self.settings = {'theme_music_consent': False}; self.lock = asyncio.Lock()
    def _is_standalone(self): return True
    async def get_settings(self): return dict(self.settings)
    def _write_settings(self, settings): self.settings = dict(settings)
    async def set_setting(self, key, value):
        self.settings[key] = value
        return dict(self.settings)
    def _plugin_dir(self): return str(Path(__file__).resolve().parents[1])
    def _media_lock(self): return self.lock
    def _power_sync(self): return {'ac': True, 'battery': 80}
    def _running_game(self): return False
    def _media_work_allowed(self): return self._power_sync()['ac'] and not self._running_game()


async def finish(p, job):
    await asyncio.wait_for(p._music_jobs[job['job']][1], 5)
    return (await p.music_job_status(job['job']))['result']


@pytest.mark.parametrize('phase', ['runtime', 'loader', 'queued', 'final_settings'])
def test_setup_revoke_never_restores_consent(tmp_path, phase):
    from deck_music_backend import with_music
    p = with_music(Base, tmp_path)()
    entered, release = threading.Event(), threading.Event()
    manager = p._media(); installed = []
    def prepare(consent):
        if phase == 'runtime':
            entered.set(); assert release.wait(5)
        return {'ok': True}
    def install(*args):
        installed.append(True)
        if phase == 'loader':
            entered.set(); assert release.wait(5)
        return {'ok': True}
    manager.runtime.prepare = prepare; manager.install_ytdlp = install
    async def check():
        job = await p.setup_deck_music(True)
        if phase == 'queued':
            await p.set_setting('theme_music_consent', False)
        elif phase == 'final_settings':
            read = p.get_settings
            async def revoking_read():
                await p.set_setting('theme_music_consent', False)
                return await read()
            # Base.set_setting does not reenter get_settings.
            p.get_settings = revoking_read
        else:
            try:
                assert await asyncio.to_thread(entered.wait, 5)
                await p.set_setting('theme_music_consent', False)
            finally: release.set()
        result = await finish(p, job)
        assert p.settings['theme_music_consent'] is False
        assert result.get('error') == 'cancelled' and result['ok'] is False
        if phase in ('runtime', 'queued'): assert not installed
    asyncio.run(check())


@pytest.mark.parametrize('battery,ac,game,expected', [(80, False, False, 'ok'), (25, False, False, 'charging_required'),
    (30, False, False, 'charging_required'), (31, False, False, 'ok'), (5, True, False, 'ok'),
    (80, False, True, 'game_or_low_battery')])
def test_setup_battery_policy_preserves_video_gate(tmp_path, battery, ac, game, expected):
    from deck_music_backend import with_music
    p = with_music(Base, tmp_path)()
    p._power_sync = lambda: {'ac': ac, 'battery': battery}
    p._running_game = lambda: game
    m = p._media(); calls = []
    def prepare(consent):
        assert m.runtime._check_allowed(), 'runtime retained the AC-only setup gate'
        calls.append('runtime'); return {'ok': True}
    m.runtime.prepare = prepare
    m.install_ytdlp = lambda *a: calls.append('loader') or {'ok': True}
    async def check(): return await finish(p, await p.setup_deck_music(True))
    result = asyncio.run(check())
    assert ('ok' if result.get('ok') else result.get('deferred')) == expected
    assert calls == (['runtime', 'loader'] if expected == 'ok' else [])
    p._music_operation = False
    assert p._deck_work_allowed() == (ac and not game), 'video must remain AC-only'
    if battery == 25 and not ac:
        for low in (0, 5, 15):
            p._power_sync = lambda: {'ac': False, 'battery': low}
            result = asyncio.run(check())
            assert result.get('deferred') == 'charging_required', 'all charges at or below 30% need the setup charging status'
            assert not calls


def test_deck_path_has_single_sanitized_subprocess_entry():
    import ast
    import standalone_media as sm
    root = Path(sm.__file__).parent
    launches = []
    import public_media_policy as policy
    for filename in ('standalone_media.py', 'deck_media_runtime.py', 'deck_music_backend.py',
                     'deck_music_media.py', 'loader_transaction.py', 'public_media_policy.py'):
        path = Path(policy.__file__) if filename == 'public_media_policy.py' else root / filename
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                if node.func.value.id == 'subprocess' and node.func.attr in ('Popen', 'run', 'call', 'check_output', 'check_call'):
                    launches.append((filename, node.func.attr))
    assert launches == [('standalone_media.py', 'Popen')]


@pytest.mark.parametrize('phase', ['download', 'extract', 'manifest'])
def test_runtime_cancel_cleans_staging_and_can_retry(tmp_path, monkeypatch, phase):
    import deck_media_runtime as dm
    import json
    import tarfile
    runtime = dm.MediaRuntime(tmp_path, allowed=lambda: True)
    packages = {}
    bodies = {}
    for name, tools in dm.TOOLS.items():
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode='w:xz') as tf:
            for filename in (*tools, 'LICENSE'):
                body = b'fixture'; member = tarfile.TarInfo(f'{name}/' + ('bin/' if filename != 'LICENSE' else '') + filename)
                member.size = len(body); tf.addfile(member, io.BytesIO(body))
        bodies[name] = output.getvalue()
        packages[name] = {'url': f'https://nodejs.org/{name}.tar.xz', 'filename': name + '.tar.xz',
            'size_bytes': len(bodies[name]), 'sha256': hashlib.sha256(bodies[name]).hexdigest(),
            'tools': tools, 'license_file': 'LICENSE', 'target_license': f'LICENSE_{name}.txt'}
    runtime._meta = {'packages': packages, 'caps': {'max_decompressed_bytes': 1048576}}
    class Response(io.BytesIO):
        def __init__(self, body, url): super().__init__(body); self.url = url
        def getheader(self, name): return str(len(self.getvalue()))
        def read(self, size):
            chunk = super().read(size)
            if phase == 'download': runtime.cancel()
            return chunk
    runtime._urlopen = lambda req, **kw: Response(bodies[req.full_url.split('/')[-1].split('.')[0]], req.full_url)
    original = runtime._open_new
    def opening(path, *args, **kw):
        handle = original(path, *args, **kw)
        if (phase == 'extract' and path.name == 'node') or (phase == 'manifest' and path.name.startswith('.manifest-')):
            runtime.cancel()
        return handle
    monkeypatch.setattr(runtime, '_open_new', opening)
    result = runtime.prepare(True)
    assert result.get('error') == 'cancelled' and not result['ok']
    assert not runtime.manifest_path.exists()
    assert not list(runtime.runtime_dir.glob('.staging-*'))
    assert not list(runtime.runtime_dir.glob('.manifest-*.tmp'))
    assert not list((runtime.runtime_dir / 'versions').glob('*'))
    # New manager/runtime is a new authorized operation, so a prior cancellation cannot poison retry.
    fresh = dm.MediaRuntime(tmp_path, allowed=lambda: True)
    fresh._meta = runtime._meta
    fresh._urlopen = lambda req, **kw: io_response(req.full_url)
    def io_response(url):
        name = url.split('/')[-1].split('.')[0]
        response = io.BytesIO(bodies[name]); response.url = url
        return response
    assert fresh.prepare(True)['ok']


@pytest.mark.parametrize('existing', [False, True])
def test_loader_cancel_removes_part_and_preserves_verified_loader(tmp_path, existing):
    from deck_music_media import DeckMediaManager
    manager = DeckMediaManager(tmp_path)
    manager.bin.mkdir()
    old = b'PK' + b'o' * (512 * 1024)
    if existing:
        (manager.bin / 'yt-dlp').write_bytes(old)
        manager._save_state({'yt_dlp': {'version': 'old', 'sha256': hashlib.sha256(old).hexdigest()}})
    body = b'PK' + b'n' * (512 * 1024)
    base = 'https://github.com/yt-dlp/yt-dlp/releases/download/fixture/'
    manager._json_url = lambda *a: {'tag_name': 'fixture', 'assets': [
        {'name': name, 'browser_download_url': base + name} for name in ('yt-dlp', 'SHA2-256SUMS')]}
    manager._bytes = lambda *a, **kw: (hashlib.sha256(body).hexdigest() + '  yt-dlp\n').encode()
    def stream(url, part, **kw):
        part.write_bytes(body); manager.cancel()
    manager._stream = stream
    result = manager.install_ytdlp(True, True)
    assert not result['ok'] and result.get('error') == 'cancelled'
    assert not (manager.bin / 'yt-dlp.download.part').exists()
    assert (manager.bin / 'yt-dlp').exists() == existing
    if existing: assert (manager.bin / 'yt-dlp').read_bytes() == old


def test_python_missing_reason_survives_theme_status(tmp_path):
    import standalone_media as sm
    from deck_music_media import DeckMediaManager
    from deck_music_backend import with_music
    m = DeckMediaManager(tmp_path)
    def missing(*args): raise sm.Python3RequiredError()
    m.build_theme = missing
    settings = {'theme_music_consent': True, 'home_music': True}
    assert m.prepare_music(42, 'Fixture', settings)['reason'] == 'python3_required'
    p = with_music(Base, tmp_path)(); p.settings = settings; p._standalone_media = m
    m.music_files = lambda *a, **kw: {}
    m.runtime = SimpleNamespace(status=lambda: {})
    status = asyncio.run(p.get_deck_music_status(42))
    assert status['state'] == status['error'] == 'python3_required'


def test_setup_copy_and_missing_python_are_localized_in_all_languages():
    import json
    import standalone_media as sm
    path = Path(sm.__file__).parents[1] / 'assets/deck_music.js'
    script = path.read_text(encoding='utf-8').split('function createDeckMusicPlayer', 1)[0]
    result = subprocess.run(['node', '-e', script + '\nconsole.log(JSON.stringify(DM_TEXT));'],
                            capture_output=True, text=True, encoding='utf-8', check=True)
    text = json.loads(result.stdout)
    for lang in ('en', 'ru', 'uk'):
        for key in ('detail', 'consent'):
            assert '180' in text[lang][key] and '30%' in text[lang][key]
            assert '???' not in text[lang][key]
        assert '30%' in text[lang]['charging_required']
        assert 'Python 3' in text[lang]['python3_required']
