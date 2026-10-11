"""Hogwarts audit candidate: stdlib SQLite, exact enum and unique collections.

Oodle GVAS requires prior research-side decoding; unsupported compressed inputs
return an explicit empty result. FocusMission and FT State=9 remain unproven.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
if __package__ != "ddsaves":
    sys.path.insert(0, str(HERE.parents[4] / "GameHub" if HERE.parent.name == "codex" else HERE.parent))
from ddsaves._common import localize, select, ui, empty, fact, finish, newest, proton_user

APPID = 990080
TABLE = HERE.parent / "data/hogwarts_legacy.json" if HERE.parent.name == "codex" else HERE / "data/hogwarts_legacy.json"


def tables():
    return localize(json.loads(TABLE.read_text(encoding="utf-8")))


def default_files():
    roots = []
    if os.environ.get("LOCALAPPDATA"):
        roots += [Path(os.environ["LOCALAPPDATA"]) / name / "Saved/SaveGames" for name in ("Hogwarts Legacy", "Phoenix")]
    roots += [user / "AppData/Local" / name / "Saved/SaveGames" for user in proton_user(APPID) for name in ("Hogwarts Legacy", "Phoenix")]
    return [path for root in roots for path in root.rglob("HL-*-*.sav")]


def find(path_or_dir=None):
    if path_or_dir is None:
        return newest(default_files())
    path = Path(path_or_dir)
    if path.is_file():
        return path
    if path.is_dir():
        return newest(path.rglob("HL-*-*.sav"))
    return None


def open_database(path):
    data = path.read_bytes()
    offset = data.find(b"SQLite format 3\x00")
    if offset < 0:
        # ПРАВКА Claude 04.10 (повторное подключение Codex её затрёт): сжатые Oodle сейвы владельца распаковывает
        # читатель Антигравити через `ooz` (pip install pyooz в системном Python ПК; на Деке игры нет).
        import importlib.util
        spec = importlib.util.spec_from_file_location("agreader_hl", Path(__file__).resolve().parent / "_ag_hogwarts_legacy_reader.py")
        reader = importlib.util.module_from_spec(spec); spec.loader.exec_module(reader)
        data = reader.decompress_gvas_sqlite(path)
        offset = data.find(b"SQLite format 3\x00")
        if offset < 0:
            raise ValueError("Oodle GVAS SQLite not decoded; no facts inferred")
    connection = sqlite3.connect(":memory:")
    connection.deserialize(data[offset:])
    connection.execute("PRAGMA query_only=ON")
    return connection


def read(path_or_dir=None):
    path = find(path_or_dir)
    if path is None:
        return empty("Hogwarts Legacy save not found")
    connection = None
    try:
        data = tables()
        connection = open_database(path)
        connection.row_factory = sqlite3.Row
        def misc(owner, name):
            row = connection.execute("SELECT DataValue FROM MiscDataDynamic WHERE DataOwner=? AND DataName=?", (owner, name)).fetchone()
            return row[0] if row else None
        def inventory(item):
            holder = data["inventory_definitions"][item]["StorageLocation"]
            return connection.execute("SELECT coalesce(sum(Count),0) FROM InventoryDynamic WHERE CharacterID='Player0' AND ItemID=? AND HolderID=?", (item, holder)).fetchone()[0]
        levels = [int(row[0][len("Progression_PlayerLevel"):]) for row in connection.execute("SELECT LockID FROM LocksDynamic WHERE LockID LIKE 'Progression_PlayerLevel%'")
                  if row[0][len("Progression_PlayerLevel"):].isdigit()]
        level = max(levels) if levels else None
        if level is not None and str(level) not in data["experience_levels"]:
            level = None
        house_id = misc("Player", "HouseID")
        house = data["houses"].get(house_id.casefold()) if house_id else None
        focus = [row[0] for row in connection.execute("SELECT Text1 FROM MissionDynamic WHERE Type='FocusMission'") if row[0]]
        focus_id = focus[0] if len(focus) == 1 else None
        focus_title = data["missions"].get(focus_id.casefold(), {}).get("title") if focus_id else None
        focus_rows = [dict(row) for row in connection.execute("SELECT * FROM MissionDynamic WHERE Type='Main' AND MissionID=?", (focus_id,))] if focus_id else []
        solved = data["interactive_state"]["EInteractiveState::Solved"]
        merlin = connection.execute("SELECT count(DISTINCT SphinxPuzzleGUID) FROM SphinxPuzzleDynamic WHERE EInteractiveState=?", (solved,)).fetchone()[0]
        raw_collections = connection.execute("SELECT count(*) FROM CollectionDynamic WHERE ItemState='Obtained'").fetchone()[0]
        collections = connection.execute("SELECT count(*) FROM (SELECT DISTINCT lower(CategoryID),lower(SubcategoryID),lower(ItemID) FROM CollectionDynamic WHERE ItemState='Obtained')").fetchone()[0]
        floo = connection.execute("SELECT count(*) FROM MapLocationDataDynamic WHERE MapLocationID GLOB 'FT_*' AND State=9").fetchone()[0]
        gold, potions = inventory("Knuts"), inventory("WoundCleaning")
        progress = {"player_level": level, "experience": misc("ExperienceManager", "ExperiencePoints"), "house_id": house_id,
                    "merlin_trials": merlin, "merlin_trials_total": len(data["merlin_locations"]), "floo_flames": floo,
                    "fast_travel_reference_rows": len(data["fast_travel_locations"]),
                    "collections_count": collections, "collections_raw_rows": raw_collections,
                    "gold_knuts": gold, "healing_potions": potions, "world_id": misc("Player", "World"),
                    "focused_mission_id": focus_id, "focused_mission_title": focus_title, "focused_mission_records": focus_rows}
        facts, proven = [], ["merlin_trials", "merlin_trials_total", "collections_count", "gold_knuts", "healing_potions"]
        if level is not None:
            facts.append(fact("badge", "Уровень", level)); proven.append("player_level")
        if house:
            facts.append(fact("shield", "Факультет", house)); proven.append("house_id")
        facts += [fact("puzzle", "Испытания Мерлина", f"{merlin} / {len(data['merlin_locations'])}"),
                  fact("book", "Коллекции", collections), fact("coin", "Золото", gold)]
        if potions:
            facts.append(fact("potion", "Рябиновый отвар", potions))
        return finish({"place": None, "chapter": None, "objective": None, "progress": progress, "facts": facts,
                       "proven": sorted(proven), "unproven": ["place", "chapter", "objective", "floo_flames", "world_id", "experience",
                                                              "fast_travel_reference_rows", "focused_mission_id", "focused_mission_title", "focused_mission_records"],
                       "nonmonotonic": {"gold_knuts": "Spendable inventory currency", "healing_potions": "Consumable inventory"}}, path)
    except (ValueError, OSError, sqlite3.Error, KeyError) as error:
        out = empty(str(error)); out["unproven"] = ["save_decode"]
        return finish(out, path)
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    print(json.dumps(read(sys.argv[1] if len(sys.argv) > 1 else None), ensure_ascii=False, indent=2))
