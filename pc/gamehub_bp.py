"""Continue? public Windows Big Picture service. Packaged as pc/gamehub_bp.py.

This entrypoint requires an application RELEASE.json. It never imports the
owner's service or hub. Commands: run, stop, status [--json], bundle.
"""
from __future__ import annotations

import argparse
import asyncio
import concurrent.futures
import hashlib
import hmac
import importlib.util
import json
import logging
import logging.handlers
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import sys
import threading
import time
import types
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger('continue_pc')
MEDIA_TYPES = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp',
               '.mp4': 'video/mp4', '.webm': 'video/webm', '.mp3': 'audio/mpeg', '.ogg': 'audio/ogg',
               '.opus': 'audio/ogg', '.m4a': 'audio/mp4', '.svg': 'image/svg+xml'}


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return default if default is not None else {}


def write_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    os.replace(tmp, path)


def steam_registry_path():
    """Thin read-only wrapper; fixtures supply Config.steam explicitly."""
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam') as key:
        return Path(winreg.QueryValueEx(key, 'SteamPath')[0])


class Config:
    def __init__(self, app, root=None, steam=None, cdp_port=8080, media_port=8793):
        self.app = Path(app).resolve()
        self.root = Path(root or Path(os.environ['LOCALAPPDATA']) / 'Continue').resolve()
        marker = read_json(self.app / 'RELEASE.json')
        if marker.get('channel') != 'public' or not re.fullmatch(r'\d+\.\d+\.\d+', str(marker.get('version', ''))):
            raise ValueError('A public RELEASE.json is required')
        self.version = marker['version']
        self.plugin = self.app / 'plugin'
        self.steam = Path(steam).resolve() if steam else steam_registry_path().resolve()
        self.cdp_port, self.media_port = int(cdp_port), int(media_port)
        self.data, self.logs = self.root / 'data', self.root / 'logs'
        self.ready = self.root / 'service_ready.json'
        self.cef = 'http://127.0.0.1:%s' % self.cdp_port
        self.media_url = 'http://127.0.0.1:%s/' % self.media_port
        self.token = secrets.token_hex(32)


def setup_logging(config):
    config.logs.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(config.logs / 'bp.log', maxBytes=512000, backupCount=3, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    log.addHandler(handler)
    log.setLevel(logging.INFO)


class ServiceLock:
    """Cross-process, non-blocking lock scoped to one Continue data root."""

    def __init__(self, root):
        self.path = Path(root) / 'service.lock'
        self.file = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open('a+b', buffering=0)
        try:
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b'\0')
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, IOError):
            handle.close()
            return False
        self.file = handle
        return True

    def close(self):
        handle, self.file = self.file, None
        if handle is None:
            return
        try:
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except (OSError, IOError):
            pass
        handle.close()


class HeaderLimit(Exception):
    pass


class LimitedReader:
    def __init__(self, stream):
        self.stream, self.used = stream, 0

    def readline(self, limit=-1):
        line = self.stream.readline(min(limit if limit >= 0 else 16385, 16385 - self.used))
        self.used += len(line)
        if self.used > 16384 or (line and not line.endswith(b'\n')):
            raise HeaderLimit()
        return line

    def __getattr__(self, name):
        return getattr(self.stream, name)


class MediaHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'

    def setup(self):
        self.request.settimeout(5)
        super().setup()
        self.rfile = LimitedReader(self.rfile)

    def handle_one_request(self):
        self.rfile.used = 0
        try:
            super().handle_one_request()
        except HeaderLimit:
            self.requestline = getattr(self, 'requestline', '')
            self.request_version = getattr(self, 'request_version', 'HTTP/1.0')
            self.command = getattr(self, 'command', None)
            self.send_error(431, 'Headers too large')
            self.close_connection = True

    def log_message(self, *_args):
        pass

    def parse_request(self):
        # BaseHTTPRequestHandler normalizes // before dispatch. Check original.
        target = self.raw_requestline.split(b' ')[1:2]
        if target and (not target[0].startswith(b'/') or target[0].startswith(b'//')):
            self.request_version, self.requestline, self.command = 'HTTP/1.0', '', None
            self.send_error(400)
            return False
        if not super().parse_request():
            return False
        valid = {'127.0.0.1:%s' % self.server.server_port, 'localhost:%s' % self.server.server_port}
        if len(self.headers.get_all('Host', [])) != 1 or self.headers.get('Host') not in valid:
            self.send_error(403, 'Loopback Host required')
            return False
        return True

    def resolve(self):
        path = urllib.parse.unquote(self.path.split('?', 1)[0])
        if (not path.startswith('/') or path.startswith('//') or re.search(r'%[0-9a-fA-F]{2}', path)
                or any(c in path for c in ('\\', ':', '\x00'))):
            return None
        parts = path[1:].split('/')
        if any(p in ('', '.', '..') for p in parts) or parts[0] in ('hub', 'own'):
            return None
        root = self.server.data.resolve()
        candidate = root.joinpath(*parts)
        try:
            p = candidate
            while p != root:
                info = p.lstat()
                if p.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
                    return None  # all reparse points, including Windows junctions
                p = p.parent
            resolved = candidate.resolve(strict=True)
            if root not in resolved.parents or resolved.suffix.lower() not in MEDIA_TYPES or not resolved.is_file():
                return None
            return resolved
        except (OSError, ValueError):
            return None

    def do_POST(self):
        if self.path != '/__continue_stop' or not hmac.compare_digest(self.headers.get('X-Continue-Token', ''), self.server.token):
            self.send_error(403)
            return
        self.send_response(204)
        self.send_header('Content-Length', '0')
        self.end_headers()
        self.server.stop_event.set()

    def do_HEAD(self):
        self.do_GET(False)

    def do_GET(self, body=True):
        if self.path == '/__continue_health':
            raw = json.dumps({'service': 'ContinueBigPicture', 'pid': os.getpid(), 'version': self.server.version}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            if body:
                self.wfile.write(raw)
            return
        path = self.resolve()
        if path is None:
            self.send_error(404)
            return
        try:
            stream = path.open('rb')
        except OSError:
            self.send_error(404)
            return
        with stream:
            size = os.fstat(stream.fileno()).st_size
            start, end, partial = 0, size - 1, False
            value = self.headers.get('Range')
            if value:
                match = re.fullmatch(r'bytes=(\d{0,18})-(\d{0,18})', value)
                invalid = not match or not any(match.groups()) or size == 0
                if not invalid:
                    first, last = match.groups()
                    if first:
                        start = int(first)
                        end = min(int(last), size - 1) if last else size - 1
                    else:
                        invalid = int(last) == 0
                        start = max(0, size - int(last))
                    invalid = invalid or start > end
                if invalid:
                    self.send_response(416)
                    self.send_header('Content-Range', 'bytes */%s' % size)
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                partial = True
            self.send_response(206 if partial else 200)
            if partial:
                self.send_header('Content-Range', 'bytes %s-%s/%s' % (start, end, size))
            self.send_header('Content-Type', MEDIA_TYPES[path.suffix.lower()])
            self.send_header('Content-Length', str(max(0, end - start + 1)))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cache-Control', 'max-age=86400')
            self.end_headers()
            if body:
                try:
                    stream.seek(start)
                    left = end - start + 1
                    while left > 0:
                        block = stream.read(min(left, 65536))
                        if not block:
                            break
                        self.wfile.write(block)
                        left -= len(block)
                except (OSError, ConnectionError):
                    pass


def media_server(data, port, token='', stop_event=None, version='fixture'):
    server = ThreadingHTTPServer(('127.0.0.1', int(port)), MediaHandler)
    server.daemon_threads = True
    server.data, server.token, server.version = Path(data), token, version
    server.stop_event = stop_event or threading.Event()
    return server


def build_bundle(config):
    src = (config.plugin / 'dist/index.js').read_text(encoding='utf-8')
    body = src[src.index('const React = window.SP_REACT;'):src.index('var index = DFL.definePlugin(')]
    body, count = re.subn(r'^const DATA = .*;$', 'const DATA = %s;' % json.dumps(config.media_url), body, flags=re.M)
    if count != 1:
        raise ValueError('Expected single DATA declaration')
    here = config.app / 'pc'
    prelude = (here / 'bp_prelude.js').read_text(encoding='utf-8')
    suffix = (here / 'bp_suffix.js').read_text(encoding='utf-8')
    version = hashlib.sha256((prelude + body + suffix).encode()).hexdigest()[:12]
    suffix = suffix.replace('__GH_VER__', json.dumps(version))
    return '(() => {\n' + prelude + '\n' + body + '\n' + suffix + '\n})();', version


class Backend:
    PUBLIC = {'get_card', 'get_about', 'get_hltb', 'get_settings', 'set_setting', 'set_game_bg', 'get_power',
              'get_aliases', 'get_music_map', 'get_music_files', 'get_status', 'set_lang', 'get_media_status',
              'set_game_source', 'refresh_media', 'set_media_context', 'clear_media_cache', 'install_ytdlp',
              'check_update', 'preview_tester_report', 'save_tester_report', 'ensure_blank_movie', 'get_protondb'}

    def __init__(self, config):
        self.config = config
        self.gate = threading.Lock()  # language and settings mutations are ordered
        stub = types.ModuleType('decky')
        stub.DECKY_PLUGIN_RUNTIME_DIR, stub.logger = str(config.data), log
        sys.modules['decky'] = stub
        sys.path[:0] = [str(config.app / 'pc'), str(config.plugin / 'py_modules'), str(config.plugin)]
        import hltb_stdlib
        sys.modules['hltb'] = hltb_stdlib
        spec = importlib.util.spec_from_file_location('continue_pc_plugin', config.plugin / 'main.py')
        main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main)
        self.main, self.deck_saves = main, main.deck_saves
        # Public ddsaves uses native Windows profile discovery. No Deck->emulator rewrite.
        from ddsaves import _common
        self.libraries = _common.steam_libraries()
        self.deck_saves.HOME = str(Path.home())
        self.deck_saves.STEAM = str(config.steam)

        class PCPlugin(main.Plugin):
            def _settings_path(self):
                return str(config.root / 'settings.json')

            def _steam_root(self):
                return str(config.steam)

            def _hub_index(self):
                return {'cards': {}}

            def _translate(self, *args):
                return None

            @staticmethod
            def _power_sync():
                if os.name == 'nt':
                    import ctypes
                    class Power(ctypes.Structure):
                        _fields_ = [('ac', ctypes.c_byte), ('flags', ctypes.c_byte), ('percent', ctypes.c_byte),
                                    ('reserved', ctypes.c_byte), ('life', ctypes.c_uint32), ('full', ctypes.c_uint32)]
                    power = Power()
                    if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(power)):
                        return {'ac': power.ac == 1, 'battery': power.percent if 0 <= power.percent <= 100 else None}
                return {'ac': True, 'battery': None}

            async def get_protondb(self, appid):
                return {'tier': None}  # Linux compatibility badge is irrelevant here

            async def ensure_blank_movie(self):
                return False  # Windows install changes only the disclosed debugging flag

            async def get_aliases(self):
                return {}

            async def get_music_map(self):
                return {}

            async def get_music_files(self):
                return {}

            async def check_update(self, force=False):
                from public_update import PublicUpdater
                return await asyncio.get_running_loop().run_in_executor(None, lambda: PublicUpdater(config.root).check(bool(force)))

        self.plugin = PCPlugin()
        self.loop = asyncio.new_event_loop()
        self.worker = threading.Thread(target=self.loop.run_forever, name='backend', daemon=True)
        self.worker.start()
        self.call('_main', [], internal=True)
        target = config.data / 'icons'
        target.mkdir(exist_ok=True)
        for file in (config.plugin / 'assets/icons').glob('*.svg'):
            shutil.copyfile(file, target / file.name)

    def call(self, method, args, internal=False):
        if not isinstance(args, list) or len(args) > 8 or (not internal and method not in self.PUBLIC):
            raise ValueError('Unknown public method or invalid arguments')
        with self.gate:
            future = asyncio.run_coroutine_threadsafe(getattr(self.plugin, method)(*args), self.loop)
            try:
                result = future.result(timeout=55)
                json.dumps(result, allow_nan=False)
                return result
            except concurrent.futures.TimeoutError:
                future.cancel()
                raise

    def close(self):
        try:
            self.call('_unload', [], internal=True)
        finally:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.worker.join(3)
            if not self.worker.is_alive():
                self.loop.close()


