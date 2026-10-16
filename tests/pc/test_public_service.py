"""Public PC runtime tests: temporary application only, never owner Steam."""
import importlib.util
import json
import socket
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

SOURCE = (Path(__file__).resolve().parents[2] / 'pc')


def module():
    assert (SOURCE / 'gamehub_bp.py').exists(), 'public entrypoint missing'
    sys.path.insert(0, str(SOURCE))
    spec = importlib.util.spec_from_file_location('continue_public_service', SOURCE / 'gamehub_bp.py')
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_bootstrap_retries_and_resets_backoff_on_context_change():
    mod=module()
    class Session:
        context_revision=0
        calls=0
        marker=None
        def evaluate(self,js,**kwargs):
            if js=='ready':return True
            if js=='bundle':
                self.calls+=1
                if self.calls<2:raise RuntimeError('transient')
                self.marker='version'
                return
            return self.marker
    s=Session();retry=mod.InjectionRetry()
    assert not retry.tick(s,'bundle','version','ready',now=0)
    assert not retry.tick(s,'bundle','version','ready',now=2)
    assert s.calls==1
    assert retry.tick(s,'bundle','version','ready',now=3)
    assert not retry.tick(s,'bundle','version','ready',now=4)
    assert s.calls==2
    s.marker=None;s.context_revision+=1
    assert retry.tick(s,'bundle','version','ready',now=4)
    assert s.calls==3


def test_send_deadline_interrupts_stalled_writer():
    import time
    mod=module();s=mod.Session.__new__(mod.Session)
    released=threading.Event()
    class Socket:
        def send(self,*args):released.wait(2)
        def abort(self):released.set()
    s.ws=Socket();s.lock=threading.Lock();s.seq=0;s.waiting={};s.alive=True
    started=time.monotonic()
    with pytest.raises(TimeoutError):s.send('fixture',timeout=.03)
    assert time.monotonic()-started<.5
    assert not s.waiting and not s.alive


def test_port_conflict_retries_then_reports_nonzero(tmp_path,monkeypatch):
    import types
    mod=module();waits=[];attempts=[]
    config=types.SimpleNamespace(root=tmp_path,data=tmp_path/'data',media_port=8793,token='fixture',version='0.1.4',ready=tmp_path/'service_ready.json')
    config.ready.write_text('{}')
    def occupied(*args):attempts.append(1);raise OSError('occupied fixture')
    monkeypatch.setattr(mod,'media_server',occupied)
    stop=types.SimpleNamespace(wait=lambda seconds:waits.append(seconds) or False)
    assert mod.serve(config,stop)==3
    assert len(attempts)==5 and waits==[3,3,3,3]
    assert not config.ready.exists()
    assert json.loads((tmp_path/'service-error.json').read_text())['error']=='media_port_occupied'


def test_release_marker_is_required(tmp_path):
    mod = module()
    with pytest.raises(ValueError, match='RELEASE'):
        mod.Config(tmp_path / 'app', tmp_path)


@pytest.fixture
def media(tmp_path):
    mod = module()
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'movie.mp4').write_bytes(b'0123456789')
    (tmp_path / 'secret.mp4').write_bytes(b'private')
    server = mod.media_server(data, 0, token='fixture-token')
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield server, tmp_path
    finally:
        server.shutdown()
        server.server_close()
        worker.join(3)


def response(media, target='/movie.mp4', headers=None, method='GET'):
    server, _ = media
    req = urllib.request.Request('http://127.0.0.1:%s%s' % (server.server_port, target), headers=headers or {}, method=method)
    try:
        return urllib.request.urlopen(req, timeout=3)
    except urllib.error.HTTPError as exc:
        return exc


def test_media_range_head(media):
    with response(media, headers={'Range': 'bytes=2-5'}) as r:
        assert r.status == 206
        assert r.headers['Content-Range'] == 'bytes 2-5/10'
        assert r.read() == b'2345'
    with response(media, headers={'Range': 'bytes=-3'}) as r:
        assert r.read() == b'789'
    with response(media, method='HEAD') as r:
        assert r.headers['Content-Length'] == '10'
        assert r.read() == b''
    assert response(media, headers={'Range': 'bytes=50-'}).code == 416
    assert response(media, headers={'Range': 'bytes=0-1,3-4'}).code == 416


