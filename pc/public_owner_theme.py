"""Opt-in packaged visuals for an existing card renderer; never creates a game backend.

No bridge bindings, personal imports, task changes or card data calls.
Optional local recording loops are served from Continue's isolated cache.
The regular public lifecycle owns this process and its authenticated control socket.
"""
from functools import lru_cache
import base64
import hashlib
import hmac
import importlib.util
import json
import logging
import os
from pathlib import Path
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from public_game_assets import ALLOWED_APPIDS, _RU_TO_ID, _canonical_key, _inside_regular, _safe_rel

log = logging.getLogger('continue_pc')
# Exact UI labels from the accepted per-game catalogs' labels sections.
# Visual associations only: no save values, reader code or reader registration.
DS_VISUAL_LABELS = {
    'order_id': ('Order', 'Заказ', 'Замовлення'),
    'order_name': ('Order name', 'Название заказа', 'Назва замовлення'),
    'order_status': ('Order status', 'Статус заказа', 'Статус замовлення'),
    'save_slot_type': ('Save type', 'Тип сохранения', 'Тип збереження'),
    'playtime_seconds': ('Time in this save', 'Время в сохранении', 'Час у збереженні'),
    'episode_number': ('Episode', 'Эпизод', 'Епізод'),
}
STATE_JS = r'''(()=>{const w=window.SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance;
const path=w?.m_history?.location?.pathname||'',m=/^\/library\/app\/(\d+)$/.exec(path);
const d=w?.BrowserWindow?.document,t=window.__continueOwnerTheme;
return {app:m?.[1]||null,ready:!!(window.__ghPC&&typeof window.__ghBridge==='function'&&d?.querySelectorAll('.gh-root').length===1),
active:t?{app:t.app,version:t.version}:null,games:(window.SteamUIStore?.RunningApps||[]).filter(a=>a.app_type!==2).length};})()'''


