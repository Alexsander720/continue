"""Standalone public card display customization backend (stdlib only).

Architecture / Interface:
    PublicPreferences(root, settings_lock=None)
    - root: supplied per-user or test Continue data root. Only
      <root>/settings.json is ever read/written. No other I/O.
    - settings_lock: optional RLock shared with primary Backend.gate for
      root/settings.json reads/writes. Defaults to a private RLock.
    - No I/O at construction (no dirs, no reads, no network/subprocess).

    METHODS = {"get_card_preferences", "set_card_preference",
               "reset_card_preferences"}
    .call(method, args) synchronous dispatcher (args must be list/tuple).

Schema (sparse, inherit-via-absence):
    settings.json top-level:
      "card_display": {story,description,facts,characters,achievements,
                       latest_achievement,playtime: bool,
                       hidden_fact_ids: [stable-id]}      # global, sparse
      "card_display_games": {"<appid>": {same sparse override}}  # per-game

    Defaults: every bool True, hidden_fact_ids []. Absent key = default /
    inherit global. Unicode labels belong to UI, never stored (only stable IDs).

Pure helpers (no I/O, no settings lock):
    filter_card(card, preferences) -> filtered deepcopy (input unmodified).
    card_fields(card, preferences=None) -> [{id,label,has_characters,visible}]
        of actual SOURCE facts only (synthetic achievement/playtime/latest
        excluded; no invented counts).
    effective_preferences(global_prefs, game_override) -> merged effective.
    DEFAULTS / BOOL_KEYS / ALL_KEYS / FACT_ID_RE exposed for tests/UI.

Filter semantics (documented for primary frontend integration):
    - story=False removes block story keys (kicker/title/sub/objective/
      objective_sub/subtitle/place). If block empties -> None. Never touches
      card name/appid/media (identity).
    - description=False removes block detail keys (detail/objective_detail/
      description) + card about-derived text (about/description/detail/
      summary/about_text/about_html). Preserves standalone_about (frontend
      owns it and overrides primary) + tagline/name.
    - facts=False removes ALL facts (facts=[]).
    - characters=False hides people rows: has_characters is True, or
      characters/people truthy, or stable id in CHARACTER_FACT_IDS.
    - hidden_fact_ids removes ONLY exact stable-id matches.
    - achievements=False / latest_achievement=False / playtime=False are
      consumed by primary frontend synthetic rows, but filter any matching
      known IDs in card["facts"] too (best-effort label fallback for legacy
      cards without IDs).
    - Never translates, interprets or fabricates factual data.

Hardening:
    - Strict AppID (reject bool/float/str-non-digits/out-of-range).
    - Strict bool (type(value) is bool); hidden list validated, <=128.
    - FACT_ID_RE ^[a-z0-9_:-]{1,80}$ (lowercase only).
    - Max 10000 per-game rows; no arbitrary key/path (key allowlist).
    - Bounded reads (1 MB), atomic writes (tmp+replace), symlink guard
      (settings.json symlink -> fail-safe read defaults, write raises).
    - Malformed settings fail safe: get returns defaults without deleting/
      truncating; set/reset preserve unrelated keys + other apps.
    - All public methods hold settings_lock (RLock) for read-modify-write.
    - Readbacks contain ONLY display settings (no credentials/unrelated).
"""
from __future__ import annotations

import copy
import json
import os
import re
import threading
from pathlib import Path
from typing import Any

BOOL_KEYS = (
    "story",
    "description",
    "facts",
    "characters",
    "achievements",
    "latest_achievement",
    "playtime",
)
ALL_KEYS = BOOL_KEYS + ("hidden_fact_ids",)

DEFAULTS: dict[str, Any] = {k: True for k in BOOL_KEYS}
DEFAULTS["hidden_fact_ids"] = []

MAX_HIDDEN = 128
MAX_APPS = 10000
MAX_JSON_BYTES = 1024 * 1024  # 1 MB
_MAX_APPID = 0xFFFFFFFF

