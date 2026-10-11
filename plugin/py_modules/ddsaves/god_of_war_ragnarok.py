"""God of War Ragnarök (appid 2322010): GOWRSAVE<N> в «Saved Games/God of War Ragnarök/<id>/».

Перенесено 08.10.2026 из GameHub/gowsave.py — только доказанное (для Continue? и Деки, одна стандартная библиотека):
  • место и задание — строка, которую САМА игра пишет в заголовок сейва на своём языке: «Мир - Область - Задание»
    (0x50..0x190); сверено на 22 слотах: ID строки задания (0x1B0) указывает в r_lang_<язык>.wad ровно на этот текст;
  • время игры (0x190), счётчик сохранений (0x1BC — выбор самого свежего слота);
  • серебро — кошелёк героя, предмет с хешем имени «Hacksilver» 0x5AE80674… (в 0x198 заголовка — накопленное
    за всю игру, не то, что на экране);
  • Вороны Одина: предмет кошелька 0x482780EF… + 3 × дары Древа воронов 0x28FB7355… (сверено с экраном
    просьбы «Глаза Одина» 21.09 и 02.10), всего в игре 48.
Не переносится: рукописные описания вех, «уровень» (среднее снаряжения), текст из дневника (ID+1 не всегда описание).
"""
from __future__ import annotations

import os
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ddsaves._common import dur, empty, fact, finish, num, proton_user

APPID = 2322010
MAGIC_VERSION = 0x00660404
STRING_OFFSET, STRING_END = 0x50, 0x190
HERO_WALLET_HASH = 0x00004895C643225F
RAVEN_ITEM, RAVEN_GIFT, RAVENS_TOTAL = 0x482780EFF18ED57E, 0x28FB73555D08478B, 48
HACKSILVER = 0x5AE80674D240529E
FOLDERS = ("God of War Ragnarök", "God of War Ragnarok")


def _saved_games_dirs() -> List[Path]:
    out: List[Path] = []
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
                out.append(Path(os.path.expandvars(winreg.QueryValueEx(k, "{4C5C32FF-BB9D-43b0-B5B4-2D72E54EAAA4}")[0])))
        except OSError:
            pass
        home = Path(os.environ.get("USERPROFILE") or Path.home())
        out += [home / "Saved Games", home / "OneDrive/Saved Games"]
    out += [u / "Saved Games" for u in proton_user(APPID)]
    return out


def default_dirs() -> List[Path]:
    dirs = []
    for base in _saved_games_dirs():
        for name in FOLDERS:
            root = base / name
            if root.is_dir():
                dirs += [d for d in root.iterdir() if d.is_dir() and any(d.glob("GOWRSAVE*"))]
    return dirs


def header(buf: bytes) -> Optional[Dict[str, Any]]:
    if len(buf) < 0x1C0:
        return None
    if struct.unpack_from("<I", buf, 0x0C)[0] != MAGIC_VERSION or struct.unpack_from("<I", buf, 0x4C)[0] != MAGIC_VERSION:
        return None
    place = buf[STRING_OFFSET:STRING_END].split(b"\x00")[0].decode("utf-8", "replace").strip()
    return {"place": place,
            "play_seconds": struct.unpack_from("<I", buf, 0x190)[0],
            "objective_string_id": struct.unpack_from("<I", buf, 0x1B0)[0],
            "save_counter": struct.unpack_from("<I", buf, 0x1BC)[0]}


def split_place(place: str) -> Dict[str, Optional[str]]:
    """«Ванахейм - Джунгли - Отправиться в Муспельхейм» → мир / область / задание (разделитель пишет игра)."""
    parts = [p.strip() for p in (place or "").split(" - ") if p.strip()]
    if len(parts) >= 3:
        return {"realm": parts[0], "area": " - ".join(parts[1:-1]), "objective": parts[-1]}
    if len(parts) == 2:
        return {"realm": parts[0], "area": None, "objective": parts[1]}
    return {"realm": parts[0] if parts else None, "area": None, "objective": None}


def wallet(data: bytes) -> Dict[int, int]:
    off = data.find(struct.pack("<Q", HERO_WALLET_HASH))
    if off < 0:
        return {}
    try:
        count = struct.unpack_from("<I", data, off + 8)[0]
    except struct.error:
        return {}
    wallet, cur = {}, off + 20
    for _ in range(min(count, 100000)):
        if cur + 16 > len(data):
            break
        h, q = struct.unpack_from("<QI", data, cur)
        wallet[h] = q
        cur += 16
    return wallet


def find(path_or_dir: Optional[Union[str, Path]] = None) -> Optional[Path]:
    """Самый свежий слот: по счётчику сохранений игры (mtime у старых копий бывает перепутан)."""
    if path_or_dir is not None and Path(path_or_dir).is_file():
        return Path(path_or_dir)
    dirs = [Path(path_or_dir)] if path_or_dir is not None else default_dirs()
    best, key = None, None
    for d in dirs:
        for p in d.glob("GOWRSAVE*"):
            try:
                with p.open("rb") as f:
                    h = header(f.read(0x1C0))
            except OSError:
                continue
            if h and h["place"]:
                k = (h["save_counter"], p.stat().st_mtime)
                if key is None or k > key:
                    best, key = p, k
    return best


def read(path_or_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    path = find(path_or_dir)
    if not path:
        return empty("сохранения God of War Ragnarök не найдены")
    data = path.read_bytes()
    h = header(data)
    if not h:
        return empty("заголовок сейва не распознан")
    sp = split_place(h["place"])
    facts = []
    w = wallet(data)
    rv = w.get(RAVEN_ITEM, 0) + 3 * w.get(RAVEN_GIFT, 0) if (RAVEN_ITEM in w or RAVEN_GIFT in w) else None
    silver = w.get(HACKSILVER)
    if rv is not None:
        facts.append(fact("raven", "Вороны Одина", f"{rv} / {RAVENS_TOTAL}"))
    if silver is not None:
        facts.append(fact("coins", "Серебро", num(silver)))
    if dur(h["play_seconds"]):
        facts.append(fact("clock", "Время игры", dur(h["play_seconds"])))
    return finish({
        "place": h["place"],   # как пишет игра: карточка делит по последнему « - » на место и задание
        "objective": None,   # задание уже в place; иначе карточка повторит его строкой пояснения
        "progress": {"realm": sp["realm"], "area": sp["area"], "objective": sp["objective"],
                     "hacksilver": silver, "odin_ravens": rv, "save_counter": h["save_counter"],
                     "objective_string_id": h["objective_string_id"]},
        "facts": facts,
        "play_seconds": h["play_seconds"],
        "proven": ["place", "objective", "hacksilver", "odin_ravens", "play_seconds"],
    }, path)


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(read(sys.argv[1] if len(sys.argv) > 1 else None), ensure_ascii=False, indent=1, default=str))
