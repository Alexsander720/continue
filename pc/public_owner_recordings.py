"""Local recordings for the leased owner-theme decorator; no personal imports."""
import json
import hmac
import logging
from pathlib import Path
import re
import sys
import threading
import time

from public_game_assets import _inside_regular

log = logging.getLogger('continue_pc')
# Bump when the selection/encoding changes so every cached background is rebuilt.
RECORDING_ALGORITHM = 2


class OwnerRecordings:
    def __init__(self, config, *, manager_factory=None):
        # Owner-theme bypasses Backend, which normally adds the packaged shared
        # directory. Never resolve these modules from the personal installation.
        shared = str((config.plugin / 'py_modules').resolve())
        if shared not in sys.path:
            sys.path.insert(0, shared)
        from public_media_policy import PCMediaManager
        from public_media_runtime import MediaRuntime
        self.config = config
        self.stopped = threading.Event()
        self.playing = True  # Wait for a current Steam running-apps observation.
        self.selected = None
        self.working = None
        self.worker = None
        self.next_attempt = {}
        self.gate = threading.Lock()
        self.manager = (manager_factory or PCMediaManager)(
            config.data / 'owner-recordings', plugin_dir=config.plugin,
            allowed=lambda: not self.stopped.is_set() and not self.playing and self.selected == self.working)
        if manager_factory is None:
            self.manager.runtime = MediaRuntime(config.data)
        self.media = self.manager.media
        self.manager._steam_roots = lambda: [config.steam]

    def request(self, app, *, games):
        self.playing = bool(games)
        self.selected = app
        if self.playing or not isinstance(app, str) or not re.fullmatch(r'[1-9][0-9]{0,9}', app):
            return None
        try:
            settings = json.loads((self.config.root / 'settings.json').read_text('utf-8'))
            if not isinstance(settings, dict):
                return None
        except FileNotFoundError:
            settings = {}
        except (OSError, ValueError):
            return None
        if settings.get('recording_enabled') is False or settings.get('live_bg') == 'off' or (settings.get('game_bg') or {}).get(app) in ('image', 'steam'):
            return None
        cached = self.manager._asset(int(app), 'recording')
        relative = f'/recordings/{app}.mp4?v={cached.stat().st_mtime_ns}' if cached else None
        # A local cache stays usable through scan/conversion failures. Rebuild
        # when Steam's newest completed recording changes, at most once/minute.
        with self.gate:
            if self.stopped.is_set() or self.working or time.monotonic() < self.next_attempt.get(app, 0):
                return relative
            self.working = app
            self.next_attempt[app] = time.monotonic() + 60
            self.worker = threading.Thread(target=self._build, args=(app, settings), name='owner-recording', daemon=True)
            self.worker.start()
        return relative

    def _build(self, app, settings):
        try:
            manager = self.manager
            manager._operation_deadline = time.monotonic() + 600
            manager._configure(settings)
            # The standard worker already restricts all writes to its own data.
            # No remote source, tool installation, music or personal backend.
            if hasattr(manager, 'recording_candidates'):
                candidates = manager.recording_candidates(int(app))
                signature = [[str(p), p.stat().st_mtime_ns,
                              max((c.stat().st_mtime_ns for c in p.parent.glob('chunk-stream0-*.m4s')), default=0)] for p in candidates]
                receipt = manager.data / f'{app}-recording.json'
                try:
                    prior = json.loads(receipt.read_text('utf-8'))
                except (OSError, ValueError):
                    prior = {}
                if not candidates or (manager._asset(int(app), 'recording') and prior.get('signature') == signature
                                                                     and prior.get('algorithm') == RECORDING_ALGORITHM):
                    return
            else:
                signature, receipt = [], None
            # Use the same bounded scratch reservation as the full public
            # worker, inside this adapter's cache only. No provider/music jobs.
            manager._checkpoint()
            manager._reserve_job(int(app))
            result = manager.build_recording(int(app), app, dict(settings, recording_enabled=True,
                preset=str(settings.get('media_quality') or settings.get('preset') or 'light')))
            if result.get('ok'):
                manager.enforce_limit(settings.get('disk_limit_gb', 2))
            if result.get('ok') and receipt:
                manager._atomic_json(receipt, {'signature': signature, 'algorithm': RECORDING_ALGORITHM, 'result': result})
            log.info('Local recording app=%s ready=%s selection=%s', app, result.get('ok'), result.get('selection'))
        except Exception as error:
            log.info('Local recording app=%s waiting (%s)', app, type(error).__name__)
        finally:
            with self.gate:
                self.working = None

    def close(self):
        self.stopped.set()
        if self.worker:
            self.worker.join(8)


def serve_recording(handler, *, body=True):
    """Serve only known Continue cached MP4 names, including CEF byte ranges."""
    match = re.fullmatch(r'/recordings/([1-9][0-9]{0,9})\.mp4(?:\?key=([a-f0-9]{64})(?:&v=[0-9]+)?)?', handler.path)
    adapter = getattr(handler.server, 'recordings', None)
    if not match or adapter is None:
        handler.send_error(404)
        return
    if not hmac.compare_digest(match[2] or '', getattr(handler.server, 'recording_key', '')) or not match[2]:
        handler.send_error(403)
        return
    root = adapter.media
    path = root / f'{match[1]}_recording.mp4'
    if not _inside_regular(path, root):
        handler.send_error(404)
        return
    try:
        stream = path.open('rb')
    except OSError:
        handler.send_error(404)
        return
    with stream:
        import os
        size = os.fstat(stream.fileno()).st_size
        start, end, partial = 0, size - 1, False
        value = handler.headers.get('Range')
        if value:
            ranges = re.fullmatch(r'bytes=(\d{0,18})-(\d{0,18})', value)
            invalid = not ranges or not any(ranges.groups()) or size == 0
            if not invalid:
                first, last = ranges.groups()
                if first:
                    start = int(first)
                    end = min(int(last), size - 1) if last else size - 1
                else:
                    invalid = int(last) == 0
                    start = max(0, size - int(last))
                invalid = invalid or start > end
            if invalid:
                handler.send_response(416)
                handler.send_header('Content-Range', f'bytes */{size}')
                handler.send_header('Content-Length', '0')
                handler.end_headers()
                return
            partial = True
        handler.send_response(206 if partial else 200)
        if partial:
            handler.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        handler.send_header('Content-Type', 'video/mp4')
        handler.send_header('Content-Length', str(max(0, end-start+1)))
        handler.send_header('Accept-Ranges', 'bytes')
        handler.send_header('Cache-Control', 'no-store')
        handler.send_header('X-Content-Type-Options', 'nosniff')
        handler.end_headers()
        if body:
            try:
                stream.seek(start)
                left = end-start+1
                while left > 0:
                    block = stream.read(min(left, 65536))
                    if not block:
                        break
                    handler.wfile.write(block)
                    left -= len(block)
            except (OSError, ConnectionError):
                pass