class Session:
    def __init__(self, url, backend, pool):
        import ws_min
        self.ws = ws_min.create_connection(url, timeout=10, suppress_origin=True, enable_multithread=True)
        self.ws.settimeout(None)
        self.backend, self.pool = backend, pool
        self.lock, self.seq, self.waiting = threading.Lock(), 0, {}
        self.alive = True
        self.reader = threading.Thread(target=self.read_loop, name='cdp', daemon=True)
        self.reader.start()

    def send(self, method, params=None, timeout=30, wait=True):
        with self.lock:
            self.seq += 1
            mid = self.seq
            future = concurrent.futures.Future() if wait else None
            if future:
                self.waiting[mid] = future
            try:
                self.ws.send(json.dumps({'id': mid, 'method': method, 'params': params or {}}))
            except Exception:
                self.waiting.pop(mid, None)
                raise
        try:
            return future.result(timeout=timeout) if future else None
        finally:
            if future:
                with self.lock:
                    self.waiting.pop(mid, None)

    def evaluate(self, expression, timeout=30):
        answer = self.send('Runtime.evaluate', {'expression': expression, 'returnByValue': True, 'awaitPromise': True}, timeout)
        if answer.get('error') or (answer.get('result') or {}).get('exceptionDetails'):
            raise RuntimeError('Steam Runtime.evaluate failed')
        return ((answer.get('result') or {}).get('result') or {}).get('value')

    def read_loop(self):
        try:
            while self.alive:
                msg = json.loads(self.ws.recv())
                if 'id' in msg:
                    with self.lock:
                        future = self.waiting.pop(msg['id'], None)
                    if future and not future.done():
                        future.set_result(msg)
                elif msg.get('method') == 'Runtime.bindingCalled' and msg.get('params', {}).get('name') == '__ghBridge':
                    self.pool.submit(self.handle, msg['params'].get('payload', '{}'))
        except Exception as error:
            log.info('CDP disconnected (%s)', type(error).__name__)
        finally:
            self.alive = False
            with self.lock:
                pending, self.waiting = self.waiting, {}
            for future in pending.values():
                if not future.done():
                    future.set_exception(ConnectionError('CDP closed'))

    def handle(self, payload):
        try:
            if len(payload) > 65536:
                return
            request = json.loads(payload)
            mid = int(request['id'])
            if mid < 0 or mid > 2**53:
                return
            try:
                value = self.backend.call(request.get('method'), request.get('args') or [])
                ok = True
            except Exception as error:
                log.warning('RPC %s failed (%s)', request.get('method'), type(error).__name__)
                value, ok = type(error).__name__ + ': request failed', False
            self.send('Runtime.evaluate', {'expression': 'window.__ghPC && window.__ghPC.reply(%s,%s,%s)' %
                       (mid, json.dumps(ok), json.dumps(value, ensure_ascii=False))}, wait=False)
        except Exception:
            pass

    def close(self):
        self.alive = False
        self.ws.close()
        if threading.current_thread() is not self.reader:
            self.reader.join(2)


