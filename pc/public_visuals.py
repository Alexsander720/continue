"""Bounded optional Steam 2x hero cache for the existing PC header treatment."""
import concurrent.futures
import json
import threading
import time
import urllib.request
from pathlib import Path

MAX_IMAGE = 16 * 1024 * 1024
class SteamOnlyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        from urllib.parse import urlparse
        p = urlparse(newurl)
        if p.scheme != 'https' or p.hostname != 'shared.steamstatic.com' or p.username or p.port not in (None,443):
            raise ValueError('Steam image redirect rejected')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

class PublicVisuals:
    METHODS = {'get_hero4k'}
    def __init__(self, root, media_factory, work_allowed):
        self.root, self.media_factory, self.work_allowed = Path(root), media_factory, work_allowed
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix='pc-hero')
        self.lock, self.jobs, self.misses, self.closed = threading.Lock(), set(), {}, False

    def call(self, method, args):
        if method != 'get_hero4k' or len(args) != 1 or type(args[0]) is not int or not 1 <= args[0] <= 0xffffffff:
            raise ValueError('Invalid Steam hero request')
        appid = args[0]
        manager = self.media_factory()
        path = manager.media / f'{appid}_hero.jpg'
        if path.is_file() and not path.is_symlink() and 50000 < path.stat().st_size <= MAX_IMAGE:
            return {'file':manager._relative(path),'pending':False}
        with self.lock:
            if self.closed or appid >= 0x80000000 or not self.work_allowed() or time.time()-self.misses.get(appid,0) < 86400:
                return {'file':None,'pending':False}
            if appid not in self.jobs and len(self.jobs) < 2:
                self.jobs.add(appid)
                self.pool.submit(self.fetch, appid)
            return {'file':None,'pending':appid in self.jobs}

    def fetch(self, appid):
        try:
            if self.closed or not self.work_allowed():
                return
            manager = self.media_factory()
            settings = json.loads((self.root/'settings.json').read_text(encoding='utf-8')) if (self.root/'settings.json').exists() else {}
            manager._configure(settings)
            # Same media budget as videos/music; do not exceed it for header art.
            if manager._cache_bytes() + MAX_IMAGE > manager._limit_bytes:
                return
            url=f'https://shared.steamstatic.com/store_item_assets/steam/apps/{appid}/library_hero_2x.jpg'
            opener=urllib.request.build_opener(SteamOnlyRedirect())
            with opener.open(urllib.request.Request(url,headers={'User-Agent':'ContinuePC/1.0'}),timeout=15) as response:
                data=response.read(MAX_IMAGE+1)
            if len(data)>MAX_IMAGE or len(data)<50000 or not data.startswith(b'\xff\xd8\xff'):
                return
            if self.closed or not self.work_allowed():
                return
            manager.media.mkdir(exist_ok=True,parents=True)
            path=manager.media/f'{appid}_hero.jpg'
            if path.is_symlink():
                return
            tmp=path.with_suffix('.tmp')
            tmp.write_bytes(data)
            tmp.replace(path)
        except (OSError,ValueError):
            with self.lock:
                self.misses[appid]=time.time()
                if len(self.misses)>512:
                    self.misses.pop(next(iter(self.misses)))
        finally:
            with self.lock:
                self.jobs.discard(appid)

    def close(self):
        self.closed=True
        self.pool.shutdown(wait=False,cancel_futures=True)
