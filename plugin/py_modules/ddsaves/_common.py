"""Общие куски разборов ddsaves: только стандартная библиотека (на Деке нет pip).

Контракт read() каждого модуля (как в steamdeck/research/deep_dig/BRIEF.md):
  {place, objective, chapter, progress{}, facts[{icon,label,value}], unproven[], observed_at}
плюс необязательные для хаба: play_seconds, difficulty, source_path, proven[].
"""
from __future__ import annotations

import base64
import json
import os
import struct
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DATA = Path(__file__).resolve().parent / "data"


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
    return json.loads((DATA / f"{slug}.json").read_text(encoding="utf-8"))


def empty(reason: str = "") -> Dict[str, Any]:
    return {"place": None, "objective": None, "chapter": None, "progress": {}, "facts": [],
            "unproven": [], "observed_at": None, "reason": reason}


def newest(paths: Iterable[Path]) -> Optional[Path]:
    files = [p for p in paths if p.is_file()]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


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
    pos = 0

    def rd(n):
        nonlocal pos
        v = b[pos:pos + n]
        pos += n
        return v

    def obj():
        nonlocal pos
        t = b[pos]
        pos += 1
        if t <= 0x7F:
            return t
        if t >= 0xE0:
            return t - 0x100
        if 0x80 <= t <= 0x8F:
            return {_key(obj()): obj() for _ in range(t & 0x0F)}
        if 0x90 <= t <= 0x9F:
            return [obj() for _ in range(t & 0x0F)]
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
            return rd(n)
        if t in (0xC7, 0xC8, 0xC9):
            n = struct.unpack(">" + "BHI"[t - 0xC7], rd(1 << (t - 0xC7)))[0]
            rd(1)
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
            return rd(n).decode("utf-8", "replace")
        if t in (0xDC, 0xDD):
            n = int.from_bytes(rd(2 if t == 0xDC else 4), "big")
            return [obj() for _ in range(n)]
        if t in (0xDE, 0xDF):
            n = int.from_bytes(rd(2 if t == 0xDE else 4), "big")
            return {_key(obj()): obj() for _ in range(n)}
        raise ValueError(f"msgpack: неизвестный тип 0x{t:02x}")

    def _key(k):
        return k if not isinstance(k, (list, dict)) else json.dumps(k)

    return obj()


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


def steam_libraries() -> List[Path]:
    """Все библиотеки Steam (корни с папкой steamapps): основная + из libraryfolders.vdf — другие диски на ПК,
    microSD и внешние диски на Деке (/run/media/...). Кэш на процесс; пустой результат не кэшируем."""
    global _LIBS
    if _LIBS:
        return _LIBS
    import re
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
    _LIBS = _uniq(p for p in libs if (p / "steamapps").is_dir())
    return _LIBS


def game_dirs(installdir: str) -> List[Path]:
    """Папки установленной игры (steamapps/common/<installdir>) во всех библиотеках."""
    return [d for d in (lib / "steamapps/common" / installdir for lib in steam_libraries()) if d.is_dir()]


def steam_userdata(appid: int, sub: str = "") -> List[Path]:
    """userdata/<аккаунт>/<appid>[/sub] во всех установках Steam (облачные сейвы)."""
    out: List[Path] = []
    for root in steam_roots():
        for u in (root / "userdata").glob("*"):
            p = u / str(appid) / sub if sub else u / str(appid)
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