READY_JS = '!!(window.webpackChunksteamui && window.SteamUIStore && window.appStore && window.appDetailsStore)'


def shared_ctx_ws(config):
    try:
        with urllib.request.urlopen(config.cef + '/json', timeout=3) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            return None
        for target in json.loads(raw):
            if target.get('title') == 'SharedJSContext':
                url = target.get('webSocketDebuggerUrl', '')
                parsed = urllib.parse.urlsplit(url)
                if parsed.scheme == 'ws' and parsed.hostname in ('127.0.0.1', 'localhost') and parsed.port == config.cdp_port:
                    return url
    except Exception:
        pass
    return None


def update_once(config, backend, stop_event):
    """Prepare one verified release update and let a detached helper apply it.

    The helper receives this service's exact PID and starts only after this
    process has exited, so it never swaps files underneath a live interpreter.
    """
    from public_update import PublicUpdater
    updater = PublicUpdater(config.root)
    info = updater.check()
    if not info.get('available') or getattr(backend.plugin, '_media_game_running', False):
        return False
    archive = updater.download(info)
    if stop_event.is_set() or getattr(backend.plugin, '_media_game_running', False):
        return False
    updater.spawn_helper(archive, info['sha256'], wait_pid=os.getpid())
    stop_event.set()
    return True