def _json(path):
    try:
        value = json.loads(Path(path).read_text('utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _png(path, root):
    if not _inside_regular(path, root):
        return None
    raw = path.read_bytes()
    if len(raw) > 2 * 1024 * 1024 or not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        return None
    return 'data:image/png;base64,' + base64.b64encode(raw).decode('ascii')


@lru_cache(maxsize=1)
def _shared_visuals():
    path = Path(__file__).resolve().parent.parent / 'plugin/py_modules/game_visuals.py'
    spec = importlib.util.spec_from_file_location('continue_owner_game_visuals', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=64)
def payload(app_root, app):
    if not isinstance(app, str) or not re.fullmatch(r'[1-9][0-9]{0,9}', app):
        return None
    assets = Path(app_root) / 'pc/assets'
    style = _json(assets / 'game_styles.json').get(app, {})
    # Decorative metadata is independent of save readers and the fact-icon gate.
    if int(app) not in ALLOWED_APPIDS and (not isinstance(style, dict) or not style):
        return None
    visual = _shared_visuals().game_visual(assets, app)
    rail = None
    rel = style.get('rail') if isinstance(style, dict) else None
    if isinstance(rel, str) and re.fullmatch(r'rails/[0-9]+\.png', rel):
        rail = _png(assets / rel, assets)
    elif rel == f'rails/{app}.svg':
        rail = _shared_visuals().game_visual(assets, app).get('rail')
    manifest = _json(assets / 'game_icons/manifest.json').get(app, {}) if int(app) in ALLOWED_APPIDS else {}
    icons = {}
    if isinstance(manifest, dict):
        for label, relative in list(manifest.items())[:400]:
            relative = _safe_rel(relative, int(app))
            if relative and relative.endswith('.png'):
                image = _png(assets / 'game_icons' / relative, assets)
                if image:
                    icons[label] = image
                    icons[_canonical_key(label)] = image
        for label, key in _RU_TO_ID.items():
            if key in icons:
                icons.setdefault(label, icons[key])
        if app in ('1850570', '3280350'):
            for key, labels in DS_VISUAL_LABELS.items():
                if key in icons:
                    for label in labels:
                        icons[label] = icons[key]
    return {'app': app, 'rail': rail, 'icons': icons, 'accent': visual.get('accent')}


def script(app_root, value, version, lease_ms=15000):
    source = (Path(app_root) / 'pc/bp_owner_theme.js').read_text('utf-8')
    return source.replace('/*CONTINUE_THEME_CONFIG*/null', json.dumps(
        {'payload': value, 'version': version, 'leaseMs': lease_ms}, ensure_ascii=True))


@lru_cache(maxsize=64)
def revision(app_root, app, package_version):
    digest = hashlib.sha256((Path(app_root) / 'pc/bp_owner_theme.js').read_bytes())
    digest.update(package_version.encode())
    digest.update(json.dumps(payload(app_root, app), sort_keys=True).encode())
    return digest.hexdigest()[:20]


class ControlHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        if self.path.startswith('/recordings/'):
            from public_owner_recordings import serve_recording
            return serve_recording(self)
        if self.path != '/__continue_health':
            self.send_error(404)
            return
        raw = json.dumps({'service': 'ContinueBigPicture', 'pid': os.getpid(),
                          'version': self.server.version, 'mode': 'owner-theme'}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_HEAD(self):
        from public_owner_recordings import serve_recording
        serve_recording(self, body=False)

    def do_POST(self):
        if self.path != '/__continue_stop' or not hmac.compare_digest(self.headers.get('X-Continue-Token', ''), self.server.token):
            self.send_error(403)
            return
        self.send_response(204)
        self.send_header('Content-Length', '0')
        self.end_headers()
        self.server.stop_event.set()


def serve_theme(config, session_factory, find_ws, write_json, stop_event=None):
    stop_event = stop_event or threading.Event()
    server = ThreadingHTTPServer(('127.0.0.1', 0), ControlHandler)
    server.version, server.token, server.stop_event = config.version, config.token, stop_event
    server.recording_key = secrets.token_hex(32)
    recordings = None
    if getattr(config, 'data', None) and getattr(config, 'steam', None):
        from public_owner_recordings import OwnerRecordings
        recordings = OwnerRecordings(config)
    server.recordings = recordings
    worker = threading.Thread(target=server.serve_forever, name='visual-control', daemon=True)
    worker.start()
    session, url_seen = None, None
    write_json(config.ready, {'pid': os.getpid(), 'version': config.version, 'mode': 'owner-theme',
        'at': time.time(), 'token': config.token, 'nonce': os.environ.get('CONTINUE_UPDATE_NONCE', ''),
        'media_port': server.server_address[1], 'cdp_port': config.cdp_port})
    log.info('Ready version=%s mode=owner-theme control=%s', config.version, server.server_address[1])
    try:
        while not stop_event.is_set():
            try:
                url = find_ws(config)
                if session and (not session.alive or url != url_seen):
                    session.close()
                    session = None
                if url:
                    if session is None:
                        session = session_factory(url, None, None)
                        url_seen = url
                    state = session.evaluate(STATE_JS, timeout=5)
                    recording = recordings.request((state or {}).get('app'), games=(state or {}).get('games', 1)) if recordings else None
                    if state and state.get('ready') and state.get('app'):
                        value = payload(config.app, state['app'])
                        if recording:
                            recording = recording.replace('?v=', '?key=' + server.recording_key + '&v=')
                            value = dict(value or {'app': state['app'], 'rail': None, 'icons': {}, 'accent': None},
                                         recording=f'http://127.0.0.1:{server.server_address[1]}' + recording)
                        if value and (value['rail'] or value['icons'] or recording):
                            version = revision(config.app, state['app'], config.version)
                            version += hashlib.sha256(str(recording).encode()).hexdigest()[:12]
                            if state.get('active') == {'app': value['app'], 'version': version}:
                                session.evaluate('window.__continueOwnerTheme?.renew()', timeout=5)
                            else:
                                result = session.evaluate(script(config.app, value, version), timeout=5)
                                write_json(config.root / 'injected.json', {'mode': 'owner-theme', 'ver': version, 'app': value['app'], 'result': result, 'at': time.time()})
            except Exception as error:
                if recordings:
                    recordings.playing = True
                log.info('Visuals waiting for Steam (%s)', type(error).__name__)
                if session:
                    session.close()
                session = None
            stop_event.wait(1)
        return 0
    finally:
        if recordings:
            recordings.close()
        if session:
            try:
                session.evaluate('window.__continueOwnerTheme?.unload()', timeout=3)
            except Exception:
                pass  # the browser lease also cleans up after a disconnected process
            session.close()
        server.shutdown()
        server.server_close()
        worker.join(2)
        config.ready.unlink(missing_ok=True)
