"""Alan Wake (appid 108710) card parser.

Save: Remedy Entertainment proprietary binary format (savegame.aws + config).
Names come from antigravity/dumps/alan_wake/ (loc_ru.json, episodes.json, difficulties.json, collectibles.json).

Accepted card fields are limited to the game-written level/episode keys and
the six named profile-wide collectible records.  Difficulty, manuscripts,
completed levels and an inferred progress percentage remain explicitly
unproven and are not shown as facts.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import struct
import sys
from typing import Any, Dict, List, Optional, Union

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from _card import Facts, empty, finish
from ddsaves._common import documents_dirs, newest, proton_user, read_bytes, select, steam_userdata, ui

APPID = 108710
DUMPS = HERE / "data" / "alan_wake"
SUB = "Documents/Remedy/AlanWake"

_DATA = None


def get_data() -> dict:
    global _DATA
    if _DATA is None:
        eps = json.loads((DUMPS / "episodes.json").read_text(encoding="utf-8"))["data"]
        cols = json.loads((DUMPS / "collectibles.json").read_text(encoding="utf-8"))["data"]
        _DATA = {
            "episodes": eps["episodes"],
            "levels": eps["levels"],
            "collectibles": cols["items"],
        }
    return _DATA


def default_dirs() -> List[Path]:
    roots = []
    for d in documents_dirs():
        if (d / "Remedy/AlanWake").is_dir():
            roots.append(d / "Remedy/AlanWake")
    roots += steam_userdata(APPID, "remote") + steam_userdata(APPID, "Storage")
    roots += [u / SUB for u in proton_user(APPID)]
    return [d for d in roots if d.is_dir()]


def find(path_or_dir: Optional[Union[str, Path]] = None) -> Optional[Path]:
    if path_or_dir is not None:
        p = Path(path_or_dir)
        if p.is_file():
            return p
        if p.is_dir():
            aws = newest(p.rglob("*.aws"))
            if aws:
                return aws
            cfg = newest(p.rglob("config"))
            if cfg:
                return cfg
            return p
    candidates = []
    for d in default_dirs():
        aws = newest(d.rglob("*.aws"))
        if aws:
            candidates.append(aws)
        cfg = newest(d.rglob("config"))
        if cfg:
            candidates.append(cfg)
    return newest(candidates)


def _named_ids(raw: bytes, name: str) -> Optional[bytes]:
    """Read one exact named byte-list record; ambiguous/malformed data proves nothing."""
    encoded = name.encode("ascii")
    marker = struct.pack("<I", len(encoded)) + encoded
    positions, start = [], 0
    while True:
        pos = raw.find(marker, start)
        if pos < 0:
            break
        positions.append(pos)
        start = pos + 1
    if len(positions) != 1:
        return None
    pos = positions[0] + len(marker)
    if pos >= len(raw):
        return None
    count = raw[pos]
    ids = raw[pos + 1:pos + 1 + count]
    if len(ids) != count or len(set(ids)) != count:
        return None
    return ids


def read(path_or_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    try:
        return _read(path_or_dir)
    except Exception as e:
        return {**empty(f"Сохранение Alan Wake не прочитано: {e}"), "proven": [], "fact_sources": {}}


def _read(path_or_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    target = find(path_or_dir)
    if target is None:
        return {**empty("Сохранение Alan Wake не найдено"), "proven": [], "fact_sources": {}}

    stage_dir = target if target.is_dir() else target.parent
    aws_file = (target if target.is_file() and target.suffix.lower() == ".aws"
                else newest(stage_dir.glob("*.aws")))

    config_candidates = sorted(stage_dir.glob("config"))
    config_file = config_candidates[0] if config_candidates else None

    if not aws_file and not config_file:
        return {**empty("Сохранение Alan Wake не найдено"), "proven": [], "fact_sources": {}}

    data = get_data()

    level_id = None
    diff_id: Optional[int] = None
    if aws_file and aws_file.exists():
        raw = read_bytes(aws_file)
        if len(raw) >= 12:
            slen = struct.unpack("<I", raw[8:12])[0]
            if 0 < slen < 100 and 12 + slen <= len(raw):
                level_name = raw[12 : 12 + slen].decode("ascii", errors="replace")
                level_id = level_name.split(":")[-1]
                diff_off = 25 + 2 * slen
                if diff_off + 4 <= len(raw):
                    diff_id = struct.unpack("<I", raw[diff_off : diff_off + 4])[0]

    collectibles: Dict[str, int] = {}

    if config_file and config_file.exists():
        craw = read_bytes(config_file)
        for k in [
            "THERMOS", "CHESTS", "CANPYRAMIDS", "TVSHOWS", "RADIOSHOWS",
            "SIGNS", "DLC1_ALARMCLOCKS", "DLC1_CARDBOARDCUTOUTS", "DLC2_NIGHTSPRINGSVIDEOGAMES"
        ]:
            ids = _named_ids(craw, k)
            if ids is not None and len(ids) <= data["collectibles"][k]["total"]:
                collectibles[k] = len(ids)

    lvl_info = data["levels"].get(level_id, {})
    place = select({"ru": lvl_info.get("level_ru"), "en": lvl_info.get("level_en")})
    chapter = select({"ru": lvl_info.get("episode_ru"), "en": lvl_info.get("episode_en")})
    place_key = level_id if lvl_info else None
    chapter_key = lvl_info.get("episode_key")

    F = Facts()
    fields = {
        "THERMOS": ("coffee_thermos", "cup"),
        "CHESTS": ("chests", "box"),
        "CANPYRAMIDS": ("can_pyramids", "target"),
        "TVSHOWS": ("tv_shows", "tv"),
        "RADIOSHOWS": ("radio_shows", "radio"),
        "SIGNS": ("signs", "sign"),
    }
    proven = [key for key, value in (("place", place), ("place_key", place_key),
                                      ("chapter", chapter), ("chapter_key", chapter_key)) if value]
    values = {}
    for record, (field, icon) in fields.items():
        count = collectibles.get(record)
        values[field] = count
        if count is None:
            continue
        definition = data["collectibles"][record]
        name = select({"ru": definition.get("ru"), "en": definition.get("en")}) or record
        F.sfact(field, icon, ui("profile_counter", name=name), f"{count}/{definition['total']}")
        proven.append(field)

    out = {
        "place": place,
        "place_key": place_key,
        "chapter": chapter,
        "chapter_key": chapter_key,
        "objective": None,
        "progress": {},
        "facts": F.items,
        "fact_sources": F.sources,
        "proven": proven,
        "unproven": [
            "progress",
            "manuscripts",
            "difficulty",
            "levels_completed",
            "health",
            "flashlight_battery",
            "revolver_ammo",
            "shotgun_ammo",
            "hunting_rifle_ammo",
            "flare_gun_ammo",
            "hand_flares",
            "flashbang_grenades",
        ],
        "difficulty": diff_id,
        "manuscripts": None,
        "levels_completed": None,
        **values,
        "counter_scope": "profile",
        "nonmonotonic": {
            field: "independent profile saves"
            for field in values
        },
    }

    ref_file = aws_file or config_file or target
    return finish(out, ref_file)