FACT_ID_RE = re.compile(r"[a-z0-9_:\-]{1,80}")
_APPID_STR_RE = re.compile(r"[1-9][0-9]{0,9}")

# Stable IDs for synthetic rows (primary frontend also synthesizes these).
ACHIEVEMENT_FACT_IDS = frozenset({
    "achievements", "achievement_progress", "achievements_progress",
    "achievements_pct", "achievements_percent",
})
LATEST_FACT_IDS = frozenset({
    "latest_achievement", "last_achievement", "last_ach", "recent_achievement",
})
PLAYTIME_FACT_IDS = frozenset({
    "playtime", "play_time", "time_played", "hours_played", "hours",
})
CHARACTER_FACT_IDS = frozenset({
    "alive_count", "alive", "characters", "people", "party",
    "survivors", "companions",
})
SYNTHETIC_FACT_IDS = ACHIEVEMENT_FACT_IDS | LATEST_FACT_IDS | PLAYTIME_FACT_IDS

# Legacy label fallback (English only, lowercased) for cards without IDs.
_ACH_LABELS = {"achievements", "achievement", "achievements progress"}
_LATEST_LABELS = {"last achievement", "latest achievement", "last_achievement"}
_PLAYTIME_LABELS = {"playtime", "play time", "hours played", "time played"}

_BLOCK_STORY_KEYS = (
    "kicker", "title", "sub", "subtitle", "objective", "objective_sub", "place",
)
_BLOCK_DETAIL_KEYS = ("detail", "objective_detail", "description")
_CARD_ABOUT_KEYS = (
    "about", "description", "detail", "summary", "about_text", "about_html",
)


