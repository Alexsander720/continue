"""NieR:Automata save game reader for SlotData_*.dat files.

Container format: Platinum Games proprietary binary/ASCII structured format.
Structure (SlotData_*.dat, 235,980 bytes):
  - Header:
      * 0x00004: Steam Account ID (uint64)
      * 0x00024: In-game play time in seconds (uint32)
      * 0x0002C: Current transporter / location index (int32, 1..27)
      * 0x00030: Endings bitmask (uint32, bit i -> Ending chr(ord('A') + i))
      * 0x00034: Player profile name (UTF-16LE, null-padded)
  - Gameworld State Text Segment (0x0007C to 0x30000, ASCII text):
      * SceneState: PL/2B, PL/9S, PL/A2 (active character)
      * Route: Route/A, Route/B, Route/C (active route)
      * Quests: active side-quests and progression tags (qXXX/DONE, qXXX/FIN)
      * Story progress markers: event and scene flags
  - Binary Progression Segment:
      * 0x3056C: Gold / G currency (uint32)
      * 0x31D70: Weapons table (39 weapon records * 20 bytes each)
      * 0x3871C: Experience points (uint32)
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import struct
from ddsaves._common import localize, select, ui

ROOT = Path(__file__).resolve().parents[2]
DUMPS_DIR = Path(__file__).resolve().parent / "data" / "nier_automata"


def _load_dump(name: str) -> dict:
    p = DUMPS_DIR / name
    if p.exists():
        try:
            return localize(json.loads(p.read_text(encoding="utf-8")).get("data", {}))
        except Exception:
            return {}
    return {}


def dump(path: Path | str) -> dict:
    p = Path(path)
    if p.is_file():
        save_file = p
    else:
        candidates = sorted(p.rglob("SlotData_*.dat"))
        save_file = candidates[0] if candidates else None

    if not save_file or not save_file.exists():
        return {
            "has_save": False,
            "error": "No SlotData_*.dat found",
        }

    raw = save_file.read_bytes()
    if len(raw) < 0x38720:
        return {
            "has_save": False,
            "error": f"File too small: {len(raw)} bytes",
        }

    steam_id, = struct.unpack_from("<Q", raw, 0x04)
    play_time_seconds, = struct.unpack_from("<I", raw, 0x24)
    loc_id, = struct.unpack_from("<i", raw, 0x2C)
    endings_mask, = struct.unpack_from("<I", raw, 0x30)
    player_name = raw[0x34:0x7A].decode("utf-16le", errors="ignore").split("\x00")[0]

    gold, = struct.unpack_from("<I", raw, 0x3056C)
    exp, = struct.unpack_from("<I", raw, 0x3871C)

    # Weapons count (39 slots * 20 bytes at 0x31D70)
    weapons_owned = 0
    for i in range(39):
        wid, _ = struct.unpack_from("<ii", raw, 0x31D70 + i * 20)
        if wid > 0:
            weapons_owned += 1

    # Endings count
    endings_unlocked = bin(endings_mask).count("1")

    # Text segment (0x7C to 0x30000)
    txt = raw[0x7C:0x30000].decode("ascii", errors="ignore")
    scene_items = set()
    active_quests = []
    sec = None
    for line in txt.splitlines():
        st = line.strip()
        if not line.startswith(" ") and not line.startswith("\t") and st:
            sec = st
        elif sec == "SceneState" and st:
            scene_items.add(st)
        elif sec == "Quest" and st:
            active_quests.append(st)

    # Active Character
    if "PL/A2" in scene_items:
        active_character = "A2"
    elif "PL/9S" in scene_items:
        active_character = "9S"
    elif "PL/2B" in scene_items:
        active_character = "2B"
    else:
        active_character = None

    # Active Route
    if "Route/C" in scene_items:
        story_route = "Route C"
    elif "Route/B" in scene_items:
        story_route = "Route B"
    elif "Route/A" in scene_items:
        story_route = "Route A"
    else:
        story_route = None

    # Location name
    trans_dump = _load_dump("transporters.json").get("transporters", {})
    loc_entry = trans_dump.get(str(loc_id))
    location_name = loc_entry.get("name") if loc_entry else None

    # Chapter determination from canonical event string at 0x395F4
    ev_raw = raw[0x395F4:0x395F4 + 64]
    ev_name = ev_raw.split(b"\x00")[0].decode("ascii", errors="ignore").strip()
    events_dump = _load_dump("chapter_events.json").get("events", {})
    ev_info = events_dump.get(ev_name)
    if not ev_info and ev_name:
        norm = re.sub(r"_\d{2}_", "_00_", ev_name)
        ev_info = events_dump.get(norm)
    story_chapter = ev_info.get("chapter_title") if ev_info else None

    # Player level from experience
    exp_dump = _load_dump("experience.json").get("levels", {})
    player_level = 1
    for lvl_str in sorted(exp_dump.keys(), key=lambda x: int(x)):
        if exp >= exp_dump[lvl_str]:
            player_level = int(lvl_str)

    # Target objective / quest name
    quest_dump = _load_dump("quests.json").get("quests", {})
    target_objective = None
    for qid in active_quests:
        q_info = quest_dump.get(qid)
        if q_info and q_info.get("title"):
            target_objective = q_info["title"]
            break

    # Quests completed count
    valid_qids = {k for k in quest_dump if not k.endswith("_US")}
    completed_qids = set()
    for item in scene_items:
        m = re.match(r"^(q\d+)[_/].*(?:DONE|FIN|CLE)", item)
        if m and m.group(1) in valid_qids:
            completed_qids.add(m.group(1))
    quests_completed = len(completed_qids)
    quests_total = len(valid_qids)

    return {
        "has_save": True,
        "file_size": len(raw),
        "steam_id": steam_id,
        "player_name": player_name,
        "play_time_seconds": play_time_seconds,
        "raw_location_id": loc_id,
        "location_name": location_name,
        "story_chapter": story_chapter,
        "target_objective": target_objective,
        "active_character": active_character,
        "story_route": story_route,
        "player_level": player_level,
        "gold": gold,
        "experience": exp,
        "weapons_owned": weapons_owned,
        "endings_unlocked": endings_unlocked,
        "quests_completed": quests_completed,
        "quests_total": quests_total,
    }
