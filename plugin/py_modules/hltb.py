"""HowLongToBeat: сколько идёт сюжет / сюжет+доп. / 100%. Кэш на диске — офлайн берём оттуда.

С 09.2026 /api/search/site/init отдаёт только {"token"} — поиск принимает один x-auth-token
(проверено 01.10.2026). Русские названия из библиотеки HLTB не находит, поэтому для них
берём английское имя из Steam Store (appdetails?l=english).
"""
import difflib, json, os, re, ssl, time, tempfile

import aiohttp

try:
    import certifi
    SSL = ssl.create_default_context(cafile=certifi.where())
except Exception:  # pragma: no cover
    SSL = ssl.create_default_context()

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
BASE = {"Content-Type": "application/json", "Origin": "https://howlongtobeat.com", "Referer": "https://howlongtobeat.com/", "User-Agent": UA}
TTL = 30 * 86400
MISS_TTL = 3 * 86400


def norm(s):
    s = re.sub(r"[™®©]", "", str(s or "")).lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


class HLTB:
    def __init__(self, data_dir):
        self.path = os.path.join(data_dir, "hltb.json")
        try:
            with open(self.path, encoding="utf-8") as stream:
                self.cache = json.load(stream)
        except Exception:
            self.cache = {}

    def cached(self, appid):
        e = self.cache.get(str(appid))
        return e if e and e.get("main") else None

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix="hltb.", suffix=".tmp", dir=os.path.dirname(self.path))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(self.cache, stream, ensure_ascii=False, indent=1)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    async def _english_name(self, session, appid):
        if int(appid) > 2**31:  # ярлык не из Steam
            return None
        try:
            async with session.get(f"https://store.steampowered.com/api/appdetails?appids={appid}&l=english&filters=basic",
                                   ssl=SSL, timeout=aiohttp.ClientTimeout(total=10)) as r:
                js = await r.json(content_type=None)
            return ((js or {}).get(str(appid)) or {}).get("data", {}).get("name")
        except Exception:
            return None

    async def _search(self, session, name):
        async with session.get(f"https://howlongtobeat.com/api/search/site/init?t={int(time.time() * 1000)}", headers=BASE,
                               ssl=SSL, timeout=aiohttp.ClientTimeout(total=15)) as r:
            token = (await r.json(content_type=None)).get("token")
        body = {"searchType": "games", "searchTerms": norm(name).split(), "searchPage": 1, "size": 10,
                "searchOptions": {"games": {"userId": 0, "platform": "", "sortCategory": "popular", "rangeCategory": "main",
                                            "rangeTime": {"min": 0, "max": 0},
                                            "gameplay": {"perspective": "", "flow": "", "genre": "", "difficulty": ""},
                                            "modifier": "hide_dlc"}, "users": {}, "filter": "", "sort": 0, "randomizer": 0}}
        async with session.post("https://howlongtobeat.com/api/search/site", headers={**BASE, "x-auth-token": token or ""},
                                json=body, ssl=SSL, timeout=aiohttp.ClientTimeout(total=15)) as r:
            return (await r.json(content_type=None)).get("data") or []

    @staticmethod
    def _best(results, name):
        n = norm(name)
        scored = []
        for g in results:
            cand = [norm(g.get("game_name")), norm(g.get("game_alias"))]
            score = max(difflib.SequenceMatcher(None, n, c).ratio() for c in cand if c) if any(cand) else 0
            scored.append((score, g))
        scored.sort(key=lambda x: -x[0])
        return scored[0] if scored and scored[0][0] >= 0.6 else (None, None)

    async def get(self, appid, name, force=False):
        key = str(appid)
        e = self.cache.get(key)
        if e and not force:
            age = time.time() - e.get("fetched_at", 0)
            if (e.get("main") and age < TTL) or (not e.get("main") and age < MISS_TTL):
                return e if e.get("main") else None
        async with aiohttp.ClientSession(headers={"User-Agent": UA}) as s:
            tried = []
            for q in [name, await self._english_name(s, appid)]:
                if not q or norm(q) in tried:
                    continue
                tried.append(norm(q))
                try:
                    score, g = self._best(await self._search(s, q), q)
                except Exception:
                    return e if e and e.get("main") else None  # нет сети — отдаём что было
                if g:
                    h = lambda sec: round(sec / 3600, 1) if sec else None
                    e = {"main": h(g.get("comp_main")), "extra": h(g.get("comp_plus")), "complete": h(g.get("comp_100")),
                         "game_id": g.get("game_id"), "name": g.get("game_name"), "match": round(score, 2), "fetched_at": time.time()}
                    self.cache[key] = e
                    self._save()
                    return e
        self.cache[key] = {"fetched_at": time.time(), "miss": tried}
        self._save()
        return None