def _strict_appid(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("Invalid appid")
    if isinstance(value, int):
        if 1 <= value <= _MAX_APPID:
            return value
        raise ValueError("AppID out of range")
    if isinstance(value, str):
        s = value.strip()
        if _APPID_STR_RE.fullmatch(s) and int(s) <= _MAX_APPID:
            return int(s)
        raise ValueError("Invalid appid")
    raise ValueError("Invalid appid")


def _validate_fact_id(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("Invalid fact id type")
    if not FACT_ID_RE.fullmatch(value):
        raise ValueError("Invalid fact id %r" % (value[:40],))
    return value


def _normalize_hidden(value: Any) -> list:
    if not isinstance(value, list):
        raise ValueError("hidden_fact_ids must be a list")
    if len(value) > MAX_HIDDEN:
        raise ValueError("hidden_fact_ids exceeds %d" % MAX_HIDDEN)
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        fid = _validate_fact_id(item)
        if fid not in seen:
            seen.add(fid)
            out.append(fid)
    return out


def _validate_key(key: Any) -> str:
    if not isinstance(key, str) or key not in ALL_KEYS:
        raise ValueError("Unknown preference key %r" % (key,))
    return key


def _validate_value(key: str, value: Any) -> Any:
    if key == "hidden_fact_ids":
        return _normalize_hidden(value)
    if type(value) is not bool:
        raise ValueError("Preference %r must be bool" % key)
    return value


def _is_symlink(path: Path) -> bool:
    try:
        return path.is_symlink()
    except OSError:
        return False


def _read_raw_settings(path: Path) -> tuple[dict | None, bool]:
    """Return (parsed dict or None, malformed flag). No writes. Bounded."""
    try:
        if _is_symlink(path):
            return None, True
        try:
            size = path.stat().st_size
        except OSError:
            return None, False  # missing -> not malformed, just absent
        if size > MAX_JSON_BYTES:
            return None, True
        try:
            text = path.read_text(encoding="utf-8-sig")
        except OSError:
            return None, False
        if len(text.encode("utf-8")) > MAX_JSON_BYTES + 1024:
            return None, True
        try:
            data = json.loads(text)
        except ValueError:
            return None, True
        if not isinstance(data, dict):
            return None, True
        return data, False
    except OSError:
        return None, True


def _extract_display(raw: dict | None) -> tuple[dict, dict]:
    """Extract (global_sparse, games_sparse) fail-safe."""
    if not isinstance(raw, dict):
        return {}, {}
    g = raw.get("card_display")
    if not isinstance(g, dict):
        g = {}
    games = raw.get("card_display_games")
    if not isinstance(games, dict):
        games = {}
    # sanitize: keep only known keys with valid types; drop garbage
    clean_g: dict[str, Any] = {}
    for k, v in g.items():
        if k not in ALL_KEYS:
            continue
        try:
            if k == "hidden_fact_ids":
                clean_g[k] = _normalize_hidden(v)
            elif type(v) is bool:
                clean_g[k] = v
        except ValueError:
            continue
    clean_games: dict[str, dict] = {}
    for appk, ov in games.items():
        try:
            aid = _strict_appid(appk)
        except ValueError:
            continue
        if not isinstance(ov, dict):
            continue
        entry: dict[str, Any] = {}
        for k, v in ov.items():
            if k not in ALL_KEYS:
                continue
            try:
                if k == "hidden_fact_ids":
                    entry[k] = _normalize_hidden(v)
                elif type(v) is bool:
                    entry[k] = v
            except ValueError:
                continue
        if entry:
            clean_games[str(aid)] = entry
    return clean_g, clean_games


def _merge_effective(global_sparse: dict, game_sparse: dict) -> dict:
    eff = dict(DEFAULTS)
    eff["hidden_fact_ids"] = list(DEFAULTS["hidden_fact_ids"])
    for k, v in global_sparse.items():
        if k == "hidden_fact_ids":
            eff[k] = list(v)
        else:
            eff[k] = v
    for k, v in game_sparse.items():
        if k == "hidden_fact_ids":
            eff[k] = list(v)
        else:
            eff[k] = v
    return eff


def effective_preferences(global_prefs: dict | None, game_override: dict | None) -> dict:
    """Merge sparse global + sparse game override onto defaults (pure)."""
    g = dict(global_prefs) if isinstance(global_prefs, dict) else {}
    o = dict(game_override) if isinstance(game_override, dict) else {}
    # keep only known keys
    g = {k: v for k, v in g.items() if k in ALL_KEYS}
    o = {k: v for k, v in o.items() if k in ALL_KEYS}
    base = dict(DEFAULTS)
    base["hidden_fact_ids"] = list(DEFAULTS["hidden_fact_ids"])
    for src in (g, o):
        for k, v in src.items():
            if k == "hidden_fact_ids" and isinstance(v, list):
                base[k] = list(v)
            elif k in BOOL_KEYS and type(v) is bool:
                base[k] = v
    return base


def definitions() -> dict:
    return {
        "bool_keys": list(BOOL_KEYS),
        "all_keys": list(ALL_KEYS),
        "defaults": copy.deepcopy(DEFAULTS),
        "max_hidden": MAX_HIDDEN,
        "max_apps": MAX_APPS,
        "character_ids": sorted(CHARACTER_FACT_IDS),
        "achievement_ids": sorted(ACHIEVEMENT_FACT_IDS),
        "latest_ids": sorted(LATEST_FACT_IDS),
        "playtime_ids": sorted(PLAYTIME_FACT_IDS),
    }


def _fact_stable_id(fact: Any) -> str | None:
    if not isinstance(fact, dict):
        return None
    for k in ("id", "key", "fact_id"):
        v = fact.get(k)
        if isinstance(v, str) and FACT_ID_RE.fullmatch(v):
            return v
    return None


def _fact_label_lower(fact: Any) -> str:
    try:
        v = fact.get("label") if isinstance(fact, dict) else None
        return str(v or "").strip().lower()
    except Exception:
        return ""


def _is_character_fact(fact: Any) -> bool:
    if not isinstance(fact, dict):
        return False
    try:
        if fact.get("has_characters") is True:
            return True
        for k in ("characters", "people"):
            v = fact.get(k)
            if v is True or (isinstance(v, (list, dict)) and len(v) > 0):
                return True
            if isinstance(v, int) and not isinstance(v, bool) and v > 0:
                return True
            if isinstance(v, str) and v.strip():
                return True
    except Exception:
        pass
    fid = _fact_stable_id(fact)
    return fid in CHARACTER_FACT_IDS if fid else False


def _matches_any(fact: Any, ids: frozenset, labels: set[str]) -> bool:
    fid = _fact_stable_id(fact)
    if fid is not None and fid in ids:
        return True
    if fid is None and _fact_label_lower(fact) in labels:
        return True
    return False


def _normalize_prefs(preferences: Any) -> dict:
    """Accept None, effective dict, or get_* result with 'effective'."""
    if preferences is None:
        eff = dict(DEFAULTS)
        eff["hidden_fact_ids"] = []
        return eff
    if isinstance(preferences, dict) and isinstance(preferences.get("effective"), dict):
        preferences = preferences["effective"]
    if not isinstance(preferences, dict):
        eff = dict(DEFAULTS)
        eff["hidden_fact_ids"] = []
        return eff
    out = dict(DEFAULTS)
    out["hidden_fact_ids"] = []
    for k in BOOL_KEYS:
        v = preferences.get(k)
        out[k] = v if type(v) is bool else True
    hid = preferences.get("hidden_fact_ids")
    if isinstance(hid, list):
        clean = []
        for item in hid:
            if isinstance(item, str) and FACT_ID_RE.fullmatch(item) and item not in clean:
                clean.append(item)
                if len(clean) >= MAX_HIDDEN:
                    break
        out["hidden_fact_ids"] = clean
    return out


def filter_card(card: Any, preferences: Any = None) -> Any:
    """Pure filter: deepcopy relevant fields, never mutate input."""
    if not isinstance(card, dict):
        raise TypeError("card must be a dict")
    eff = _normalize_prefs(preferences)
    out = copy.deepcopy(card)

    # story
    if eff.get("story") is False:
        blk = out.get("block")
        if isinstance(blk, dict):
            for k in _BLOCK_STORY_KEYS:
                blk.pop(k, None)
            # keep detail if description still on; else block may empty
            if not blk:
                out["block"] = None
            elif all(k not in blk for k in _BLOCK_STORY_KEYS) and len(blk) == 0:
                out["block"] = None

    # description
    if eff.get("description") is False:
        blk = out.get("block")
        if isinstance(blk, dict):
            for k in _BLOCK_DETAIL_KEYS:
                blk.pop(k, None)
            if not blk or all(k not in blk for k in _BLOCK_STORY_KEYS + _BLOCK_DETAIL_KEYS):
                # if story already stripped, block is meaningless
                if out.get("block") is not None and len(blk) == 0:
                    out["block"] = None
        for k in _CARD_ABOUT_KEYS:
            if k in out:
                out[k] = "" if isinstance(out[k], str) else None
        # standalone_about is frontend-owned override: never strip.
        # tagline/name/appid/media preserved (identity, not about-derived).

    # facts
    facts = out.get("facts")
    if eff.get("facts") is False:
        out["facts"] = []
    elif isinstance(facts, list):
        hidden = set(eff.get("hidden_fact_ids") or [])
        kept = []
        for f in facts:
            if not isinstance(f, dict):
                continue
            fid = _fact_stable_id(f)
            if fid is not None and fid in hidden:
                continue
            if eff.get("characters") is False and _is_character_fact(f):
                continue
            if eff.get("achievements") is False and _matches_any(f, ACHIEVEMENT_FACT_IDS, _ACH_LABELS):
                continue
            if eff.get("latest_achievement") is False and _matches_any(f, LATEST_FACT_IDS, _LATEST_LABELS):
                continue
            if eff.get("playtime") is False and _matches_any(f, PLAYTIME_FACT_IDS, _PLAYTIME_LABELS):
                continue
            kept.append(f)
        out["facts"] = kept
    elif "facts" in out and facts is None:
        out["facts"] = []
    return out


def card_fields(card: Any, preferences: Any = None) -> list:
    """Return [{id,label,has_characters,visible}] of SOURCE facts only.

    Synthetic achievement/playtime/latest rows excluded (they are frontend
    synthetic, not save facts). No counts invented. `visible` computed
    against `preferences` when supplied, else True for all source facts.
    """
    if not isinstance(card, dict):
        raise TypeError("card must be a dict")
    eff = _normalize_prefs(preferences) if preferences is not None else None
    hidden = set((eff or {}).get("hidden_fact_ids") or [])
    out = []
    for f in card.get("facts") or []:
        if not isinstance(f, dict):
            continue
        fid = _fact_stable_id(f)
        # exclude synthetic rows from source listing
        if _matches_any(f, ACHIEVEMENT_FACT_IDS, _ACH_LABELS):
            continue
        if _matches_any(f, LATEST_FACT_IDS, _LATEST_LABELS):
            continue
        if _matches_any(f, PLAYTIME_FACT_IDS, _PLAYTIME_LABELS):
            continue
        label = f.get("label")
        label_s = str(label) if label is not None else ""
        has_ch = bool(_is_character_fact(f))
        visible = True
        if eff is not None:
            if eff.get("facts") is False:
                visible = False
            elif fid is not None and fid in hidden:
                visible = False
            elif eff.get("characters") is False and has_ch:
                visible = False
        out.append({
            "id": fid if fid is not None else "",
            "label": label_s,
            "has_characters": has_ch,
            "visible": visible,
        })
    return out


class PublicPreferences:
    """Independent card display preferences over supplied root/settings.json."""

    METHODS = {
        "get_card_preferences",
        "set_card_preference",
        "reset_card_preferences",
    }

    def __init__(self, root, settings_lock=None):
        # No I/O at construction.
        self.root = Path(root).resolve()
        self._settings_lock = settings_lock if settings_lock is not None else threading.RLock()

    def call(self, method: str, args) -> Any:
        if not isinstance(args, (list, tuple)):
            raise ValueError("Arguments must be a list or tuple")
        if method not in self.METHODS:
            raise ValueError("Unknown method %r" % (method,))
        fn = getattr(self, method)
        return fn(*args)

    def _settings_path(self) -> Path:
        return self.root / "settings.json"

    def _snapshot(self) -> tuple[dict, dict]:
        """Read (global_sparse, games_sparse) fail-safe. No writes."""
        path = self._settings_path()
        raw, _malformed = _read_raw_settings(path)
        return _extract_display(raw)

    def _persist(self, global_sparse: dict, games_sparse: dict) -> None:
        """Atomic write preserving unrelated keys. Raises on symlink/oversize."""
        path = self._settings_path()
        if _is_symlink(path):
            raise ValueError("settings.json symlink refused")
        # Ensure parent exists (only on write, not construction).
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ValueError("Cannot create settings dir") from exc
        raw, _malformed = _read_raw_settings(path)
        if _malformed:
            raise ValueError('Malformed settings must be recovered before saving')
        base = dict(raw) if isinstance(raw, dict) else {}
        # Only display fields are replaced; everything else preserved.
        if global_sparse:
            base["card_display"] = dict(global_sparse)
        else:
            base.pop("card_display", None)
        if games_sparse:
            base["card_display_games"] = {k: dict(v) for k, v in games_sparse.items()}
        else:
            base.pop("card_display_games", None)
        try:
            text = json.dumps(base, ensure_ascii=False, indent=2) + "\n"
        except (TypeError, ValueError) as exc:
            raise ValueError("Cannot serialize settings") from exc
        if len(text.encode("utf-8")) > MAX_JSON_BYTES:
            raise ValueError("settings.json exceeds size limit")
        tmp = path.with_suffix(path.suffix + ".tmp")
        if _is_symlink(tmp):
            try:
                tmp.unlink()
            except OSError:
                raise ValueError("tmp symlink refused")
        try:
            tmp.write_text(text, encoding="utf-8", newline="\n")
            os.replace(tmp, path)
        except OSError as exc:
            try:
                if tmp.exists() and not _is_symlink(tmp):
                    tmp.unlink()
            except OSError:
                pass
            raise ValueError("Cannot write settings.json") from exc

    def _readback(self, appid: int | None, global_sparse: dict, games_sparse: dict) -> dict:
        g_merged = dict(DEFAULTS)
        g_merged["hidden_fact_ids"] = list(DEFAULTS["hidden_fact_ids"])
        for k, v in global_sparse.items():
            g_merged[k] = list(v) if k == "hidden_fact_ids" else v
        if appid is None:
            game_sparse: dict = {}
            eff = dict(g_merged)
            eff["hidden_fact_ids"] = list(g_merged["hidden_fact_ids"])
        else:
            game_sparse = dict(games_sparse.get(str(appid), {}))
            eff = _merge_effective(global_sparse, game_sparse)
        return {
            "global": copy.deepcopy(g_merged),
            "game": copy.deepcopy(game_sparse),
            "effective": copy.deepcopy(eff),
        }

    # -- public API (all synchronous, atomic under settings_lock) --

    def get_card_preferences(self, appid=None) -> dict:
        if appid is None:
            aid = None
        else:
            aid = _strict_appid(appid)
        with self._settings_lock:
            gsparse, games = self._snapshot()
            return self._readback(aid, gsparse, games)

    def set_card_preference(self, appid_or_none=None, key=None, value=None) -> dict:
        _validate_key(key)
        if appid_or_none is None:
            aid = None
        else:
            aid = _strict_appid(appid_or_none)
        if value is None:
            if aid is None:
                raise ValueError("Global preference cannot be null (use reset)")
            # clear per-game override key
            with self._settings_lock:
                gsparse, games = self._snapshot()
                entry = dict(games.get(str(aid), {}))
                entry.pop(key, None)
                if entry:
                    if len(games) > MAX_APPS and str(aid) not in games:
                        raise ValueError("Too many per-game rows")
                    games = dict(games)
                    games[str(aid)] = entry
                else:
                    if str(aid) in games:
                        games = dict(games)
                        games.pop(str(aid), None)
                self._persist(gsparse, games)
                return self._readback(aid, gsparse, games)
        norm = _validate_value(key, value)
        with self._settings_lock:
            gsparse, games = self._snapshot()
            if aid is None:
                gsparse = dict(gsparse)
                gsparse[key] = norm
                self._persist(gsparse, games)
            else:
                games = dict(games)
                entry = dict(games.get(str(aid), {}))
                entry[key] = norm
                if str(aid) not in games and len(games) >= MAX_APPS:
                    raise ValueError("Too many per-game rows (max %d)" % MAX_APPS)
                games[str(aid)] = entry
                self._persist(gsparse, games)
            return self._readback(aid, gsparse, games)

    def reset_card_preferences(self, appid_or_none=None) -> dict:
        if appid_or_none is None:
            aid = None
        else:
            aid = _strict_appid(appid_or_none)
        with self._settings_lock:
            gsparse, games = self._snapshot()
            if aid is None:
                gsparse = {}
            else:
                if str(aid) in games:
                    games = dict(games)
                    games.pop(str(aid), None)
            self._persist(gsparse, games)
            return self._readback(aid, gsparse, games)