def serve(config, stop_event=None):
    config.root.mkdir(parents=True, exist_ok=True)
    instance_lock = ServiceLock(config.root)
    if not instance_lock.acquire():
        log.info('Another Continue service instance is already running')
        return 0
    try:
        return _serve_locked(config, stop_event)
    finally:
        instance_lock.close()


def _serve_locked(config, stop_event=None):
    config.data.mkdir(exist_ok=True)
    stop_event = stop_event or threading.Event()
    try:
        server = media_server(config.data, config.media_port, config.token, stop_event, config.version)
    except OSError:
        log.info('Media port %s occupied; this instance exits', config.media_port)
        return 0
    backend, session = None, None
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix='bridge')
    worker = threading.Thread(target=server.serve_forever, name='media', daemon=True)
    worker.start()
    try:
        backend = Backend(config)
        bundle, version = build_bundle(config)
        write_json(config.ready, {'pid': os.getpid(), 'version': config.version, 'at': time.time(), 'token': config.token,
                                 'nonce': os.environ.get('CONTINUE_UPDATE_NONCE', ''),
                                 'media_port': config.media_port, 'cdp_port': config.cdp_port})
        log.info('Ready version=%s media=%s', config.version, config.media_port)
        update_busy = threading.Event()

        def update_tick():
            try:
                update_once(config, backend, stop_event)
            except Exception as error:
                log.info('Update deferred (%s)', type(error).__name__)
            finally:
                update_busy.clear()

        next_update = time.monotonic() + 60
        url_seen, failed = None, None
        while not stop_event.is_set():
            if time.monotonic() >= next_update and not update_busy.is_set():
                next_update = time.monotonic() + 86400
                update_busy.set()
                threading.Thread(target=update_tick, name='update', daemon=True).start()
            try:
                url = shared_ctx_ws(config)
                if not url:
                    if session:
                        session.close()
                    session = None
                else:
                    if session is None or not session.alive or url != url_seen:
                        if session:
                            session.close()
                        session = Session(url, backend, pool)
                        url_seen, failed = url, None
                        session.send('Runtime.addBinding', {'name': '__ghBridge'})
                    if session.evaluate(READY_JS) and session.evaluate('window.__ghPC && window.__ghPC.ver') != version and failed != (url, version):
                        try:
                            session.evaluate(bundle, timeout=60)
                            write_json(config.root / 'injected.json', {'ver': version, 'at': time.time()})
                            log.info('Injected bundle %s', version)
                        except RuntimeError:
                            failed = (url, version)
                            log.warning('Injection failed; retry after reconnect')
            except Exception as error:
                log.info('Waiting for Steam (%s)', type(error).__name__)
                if session:
                    session.close()
                session = None
            stop_event.wait(3)
        return 0
    finally:
        if session:
            session.close()
        if backend:
            backend.close()
        pool.shutdown(wait=True, cancel_futures=True)
        server.shutdown()
        server.server_close()
        worker.join(3)
        if read_json(config.ready).get('pid') == os.getpid():
            config.ready.unlink(missing_ok=True)


