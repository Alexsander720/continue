"""Actual game IDs/names and typed saved photo entries; timeline/scenes debug."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
if __package__ != "ddsaves":
    sys.path.insert(0, str(HERE.parents[4] / "GameHub" if HERE.parent.name == "codex" else HERE.parent))
from ddsaves._common import localize, select, ui, documents_dirs, empty, fact, finish, newest, proton_user
from ddsaves import gvas

APPID = 1874000
TABLE = HERE.parent / "data/life_is_strange_double_exposure.json" if HERE.parent.name == "codex" else HERE / "data/life_is_strange_double_exposure.json"
HEADER_NAME = re.compile(r"SaveSlot_([0-9]+)_header(_backup)?\.sav$")
MAIN_NAME = re.compile(r"SaveSlot_([0-9]+)(_backup)?\.sav$")


def tables():
    return localize(json.loads(TABLE.read_text(encoding="utf-8")))


def default_dirs():
    relative = "My Games/LifeIsStrangeDoubleExposure/Steam/Saved"
    return [path / relative for path in documents_dirs()] + [user / "Documents" / relative for user in proton_user(APPID)]


def find(path_or_dir=None):
    if path_or_dir is not None:
        path = Path(path_or_dir)
        if path.is_file():
            if HEADER_NAME.fullmatch(path.name):
                return path
            match = MAIN_NAME.fullmatch(path.name)
            if match:
                header = path.with_name(f"SaveSlot_{match[1]}_header{match[2] or ''}.sav")
                return header if header.is_file() else None
            return None
        roots = [path] if path.is_dir() else []
    else:
        roots = default_dirs()
    return newest(file for root in roots for file in root.rglob("SaveSlot_*_header.sav")
                  if HEADER_NAME.fullmatch(file.name) and root.is_dir())


def decode_header(raw):
    if len(raw) < 40 or raw[32:36] != b"PBL\xaa" or hashlib.md5(raw[32:]).hexdigest().encode() != raw[:32]:
        raise ValueError("Not an intact PBL save header")
    position = 36
    def integer():
        nonlocal position
        value = 0; shift = 0
        while True:
            if position >= len(raw) or shift > 63:
                raise ValueError("Invalid PBL varint")
            byte = raw[position]; position += 1; value |= (byte & 127) << shift
            if not byte & 128:
                return value
            shift += 7
    def tag(expected):
        nonlocal position
        if position >= len(raw) or raw[position] != expected:
            raise ValueError(f"Unsupported PBL header tag (expected {expected:#x})")
        position += 1
    def string(expected):
        nonlocal position
        tag(expected); count = integer(); end = position + count
        if end > len(raw):
            raise ValueError("Truncated PBL string")
        value = raw[position:end]; position = end
        return value
    size = integer()
    if size != len(raw) - position:
        raise ValueError("PBL header length mismatch")
    tag(0x64); tag(0x08); version = integer()
    if version != 1:
        raise ValueError("Unsupported PBL save header version")
    episode = string(0x13).decode("ascii"); scene = string(0x1b).decode("ascii")
    tag(0x20); raw_index = integer()
    date_blob = string(0x2b)
    tag(0x30); field6 = integer()
    serialized = string(0x3b)
    tag(0x00)  # end of the serialized header object, outside the JSON string
    context = json.loads(serialized)
    if not isinstance(context, dict):
        raise ValueError("Invalid header JSON object")
    return {"episode_code": episode, "scene_code": scene, "timeline_num": context.get("Timeline"),
            "header_raw_index": raw_index, "header_field6": field6, "header_date_blob": date_blob.hex()}


def album(path, expected_name):
    data = gvas.read(path.read_bytes())
    if data["class"] != "/Script/Chronos.ChronosPhotoSave":
        raise ValueError("Not a ChronosPhotoSave")
    props = data["props"]
    if props.get("PlayerSaveSlotName") != expected_name:
        raise ValueError(f"Photo slot mismatch: {props.get('PlayerSaveSlotName')!r}, expected {expected_name!r}")
    records = props.get("PhotoData", [])
    if not isinstance(records, list) or any(not isinstance(pair, list) or len(pair) != 2 or
                                          not isinstance(pair[0], str) or not isinstance(pair[1], dict) for pair in records):
        raise ValueError("Invalid/unsupported PhotoData map")
    keys = [pair[0] for pair in records]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate PhotoData IDs")
    return {"photos_taken": len(records), "photo_ids": sorted(keys),
            "photo_records_marked_polaroid": sum(value.get("IsPolaroid") is True for _, value in records),
            "photo_slot_name": props["PlayerSaveSlotName"], "photo_source_path": str(path)}


def read(path_or_dir=None):
    path = find(path_or_dir)
    if path is None:
        return empty("LISDE gameplay save header not found; settings/photos alone are not a gameplay slot")
    try:
        progress = decode_header(path.read_bytes()); data = tables()
        episode = data["episodes"].get(progress["episode_code"])
        if episode is None:
            out = empty("Unknown saved episode ID; no title or number inferred")
            out.update(progress=progress, proven=[], unproven=list(progress) + ["place", "chapter", "objective"])
            return finish(out, path)
        progress.update(episode_num=episode["number"], episodes_total=data["episodes_total"])
        full_scene = progress["episode_code"] + "_" + progress["scene_code"]
        scene = data["scenes"].get(full_scene)
        place = scene["ru"] or scene["en"] if scene else None
        chapter = ui("episode_title", n=episode['number'], title=episode['ru'] or episode['en'])
        match = HEADER_NAME.fullmatch(path.name); backup = match[2] or ""
        main = path.with_name(f"SaveSlot_{match[1]}{backup}.sav")
        scene_ids = sorted({value.decode() for value in re.findall(rb"Scene_EP\d+_S\d+_[A-Za-z0-9]+", main.read_bytes())}) if main.is_file() else []
        progress.update(scenes_completed=len(scene_ids) if main.is_file() else None, scene_ids_observed=scene_ids,
                        full_scene_id=full_scene, photos_taken=None)
        try:
            if backup:
                raise ValueError("Historical backup has no paired historical photo save")
            progress.update(album(path.with_name(f"PhotoSave_{match[1]}.sav"), f"PhotoSave_{match[1]}"))
        except (OSError, ValueError, KeyError, IndexError) as error:
            progress["photo_read_reason"] = str(error)
        facts = [fact("flag", "Эпизод", f"{episode['number']} / {data['episodes_total']}")]
        proven = ["episode_num", "episodes_total", "episode_code", "chapter"]
        if progress["photos_taken"] is not None:
            facts.append(fact("camera", "Снимки", progress["photos_taken"]))
            proven += ["photos_taken", "photo_ids", "photo_slot_name"]
        if place is not None:
            proven.append("place")
        unproven = [key for key in progress if key not in proven]
        unproven += ["objective"] + (["place"] if place is None else [])
        return finish({"place": place, "chapter": chapter, "objective": None, "progress": progress, "facts": facts,
                       "proven": proven, "unproven": unproven,
                       "place_semantics": "Saved scene's exact title in the game's scene menu, not a physical room name",
                       "photo_semantics": "Unique stored photo IDs in the paired album; includes several photo types, no total denominator"}, path)
    except (OSError, ValueError, KeyError, IndexError) as error:
        return finish(empty(str(error)), path)


if __name__ == "__main__":
    print(json.dumps(read(sys.argv[1] if len(sys.argv) > 1 else None), ensure_ascii=False, indent=2))
