"""Public standalone theme engine (Big Picture) with owner UI parity.

Port of the pure theme mechanism from the owner's theme engine. No owner
paths, no Deck or machine settings, no shell or network calls. Operates only on
a supplied assets package (theme dirs + ``css_translations.json``) and a
supplied per-user Continue root (state file ``themes.json``).

Assets layout: ``assets/<Theme>/theme.json`` (+ ``*.css``) and
``assets/css_translations.json``. A legacy ``assets/deck/<Theme>/`` layout is
also accepted. Optional ``assets/defaults.json`` supplies a sanitized theme
option map used only to seed new public state.

State: ``root/themes.json`` written atomically (tmp + os.replace), distinct
from the owner ``data/themes.json``. Nothing is read or written at import or
construction time.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

KINDS = ("bp", "menu", "qam")
METHODS = frozenset({"themes_list", "themes_set", "themes_css"})

PC_OFF = frozenset({"Clean Gameview", "No What's New"})
PC_NOTE = "на ПК это уже делает Continue?"
FIXES = (("calc(100vh - 80px - 14px", "calc(100vh - 40px - 14px"),)

DEFAULT_MAPPINGS = {
    "bigpicture": ["@bp"], "bigpictureoverlay": ["@qam", "@menu"],
    "SP": ["bigpicture"], "Steam Big Picture Mode": ["bigpicture"],
    "MainMenu": ["@menu"], "MainMenu_.*": ["@menu"],
    "QuickAccess": ["@qam"], "QuickAccess_.*": ["@qam"],
    "All": ["bigpicture", "bigpictureoverlay"],
}

# Bounded sizes (no arbitrary reads).
MAX_THEME_JSON_BYTES = 512 * 1024
MAX_TRANSLATIONS_BYTES = 8 * 1024 * 1024
MAX_DEFAULTS_BYTES = 256 * 1024
MAX_STATE_BYTES = 512 * 1024
MAX_CSS_BYTES = 512 * 1024
MAX_TOTAL_CSS_BYTES = 4 * 1024 * 1024
MAX_JSON_DEPTH = 8
MAX_THEMES = 256
MAX_PATCHES_PER_THEME = 100
MAX_VALUES_PER_PATCH = 100
MAX_NAME_LEN = 128
MAX_PATCH_LEN = 128
MAX_VALUE_LEN = 256
MAX_CLASSES = 50000
MAX_CLASS_LEN = 256

_CLASS_RE = re.compile(r"\.([_a-zA-Z]+[_a-zA-Z0-9-]*)")
_ATTR_RE = re.compile(r'(\[class[*^|~]=")([_a-zA-Z0-9-]*)("\])')
_KEY_RE = re.compile(r"[A-Za-z0-9 _\-./]{1,256}")
_VAR_RE = re.compile(r"--[A-Za-z0-9_-]{1,64}")


def _bounded_str(value, lo=1, hi=MAX_VALUE_LEN):
    return isinstance(value, str) and lo <= len(value) <= hi


def _json_depth_ok(node, depth=0):
    if depth > MAX_JSON_DEPTH:
        return False
    if isinstance(node, dict):
        if len(node) > 512:
            return False
        return all(isinstance(k, str) and _json_depth_ok(v, depth + 1) for k, v in node.items())
    if isinstance(node, list):
        if len(node) > 512:
            return False
        return all(_json_depth_ok(v, depth + 1) for v in node)
    return isinstance(node, (str, bool, int, float)) or node is None


def _read_json_capped(path: Path, cap: int):
    try:
        if path.stat().st_size > cap:
            return None
        with path.open('rb') as stream:
            raw = stream.read(cap + 1)
    except OSError:
        return None
    if len(raw) > cap or not raw.strip():
        return None
    try:
        node = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    if not _json_depth_ok(node):
        return None
    return node


def _safe_file_key(key: str):
    """Validate a theme file key; return normalized relative path or None."""
    if not isinstance(key, str) or not (1 <= len(key) <= 256):
        return None
    if "\x00" in key or "://" in key or key.lower().startswith("file:"):
        return None
    if key.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", key):
        return None
    if not _KEY_RE.fullmatch(key):
        return None
    if not key.lower().endswith(".css"):
        return None
    parts = key.replace("\\", "/").split("/")
    if any(p in ("", ".", "..") for p in parts) or len(parts) > 8:
        return None
    return "/".join(parts)


def _resolve_within(path: Path, base: Path):
    """Resolved path if it stays within base (symlink-safe), else None."""
    try:
        resolved = path.resolve()
        base_r = base.resolve()
    except OSError:
        return None
    try:
        resolved.relative_to(base_r)
    except ValueError:
        return None
    return resolved


def _rgb(col):
    if not isinstance(col, str) or not col.startswith("#"):
        return None
    v = col[1:]
    if not v or len(v) > 8 or any(c not in "0123456789abcdefABCDEF" for c in v):
        return None
    try:
        if len(v) < 6:
            return tuple(int(v[i], 16) * 17 for i in range(3)) if len(v) >= 3 else None
        return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, IndexError):
        return None


class _Theme:
    def __init__(self, folder: Path, data=None, broken=False):
        self.folder = folder
        self.broken = broken
        self.json = data
        if data is None:
            self.name = folder.name
            self.tabs, self.deps, self.patches = {}, {}, {}
            self.inject = {"theme.css": ["All"]} if (folder / "theme.css").is_file() else {}
            return
        name = data.get("name")
        self.name = name if _bounded_str(name, 1, MAX_NAME_LEN) else folder.name
        tabs = data.get("tabs") or {}
        self.tabs = {k: v for k, v in tabs.items()
                     if _bounded_str(k, 1, MAX_PATCH_LEN) and isinstance(v, list)} \
            if isinstance(tabs, dict) else {}
        deps = data.get("dependencies") or {}
        self.deps = {k: v for k, v in deps.items()
                     if _bounded_str(k, 1, MAX_NAME_LEN)} \
            if isinstance(deps, dict) else {}
        inject = data.get("inject") or {}
        self.inject = dict(inject) if isinstance(inject, dict) else {}
        self.patches = {}
        patches = data.get("patches") or {}
        if not isinstance(patches, dict):
            return
        for pname, p in list(patches.items())[:MAX_PATCHES_PER_THEME]:
            if not _bounded_str(pname, 1, MAX_PATCH_LEN) or not isinstance(p, dict):
                continue
            values = p["values"] if "values" in p and isinstance(p["values"], dict) \
                else {k: v for k, v in p.items() if k != "default"}
            if not values or not isinstance(values, dict):
                continue
            values = {k: v for k, v in list(values.items())[:MAX_VALUES_PER_PATCH]
                      if _bounded_str(k, 1, MAX_VALUE_LEN)}
            if not values:
                continue
            ptype = p.get("type", "dropdown")
            if ptype not in ("dropdown", "checkbox", "slider", "none"):
                ptype = "dropdown"
            if ptype == "checkbox" and not {"Yes", "No"} <= set(values):
                ptype = "dropdown"
            default = p.get("default")
            if default not in values:
                default = next(iter(values))
            comps = [c for c in (p.get("components") or [])
                     if isinstance(c, dict) and c.get("type") == "color-picker"]
            self.patches[pname] = {"type": ptype, "default": default,
                                   "values": values, "components": comps[:32]}

    def kinds(self, tabs):
        """Map tab targets to {'bp','menu','qam'} with recursion guard."""
        if not isinstance(tabs, list):
            return set()
        if not tabs:
            tabs = self.tabs.get("default") or []
        out, stack = set(), [(list(tabs)[:32], 0, frozenset())]
        while stack:
            items, depth, seen = stack.pop()
            if depth > 8:
                continue
            for t in items:
                if not isinstance(t, str) or len(t) > MAX_PATCH_LEN:
                    continue
                if t.startswith("@"):
                    if t[1:] in KINDS:
                        out.add(t[1:])
                elif t in self.tabs:
                    if t in seen:
                        continue
                    sub = self.tabs[t]
                    if isinstance(sub, list):
                        stack.append((sub[:32], depth + 1, seen | {t}))
                elif t in DEFAULT_MAPPINGS:
                    stack.append((DEFAULT_MAPPINGS[t], depth + 1, seen))
                elif t.startswith("~") and t.endswith("~") and len(t) > 2:
                    if "Steam Gamepad" in t or "Steam%20Gamepad" in t:
                        out.add("bp")
                elif not t.startswith("!"):
                    for kind, title in (("menu", "MainMenu_uid1"),
                                        ("qam", "QuickAccess_uid1"), ("bp", "SP")):
                        try:
                            if re.fullmatch(t, title):
                                out.add(kind)
                        except re.error:
                            pass
        return out

    def css(self, conf, cmap, assets_root: Path):
        out = {k: [] for k in KINDS}
        total = [0]

        def add(items):
            if not isinstance(items, dict):
                return
            for key, tabs in list(items.items())[:256]:
                if not isinstance(key, str) or len(key) > 256:
                    continue
                if not isinstance(tabs, list) or len(tabs) > 32:
                    continue
                if key.startswith("--"):
                    if not _VAR_RE.fullmatch(key) or not tabs:
                        continue
                    val = tabs[0]
                    if not isinstance(val, str) or len(val) > 512:
                        continue
                    if any(c in val for c in ";{}<>"):
                        continue
                    kinds = self.kinds(tabs[1:])
                    text = ":root { %s: %s; }" % (key, val)
                else:
                    norm = _safe_file_key(key)
                    if norm is None:
                        continue
                    fpath = _resolve_within(self.folder / norm, self.folder)
                    if fpath is None or fpath != _resolve_within(self.folder / norm, assets_root):
                        continue
                    try:
                        if fpath.stat().st_size > MAX_CSS_BYTES:
                            continue
                        text = fpath.read_text(encoding="utf-8")
                    except (OSError, ValueError, UnicodeDecodeError):
                        continue
                    if len(text) > MAX_CSS_BYTES:
                        continue
                    text = _translate(text, cmap)
                    kinds = self.kinds(tabs)
                if text and kinds:
                    if total[0] + len(text) > MAX_TOTAL_CSS_BYTES:
                        return
                    total[0] += len(text)
                    for k in kinds:
                        out[k].append(text)

        add(self.inject)
        for pname, p in self.patches.items():
            raw = conf.get(pname, p["default"]) if isinstance(conf, dict) else p["default"]
            value = raw.get("value", p["default"]) if isinstance(raw, dict) else raw
            if value not in p["values"]:
                value = p["default"]
            add(p["values"][value])
            chosen = raw.get("components", {}) if isinstance(raw, dict) else {}
            if not isinstance(chosen, dict):
                chosen = {}
            for c in p["components"]:
                if not isinstance(c, dict) or c.get("on") != value:
                    continue
                var = c.get("css_variable", "")
                if not isinstance(var, str) or not var:
                    continue
                var = var if var.startswith("--") else "--" + var
                if not _VAR_RE.fullmatch(var):
                    continue
                col = chosen.get(c.get("name", ""), c.get("default", "#ffffff"))
                if not isinstance(col, str) or len(col) > 64 or ";" in col or ";" in var:
                    continue
                if "\n" in col or "{" in col or "}" in col:
                    continue
                rgb = _rgb(col)
                text = (":root { %s: %s; " % (var, col)
                        + ("{v}_r: {r}; {v}_g: {g}; {v}_b: {b}; {v}_rgb: {r}, {g}, {b}; ".format(
                            v=var, r=rgb[0], g=rgb[1], b=rgb[2]) if rgb else "") + "}")
                kinds = self.kinds(c.get("tabs") or [])
                if not kinds:
                    kinds = self.kinds([])
                    if not kinds:
                        continue
                if total[0] + len(text) > MAX_TOTAL_CSS_BYTES:
                    continue
                total[0] += len(text)
                for k in kinds:
                    out[k].append(text)
        return {k: "\n".join(v) for k, v in out.items()}


def _translate(css, cmap):
    css = _CLASS_RE.sub(lambda m: "." + cmap.get(m.group(1), m.group(1)), css)
    css = _ATTR_RE.sub(lambda m: m.group(1) + cmap.get(m.group(2), m.group(2)) + m.group(3), css)
    for a, b in FIXES:
        css = css.replace(a, b)
    return css


class PublicThemes:
    """Standalone public theme engine over supplied ``assets`` and ``root``."""

    METHODS = METHODS

    def __init__(self, assets, root):
        self.assets = Path(assets)
        self.root = Path(root)

    # -- layout helpers (no I/O at construction) --
    def _theme_root(self):
        deck = self.assets / "deck"
        try:
            if deck.is_dir():
                return deck
        except OSError:
            pass
        return self.assets

    def _table_path(self):
        direct = self.assets / "css_translations.json"
        try:
            if direct.is_file():
                return direct
        except OSError:
            pass
        return self._theme_root() / "css_translations.json"

    def _defaults_path(self):
        direct = self.assets / "defaults.json"
        try:
            if direct.is_file():
                return direct
        except OSError:
            pass
        cand = self._theme_root() / "defaults.json"
        if cand != direct:
            return cand
        return direct

    def _state_path(self):
        return self.root / "themes.json"

    # -- loading --
    def _load_themes(self):
        out = {}
        try:
            root = self._theme_root()
            if not root.is_dir():
                return out
            dirs = sorted([d for d in root.iterdir() if d.is_dir()], key=lambda p: p.name)
        except OSError:
            return out
        for d in dirs[:MAX_THEMES]:
            if d.name == "__pycache__" or d.is_symlink() or not d.resolve().is_relative_to(root.resolve()):
                continue
            try:
                has_json = (d / "theme.json").is_file()
                has_css = (d / "theme.css").is_file()
            except OSError:
                continue
            if not has_json and not has_css:
                continue
            try:
                if has_json and (d / "theme.json").stat().st_size > MAX_THEME_JSON_BYTES:
                    continue
            except OSError:
                continue
            data = None
            if has_json:
                data = _read_json_capped(d / "theme.json", MAX_THEME_JSON_BYTES)
                if data is None or not isinstance(data, dict):
                    continue
            try:
                t = _Theme(d, data)
            except (ValueError, KeyError):
                continue
            if t.name not in out:
                out[t.name] = t
        return out

    def _load_translations(self):
        node = _read_json_capped(self._table_path(), MAX_TRANSLATIONS_BYTES)
        return node if isinstance(node, dict) else {}

    def _load_defaults(self, themes):
        node = _read_json_capped(self._defaults_path(), MAX_DEFAULTS_BYTES)
        if not isinstance(node, dict):
            return {}
        clean = {}
        for name, conf in node.items():
            if not _bounded_str(name, 1, MAX_NAME_LEN) or name not in themes:
                continue
            if not isinstance(conf, dict):
                continue
            t = themes[name]
            seeded = {}
            for pname, val in conf.items():
                if pname == "active":
                    if type(val) is bool:
                        seeded["active"] = val
                    continue
                if pname not in t.patches or not _bounded_str(pname, 1, MAX_PATCH_LEN):
                    continue
                p = t.patches[pname]
                if isinstance(val, str) and val in p["values"]:
                    seeded[pname] = val
                elif isinstance(val, dict):
                    v = val.get("value")
                    if v in p["values"]:
                        comps = val.get("components", {})
                        if isinstance(comps, dict) and all(
                                isinstance(k, str) and isinstance(vv, str)
                                and len(k) <= 64 and len(vv) <= 64 for k, vv in comps.items()):
                            seeded[pname] = {"value": v, "components": dict(list(comps.items())[:32])}
                        else:
                            seeded[pname] = v
            clean[name] = seeded
        return clean

    def _load_state(self, themes):
        try:
            with self._state_path().open('rb') as stream:
                raw = stream.read(MAX_STATE_BYTES + 1)
        except OSError:
            raw = None
        st = {}
        if raw is not None:
            if len(raw) > MAX_STATE_BYTES or not raw.strip():
                st = {}
            else:
                try:
                    node = json.loads(raw.decode("utf-8"))
                    st = node if isinstance(node, dict) and _json_depth_ok(node) else {}
                except (ValueError, UnicodeDecodeError):
                    st = {}
        defaults = self._load_defaults(themes)
        changed = False
        for name in themes:
            if name not in st or not isinstance(st.get(name), dict):
                seed = {"active": False}
                for k, v in (defaults.get(name) or {}).items():
                    if k != "active":
                        seed[k] = v
                if isinstance((defaults.get(name) or {}).get("active"), bool):
                    seed["active"] = (defaults[name]["active"] and name not in PC_OFF)
                if name in PC_OFF:
                    seed["active"] = False
                st[name] = seed
                changed = True
            else:
                if name in PC_OFF and st[name].get("active") is True and name not in defaults:
                    pass  # explicit user toggle is honored; only seed defaults to off
        if changed:
            self._save_state(st)
        return st

    def _save_state(self, st):
        path = self._state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, path)

    def _class_map(self, table, actual):
        have = set(actual) if actual else set()
        out = {}
        if not isinstance(table, dict):
            return out
        for v in list(table.values())[:200000]:
            if not isinstance(v, list) or not v:
                continue
            vals = [c for c in v if isinstance(c, str) and 1 <= len(c) <= MAX_CLASS_LEN][:32]
            if not vals:
                continue
            target = next((c for c in reversed(vals) if c in have), None) if have else None
            target = target or vals[-1]
            for old in vals:
                if old != target:
                    out[old] = target
        return out

    # -- public API --
    def themes_list(self):
        themes = self._load_themes()
        st = self._load_state(themes)
        needed: dict = {}
        for name, t in themes.items():
            if isinstance(st.get(name), dict) and st[name].get("active"):
                for dep in t.deps:
                    needed.setdefault(dep, []).append(name)
        out = []
        for name, t in themes.items():
            conf = st.get(name) if isinstance(st.get(name), dict) else {}
            patches = []
            for pname, p in t.patches.items():
                if p["type"] == "none":
                    continue
                raw = conf.get(pname, p["default"])
                value = raw.get("value", p["default"]) if isinstance(raw, dict) else raw
                patches.append({"name": pname, "type": p["type"],
                                "values": list(p["values"]),
                                "value": value if value in p["values"] else p["default"]})
            out.append({"name": name, "active": bool(conf.get("active")),
                        "required_by": list(needed.get(name, [])),
                        "pc_note": PC_NOTE if name in PC_OFF else "",
                        "patches": patches})
        return out

    def themes_set(self, name, patch, value):
        if not _bounded_str(name, 1, MAX_NAME_LEN):
            raise ValueError("unknown theme")
        themes = self._load_themes()
        if name not in themes:
            raise ValueError("unknown theme")
        st = self._load_state(themes)
        conf = st.get(name)
        if not isinstance(conf, dict):
            conf = st[name] = {"active": False}
        if patch is None:
            if type(value) is not bool:
                raise ValueError("toggle value must be bool")
            conf["active"] = value
        else:
            if not _bounded_str(patch, 1, MAX_PATCH_LEN):
                raise ValueError("unknown patch")
            if not isinstance(value, str) or not (1 <= len(value) <= MAX_VALUE_LEN):
                raise ValueError("unknown patch value")
            p = themes[name].patches.get(patch)
            if p is None or value not in p["values"]:
                raise ValueError("unknown patch value")
            raw = conf.get(patch)
            conf[patch] = {**raw, "value": value} if isinstance(raw, dict) else value
        self._save_state(st)
        return self.themes_list()

    def themes_css(self, actual_classes=None):
        if actual_classes is None:
            actual_classes = []
        if not isinstance(actual_classes, list) or len(actual_classes) > MAX_CLASSES:
            raise ValueError("invalid actual_classes")
        for c in actual_classes:
            if not isinstance(c, str) or not (1 <= len(c) <= MAX_CLASS_LEN):
                raise ValueError("invalid actual_classes")
        themes = self._load_themes()
        st = self._load_state(themes)
        cmap = self._class_map(self._load_translations(), actual_classes)
        order, conf = [], {}

        def want(name, override=None, seen=()):
            t = themes.get(name)
            if t is None or name in seen:
                return
            if not _bounded_str(name, 1, MAX_NAME_LEN):
                return
            for dep, dep_over in list(t.deps.items())[:32]:
                want(dep, dep_over if isinstance(dep_over, dict) else None, seen + (name,))
            c = dict(st.get(name) or {})
            if isinstance(override, dict):
                for k, v in list(override.items())[:32]:
                    if isinstance(k, str) and len(k) <= MAX_PATCH_LEN:
                        c[k] = v
            conf[name] = c
            if name not in order:
                order.append(name)

        for name in themes:
            if isinstance(st.get(name), dict) and st[name].get("active"):
                want(name)
        out = {k: [] for k in KINDS}
        for name in order:
            try:
                parts = themes[name].css(conf[name], cmap, self._theme_root())
            except (OSError, ValueError):
                continue
            for k, css in parts.items():
                if css:
                    out[k].append("/* %s */\n%s" % (name, css))
        return {k: "\n".join(v) for k, v in out.items()}

    def call(self, method, args):
        if not isinstance(method, str) or not isinstance(args, list) or len(args) > 8:
            raise ValueError("unknown public method or invalid arguments")
        if method == "themes_list":
            if args:
                raise ValueError("unknown public method or invalid arguments")
            return self.themes_list()
        if method == "themes_set":
            if len(args) != 3:
                raise ValueError("unknown public method or invalid arguments")
            return self.themes_set(args[0], args[1], args[2])
        if method == "themes_css":
            if len(args) > 1:
                raise ValueError("unknown public method or invalid arguments")
            if not args or args[0] is None:
                return self.themes_css()
            return self.themes_css(args[0])
        raise ValueError("unknown public method or invalid arguments")
