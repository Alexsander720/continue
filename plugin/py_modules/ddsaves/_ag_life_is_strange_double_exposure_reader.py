"""Life is Strange: Double Exposure save game reader.

Saves:
  - SaveSlot_1_header.sav: binary protobuf payload with episode, scene, and timeline
  - SaveSlot_1.sav: binary save with scene checkpoints, event flags, and decisions
  - PhotoSave_1.sav: GVAS save containing Max's collected polaroids (JPEG photos)

Default location:
  %USERPROFILE%\\Documents\\My Games\\LifeIsStrangeDoubleExposure\\Steam\\Saved

Zero Cyrillic literals in code AST. No card output keys.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Union
from ._common import localize

ROOT = Path(__file__).resolve().parents[2]
DUMP_PATH = Path(__file__).resolve().parent / "data" / "life_is_strange_double_exposure" / "scenes_ru.json"
APPID = 1874000

_DATA: Optional[Dict[str, Any]] = None


def _load_dump() -> Dict[str, Any]:
    global _DATA
    if _DATA is None:
        if DUMP_PATH.exists():
            _DATA = json.loads(DUMP_PATH.read_text(encoding="utf-8"))["data"]
        else:
            _DATA = {"episodes": {}, "timelines": {}, "scenes": {}}
    return localize(_DATA)


def default_dirs() -> List[Path]:
    dirs: List[Path] = []
    try:
        sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]))
        from ddsaves._common import localize, select, ui, documents_dirs, proton_user
        for doc in documents_dirs():
            p = doc / "My Games" / "LifeIsStrangeDoubleExposure" / "Steam" / "Saved"
            if p.is_dir():
                dirs.append(p)
        for pu in proton_user(APPID):
            p = pu / "Documents" / "My Games" / "LifeIsStrangeDoubleExposure" / "Steam" / "Saved"
            if p.is_dir():
                dirs.append(p)
    except Exception:
        pass

    return dirs


def find_save(path_or_dir: Optional[Union[Path, str]] = None) -> Optional[Path]:
    if path_or_dir:
        p = Path(path_or_dir)
        if p.is_file():
            if p.name.endswith("_header.sav"):
                return p
            header_cand = p.parent / f"{p.stem}_header.sav"
            if header_cand.is_file():
                return header_cand
            return p
        if p.is_dir():
            for name in ["SaveSlot_1_header.sav", "SaveSlot_2_header.sav", "SaveSlot_1.sav"]:
                cand = p / name
                if cand.is_file():
                    return cand
            for f in sorted(p.glob("*.sav"), key=lambda x: x.stat().st_mtime, reverse=True):
                return f
        return None

    for d in default_dirs():
        cand = d / "SaveSlot_1_header.sav"
        if cand.is_file():
            return cand
    return None


def read_save(path_or_dir: Optional[Union[Path, str]] = None) -> Dict[str, Any]:
    target = find_save(path_or_dir)
    if not target or not target.is_file():
        return {"has_save": False}

    save_dir = target.parent
    base_stem = target.stem.replace("_header", "").replace("_backup", "")
    header_file = save_dir / f"{base_stem}_header.sav"
    if not header_file.is_file():
        header_file = target

    main_save_file = save_dir / f"{base_stem}.sav"
    photo_file = save_dir / f"PhotoSave_{base_stem.split('_')[-1] if '_' in base_stem else '1'}.sav"
    if not photo_file.is_file():
        photo_file = save_dir / "PhotoSave_1.sav"

    header_raw = header_file.read_bytes() if header_file.is_file() else b""
    main_raw = main_save_file.read_bytes() if main_save_file.is_file() else b""
    photo_raw = photo_file.read_bytes() if photo_file.is_file() else b""

    # Parse header
    ep_match = re.search(rb"EP[0-9]+", header_raw)
    episode_code = ep_match.group(0).decode("ascii") if ep_match else None

    sc_match = re.search(rb"S[0-9]+_[A-Za-z0-9]+", header_raw)
    scene_code = sc_match.group(0).decode("ascii") if sc_match else None

    tl_match = re.search(rb"Timeline[^\d]*(\d+)", header_raw)
    timeline_id = int(tl_match.group(1)) if tl_match else 1

    # Parse photos
    photos_count = photo_raw.count(b"\xff\xd8\xff\xe0")

    # Parse main save scenes and events
    scene_checkpoints = re.findall(rb"Scene_EP\d+_S\d+_[A-Za-z0-9]+", main_raw)
    unique_scenes = sorted(set(s.decode("ascii") for s in scene_checkpoints))
    scenes_count = len(unique_scenes)

    event_tags = re.findall(rb"EP\d+_S\d+_[A-Z]_[A-Z0-9_]+", main_raw)
    events_count = len(set(event_tags))

    dump_data = _load_dump()
    ep_info = dump_data.get("episodes", {}).get(episode_code, {})
    tl_info = dump_data.get("timelines", {}).get(str(timeline_id), {})

    full_scene_key = f"{episode_code}_{scene_code}" if episode_code and scene_code else scene_code
    scene_name_ru = dump_data.get("scenes", {}).get(full_scene_key)

    chapter_name = ep_info.get("chapter_name")
    episode_title = ep_info.get("title_ru")
    episode_num = int(ep_info.get("episode_num", 1 if episode_code else 0))
    timeline_name = tl_info.get("name_ru")

    return {
        "has_save": True,
        "path": str(header_file),
        "episode_code": episode_code,
        "episode_num": episode_num,
        "chapter_name": chapter_name,
        "episode_title": episode_title,
        "scene_code": scene_code,
        "location_name": scene_name_ru,
        "timeline_id": timeline_id,
        "timeline_name": timeline_name,
        "photos_taken": photos_count,
        "scenes_completed": scenes_count,
        "events_count": events_count,
    }


def dump(path_or_dir: Optional[Union[Path, str]] = None) -> Dict[str, Any]:
    return read_save(path_or_dir)
