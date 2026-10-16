"""Apply packaged themes to native Steam Big Picture windows; stop restores them."""
import hashlib
import json
import logging
import re
import threading
import urllib.parse
import urllib.request

log = logging.getLogger('continue_pc')
STYLE_ID = 'continue-pc-themes'
CLASSES_JS = """(()=>{let req;window.webpackChunksteamui.push([[Symbol('continue-css')],{},r=>{req=r}]);const out=new Set();
for(const id of Object.keys(req.m)){let m;try{m=req(id)}catch(e){continue}if(!m||typeof m!=='object')continue;
const ks=Object.keys(m);if(!ks.length||!ks.every(k=>typeof m[k]==='string'))continue;
for(const k of ks)for(const c of m[k].split(' '))if(c.length&&c.length<=256&&out.size<50000)out.add(c)}return [...out]})()"""

def window_kind(title):
    if title in ('SP', 'Steam Big Picture Mode', 'Big Picture Mode', 'Режим Big Picture', 'bigpicture'):
        return 'bp'
    if re.fullmatch(r'MainMenu(?:_[A-Za-z0-9_-]+)?', title):
        return 'menu'
    if re.fullmatch(r'QuickAccess(?:_[A-Za-z0-9_-]+)?', title):
        return 'qam'
    return None

def local_ws(url, port):
    try:
        p = urllib.parse.urlparse(url)
        return p.scheme == 'ws' and p.hostname in ('127.0.0.1', 'localhost') and p.port == port and not p.username and not p.password and p.path.startswith('/devtools/')
    except (ValueError, TypeError):
        return False

def style_expression(css, version):
    return "(()=>{let s=document.getElementById(%s);if(!s){s=document.createElement('style');s.id=%s;document.head.appendChild(s)}s.textContent=%s;s.dataset.v=%s;document.head.appendChild(s)})()" % (json.dumps(STYLE_ID),json.dumps(STYLE_ID),json.dumps(css),json.dumps(version))

class ThemeInjector:
    def __init__(self, config, backend):
        self.config, self.backend = config, backend
        self.stop = threading.Event()
        self.classes, self.classes_url = [], None
        self.thread = threading.Thread(target=self.loop, name='pc-themes', daemon=True)
        self.thread.start()

    def targets(self):
        with urllib.request.urlopen(self.config.cef + '/json', timeout=3) as r:
            raw = r.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            return []
        value = json.loads(raw)
        return value[:128] if isinstance(value, list) else []

    def evaluate(self, url, expression):
        if not local_ws(url, self.config.cdp_port):
            raise ValueError('Steam loopback target required')
        import ws_min
        ws = ws_min.create_connection(url, timeout=3, suppress_origin=True)
        try:
            ws.send(json.dumps({'id':1,'method':'Runtime.evaluate','params':{'expression':expression,'returnByValue':True}}))
            for _ in range(64):
                response = json.loads(ws.recv())
                if response.get('id') == 1:
                    return ((response.get('result') or {}).get('result') or {}).get('value')
            raise RuntimeError('Steam response limit')
        finally:
            ws.close()

    def tick(self):
        targets = self.targets()
        shared = next((t.get('webSocketDebuggerUrl') for t in targets if t.get('title') == 'SharedJSContext'), None)
        if shared and shared != self.classes_url:
            classes = self.evaluate(shared, CLASSES_JS)
            if isinstance(classes, list) and classes:
                self.classes = [s for s in classes[:50000] if isinstance(s, str) and 1 <= len(s) <= 256]
                self.classes_url = shared
        css = self.backend.call('themes_css', [self.classes])
        for target in targets:
            if self.stop.is_set():
                break
            kind, url = window_kind(target.get('title') or ''), target.get('webSocketDebuggerUrl')
            if not kind or not local_ws(url, self.config.cdp_port):
                continue
            text = css.get(kind) or ''
            version = hashlib.sha256(text.encode()).hexdigest()[:12]
            current = self.evaluate(url, "(()=>{const s=document.getElementById(%s);return s&&s===s.parentNode.lastElementChild?s.dataset.v:null})()" % json.dumps(STYLE_ID))
            if current != version:
                self.evaluate(url, style_expression(text, version))

    def loop(self):
        while not self.stop.is_set():
            try:
                self.tick()
            except Exception as error:
                log.debug('Theme deferred (%s)', type(error).__name__)
            self.stop.wait(3)

    def close(self):
        self.stop.set()
        self.thread.join(5)
        try:
            for target in self.targets():
                url = target.get('webSocketDebuggerUrl')
                if window_kind(target.get('title') or '') and local_ws(url, self.config.cdp_port):
                    self.evaluate(url, "document.getElementById(%s)?.remove()" % json.dumps(STYLE_ID))
        except Exception as error:
            log.debug('Theme cleanup deferred (%s)', type(error).__name__)