def status(root):
    root = Path(root)
    ready = read_json(root / 'service_ready.json')
    manifest = read_json(root / 'install.json')
    app = root / 'app'
    result = {'version': read_json(app / 'RELEASE.json').get('version'), 'service_alive': False,
              'cdp_answering': False, 'steam_running': None, 'last_log': str(root / 'logs/bp.log'),
              'cache_bytes': sum(p.stat().st_size for p in (root / 'data').rglob('*') if p.is_file()), 'hints': []}
    try:
        with urllib.request.urlopen('http://127.0.0.1:%s/__continue_health' % int(ready.get('media_port', 8793)), timeout=2) as response:
            health = json.loads(response.read(8192))
        result['service_alive'] = health.get('service') == 'ContinueBigPicture' and health.get('pid') == ready.get('pid')
        if not result['service_alive']:
            result['hints'].append('Media port belongs to another instance/program')
    except Exception:
        result['hints'].append('Service is not answering; run setup.cmd to repair')
    try:
        with urllib.request.urlopen('http://127.0.0.1:%s/json' % int(ready.get('cdp_port', 8080)), timeout=2) as response:
            targets = json.loads(response.read(2 * 1024 * 1024))
        result['cdp_answering'] = isinstance(targets, list) and any(t.get('title') == 'SharedJSContext' for t in targets)
        if not result['cdp_answering']:
            result['hints'].append('CDP port is occupied by another program or Steam has changed')
    except Exception:
        steam = Path(manifest.get('steam_path') or manifest.get('steam') or '.')
        flag = (steam / '.cef-enable-remote-debugging').is_file()
        if os.name == 'nt':
            import ctypes
            # Process discovery is read-only; status.ps1 supplies the human Steam hint.
        result['hints'].append('Steam is closed, or the debugging flag requires a Steam restart' if flag else 'Steam debugging flag is absent')
    return result


def stop_service(root):
    ready = read_json(Path(root) / 'service_ready.json')
    if not ready.get('token'):
        return False
    request = urllib.request.Request('http://127.0.0.1:%s/__continue_stop' % int(ready['media_port']), data=b'',
                                     headers={'X-Continue-Token': ready['token']})
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status == 204
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs='?', default='run', choices=['run', 'stop', 'status', 'bundle'])
    parser.add_argument('--app', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--steam', type=Path)
    parser.add_argument('--cdp-port', type=int, default=8080)
    parser.add_argument('--media-port', type=int, default=8793)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    root = args.root or Path(os.environ['LOCALAPPDATA']) / 'Continue'
    if args.command == 'stop':
        return 0 if stop_service(root) else 1
    if args.command == 'status':
        if sys.stdout:
            print(json.dumps(status(root), ensure_ascii=False, indent=2))
        return 0
    config = Config(args.app, root, args.steam, args.cdp_port, args.media_port)
    setup_logging(config)
    if args.command == 'bundle':
        bundle, version = build_bundle(config)
        (config.root / 'bundle.js').write_text(bundle, encoding='utf-8', newline='\n')
        if sys.stdout:
            print(version, len(bundle))
        return 0
    return serve(config)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        log.exception('Service startup failed (%s)', type(error).__name__)
        if sys.stderr:
            print('Continue? startup failed: %s' % error, file=sys.stderr)
        raise SystemExit(1)
