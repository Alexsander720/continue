"""SILENT HILL 2 (appid 2124490) live card: place, James' state, supplies, maps, notes.

Save: UE5 SHSaveGame slot (VASb header + zlib GVAS), read by antigravity/readers/silent_hill_2.py::state().
Names: antigravity/dumps/silent_hill_2/card_names.json (save point texts, item names, building names).

Proven (>= 2 distinct values over the 5 fallengost stages, see antigravity/diffs/silent_hill_2.md):
  place               save point from header tag -> SavePoints_DT text
  health              HealthValue (live value, goes up and down)
  healing_drinks/syringes, ammo_*   CollectedItems quantities (consumed -> not monotonic)
  investigated        MapItemsInvestigated counter
  kills_total         MeleeWeaponKillcount + RangedWeaponKillcount
  weapons             weapon items in CollectedItems
  memos_count, last_memo   MemosItemsPickedUp (append order: every earlier list is a prefix of the next)
  maps_count, maps_by_building   CollectedItems that are MapItems_DT rows, grouped by native maps family
Unproven (not shown): chapter, objective, difficulty, play time, health maximum, ending choices
  (puzzle enum values change in only one stage), registered ending (stays Invalid).
"""
from __future__ import annotations

import importlib.util
import json
import os
import struct
import sys
import zlib
from pathlib import Path
from typing import List, Optional, Union

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from _card import Facts, empty, finish
from ddsaves._common import localize, select, ui, proton_user

_spec = importlib.util.spec_from_file_location("agreader_silent_hill_2", HERE / "_ag_silent_hill_2_reader.py")
reader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reader)

APPID = 2124490
NAMES = json.loads((HERE / "data" / "silent_hill_2" / "card_names.json").read_text(encoding="utf-8"))
AMMO_ICON = "sword"


def find(path_or_dir: Optional[Union[Path, str]] = None) -> Optional[Path]:
    roots = [Path(path_or_dir)] if path_or_dir else [Path(os.environ.get("LOCALAPPDATA", "")) / "SilentHill2/Saved/SaveGames"]
    if not path_or_dir:
        roots.extend(p / "AppData/Local/SilentHill2/Saved/SaveGames" for p in proton_user(APPID))
    cands: List[Path] = []
    for r in roots:
        if r.is_file():
            cands.append(r)
        elif r.exists():
            cands.extend(r.rglob("SaveGameData_*.sav"))
    scored = []
    for p in cands:
        try:
            scored.append((reader._header(p.read_bytes())[0]["ticks"], str(p), p))   # embedded time, not mtime
        except (OSError, ValueError, IndexError, struct.error, zlib.error):
            pass
    return max(scored)[2] if scored else None


def read(path_or_dir=None) -> dict:
    NAMES = localize(globals()["NAMES"])
    path = find(path_or_dir)
    if path is None:
        return empty("SH2 gameplay slot not found")
    try:
        s = reader.state(path)
    except (OSError, ValueError, KeyError, IndexError, struct.error, zlib.error, RuntimeError):
        return finish(empty("SH2 unknown or incomplete slot"), path)

    names, items = NAMES["items"], s["items"]
    place = NAMES["places"].get(s["location_tag"])
    health = s["health"] if isinstance(s["health"], float) else None
    if health is not None:
        health = int(round(health))

    def qty(row):
        return items.get(row) if items else None

    drinks, syringes = qty("HealthDrink"), qty("Syringe")
    ammo = {row: qty(row) for row in NAMES["ammunition"]}
    kills = None
    if isinstance(s["kills_melee"], int) and isinstance(s["kills_ranged"], int):
        kills = s["kills_melee"] + s["kills_ranged"]
    investigated = s["map_items_investigated"] if isinstance(s["map_items_investigated"], int) else None

    weapons = None
    if items:
        owned = [r for r in NAMES["melee_weapons"] + NAMES["ranged_weapons"] if items.get(r, 0) > 0]
        weapons = ", ".join(names[r] for r in owned) or None

    memos = s["memo_ids"]
    memos_count = len(memos) if memos is not None else None
    last_memo = names.get(memos[-1]) if memos else None

    maps_count, maps_by_building = None, None
    if items:
        rows = [r for r, q in items.items() if q > 0 and r in NAMES["map_family_of_row"]]
        maps_count = len(rows)
        per = {}
        for r in rows:
            label = NAMES["map_family_building"][NAMES["map_family_of_row"][r]]
            per[label] = per.get(label, 0) + 1
        maps_by_building = "; ".join(f"{k}: {v}" for k, v in per.items()) or None

    progress = {
        "health": health, "healing_drinks": drinks, "healing_syringes": syringes,
        "ammo_handgun": ammo.get("HandgunAmmo"), "ammo_shotgun": ammo.get("ShotgunAmmo"), "ammo_rifle": ammo.get("RifleAmmo"),
        "investigated": investigated, "kills_total": kills, "weapons": weapons,
        "memos_count": memos_count, "last_memo": last_memo,
        "maps_count": maps_count, "maps_by_building": maps_by_building,
        "location_tag": s["location_tag"],
    }

    F = Facts()
    if health is not None:
        F.sfact("health", "heart", "Здоровье", health)
    if drinks is not None:
        F.sfact("healing_drinks", "bottle", "Лечебные напитки", drinks)
    if syringes is not None:
        F.sfact("healing_syringes", "syringe", "Шприцы", syringes)
    if progress["ammo_handgun"] is not None:
        F.sfact("ammo_handgun", AMMO_ICON, "Патроны для пистолета", progress["ammo_handgun"])
    if progress["ammo_shotgun"] is not None:
        F.sfact("ammo_shotgun", AMMO_ICON, "Патроны для дробовика", progress["ammo_shotgun"])
    if progress["ammo_rifle"] is not None:
        F.sfact("ammo_rifle", AMMO_ICON, "Патроны для винтовки", progress["ammo_rifle"])
    if weapons:
        F.sfact("weapons", "sword", "Оружие", weapons)
    if kills is not None:
        F.sfact("kills_total", "skull", "Убито врагов", kills)
    if investigated is not None:
        F.sfact("investigated", "search", "Изучено на картах", investigated)
    if memos_count is not None:
        F.sfact("memos_count", "book", "Подобрано записок", memos_count)
    if last_memo:
        F.sfact("last_memo", "book", "Последняя записка", last_memo)
    if maps_count is not None:
        F.sfact("maps_count", "map-pin", "Карт в инвентаре", maps_count)
    if maps_by_building:
        F.sfact("maps_by_building", "map-pin", "Карты по зданиям", maps_by_building)

    proven = [k for k, v in progress.items() if v is not None and k != "location_tag"]
    if place:
        proven.append("place")
    return finish({
        "place": place, "chapter": None, "objective": None, "progress": progress,
        "facts": F.items, "fact_sources": F.sources, "proven": proven,
        "unproven": ["chapter", "objective", "difficulty", "play_time", "health_max", "ending_choices", "registered_ending"],
        "nonmonotonic": {k: "consumed or healed during play" for k in
                         ("health", "healing_drinks", "healing_syringes", "ammo_handgun", "ammo_shotgun", "ammo_rifle",
                          "maps_count")},
    }, path)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(read(sys.argv[1] if len(sys.argv) > 1 else None), ensure_ascii=False, indent=2))
