"""Continue? для Steam Deck — бэкенд.

Карточка игры = данные из хаба на ПК (hub_cards.json, кладёт deck_sync.py) + разбор сейвов на самом
Деке (deck_saves) + HLTB. Всё читается с диска, поэтому работает без ПК и без интернета;
сеть нужна только чтобы один раз узнать HLTB новой игры.
"""
import asyncio, glob, hashlib, html, json, os, re, ssl, time, urllib.request
import tempfile
import threading
import urllib.parse

import decky  # type: ignore

import deck_saves
import hubcard
import standalone_media
import ui_i18n
from hltb import HLTB

DATA = decky.DECKY_PLUGIN_RUNTIME_DIR
DEFAULTS = {"home_installed_first": True, "home_live": True, "home_music": True, "live_bg": "always", "hub_music": True, "game_bg": {}, "brightness_bar": True,
            "hide_launch_notice": True, "music_provider": "continue"}
STANDALONE_DEFAULTS = {"standalone": True, "preset": "light", "bg_source": "steam", "game_source": {},
                       "disk_limit_gb": 2, "youtube_consent": False, "recording_enabled": False,
                       "theme_music_consent": False, "home_music": False, "hub_music": False,
                       "home_installed_first": False, "hide_launch_notice": False, "music_provider": "auto"}
BG_MODES = ("auto", "trailer", "gameplay", "image", "steam")
BG_SOURCES = ("steam", "youtube", "recording")

_cache_io_lock = threading.RLock()


def _read_json(path):
    with open(path, encoding="utf-8") as stream:
        value = json.load(stream)
    return value if isinstance(value, dict) else {}


