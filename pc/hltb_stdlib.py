"""Optional HowLongToBeat metadata using only Python's standard library."""
import asyncio
import difflib
import json
import os
import re
import threading
import time
import urllib.request

UA = 'Continue-PC/0.1'
BASE = {'Content-Type': 'application/json', 'Origin': 'https://howlongtobeat.com',
        'Referer': 'https://howlongtobeat.com/', 'User-Agent': UA}


def norm(value):
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', ' ', str(value or '').lower())).strip()


class HLTB:
    def __init__(self, data_dir):
        self.path = os.path.join(data_dir, 'hltb.json')
        self.lock = threading.Lock()
        try:
            with open(self.path, encoding='utf-8') as stream:
                self.cache = json.load(stream)
            if not isinstance(self.cache, dict):
                self.cache = {}
        except (OSError, ValueError):
            self.cache = {}

    def cached(self, appid):
        entry = self.cache.get(str(appid))
        return entry if isinstance(entry, dict) and entry.get('main') else None

    @staticmethod
    def _json(url, headers=None, data=None):
        request = urllib.request.Request(url, headers=headers or BASE, data=data)
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise ValueError('HLTB response too large')
            return json.loads(raw)

    def _lookup(self, appid, name, force):
        with self.lock:
            key = str(appid)
            old = self.cache.get(key) or {}
            if not force and time.time() - old.get('fetched_at', 0) < (30 if old.get('main') else 3) * 86400:
                return old if old.get('main') else None
            try:
                candidates = [name]
                if 0 < int(appid) < 2**31:
                    store = self._json('https://store.steampowered.com/api/appdetails?appids=%s&l=english&filters=basic' % int(appid))
                    candidates.append(((store.get(key) or {}).get('data') or {}).get('name'))
                for query in dict.fromkeys(norm(x) for x in candidates if x):
                    token = self._json('https://howlongtobeat.com/api/search/site/init?t=%s' % int(time.time() * 1000)).get('token')
                    body = {'searchType': 'games', 'searchTerms': query.split(), 'searchPage': 1, 'size': 10,
                            'searchOptions': {'games': {'userId': 0, 'platform': '', 'sortCategory': 'popular',
                            'rangeCategory': 'main', 'rangeTime': {'min': 0, 'max': 0},
                            'gameplay': {'perspective': '', 'flow': '', 'genre': '', 'difficulty': ''},
                            'modifier': 'hide_dlc'}, 'users': {}, 'filter': '', 'sort': 0, 'randomizer': 0}}
                    results = self._json('https://howlongtobeat.com/api/search/site',
                                         {**BASE, 'x-auth-token': token or ''}, json.dumps(body).encode())
                    ranked = []
                    for item in results.get('data') or []:
                        score = max((difflib.SequenceMatcher(None, query, norm(item.get(k))).ratio()
                                     for k in ('game_name', 'game_alias')), default=0)
                        ranked.append((score, item))
                    if ranked and max(x[0] for x in ranked) >= .6:
                        score, game = max(ranked, key=lambda x: x[0])
                        hours = lambda field: round(game[field] / 3600, 1) if game.get(field) else None
                        entry = {'main': hours('comp_main'), 'extra': hours('comp_plus'), 'complete': hours('comp_100'),
                                 'game_id': game.get('game_id'), 'name': game.get('game_name'),
                                 'match': round(score, 2), 'fetched_at': time.time()}
                        self.cache[key] = entry
                        self._save()
                        return entry
                self.cache[key] = {'fetched_at': time.time()}
                self._save()
            except Exception:
                return old if old.get('main') else None
            return None

    def _save(self):
        try:
            with open(self.path + '.tmp', 'w', encoding='utf-8', newline='\n') as stream:
                json.dump(self.cache, stream, ensure_ascii=False)
            os.replace(self.path + '.tmp', self.path)
        except OSError:
            pass

    async def get(self, appid, name, force=False):
        return await asyncio.get_running_loop().run_in_executor(None, self._lookup, int(appid), name, bool(force))
