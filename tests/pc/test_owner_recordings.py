import importlib.util
from pathlib import Path
from types import SimpleNamespace
import threading
import time
import urllib.request
import subprocess
import sys

from playwright.sync_api import sync_playwright
from test_owner_theme import module as theme_module, init, ROOT


def module():
    path = ROOT / 'pc/public_owner_recordings.py'
    assert path.is_file(), 'Owner-theme mode needs an isolated recording adapter'
    spec = importlib.util.spec_from_file_location('owner_recording_under_test', path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_packaged_mode_imports_only_its_own_shared_modules(tmp_path):
    code = f'''import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, {str(ROOT / 'pc')!r})
from public_owner_recordings import OwnerRecordings
c=SimpleNamespace(root=Path({str(tmp_path)!r}), data=Path({str(tmp_path / 'data')!r}), plugin=Path({str(ROOT / 'plugin')!r}), steam=Path({str(tmp_path / 'Steam')!r}))
a=OwnerRecordings(c)
import standalone_media
assert Path(standalone_media.__file__).resolve()==c.plugin/'py_modules/standalone_media.py'
a.close()
print('packaged-only imports OK')
'''
    result = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', code], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_owner_decorator_video_load_failure_and_unload_restore_dom():
    theme = theme_module()
    value = dict(theme.payload(ROOT, '108710'), recording='http://127.0.0.1:12345/recordings/108710.mp4?key=' + 'a'*64)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            init(page)
            page.evaluate(theme.script(ROOT, value, 'recording-test'))
            assert page.locator('video.continue-owner-recording').count() == 1
            assert page.locator('video.continue-owner-recording').evaluate('(v)=>v.muted&&v.loop&&v.autoplay')
            # Playback failure leaves the original background and full card intact.
            page.locator('video.continue-owner-recording').evaluate('(v)=>v.dispatchEvent(new Event("error"))')
            assert page.locator('video.continue-owner-recording').count() == 0
            assert page.locator('.gh-title').inner_text() == 'Original title'
            page.evaluate('window.__continueOwnerTheme.unload()')
            assert page.evaluate('document.querySelector(".gh-root").outerHTML===beforeHTML')
            assert page.evaluate('window.__ghPC===ownerBefore&&window.__ghBridge===bridgeBefore')
        finally:
            browser.close()


def test_cache_endpoint_range_and_path_containment(tmp_path):
    mod = module()
    cache = tmp_path / 'media'
    cache.mkdir()
    data = b'0123456789'
    (cache / '2172010_recording.mp4').write_bytes(data)
    adapter = SimpleNamespace(media=cache)
    from public_owner_theme import ControlHandler
    from http.server import ThreadingHTTPServer
    server = ThreadingHTTPServer(('127.0.0.1', 0), ControlHandler)
    server.recordings = adapter
    server.recording_key = 'a'*64
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        import pytest
        for url in (base + '/recordings/2172010.mp4', base + '/recordings/2172010.mp4?key=' + 'b'*64):
            with pytest.raises(urllib.error.HTTPError) as denied:
                urllib.request.urlopen(url)
            assert denied.value.code == 403
        authorized = base + '/recordings/2172010.mp4?key=' + server.recording_key
        with urllib.request.urlopen(urllib.request.Request(authorized, headers={'Range':'bytes=2-5'})) as response:
            assert response.status == 206 and response.read() == b'2345'
            assert response.headers['Content-Range'] == 'bytes 2-5/10'
        for path in ('/recordings/../secret.mp4', '/recordings/2172010_recording.mp4', '/recordings/1.mp4'):
            with pytest.raises(urllib.error.HTTPError):
                urllib.request.urlopen(base + path)
        with pytest.raises(urllib.error.HTTPError) as bad:
            urllib.request.urlopen(urllib.request.Request(authorized, headers={'Range':'bytes=99-100'}))
        assert bad.value.code == 416
    finally:
        server.shutdown()
        server.server_close()
        worker.join()


def test_single_worker_cancel_on_running_game_and_keep_settings(tmp_path):
    mod = module()
    gate = threading.Event()
    calls = []
    class Manager:
        def __init__(self, *args, allowed=None, **kwargs):
            self.media = tmp_path / 'media'
            self.allowed = allowed
        def _asset(self, *args): return None
        def build_recording(self, app, name, settings):
            calls.append((app, settings.copy()))
            gate.wait(3)
            assert not self.allowed(), 'Running game must cancel the recording job'
            raise RuntimeError('cancelled')
        def _configure(self, settings): pass
        def _checkpoint(self): pass
        def _reserve_job(self, app): pass
    config = SimpleNamespace(root=tmp_path, data=tmp_path/'data', steam=tmp_path/'Steam', plugin=ROOT/'plugin')
    adapter = mod.OwnerRecordings(config, manager_factory=Manager)
    try:
        assert adapter.request('2172010', games=0) is None
        end = time.monotonic()+3
        while not calls and time.monotonic()<end: time.sleep(.01)
        adapter.request('2172010', games=0)
        assert adapter.request('1778820', games=1) is None
        gate.set()
        adapter.close()
        assert len(calls) == 1
        assert not (tmp_path/'settings.json').exists()
    finally:
        gate.set()
        adapter.close()


def test_full_isolated_cache_reserves_space_and_enforces_game_count(tmp_path):
    mod = module()
    from public_media_policy import PCMediaManager
    class Manager(PCMediaManager):
        def _configure(self, settings):
            self._limit_bytes = 300
            self._max_games = 2
            self._min_free_bytes = 0
        def recording_candidates(self, app): return [source]
        def build_recording(self, app, name, settings):
            self._check_space(100)
            (self.media / f'{app}_recording.mp4').write_bytes(b'new' + b'0'*97)
            return {'ok':True,'selection':'fixture'}
    source = tmp_path / 'Steam/userdata/first/gamerecordings/video/bg_2172010_20261017_181302/init-stream0.m4s'
    source.parent.mkdir(parents=True)
    source.write_bytes(b'never touched source')
    config = SimpleNamespace(root=tmp_path, data=tmp_path/'data', steam=tmp_path/'Steam', plugin=ROOT/'plugin')
    adapter = mod.OwnerRecordings(config, manager_factory=Manager)
    adapter.media.mkdir(parents=True)
    for app in (1,2,3):
        (adapter.media/f'{app}_recording.mp4').write_bytes(bytes(80))
    assert adapter.request('2172010', games=0) is None
    adapter.worker.join(5)
    adapter.close()
    assert (adapter.media/'2172010_recording.mp4').is_file(), 'Full cache must leave room for a new recording'
    assert len(list(adapter.media.glob('*_recording.mp4'))) <= 2
    assert source.read_bytes() == b'never touched source'
