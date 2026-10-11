#!/usr/bin/env python3
"""Hogwarts Legacy save file reader.

Parses GVAS save files containing embedded SQLite 3 database compressed with Oodle Kraken.
Extracts character level, house, experience, gold, Merlin trials, fast travel, collections, and active quests.

Zero Cyrillic in code AST: localized names are loaded from strings_ru.json dump.
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import struct
import ooz
from ddsaves._common import localize, select, ui

ROOT = Path(__file__).resolve().parents[2]
DUMP_PATH = Path(__file__).resolve().parent / "data" / "hogwarts_legacy" / "strings_ru.json"
CHUNK_MAGIC = bytes.fromhex("c1832a9e")
SQLITE_HEADER = b"SQLite format 3\x00"

_STRINGS_CACHE: dict | None = None


def _load_strings() -> dict:
    global _STRINGS_CACHE
    if _STRINGS_CACHE is None:
        if DUMP_PATH.exists():
            _STRINGS_CACHE = json.loads(DUMP_PATH.read_text(encoding="utf-8"))
        else:
            _STRINGS_CACHE = {"houses": {}, "missions": {}, "locations": {}, "ui": {}}
    return localize(_STRINGS_CACHE)


def decompress_gvas_sqlite(sav_path: str | Path) -> bytes:
    data = Path(sav_path).read_bytes()
    pos = 0
    found: list[int] = []
    while True:
        pos = data.find(CHUNK_MAGIC, pos)
        if pos == -1:
            break
        found.append(pos)
        pos += 4

    if not found:
        # Check if already raw sqlite
        sql_pos = data.find(SQLITE_HEADER)
        if sql_pos != -1:
            return data[sql_pos:]
        raise ValueError(f"No compressed chunks or SQLite header found in {sav_path}")

    full_stream = bytearray()
    for chunk_pos in found:
        if chunk_pos + 48 > len(data):
            break
        tag, blk_sz, comp_sz, uncomp_sz = struct.unpack("<QQQQ", data[chunk_pos : chunk_pos + 32])
        c_sz, u_sz = struct.unpack("<QQ", data[chunk_pos + 32 : chunk_pos + 48])
        if chunk_pos + 48 + c_sz > len(data):
            break
        payload = data[chunk_pos + 48 : chunk_pos + 48 + c_sz]
        decomp = ooz.decompress(payload, u_sz)
        full_stream.extend(decomp)

    sql_pos = full_stream.find(SQLITE_HEADER)
    if sql_pos == -1:
        raise ValueError(f"SQLite header not found in decompressed stream of {sav_path}")

    return bytes(full_stream[sql_pos:])


def open_save_db(sav_path: str | Path) -> sqlite3.Connection:
    db_bytes = decompress_gvas_sqlite(sav_path)
    conn = sqlite3.connect(":memory:")
    conn.deserialize(db_bytes)
    return conn


def read_save(path: str | Path) -> dict:
    conn = open_save_db(path)
    cur = conn.cursor()
    strings = _load_strings()

    # 1. House
    house_row = cur.execute(
        "SELECT DataValue FROM MiscDataDynamic WHERE DataOwner='Player' AND DataName='HouseID'"
    ).fetchone()
    house = house_row[0] if house_row else "Unknown"
    house_ru = strings.get("houses", {}).get(house, house)

    # 2. Player level from locks
    lvl_rows = cur.execute(
        "SELECT LockID FROM LocksDynamic WHERE LockID LIKE 'Progression_PlayerLevel%'"
    ).fetchall()
    levels = [
        int(r[0].replace("Progression_PlayerLevel", ""))
        for r in lvl_rows
        if r[0].replace("Progression_PlayerLevel", "").isdigit()
    ]
    level = max(levels) if levels else 1

    # 3. Experience points
    xp_row = cur.execute(
        "SELECT DataValue FROM MiscDataDynamic WHERE DataOwner='ExperienceManager' AND DataName='ExperiencePoints'"
    ).fetchone()
    xp = int(xp_row[0]) if xp_row and xp_row[0].isdigit() else 0

    # 4. Gold / Knuts
    gold_row = cur.execute(
        "SELECT Count FROM InventoryDynamic WHERE CharacterID='Player0' AND ItemID='Knuts'"
    ).fetchone()
    gold = int(gold_row[0]) if gold_row else 0

    # 5. Healing potions (WoundCleaning)
    heal_row = cur.execute(
        "SELECT Count FROM InventoryDynamic WHERE CharacterID='Player0' AND ItemID='WoundCleaning' AND HolderID='HealthPotionStorage'"
    ).fetchone()
    healing_potions = int(heal_row[0]) if heal_row else 0

    # 6. Merlin Trials completed (SphinxPuzzleDynamic where bit 1 is set: state 2 or 34)
    merlin_count = cur.execute(
        "SELECT count(*) FROM SphinxPuzzleDynamic WHERE (EInteractiveState & 2) != 0"
    ).fetchone()[0]

    # 7. Fast Travel (Floo Flames) unlocked (MapLocationDataDynamic where state == 9)
    floo_count = cur.execute(
        "SELECT count(*) FROM MapLocationDataDynamic WHERE MapLocationID LIKE 'FT_%' AND State=9"
    ).fetchone()[0]

    # 8. Collections obtained
    coll_count = cur.execute(
        "SELECT count(*) FROM CollectionDynamic WHERE ItemState='Obtained'"
    ).fetchone()[0]

    # 9. Active Missions
    active_rows = cur.execute(
        "SELECT MissionID, Text1, Text2 FROM MissionDynamic WHERE Text2='Active'"
    ).fetchall()
    active_list = []
    primary_mission_id = ""
    primary_mission_name = ""
    primary_mission_step = ""

    for m_id, step, state in active_rows:
        ru_name = strings.get("missions", {}).get(m_id, m_id)
        active_list.append({"mission_id": m_id, "step": step, "title": ru_name})
        if not primary_mission_id:
            primary_mission_id = m_id
            primary_mission_name = ru_name
            primary_mission_step = step

    # 10. World location
    world_row = cur.execute(
        "SELECT DataValue FROM MiscDataDynamic WHERE DataOwner='Player' AND DataName='World'"
    ).fetchone()
    world_id = world_row[0] if world_row else "Overland"

    # Year & Season
    year_row = cur.execute(
        "SELECT DataValue FROM MiscDataDynamic WHERE DataOwner='Player' AND DataName='Year'"
    ).fetchone()
    year = int(year_row[0]) if year_row and year_row[0].isdigit() else 5

    season_row = cur.execute(
        "SELECT Integer1 FROM MissionDynamic WHERE Type='Season'"
    ).fetchone()
    season = int(season_row[0]) if season_row else 1

    return {
        "house_id": house,
        "house_name": house_ru,
        "player_level": level,
        "experience": xp,
        "gold_knuts": gold,
        "healing_potions": healing_potions,
        "merlin_trials": merlin_count,
        "merlin_trials_total": 95,
        "floo_flames": floo_count,
        "floo_flames_total": 176,
        "collections_count": coll_count,
        "active_mission_id": primary_mission_id,
        "active_mission_title": primary_mission_name,
        "active_mission_step": primary_mission_step,
        "active_missions": active_list,
        "world_name": world_id,
        "school_year": year,
        "season_index": season,
    }


def dump(path: str | Path) -> dict:
    conn = open_save_db(path)
    cur = conn.cursor()
    save_info = read_save(path)

    # Collect summary of tables
    table_counts = {}
    for t, in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        try:
            cnt = cur.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            table_counts[t] = cnt
        except Exception:
            pass

    return {
        "parsed": save_info,
        "tables_count": len(table_counts),
        "tables": table_counts,
    }


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "fixtures/hogwarts_legacy/owner/HL-00-10.sav"
    res = read_save(target)
    print(json.dumps(res, ensure_ascii=False, indent=2))
