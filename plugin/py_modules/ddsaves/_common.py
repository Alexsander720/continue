"""Общие куски разборов ddsaves: только стандартная библиотека (на Деке нет pip).

Контракт read() каждого модуля (как в steamdeck/research/deep_dig/BRIEF.md):
  {place, objective, chapter, progress{}, facts[{icon,label,value}], unproven[], observed_at}
плюс необязательные для хаба: play_seconds, difficulty, source_path, proven[].
"""
from __future__ import annotations

import base64
import json
import os
import re
import struct
import subprocess
import time
from pathlib import Path, PureWindowsPath
from typing import Any, Dict, Iterable, List, Optional

DATA = Path(__file__).resolve().parent / "data"

MAX_SAVE_BYTES = 64 * 1024 * 1024
_MSGPACK_MAX_ITEMS = 1_000_000
_MSGPACK_MAX_DEPTH = 100


def lang() -> str:
    """Requested Continue? language; invalid/unset values use the owner's RU default."""
    value = os.environ.get("CONTINUE_LANG", "ru").strip().lower()
    return value if value in ("ru", "en", "uk") else "ru"


def select(value):
    """Select a source-backed language map: requested language, then EN, then RU."""
    if isinstance(value, str) or value is None:
        return value
    if not isinstance(value, dict):
        return None
    for code in dict.fromkeys((lang(), "en", "ru")):
        text = value.get(code)
        if isinstance(text, str) and text:
            return text
    return None