@pytest.mark.parametrize('target', ['/../secret.mp4', '/%2e%2e/secret.mp4', '/%252e%252e/secret.mp4', '/C:/secret.mp4', '/%5csecret.mp4', '//secret.mp4', '/hub/movie.mp4', '/own/movie.mp4'])
def test_media_rejects_escape(media, target):
    assert response(media, target).code in (400, 404)


def test_media_host_and_header_limit(media):
    assert response(media, headers={'Host': 'evil.invalid'}).code == 403
    assert response(media, headers={'X-Large': 'x' * 17000}).code == 431


def test_media_symlink_outside(media):
    server, root = media
    try:
        (root / 'data/link.mp4').symlink_to(root / 'secret.mp4')
    except OSError:
        pytest.skip('Windows symlink privilege unavailable; junction tested in E2E')
    assert response(media, '/link.mp4').code == 404


def test_public_hltb_uses_stdlib_and_offline_is_empty(tmp_path, monkeypatch):
    assert (SOURCE / 'hltb_stdlib.py').exists(), 'stdlib HLTB missing'
    spec = importlib.util.spec_from_file_location('test_hltb_stdlib', SOURCE / 'hltb_stdlib.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    import asyncio
    monkeypatch.setattr(mod.urllib.request, 'urlopen', lambda *a, **k: (_ for _ in ()).throw(OSError('offline')))
    hltb = mod.HLTB(str(tmp_path))
    assert asyncio.run(hltb.get(10, 'Fixture')) is None


def test_none_stdout_does_not_break_import(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'stdout', None)
    assert module().log is not None

def test_theme_controls_do_not_wait_for_slow_game_metadata():
    import asyncio
    import types
    import time
    mod=module();backend=mod.Backend.__new__(mod.Backend)
    backend.gate=threading.RLock();backend.theme_gate=threading.Lock()
    started=threading.Event();release=threading.Event()
    async def about(_appid):
        started.set()
        while not release.is_set():
            await asyncio.sleep(.01)
        return None
    backend.plugin=types.SimpleNamespace(get_about=about)
    backend.themes=types.SimpleNamespace(METHODS={'themes_list'},call=lambda method,args:['fixture'])
    backend.PUBLIC=mod.Backend.PUBLIC|backend.themes.METHODS
    backend.loop=asyncio.new_event_loop()
    loop_thread=threading.Thread(target=backend.loop.run_forever);loop_thread.start()
    reader=threading.Thread(target=lambda:backend.call('get_about',[42]));reader.start()
    assert started.wait(2)
    timer=threading.Timer(.4,release.set);timer.start()
    try:
        at=time.monotonic()
        assert backend.call('themes_list',[])==['fixture']
        assert time.monotonic()-at<.2,'Theme UI must not queue behind external metadata'
    finally:
        release.set();timer.cancel();reader.join(2)
        backend.loop.call_soon_threadsafe(backend.loop.stop);loop_thread.join(2);backend.loop.close()


def test_service_lock_rejects_second_instance_and_can_be_reacquired(tmp_path):
    mod = module()
    first = mod.ServiceLock(tmp_path)
    second = mod.ServiceLock(tmp_path)
    assert first.acquire()
    try:
        assert not second.acquire()
    finally:
        first.close()
    assert second.acquire()
    second.close()


def test_update_launches_helper_with_own_pid_and_then_stops(tmp_path, monkeypatch):
    import types
    mod = module()
    launched = []
    class Updater:
        def __init__(self, root):
            pass
        def check(self):
            return {'available': True, 'sha256': 'f' * 64}
        def download(self, info):
            return tmp_path / 'fixture.zip'
        def spawn_helper(self, archive, checksum, *, wait_pid):
            launched.append(wait_pid)
    monkeypatch.setitem(sys.modules, 'public_update', types.SimpleNamespace(PublicUpdater=Updater))
    stop = threading.Event()
    mod.update_once(types.SimpleNamespace(root=tmp_path), types.SimpleNamespace(plugin=types.SimpleNamespace()), stop)
    assert stop.is_set() and launched == [__import__('os').getpid()]
