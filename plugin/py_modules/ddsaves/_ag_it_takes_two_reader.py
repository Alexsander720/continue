"""It Takes Two save game reader.

Save file: SaveData.Nuts (JSON format) located at:
  - Windows: %LOCALAPPDATA%\\ItTakesTwo\\SaveData.Nuts
  - Proton: <compatdata>/2420110/... /ItTakesTwo/SaveData.Nuts

Zero Cyrillic literals in code AST: localized names are loaded from
antigravity/dumps/it_takes_two/chapters_ru.json.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Union
from ._common import localize

ROOT = Path(__file__).resolve().parents[2]
DUMP_PATH = Path(__file__).resolve().parent / "data" / "it_takes_two" / "chapters_ru.json"

_DATA: Optional[Dict[str, Any]] = None


def _load_dump() -> Dict[str, Any]:
    global _DATA
    if _DATA is None:
        if DUMP_PATH.exists():
            _DATA = json.loads(DUMP_PATH.read_text(encoding="utf-8"))["data"]
        else:
            _DATA = {"groups": [], "subchapters": [], "by_key": {}, "minigames": {}}
    return localize(_DATA)


APPID = 1426210  # It Takes Two Steam AppID


def default_dirs() -> List[Path]:
    dirs: List[Path] = []
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        p = Path(local_app_data) / "ItTakesTwo"
        if p.is_dir():
            dirs.append(p)

    # GameHub proton helpers if available
    try:
        sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]))
        from ddsaves._common import localize, select, ui, proton_user
        for pu in proton_user(APPID):
            p = pu / "AppData" / "Local" / "ItTakesTwo"
            if p.is_dir():
                dirs.append(p)
    except Exception:
        pass

    return dirs


def find_save(path_or_dir: Optional[Union[Path, str]] = None) -> Optional[Path]:
    if path_or_dir:
        p = Path(path_or_dir)
        if p.is_file():
            return p
        if p.is_dir():
            cand = p / "SaveData.Nuts"
            if cand.is_file():
                return cand
            for f in sorted(p.glob("*.Nuts"), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.name.lower() == "savedata.nuts":
                    return f
        return None

    for d in default_dirs():
        cand = d / "SaveData.Nuts"
        if cand.is_file():
            return cand
    return None


def read_save(path_or_dir: Optional[Union[Path, str]] = None) -> Dict[str, Any]:
    save_file = find_save(path_or_dir)
    if not save_file or not save_file.is_file():
        return {"has_save": False}

    try:
        raw_text = save_file.read_text(encoding="utf-8")
        raw = json.loads(raw_text)
    except Exception as e:
        return {"has_save": False, "error": str(e), "path": str(save_file)}

    dump_data = _load_dump()
    by_key = dump_data.get("by_key", {})
    groups = dump_data.get("groups", [])

    furthest = raw.get("FurthestUnlockedChapter")
    last_chap = raw.get("LastSaveChapter")
    last_prog = raw.get("LastSaveProgressPoint")

    # Minigames
    unlocked_minigames = []
    for k, v in raw.items():
        if k.startswith("Minigame.") and str(v).lower() == "true":
            mg_id = k.split(".", 1)[1]
            unlocked_minigames.append(mg_id)
    minigames_count = len(unlocked_minigames)

    chapter_ru: Optional[str] = None
    chapter_en: Optional[str] = None
    chapter_num: int = 0
    subchapter_ru: Optional[str] = None
    subchapter_en: Optional[str] = None
    subchapter_num: int = 0

    key_to_resolve = furthest or last_chap
    if key_to_resolve and key_to_resolve in by_key:
        info = by_key[key_to_resolve]
        chapter_ru = info.get("chapter_ru")
        chapter_en = info.get("chapter_en")
        chapter_num = int(info.get("chapter_num", 0))
        subchapter_ru = info.get("subchapter_ru")
        subchapter_en = info.get("subchapter_en")
        subchapter_num = int(info.get("subchapter_num", 0))
    elif key_to_resolve:
        # Fallback by map path prefix to determine chapter group
        prefix_to_num = {
            "/Game/Maps/RealWorld/": 1,
            "/Game/Maps/Shed/": 1,
            "/Game/Maps/Tree/": 2,
            "/Game/Maps/PlayRoom/": 3,
            "/Game/Maps/Clockwork/": 4,
            "/Game/Maps/SnowGlobe/": 5,
            "/Game/Maps/Garden/": 6,
            "/Game/Maps/Music/": 7,
        }
        for pfx, gnum in prefix_to_num.items():
            if pfx in key_to_resolve:
                chapter_num = gnum
                if gnum <= len(groups):
                    chapter_ru = groups[gnum - 1].get("name_ru")
                    chapter_en = groups[gnum - 1].get("name_en")
                break

    return {
        "has_save": True,
        "path": str(save_file),
        "uid": raw.get("UID"),
        "chapter_name": chapter_ru,
        "chapter_en": chapter_en,
        "chapter_num": chapter_num,
        "location_name": subchapter_ru,
        "location_name_en": subchapter_en,
        "subchapter_num": subchapter_num,
        "minigames_unlocked": minigames_count,
        "minigames_list": sorted(unlocked_minigames),
        "furthest_unlocked_chapter": furthest,
        "last_save_chapter": last_chap,
        "last_save_progress_point": last_prog,
    }


def dump(path_or_dir: Optional[Union[Path, str]] = None) -> Dict[str, Any]:
    return read_save(path_or_dir)