def localize(value):
    """Resolve display leaves without mutating cached source tables or provenance."""
    if isinstance(value, dict):
        if value.get("_i18n") == 1:
            return select(value)
        return {k: v if k.startswith("_source") else localize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [localize(v) for v in value]
    return value


_LABELS = None


def labels():
    global _LABELS
    if _LABELS is None:
        _LABELS = json.loads((DATA / "_labels.json").read_text(encoding="utf-8"))
    return _LABELS


def ui(key: str, **values) -> str:
    """Our interface text (not a game translation)."""
    return (select(labels()["ui"][key]) or "").format(**values)


def table(slug: str) -> Dict[str, Any]:
    """Таблица названий, выгруженная из данных игры (ddsaves/data/<slug>.json, генерирует deep_dig/tools)."""
    if not isinstance(slug, str) or not slug:
        raise ValueError(f"table: недопустимый slug {slug!r}")
    if "\\" in slug or slug.startswith("/") or slug.startswith("\\"):
        raise ValueError(f"table: недопустимый slug {slug!r}")
    parts = slug.replace("\\", "/").split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise ValueError(f"table: недопустимый slug {slug!r}")
    if any(re.fullmatch(r"[A-Za-z0-9_.\-]+", p) is None for p in parts):
        raise ValueError(f"table: недопустимый slug {slug!r}")
    target = (DATA / f"{slug}.json").resolve()
    try:
        target.relative_to(DATA.resolve())
    except ValueError:
        raise ValueError(f"table: недопустимый slug {slug!r}")
    return json.loads(target.read_text(encoding="utf-8"))


def empty(reason: str = "") -> Dict[str, Any]:
    return {"place": None, "objective": None, "chapter": None, "progress": {}, "facts": [],
            "unproven": [], "observed_at": None, "reason": reason}


def newest(paths: Iterable[Path]) -> Optional[Path]:
    best: Optional[Path] = None
    best_mtime: Optional[float] = None
    for p in paths:
        try:
            if p.is_symlink():
                continue
            st = p.stat()
            if not p.is_file():
                continue
            if st.st_size > MAX_SAVE_BYTES:
                continue
            mtime = st.st_mtime
        except OSError:
            continue
        if best is None or mtime > best_mtime:
            best, best_mtime = p, mtime
    return best


def read_bytes(path) -> bytes:
    """Прочитать сейв целиком, проверив размер ДО выделения буфера; симлинки запрещены."""
    p = Path(path)
    if p.is_symlink():
        raise OSError(f"read_bytes: симлинк запрещён: {p}")
    size = p.stat().st_size
    if size > MAX_SAVE_BYTES:
        raise ValueError(f"read_bytes: сейв больше 64 MiB: {p}")
    with p.open('rb') as stream:
        data = stream.read(MAX_SAVE_BYTES + 1)
    if len(data) > MAX_SAVE_BYTES:
        raise ValueError(f"read_bytes: сейв больше 64 MiB: {p}")
    return data


def num(v) -> str:
    return f"{int(v):,}".replace(",", " ")


def dur(sec) -> str:
    try:
        s = float(sec)
    except (TypeError, ValueError):
        return ""
    if s < 60:
        return ""
    h, m = int(s // 3600), round((s % 3600) / 60)
    if m == 60:
        h, m = h + 1, 0
    return ui("hours_minutes", h=h, m=m) if h else ui("minutes", m=m)


def aes_ecb_decrypt(key: bytes, data: bytes) -> Optional[bytes]:
    """AES-ECB: cryptography, если есть (ПК), иначе системный openssl (Дека). Паддинг PKCS7 снимаем сами."""
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        d = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
        out = d.update(data) + d.finalize()
    except ImportError:
        bits = len(key) * 8
        env = {**os.environ, "LD_LIBRARY_PATH": "/usr/lib:/usr/lib64:/lib:/lib64"}  # Decky подменяет библиотеки
        r = subprocess.run(["openssl", "enc", "-d", f"-aes-{bits}-ecb", "-K", key.hex(), "-nosalt", "-nopad"],
                           input=data, capture_output=True, timeout=20, env=env)
        if r.returncode != 0:
            return None
        out = r.stdout
    pad = out[-1] if out else 0
    return out[:-pad] if 0 < pad <= 16 else out


def msgpack_unpack(b: bytes) -> Any:
    """Минимальный MessagePack-декодер (без расширений, кроме пропуска ext) — вместо пакета msgpack."""
    if not isinstance(b, (bytes, bytearray)):
        raise ValueError("msgpack: ожидаются байты")
    data = bytes(b)
    pos = 0

    def need(n: int):
        if n < 0 or pos + n > len(data):
            raise ValueError("msgpack: обрезанные данные")

    def rd(n: int) -> bytes:
        nonlocal pos
        need(n)
        v = data[pos:pos + n]
        pos += n
        return v

    def obj(depth: int = 0):
        nonlocal pos
        if depth > _MSGPACK_MAX_DEPTH:
            raise ValueError("msgpack: превышена глубина")
        if pos >= len(data):
            raise ValueError("msgpack: обрезанные данные")
        t = data[pos]
        pos += 1
        if t <= 0x7F:
            return t
        if t >= 0xE0:
            return t - 0x100
        if 0x80 <= t <= 0x8F:
            return {_key(obj(depth + 1)): obj(depth + 1) for _ in range(t & 0x0F)}
        if 0x90 <= t <= 0x9F:
            return [obj(depth + 1) for _ in range(t & 0x0F)]
        if 0xA0 <= t <= 0xBF:
            return rd(t & 0x1F).decode("utf-8", "replace")
        if t == 0xC0:
            return None
        if t == 0xC2:
            return False
        if t == 0xC3:
            return True
        if t in (0xC4, 0xC5, 0xC6):
            n = struct.unpack(">" + "BHI"[t - 0xC4], rd(1 << (t - 0xC4)))[0]
            if n > MAX_SAVE_BYTES or n > len(data) - pos:
                raise ValueError("msgpack: недопустимый размер bin")
            return rd(n)
        if t in (0xC7, 0xC8, 0xC9):
            n = struct.unpack(">" + "BHI"[t - 0xC7], rd(1 << (t - 0xC7)))[0]
            rd(1)
            if n > MAX_SAVE_BYTES or n > len(data) - pos:
                raise ValueError("msgpack: недопустимый размер ext")
            return rd(n)
        if t == 0xCA:
            return struct.unpack(">f", rd(4))[0]
        if t == 0xCB:
            return struct.unpack(">d", rd(8))[0]
        if 0xCC <= t <= 0xCF:
            return int.from_bytes(rd(1 << (t - 0xCC)), "big")
        if 0xD0 <= t <= 0xD3:
            return int.from_bytes(rd(1 << (t - 0xD0)), "big", signed=True)
        if 0xD4 <= t <= 0xD8:
            rd(1)
            return rd(1 << (t - 0xD4))
        if t in (0xD9, 0xDA, 0xDB):
            n = int.from_bytes(rd(1 << (t - 0xD9)), "big")
            if n > MAX_SAVE_BYTES or n > len(data) - pos:
                raise ValueError("msgpack: недопустимый размер str")
            return rd(n).decode("utf-8", "replace")
        if t in (0xDC, 0xDD):
            n = int.from_bytes(rd(2 if t == 0xDC else 4), "big")
            if n > _MSGPACK_MAX_ITEMS or n > len(data) - pos:
                raise ValueError("msgpack: недопустимый размер array")
            return [obj(depth + 1) for _ in range(n)]
        if t in (0xDE, 0xDF):
            n = int.from_bytes(rd(2 if t == 0xDE else 4), "big")
            if n > _MSGPACK_MAX_ITEMS or n > len(data) - pos:
                raise ValueError("msgpack: недопустимый размер map")
            return {_key(obj(depth + 1)): obj(depth + 1) for _ in range(n)}
        raise ValueError(f"msgpack: неизвестный тип 0x{t:02x}")

    def _key(k):
        return k if not isinstance(k, (list, dict)) else json.dumps(k)

    try:
        return obj()
    except (IndexError, struct.error) as e:
        raise ValueError(f"msgpack: обрезанные данные ({e})")


def dotnet_b64_string(raw: bytes) -> bytes:
    """BinaryFormatter-обёртка одной строки (22 байта заголовка + 7-битная длина) → base64-декод."""
    i, n, shift = 22, 0, 0
    while True:
        c = raw[i]
        i += 1
        n |= (c & 0x7F) << shift
        shift += 7
        if not c & 0x80:
            break
    return base64.b64decode(raw[i:i + n])


def fact(icon: str, label: str, value, *, id: Optional[str] = None) -> Dict[str, str]:
    """Stable fact ID and our translated label; legacy callers keep their RU label."""
    data = labels()
    key = id or data["legacy"].get(label)
    if key is None:
        # Private dynamic labels retain their exact text and a deterministic ID.
        import hashlib
        key = "label_" + hashlib.sha256(label.encode("utf-8")).hexdigest()[:12]
    # Some games use the same field ID with different UI nouns (e.g. gold/G).
    label_key = data["legacy"].get(label) or key
    name = select(data["labels"].get(label_key)) or label
    return {"id": key, "icon": icon, "label": name, "value": str(value)}


def finish(out: Dict[str, Any], path: Path) -> Dict[str, Any]:
    out.setdefault("objective", None)
    out.setdefault("chapter", None)
    out.setdefault("unproven", [])
    out["observed_at"] = path.stat().st_mtime
    out["source_path"] = str(path)
    return out


def deck_home() -> Path:
    """Домашняя папка Деки: Decky может запускать бэкенд от root (HOME=/root), а сейвы лежат у deck."""
    if Path("/home/deck").is_dir():
        return Path("/home/deck")
    return Path(os.environ.get("HOME") or "/home/deck")


def _uniq(paths: Iterable[Path]) -> List[Path]:
    seen, out = set(), []
    for p in paths:
        try:
            key = str(p.resolve()).lower() if os.name == "nt" else str(p.resolve())
        except OSError:
            key = str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def steam_roots() -> List[Path]:
    """Папки установки Steam: на Windows — из реестра (SteamPath) и Program Files, на Linux/Деке — ~/.local/share/Steam."""
    out: List[Path] = []
    if os.name == "nt":
        try:
            import winreg
            for hive, key, name in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                                    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath")):
                try:
                    with winreg.OpenKey(hive, key) as k:
                        out.append(Path(winreg.QueryValueEx(k, name)[0]))
                except OSError:
                    pass
        except ImportError:
            pass
        # реестр отдаёт путь в нижнем регистре — при совпадении оставляем вариант из Program Files
        pf86 = os.environ.get("ProgramFiles(x86)") or os.path.join(os.environ.get("SystemDrive", "C:") + os.sep, "Program Files (x86)")
        out.insert(0, Path(pf86) / "Steam")
    else:
        h = deck_home()
        out += [h / ".local/share/Steam", h / ".steam/steam"]
    return _uniq(p for p in out if (p / "steamapps").is_dir())


_LIBS: Optional[List[Path]] = None
_LIBS_AT: float = 0.0


def steam_libraries() -> List[Path]:
    """Все библиотеки Steam (корни с папкой steamapps): основная + из libraryfolders.vdf — другие диски на ПК,
    microSD и внешние диски на Деке (/run/media/...). Кэш на процесс (60 с); пустой результат не кэшируем."""
    global _LIBS, _LIBS_AT
    now = time.monotonic()
    if _LIBS and (now - _LIBS_AT) < 60.0:
        return _LIBS
    libs: List[Path] = list(steam_roots())
    for root in list(libs):
        vdf = root / "steamapps/libraryfolders.vdf"
        try:
            text = vdf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for p in re.findall(r'"path"\s+"([^"\n]+)"', text):
            libs.append(Path(p.replace("\\\\", "\\")))
    if os.name != "nt":   # SD-карта, ещё не попавшая в vdf (Steam пишет его лениво)
        libs += [p.parent for p in Path("/run/media").glob("*/steamapps")]
        libs += [p.parent for p in Path("/run/media").glob("*/*/steamapps")]
    result = _uniq(p for p in libs if (p / "steamapps").is_dir())
    if result:
        _LIBS = result
        _LIBS_AT = now
    return result


def game_dirs(installdir: str) -> List[Path]:
    """Папки установленной игры (steamapps/common/<installdir>) во всех библиотеках."""
    if not isinstance(installdir, str) or not installdir or installdir in (".", ".."):
        raise ValueError(f"game_dirs: недопустимый installdir {installdir!r}")
    if "\\" in installdir or Path(installdir).is_absolute() or PureWindowsPath(installdir).drive or ".." in installdir.split("/"):
        raise ValueError(f"game_dirs: недопустимый installdir {installdir!r}")
    return [d for d in (lib / "steamapps/common" / installdir for lib in steam_libraries()) if d.is_dir()]


def steam_userdata(appid: int, sub: str = "") -> List[Path]:
    """userdata/<аккаунт>/<appid>[/sub] во всех установках Steam (облачные сейвы)."""
    if isinstance(appid, bool) or not isinstance(appid, int):
        raise ValueError(f"steam_userdata: недопустимый appid {appid!r}")
    if not 0 < appid < 2 ** 32:
        raise ValueError(f"steam_userdata: недопустимый appid {appid!r}")
    if not isinstance(sub, str):
        raise ValueError(f"steam_userdata: недопустимый sub {sub!r}")
    safe_parts: List[str] = []
    if sub:
        if "\\" in sub or sub.startswith("/"):
            raise ValueError(f"steam_userdata: недопустимый sub {sub!r}")
        parts = sub.replace("\\", "/").split("/")
        if any(p in ("", ".", "..") for p in parts):
            raise ValueError(f"steam_userdata: недопустимый sub {sub!r}")
        if any(re.fullmatch(r"[A-Za-z0-9_.\-]+", p) is None for p in parts):
            raise ValueError(f"steam_userdata: недопустимый sub {sub!r}")
        safe_parts = parts
    out: List[Path] = []
    for root in steam_roots():
        for u in (root / "userdata").glob("*"):
            p = u / str(appid)
            for part in safe_parts:
                p = p / part
            if p.is_dir() or p.is_file():
                out.append(p)
    return out


def proton_user(appid: int) -> List[Path]:
    """Папки steamuser префикса Proton (Дека и Linux). Префикс лежит в той библиотеке, где стоит игра,
    поэтому у игр на microSD он на карте — перебираем все библиотеки (до 08.10 искали только во внутренней)."""
    h = deck_home()
    sub = f"steamapps/compatdata/{appid}/pfx/drive_c/users/steamuser"
    out = [h / ".local/share/Steam" / sub, h / ".steam/steam" / sub]
    if os.name != "nt":
        out += [lib / sub for lib in steam_libraries()]
    return _uniq(out)


def documents_dirs() -> List[Path]:
    r"""Настоящие «Документы» Windows: у владельца это OneDrive\Документы (реестр User Shell Folders → Personal),
    а не %USERPROFILE%\Documents — по нему не находились сейвы NieR/Spider-Man 2/Alan Wake (03.10.2026)."""
    out: List[Path] = []
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
                out.append(Path(os.path.expandvars(winreg.QueryValueEx(k, "Personal")[0])))
        except OSError:
            pass
    if os.environ.get("USERPROFILE"):
        out.append(Path(os.environ["USERPROFILE"]) / "Documents")
    seen, uniq = set(), []
    for p in out:
        if str(p).lower() not in seen:
            seen.add(str(p).lower())
            uniq.append(p)
    return uniq