def _atomic_json(path, value):
    """A failed write keeps the last complete cache; unique temps avoid collisions."""
    path = os.fspath(path)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + ".", suffix=".tmp", dir=os.path.dirname(os.path.abspath(path)))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=1)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _appid(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    if not re.fullmatch(r"[1-9][0-9]{0,9}", str(value)):
        return None
    result = int(value)
    return result if result <= 0xFFFFFFFF else None


class Plugin:
    async def _main(self):
        os.makedirs(DATA, exist_ok=True)
        self.hltb = HLTB(DATA)
        self._standalone_media = None
        self._standalone_lock = asyncio.Semaphore(1)
        self._hub = None
        self._hub_mtime = 0
        # Разовая миграция 01.10.2026: живой фон стоит ~0,4 Вт и только на странице игры (замер:
        # 3,1 против 2,7 Вт APU; на время игры видео на паузе) — владелец разрешил «всегда».
        # Свой выбор владельца после этого не трогаем.
        s = await self.get_settings()
        if not self._is_standalone() and not s.get("schema"):
            if s.get("live_bg") in (None, "ac"):
                s["live_bg"] = "always"
            s["schema"] = 1
            self._write_settings(s)
        decky.logger.info("Continue?: старт, данные в %s", DATA)

    async def _unload(self):
        manager = getattr(self, "_standalone_media", None)
        if manager is not None:
            manager.cancel()

    # ───── настройки ─────
    def _settings_path(self):
        return os.path.join(DATA, "settings.json")

    @staticmethod
    def _plugin_dir():
        return os.path.dirname(os.path.abspath(__file__))

    @classmethod
    def _is_standalone(cls):
        return os.path.isfile(os.path.join(cls._plugin_dir(), "RELEASE.json"))

    def _media(self):
        manager = getattr(self, "_standalone_media", None)
        if manager is None:
            manager = standalone_media.MediaManager(DATA, self._plugin_dir(), allowed=self._media_work_allowed)
            self._standalone_media = manager
        return manager

    def _write_settings(self, settings):
        _atomic_json(self._settings_path(), settings)

    async def get_settings(self):
        try:
            saved = _read_json(self._settings_path())
        except Exception:
            saved = {}
        if not isinstance(saved, dict):
            saved = {}
        base = {**DEFAULTS, **STANDALONE_DEFAULTS} if self._is_standalone() else DEFAULTS
        settings = {**base, **saved}
        if self._is_standalone():
            settings["standalone"] = True
            if settings.get("preset") not in standalone_media.PRESETS:
                settings["preset"] = "light"
            if settings.get("bg_source") not in BG_SOURCES:
                settings["bg_source"] = "steam"
            if settings.get("disk_limit_gb") not in (1, 2, 4, 8):
                settings["disk_limit_gb"] = 2
            for key in ("game_source", "game_bg"):
                if not isinstance(settings.get(key), dict):
                    settings[key] = {}
        else:
            settings.pop("standalone", None)
        return settings

    # ───── «без видеозаставки» (03.10): своего выключателя у Steam нет — подставляем пустой ролик как локальную заставку ─────
    def _steam_root(self):
        from ddsaves._common import deck_home
        return str(deck_home() / ".local/share/Steam")

    async def ensure_blank_movie(self):
        """Положить assets/gh_no_startup.webm (0,2 с чёрного) в config/uioverrides/movies Steam; путь для настройки —
        /uioverrides/movies/gh_no_startup.webm (так его видит SteamClient.Customization.GetLocalStartupMovies)."""
        import shutil
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "gh_no_startup.webm")
        dst_dir = os.path.join(self._steam_root(), "config", "uioverrides", "movies")
        try:
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copyfile(src, os.path.join(dst_dir, "gh_no_startup.webm"))
            return True
        except OSError as e:
            decky.logger.warning("blank startup movie: %s", e)
            return False

    async def set_setting(self, key, value):
        s = await self.get_settings()
        if not self._valid_setting(key, value, self._is_standalone()):
            return s
        s[key] = value
        try:
            self._write_settings(s)
        except OSError as e:
            decky.logger.warning("settings: %s", e)
            s["write_error"] = f"{type(e).__name__}: {e}"
        return s

    @staticmethod
    def _valid_setting(key, value, standalone):
        if not isinstance(key, str) or key == "standalone":
            return False
        booleans = {"home_installed_first", "home_live", "home_music", "hub_music", "brightness_bar", "pdb_button", "pdb_tiles", "hide_launch_notice"}
        if key in booleans or (standalone and key == "recording_enabled"):
            return type(value) is bool
        if key in {"youtube_consent", "theme_music_consent"}:
            # Enabling consent requires install_ytdlp(consent=True); revocation is allowed here.
            return standalone and value is False
        enums = {"live_bg": ("ac", "always", "off"), "music_provider": ("auto", "theme", "continue")}
        if standalone:
            enums.update({"preset": tuple(standalone_media.PRESETS), "bg_source": BG_SOURCES})
        if key in enums:
            return isinstance(value, str) and value in enums[key]
        if standalone and key == "disk_limit_gb":
            return type(value) is int and value in (1, 2, 4, 8)
        if key == "game_bg" or (standalone and key == "game_source"):
            modes = BG_MODES if key == "game_bg" else BG_SOURCES
            return (isinstance(value, dict) and len(value) <= 10000
                    and all(isinstance(appid, str) and re.fullmatch(r"[1-9][0-9]{0,9}", appid)
                            and int(appid) <= 0xFFFFFFFF and isinstance(mode, str) and mode in modes
                            for appid, mode in value.items()))
        if key == "startup_movie_prev":
            return (isinstance(value, dict) and set(value) == {"id", "path", "shuffle"}
                    and isinstance(value["id"], str) and re.fullmatch(r"[0-9]{1,20}", value["id"])
                    and isinstance(value["path"], str) and len(value["path"]) <= 4096
                    and type(value["shuffle"]) is bool)
        return False

    async def set_game_bg(self, appid, mode):
        """Фон одной игры: auto | trailer | gameplay | image (картинка хаба) | steam (родная обложка) (auto = как решил хаб + общий переключатель)."""
        appid = _appid(appid)
        if appid is None or mode not in BG_MODES:
            return None
        s = await self.get_settings()
        m = dict(s.get("game_bg") or {})
        if mode == "auto":
            m.pop(str(appid), None)
        else:
            m[str(appid)] = mode
        s["game_bg"] = m
        try:
            self._write_settings(s)
        except OSError as e:
            decky.logger.warning("game background setting: %s", e)
            return None
        return mode

    async def set_game_source(self, appid, source):
        """Select Steam / YouTube / Background Recording for one game (public release only)."""
        appid = _appid(appid)
        if appid is None or not self._is_standalone() or source not in BG_SOURCES:
            return None
        settings = await self.get_settings()
        selected = dict(settings.get("game_source") or {})
        if source == settings.get("bg_source", "steam"):
            selected.pop(str(int(appid)), None)
        else:
            selected[str(int(appid))] = source
        settings["game_source"] = selected
        try:
            self._write_settings(settings)
        except OSError as e:
            decky.logger.warning("game source setting: %s", e)
            return None
        return source

    # ───── о чём игра (Steam Store, кэш на диске: работает офлайн) ─────
    def _about_path(self):
        return os.path.join(DATA, "about.json")

    def _about_cache(self):
        try:
            return _read_json(self._about_path())
        except Exception:
            return {}

    @staticmethod
    def _fetch_about(appid, language="ru"):
        store_language = {"ru": "russian", "uk": "ukrainian", "en": "english"}.get(language, "english")
        url = (f"https://store.steampowered.com/api/appdetails?appids={appid}&l={store_language}"
               "&filters=basic,genres,developers,release_date")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:  # у Python внутри Decky нет системных сертификатов — берём certifi или файл ОС
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            ctx = ssl.create_default_context(cafile="/etc/ssl/certs/ca-certificates.crt")
        with urllib.request.urlopen(req, timeout=8, context=ctx) as response:
            d = json.loads(response.read(1024 * 1024 + 1).decode("utf-8"))
        node = (d.get(str(appid)) or {})
        if not node.get("success"):
            return {"none": True}
        x = node.get("data") or {}
        short = re.sub(r"<[^>]+>", " ", html.unescape(x.get("short_description") or ""))
        short = re.sub(r"\s+", " ", short).strip()
        year = re.search(r"(19|20)\d\d", (x.get("release_date") or {}).get("date") or "")
        return {"short": short, "genres": [g["description"] for g in (x.get("genres") or [])][:3],
                "dev": (x.get("developers") or [""])[0], "year": year.group(0) if year else ""}

    # ───── ProtonDB (04.10, вместо плагина ProtonDB Badges): оценка совместимости с Linux, кэш 3 дня ─────
    _pdb, _pdb_lock = None, None

    async def get_protondb(self, appid):
        """{"tier": platinum|gold|silver|bronze|borked|pending|native|None, "trending", "best", "total", "confidence"}.
        tier=None — отчётов нет. Не-Steam ярлыки (appid ≥ 2^31) — None."""
        appid = _appid(appid)
        if appid is None or appid >= 0x80000000:
            return None
        path = os.path.join(DATA, "protondb.json")
        if Plugin._pdb is None:
            try:
                with open(path, encoding="utf-8") as f:
                    Plugin._pdb = json.load(f)
            except (OSError, ValueError):
                Plugin._pdb = {}
        c = Plugin._pdb.get(str(appid))
        if c and time.time() - c.get("at", 0) < 3 * 86400:
            return c.get("v")
        try:
            v = await asyncio.get_running_loop().run_in_executor(None, self._fetch_protondb, appid)
        except Exception as e:
            decky.logger.info("ProtonDB %s: %s", appid, e)
            return c.get("v") if c else None   # сеть упала — старое лучше пустого
        if self._pdb_lock is None:
            self._pdb_lock = asyncio.Lock()
        async with self._pdb_lock:
            Plugin._pdb[str(appid)] = {"at": time.time(), "v": v}
            try:
                _atomic_json(path, Plugin._pdb)
            except OSError:
                pass
        return v

    @staticmethod
    def _fetch_protondb(appid):
        url = f"https://www.protondb.com/api/v1/reports/summaries/{appid}.json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 GameHubDeck"})
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            ctx = ssl.create_default_context(cafile="/etc/ssl/certs/ca-certificates.crt")
        try:
            with urllib.request.urlopen(req, timeout=8, context=ctx) as response:
                d = json.loads(response.read(1024 * 1024 + 1).decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:   # отчётов нет
                return {"tier": None}
            raise
        return {"tier": d.get("tier"), "trending": d.get("trendingTier"), "best": d.get("bestReportedTier"),
                "total": d.get("total"), "confidence": d.get("confidence")}

    # ───── перевод английских описаний (03.10): Gemini есть только на ПК (steamdeck/about_ru.py) ─────
    # Дека помечает непереведённое в about_need.json, deck_sync переводит на ПК и кладёт about_ru.json; служба ПК
    # переопределяет _translate и переводит сразу.
    @staticmethod
    def _is_english(text):
        letters = [c for c in text or "" if c.isalpha()]
        if len(letters) < 20:
            return False
        return sum(1 for c in letters if "а" <= c.lower() <= "я" or c in "ёЁ") < 0.3 * len(letters)

    def _translate(self, appid, text):
        """Перевод из about_ru.json (готовит ПК); нет — пометить для ПК и вернуть None."""
        src = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
        try:
            got = _read_json(os.path.join(DATA, "about_ru.json")).get(appid)
            if got and got.get("src") == src:
                return got["ru"]
        except Exception:
            pass
        try:
            need_p = os.path.join(DATA, "about_need.json")
            with _cache_io_lock:
                need = _read_json(need_p) if os.path.exists(need_p) else {}
                if need.get(appid) != text:
                    need[appid] = text
                    _atomic_json(need_p, need)
        except Exception:
            pass
        return None

    def _with_ru(self, appid, got):
        if not got or got.get("none") or not self._is_english(got.get("short", "")):
            return got
        ru = self._translate(appid, got["short"])
        return {**got, "short": ru, "translated": True} if ru else got

    async def get_about(self, appid):
        r = await self._get_about_raw(appid)
        if self._is_standalone():
            # Public builds have no owner's PC translation queue.  Steam's own
            # localized text is shown as-is; an English fallback is marked so
            # the frontend can say that it is the original description.
            if r and ui_i18n.lang() in ("ru", "uk") and self._is_english(r.get("short", "")):
                r = {**r, "original_language": True, "translated": False}
            return r
        # The existing PC-assisted English -> Russian translation is part of
        # the owner's Russian UI.  Other languages use Steam's own localized
        # description and must never inherit a Russian translation/cache row.
        if ui_i18n.lang() == "ru" and r and self._is_english(r.get("short", "")):
            appid = str(int(appid))
            r = await asyncio.get_running_loop().run_in_executor(None, self._with_ru, appid, r)
        return r

    async def _get_about_raw(self, appid):
        parsed_appid = _appid(appid)
        if parsed_appid is None:
            return None
        appid = str(parsed_appid)
        hub = {} if self._is_standalone() else (self._hub_index().get("cards") or {}).get(appid) or {}
        if hub.get("about"):   # не-Steam игры: описание из своей карточки (магазин Steam о них не знает)
            return {"short": hub["about"]}
        if int(appid) >= 0x80000000:
            return None
        language = ui_i18n.lang()
        cache = self._about_cache()
        # Keep the legacy key for Russian so the owner's populated offline
        # cache remains byte-for-byte usable.  New languages have separate
        # entries because about.json used to contain Russian only.
        cache_key = appid if language == "ru" else f"{appid}:{language}"
        got = cache.get(cache_key)
        if got and (not got.get("none") or time.time() - got.get("ts", 0) < 3 * 86400):
            return None if got.get("none") else got
        try:
            got = await asyncio.get_running_loop().run_in_executor(None, self._fetch_about, appid, language)
        except Exception as e:
            decky.logger.warning("about %s: %s", appid, e)
            return None if not got or got.get("none") else got
        got["ts"] = time.time()
        try:
            with _cache_io_lock:
                cache = self._about_cache()  # merge after the executor yields
                cache[cache_key] = got
                _atomic_json(self._about_path(), cache)
        except OSError:
            pass
        return None if got.get("none") else got

    # ───── хаб ─────
    def _hub_index(self):
        p = os.path.join(DATA, "hub_cards.json")
        try:
            m = os.path.getmtime(p)
        except OSError:
            return {"cards": {}, "synced_at": None}
        if m != self._hub_mtime:
            try:
                self._hub = _read_json(p)
                self._hub_mtime = m
            except (OSError, ValueError, TypeError):
                return {"cards": {}, "synced_at": None}
        return self._hub

    @staticmethod
    def _save_count():
        count = 0
        for appid in sorted(deck_saves.READERS):
            got = deck_saves.read(appid, DATA)
            if isinstance(got, dict) and not got.get("error"):
                count += 1
        return count

    async def get_status(self):
        idx = {"cards": {}, "synced_at": None} if self._is_standalone() else self._hub_index()
        hltb = getattr(self, "hltb", None)
        base = {"synced_at": idx.get("synced_at"), "hub_cards": len(idx.get("cards") or {}),
                "hltb_cached": sum(1 for v in getattr(hltb, "cache", {}).values() if v.get("main")),
                "deck_readers": sorted(deck_saves.READERS), "standalone": self._is_standalone()}
        if self._is_standalone():
            media = await asyncio.get_running_loop().run_in_executor(None, self._media().status)
            try:
                saves = await asyncio.wait_for(asyncio.get_running_loop().run_in_executor(None, self._save_count), 8)
            except Exception:
                saves = 0
            base.update({"save_games": saves, "cached_backgrounds": media["cached_backgrounds"], "media": media})
        return base

    async def get_aliases(self):
        """Свой ярлык → копия той же игры с ПК (для кнопки «Играть с ПК» в ряду Steam)."""
        out = {}
        if self._is_standalone():
            return out
        for appid, c in (self._hub_index().get("cards") or {}).items():
            if c.get("alias_of"):
                out[str(c["alias_of"])] = int(appid)
        return out

    async def get_music_map(self):
        """appid -> id трека хаба (для Game Theme Music)."""
        if self._is_standalone():
            return {}
        out = {}
        for appid, c in (self._hub_index().get("cards") or {}).items():
            tid = (c.get("media") or {}).get("theme_id")
            if (isinstance(tid, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", tid)
                    and glob.glob(f"/home/deck/homebrew/data/SDH-GameThemeMusic/music/{glob.escape(tid)}.*")):
                out[appid] = tid
        return out

    async def get_music_files(self):
        """appid -> файл темы в data/SDH-GameThemeMusic/music (главная проигрывает его сама, без Game Theme Music)."""
        if self._is_standalone():
            return await asyncio.get_running_loop().run_in_executor(None, self._media().music_files)
        out = {}
        for appid, tid in (await self.get_music_map()).items():
            f = sorted(glob.glob(f"/home/deck/homebrew/data/SDH-GameThemeMusic/music/{glob.escape(tid)}.*"))
            if f:
                out[appid] = os.path.basename(f[0])
        return out

    # ───── карточка ─────
    _icons, _icons_mt = {}, 0.0

    def _icon_map(self):
        """icons/manifest.json (deck_sync из steamdeck/icons/out): {appid: {подпись факта: "<appid>/<id>.png"}}."""
        p = os.path.join(DATA, "icons", "manifest.json")
        try:
            mt = os.path.getmtime(p)
        except OSError:
            return {}
        if mt != Plugin._icons_mt:
            try:
                with open(p, encoding="utf-8") as f:
                    Plugin._icons = json.load(f)
                Plugin._icons_mt = mt
            except (OSError, ValueError):
                return Plugin._icons
        return Plugin._icons

    def _apply_icons(self, card, ids):
        """Свой значок игры на факт: icon = "img:icons/…" (так же рисует Big Picture ПК). Нет файла — прежний SVG.
        Подпись «Луны: Песчаное царство» ищется и целиком, и по части до двоеточия."""
        man = self._icon_map()
        maps = [man.get(str(i)) for i in ids if man.get(str(i))]
        if not maps:
            return

        from ddsaves._common import labels
        legacy = labels()["legacy"]

        def pick(label, fact_id=None):
            candidates = [fact_id, label, str(label).split(":")[0].strip()]
            # Older manifests key the authored RU noun rather than the reader field ID.
            label_id = next((key for key, translations in labels()["labels"].items()
                             if label in [translations] if isinstance(translations, str)), None)
            if label_id is None:
                label_id = next((key for key, translations in labels()["labels"].items()
                                 if isinstance(translations, dict) and label in translations.values()), None)
            candidates.extend(k for k, v in legacy.items() if fact_id and v == fact_id)
            candidates.extend(k for k, v in legacy.items() if label_id and v == label_id)
            for m in maps:
                rel = next((m.get(k) for k in candidates if k and m.get(k)), None)
                if not isinstance(rel, str) or ".." in rel.replace("\\", "/").split("/"):
                    continue
                root = os.path.realpath(os.path.join(DATA, "icons"))
                fp = os.path.realpath(os.path.join(root, rel))
                try:
                    inside = os.path.commonpath((root, fp)) == root
                except ValueError:
                    inside = False
                if inside and os.path.isfile(fp):
                    return "img:icons/%s?v=%d" % (rel.replace("\\", "/"), os.path.getmtime(fp))
            return None
        facts = []
        for f in card.get("facts") or []:
            img = pick(f.get("label"), f.get("id"))
            f = dict(f, icon=img) if img else f
            if f.get("people"):   # портреты персонажей («Персонаж: <ключ>»)
                f = dict(f, people=[dict(p, icon=pick("Персонаж: " + str(p.get("key")), "person:" + str(p.get("key")))) for p in f["people"]])
            facts.append(f)
        card["facts"] = facts
        ach = pick("Достижения", "achievements")
        if ach:
            card["ach_icon"] = ach

    # ───── язык названий из игр (08.10): ddsaves берёт CONTINUE_LANG (ru|en|uk), нет строки — en, потом ru ─────
    STEAM_LANGS = {"russian": "ru", "ukrainian": "uk", "english": "en"}

    async def set_lang(self, steam_lang):
        """Фронт присылает язык интерфейса Steam («russian», «english», …) или код вида «ru-RU»."""
        v = str(steam_lang or "").strip().lower()
        code = self.STEAM_LANGS.get(v) or {"ru": "ru", "uk": "uk", "en": "en"}.get(v[:2]) or "en"
        os.environ["CONTINUE_LANG"] = code
        return code

    async def get_card(self, appid, name=""):
        appid = int(appid)
        hub = None if self._is_standalone() else (self._hub_index().get("cards") or {}).get(str(appid))
        save_id = int((hub or {}).get("alias_of") or appid)   # копия с ПК — сейв тот же, что у своего ярлыка
        local = await asyncio.get_running_loop().run_in_executor(None, deck_saves.read, save_id, DATA)
        card = {"appid": appid, "name": name or (hub or {}).get("name"), "block": None, "facts": [],
                "media": dict((hub or {}).get("media") or {}), "accent": (hub or {}).get("accent"), "source": None}
        settings = await self.get_settings()
        if self._is_standalone():
            media = await asyncio.get_running_loop().run_in_executor(None, self._media().media_for, appid, settings)
            card["media"].update(media)
            card["standalone"] = True
            card["bg_source"] = str((settings.get("game_source") or {}).get(str(appid))
                                    or settings.get("bg_source") or "steam")
        hub_block = (hub or {}).get("block")
        local_block = None
        if local and not local.get("error"):
            local_block = hubcard.block_from_save(local["save"])
            if local_block:
                if local.get("sub") and not local_block.get("sub"):
                    local_block["sub"] = local["sub"]
                if local.get("detail") and not local_block.get("detail"):
                    local_block["detail"] = local["detail"]
                local_block["source"] = "deck"
            if local.get("shot"):
                card["media"]["shot"] = local["shot"]
        # чей блок главнее: сейв на Деке, если он свежее того, что видел хаб
        hub_t = float((hub_block or {}).get("observed_at") or 0)
        loc_t = float((local or {}).get("save", {}).get("observed_at") or 0) if local and not local.get("error") else 0
        if local_block and (not hub_block or loc_t >= hub_t):
            card["block"], card["facts"], card["source"] = local_block, local.get("facts") or [], "deck"
            if hub_block and hub_block.get("title") == local_block.get("title") and not local_block.get("detail"):
                local_block["detail"] = hub_block.get("detail")   # то же место — пояснение хаба не терять
        elif hub_block:
            card["block"], card["facts"], card["source"] = hub_block, (local.get("facts") if local and local.get("facts") else hub.get("facts")) or [], "hub"
        elif local and not local.get("error") and (local.get("facts") or local.get("detail")):
            card["facts"], card["source"] = local.get("facts") or [], "deck"
            if local.get("detail"):   # сейв есть, а место в нём не разобрано — не «Ещё не начата»
                card["block"] = {"kicker": ui_i18n.t("has_save"), "title": "", "sub": "", "detail": local["detail"], "source": "deck"}
        if local and local.get("error"):
            card["deck_error"] = local["error"]
        self._apply_icons(card, (save_id, appid))
        hltb = getattr(self, "hltb", None)
        card["hltb"] = (hltb.cached(appid) if hltb else None) or (hub or {}).get("hltb")
        card["bg_mode"] = (settings.get("game_bg") or {}).get(str(appid), "auto")
        return ui_i18n.translate_card(card)

    async def get_media_status(self):
        """Capabilities and cache counters; always JSON-serializable."""
        if not self._is_standalone():
            return {"standalone": False}
        media = await asyncio.get_running_loop().run_in_executor(None, self._media().status)
        return {"standalone": True, **media}

    async def install_ytdlp(self, consent=False, force=False, purpose="youtube"):
        if not self._is_standalone():
            return {"ok": False, "standalone": False}
        if consent is not True:
            return {"ok": False, "consent_required": True}
        if type(force) is not bool or purpose not in ("youtube", "theme"):
            return {"ok": False, "error": "Invalid install options"}
        if not (await self.get_power()).get("ac"):
            return {"ok": False, "deferred": "battery"}
        lock = self._media_lock()
        if lock.locked():
            return {"ok": False, "deferred": "busy"}
        if not await asyncio.get_running_loop().run_in_executor(None, self._media_work_allowed):
            return {"ok": False, "deferred": "power_or_game"}
        settings = await self.get_settings()
        settings["theme_music_consent" if purpose == "theme" else "youtube_consent"] = True
        try:
            self._write_settings(settings)
        except OSError as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}
        try:
            async with lock:
                return await asyncio.get_running_loop().run_in_executor(
                    None, lambda: self._media().install_ytdlp(True, bool(force)))
        except Exception as e:
            decky.logger.warning("yt-dlp install: %s", e)
            return {"ok": False, "error": f"{type(e).__name__}: {e}"[:240]}

    async def refresh_media(self, appid, name="", game_running=False, source=None, force=False):
        """Latest requested game wins; older waiters never start expensive work."""
        if not self._is_standalone():
            return {"ok": False, "standalone": False}
        appid = _appid(appid)
        if appid is None or source is not None and source not in BG_SOURCES:
            return {"ok": False, "error": "Invalid media request"}
        seq = getattr(self, "_media_refresh_seq", 0) + 1
        self._media_refresh_seq = seq
        self._media_game_running = bool(game_running)
        power = await self.get_power()
        if game_running:
            return {"ok": False, "deferred": "game_running"}
        if not power.get("ac"):
            return {"ok": False, "deferred": "battery"}
        settings = await self.get_settings()
        selected = source or (settings.get("game_source") or {}).get(str(appid)) or settings.get("bg_source") or "steam"
        if selected == "youtube" and not settings.get("youtube_consent"):
            return {"ok": False, "consent_required": True, "source": "youtube"}
        if selected == "recording" and not settings.get("recording_enabled"):
            return {"ok": False, "disabled": True, "source": "recording"}
        lock = self._media_lock()
        async with lock:
            if seq != self._media_refresh_seq:
                return {"ok": False, "deferred": "superseded"}
            if not await asyncio.get_running_loop().run_in_executor(None, self._media_work_allowed):
                return {"ok": False, "deferred": "power_or_game"}
            self._media_active_seq = seq
            try:
                return await asyncio.get_running_loop().run_in_executor(
                    None, lambda: self._media().build(appid, name, settings, selected, force=bool(force)))
            except Exception as exc:
                if seq != self._media_refresh_seq:
                    return {"ok": False, "deferred": "superseded"}
                return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:240]}
            finally:
                self._media_active_seq = None

    def _media_lock(self):
        if getattr(self, "_standalone_lock", None) is None:
            self._standalone_lock = asyncio.Semaphore(1)
        return self._standalone_lock

    async def set_media_context(self, game_running=False):
        """Heartbeat from Steam UI; the worker also checks /proc and AC itself."""
        if not self._is_standalone():
            return {"standalone": False}
        self._media_game_running = bool(game_running)
        return {"standalone": True, "game_running": self._media_game_running}

    @staticmethod
    def _running_game():
        # Steam supplies SteamAppId to the game and its runtime processes.
        # Read only the required marker; never log process environments.
        for path in glob.glob("/proc/[0-9]*/environ"):
            try:
                with open(path, "rb") as stream:
                    values = stream.read(65536).split(b"\0")
                for value in values:
                    if value.startswith(b"SteamAppId="):
                        appid = int(value.split(b"=", 1)[1] or 0)
                        if appid > 0 and appid != 1812620:
                            return True
            except (OSError, ValueError):
                pass
        return False

    def _media_work_allowed(self):
        active = getattr(self, "_media_active_seq", None)
        return (self._is_standalone() and (active is None or active == getattr(self, "_media_refresh_seq", active))
                and not getattr(self, "_media_game_running", False)
                and self._power_sync().get("ac") and not self._running_game())

    async def clear_media_cache(self):
        if not self._is_standalone():
            return {"ok": False, "standalone": False}
        lock = self._media_lock()
        if lock.locked():
            return {"ok": False, "deferred": "busy"}
        async with lock:
            try:
                return await asyncio.get_running_loop().run_in_executor(None, self._media().clear)
            except Exception as exc:
                return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:240]}

    async def preview_tester_report(self):
        if not self._is_standalone():
            return {"ok": False, "standalone": False}
        import tester_report
        import secrets
        try:
            settings = await self.get_settings()
            report = await asyncio.get_running_loop().run_in_executor(
                None, tester_report.collect, self, settings, decky, DATA)
            payload = tester_report.encode(report)
            token = secrets.token_hex(16)
            self._tester_preview = (token, time.monotonic(), payload)
            return {"ok": True, "token": token, "preview": payload,
                    "bytes": len(payload.encode("utf-8"))}
        except Exception as error:
            return {"ok": False, "error": tester_report.sanitize(
                f"{type(error).__name__}: {error}", tester_report.privacy_names(self._steam_root()))}

    async def save_tester_report(self, token):
        if not self._is_standalone():
            return {"ok": False, "standalone": False}
        import tester_report
        preview = getattr(self, "_tester_preview", None)
        if not preview or token != preview[0] or time.monotonic() - preview[1] > 900:
            return {"ok": False, "error": "Preview expired; collect and review again"}
        self._tester_preview = None  # Consume before the executor yields.
        try:
            path = await asyncio.get_running_loop().run_in_executor(None, tester_report.save, preview[2])
            return {"ok": True, "filename": path.name, "folder": path.parent.name}
        except Exception as error:
            return {"ok": False, "error": tester_report.sanitize(
                f"{type(error).__name__}: {error}", tester_report.privacy_names(self._steam_root()))}

    async def get_hltb(self, appid, name=""):
        try:
            hltb = getattr(self, "hltb", None)
            if hltb is None:
                self.hltb = HLTB(DATA)
                hltb = self.hltb
            return await hltb.get(int(appid), name)
        except Exception as e:
            decky.logger.warning("HLTB %s: %s", appid, e)
            return None

    # ───── обновления (08.10): GitHub Releases раз в сутки; ставит сам Decky (диалог + проверка sha256) ─────
    REPO = "Alexsander720/continue"

    @staticmethod
    def _ssl():
        try:  # у Python внутри Decky нет системных сертификатов
            import certifi
            return ssl.create_default_context(cafile=certifi.where())
        except Exception:
            return ssl.create_default_context(cafile="/etc/ssl/certs/ca-certificates.crt")

    @staticmethod
    def _version_tuple(v):
        return tuple(int(x) for x in re.findall(r"\d+", str(v or ""))[:3]) or (0,)

    def _current_version(self):
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "package.json"), encoding="utf-8") as f:
                return json.load(f).get("version") or "0"
        except (OSError, ValueError):
            return "0"

    def _fetch_release(self):
        req = urllib.request.Request(f"https://api.github.com/repos/{self.REPO}/releases/latest",
                                     headers={"User-Agent": "Continue-Deck", "Accept": "application/vnd.github+json"})
        rel = json.loads(self._release_bytes(req, 1024 * 1024).decode("utf-8"))
        assets = {a.get("name"): a.get("browser_download_url") for a in rel.get("assets") or []}
        zip_name = next((n for n in assets if n and n.endswith(".zip") and "deck" in n.lower()), None)
        if not zip_name:
            return {"none": True}
        url, checksum_url = assets[zip_name], assets.get(zip_name + ".sha256")
        if not self._release_asset_url(url) or not self._release_asset_url(checksum_url):
            raise ValueError("Release assets must be official Continue HTTPS downloads")
        raw = self._release_bytes(urllib.request.Request(checksum_url, headers={"User-Agent": "Continue-Deck"}), 4096).decode("utf-8", "replace")
        m = re.search(r"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])", raw)
        if not m:
            raise ValueError("Release checksum is missing or invalid")
        sha = m.group(0).lower()
        page = rel.get("html_url")
        if not isinstance(page, str) or not page.startswith(f"https://github.com/{self.REPO}/releases/"):
            page = f"https://github.com/{self.REPO}/releases"
        return {"version": str(rel.get("tag_name") or "").lstrip("v"), "url": assets[zip_name], "sha256": sha,
                "notes": (rel.get("body") or "")[:1500], "page": page}

    @classmethod
    def _release_asset_url(cls, value):
        if not isinstance(value, str):
            return False
        try:
            u = urllib.parse.urlsplit(value)
            prefix = f"/{cls.REPO}/releases/download/"
            parts = urllib.parse.unquote(u.path).split("/")
            return (u.scheme == "https" and u.netloc == "github.com" and not u.query and not u.fragment
                    and u.path.startswith(prefix) and len(u.path[len(prefix):].split("/")) == 2
                    and all(p and p not in (".", "..") and "\\" not in p for p in parts[1:]))
        except ValueError:
            return False

    def _release_bytes(self, request, limit):
        response = urllib.request.urlopen(request, timeout=10, context=self._ssl())
        try:
            # GitHub redirects downloads to its official signed asset CDN.
            final = response.geturl() if hasattr(response, "geturl") else request.full_url
            parsed = urllib.parse.urlsplit(final)
            if parsed.scheme != "https" or parsed.netloc not in ("api.github.com", "github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"):
                raise ValueError("Untrusted release redirect")
            raw = response.read(limit + 1)
            if len(raw) > limit:
                raise ValueError("Release response exceeds size limit")
            return raw
        finally:
            response.close()

    async def check_update(self, force=False):
        """{"current", "latest", "available", "url", "sha256", "notes"}; сеть раз в сутки (кэш в update.json).
        Только в собранном релизе (RELEASE.json кладёт build_deck_zip.py). Рабочая копия владельца шире публичной
        — публичный zip поверх неё снёс бы дополнительные возможности, поэтому здесь обновления выключены."""
        if not self._is_standalone():
            return {"current": "dev", "available": False, "dev": True}
        path = os.path.join(DATA, "update.json")
        try:
            with open(path, encoding="utf-8") as f:
                c = json.load(f)
        except (OSError, ValueError):
            c = {}
        failed = bool(c.get("error"))
        if force or (time.time() >= c.get("retry_after", 0) and (failed or time.time() - c.get("at", 0) > 86400)):
            try:
                rel = await asyncio.get_running_loop().run_in_executor(None, self._fetch_release)
                if not rel.get("none") and (not re.fullmatch(r"[0-9a-f]{64}", rel.get("sha256") or "") or not self._release_asset_url(rel.get("url"))):
                    raise ValueError("Incomplete release metadata")
                c = {"at": time.time(), "rel": rel}
                _atomic_json(path, c)
            except Exception as e:
                decky.logger.info("update check: %s", e)
                c = {"at": c.get("at", 0), "rel": c.get("rel") or {}, "error": True, "retry_after": time.time() + 900}
                try:
                    _atomic_json(path, c)
                except OSError:
                    pass
        cur, rel = self._current_version(), c.get("rel") or {}
        avail = bool(not c.get("error") and rel.get("version") and re.fullmatch(r"[0-9a-f]{64}", rel.get("sha256") or "")
                     and self._release_asset_url(rel.get("url"))
                     and self._version_tuple(rel["version"]) > self._version_tuple(cur))
        return {"current": cur, "latest": rel.get("version"), "available": avail, "url": rel.get("url"),
                "sha256": rel.get("sha256"), "notes": rel.get("notes"), "page": rel.get("page"), "checked_at": c.get("at"),
                "error": bool(c.get("error")), "retry_after": max(0, min(900, c.get("retry_after", 0) - time.time()))}

    # ───── питание: живой фон только на зарядке ─────
    async def get_power(self):
        return self._power_sync()

    @staticmethod
    def _power_sync():
        ac = None
        for p in glob.glob("/sys/class/power_supply/*"):
            try:
                with open(f"{p}/type") as stream:
                    kind = stream.read().strip()
                if kind in ("Mains", "USB", "USB_C", "USB_PD") and os.path.exists(f"{p}/online"):
                    with open(f"{p}/online") as stream:
                        ac = (ac or False) or stream.read().strip() == "1"
            except OSError:
                pass
        bat = next(iter(glob.glob("/sys/class/power_supply/BAT*")), None)
        pct = None
        if bat:
            try:
                with open(f"{bat}/capacity") as stream:
                    pct = int(stream.read())
                if ac is None:
                    with open(f"{bat}/status") as stream:
                        ac = stream.read().strip() in ("Charging", "Full", "Not charging")
            except (OSError, ValueError):
                pass
        return {"ac": bool(ac), "battery": pct}
