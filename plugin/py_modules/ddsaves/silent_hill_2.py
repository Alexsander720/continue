"""SILENT HILL 2 (appid 2124490) live card: place, James's vitals, arsenal, pocket clues, Polaroids, survival stats."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import struct
import sys
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from _card import Facts, empty, finish  # noqa: E402
from ddsaves._common import lang as _lang, localize, proton_user  # noqa: E402

_spec = importlib.util.spec_from_file_location("agreader_silent_hill_2", HERE / "_ag_silent_hill_2_reader.py")
reader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reader)

APPID = 2124490
NAMES = json.loads((HERE / "data" / "silent_hill_2" / "card_names.json").read_text(encoding="utf-8"))
ICONS_PATH = HERE / "data" / "silent_hill_2_icons" / "index.json"
ICONS_DOC: Dict[str, Any] = json.loads(ICONS_PATH.read_text(encoding="utf-8")) if ICONS_PATH.is_file() else {}

WEAPON_ORDER = ("WoodenPlank", "IronPipe", "Chainsaw", "Pistol", "Shotgun", "Rifle")
WEAPON_AMMO_ROW = {"Pistol": "HandgunAmmo", "Shotgun": "ShotgunAmmo", "Rifle": "RifleAmmo"}
MEMENTO_ROWS = ("LetterFromMary", "LetterFromMary2", "LetterFromMary3", "PhotoOfMary", "BcaOW_AngelasKnife", "WsaFW_MarysScarf")
DIFF_LABELS = {
    "ru": {0: "Лёгкая", 1: "Стандартная", 2: "Сложная"},
    "en": {0: "Light", 1: "Standard", 2: "Hard"},
}


def _icon_rel(row: str) -> Optional[str]:
    entry = (ICONS_DOC.get("items") or {}).get(row)
    if entry and entry.get("file"):
        return "ddsaves/data/silent_hill_2_icons/" + entry["file"]
    ui_f = (ICONS_DOC.get("ui") or {}).get(row)
    if ui_f:
        return "ddsaves/data/silent_hill_2_icons/" + ui_f
    return None


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
            scored.append((reader._header(p.read_bytes())[0]["ticks"], str(p), p))
        except (OSError, ValueError, IndexError, struct.error, zlib.error):
            pass
    return max(scored)[2] if scored else None


def read(path_or_dir=None) -> dict:
    lg = "en" if _lang() == "en" else "ru"
    loc_names = localize(globals()["NAMES"])
    path = find(path_or_dir)
    if path is None:
        return empty("SH2 gameplay slot not found")
    try:
        s = reader.state(path)
    except (OSError, ValueError, KeyError, IndexError, struct.error, zlib.error, RuntimeError):
        return finish(empty("SH2 unknown or incomplete slot"), path)

    names = loc_names["items"]
    items = s["items"] or {}
    loc_tag = s["location_tag"]
    place = loc_names["places"].get(loc_tag)
    if not place:
        p_ext = (ICONS_DOC.get("places_extra") or {}).get(loc_tag) or {}
        place = p_ext.get(lg) or p_ext.get("ru")
    if isinstance(place, str):
        place = place.replace(". — ", " — ")

    health = int(round(s["health"])) if isinstance(s["health"], (int, float)) else None
    drinks = items.get("HealthDrink", 0) if s["items"] is not None else None
    syringes = items.get("Syringe", 0) if s["items"] is not None else None

    ammo_loaded = s.get("ammo_loaded") or {}
    weapon_kills = s.get("weapon_kills") or {}
    last_weapon = s.get("last_used_weapon")
    equipment = s.get("equipment") or {}

    ammo_bp = {row: items.get(row, 0) for row in loc_names["ammunition"]} if s["items"] is not None else {}
    ammo_total = {
        "HandgunAmmo": (ammo_bp.get("HandgunAmmo") or 0) + ammo_loaded.get("Pistol", 0),
        "ShotgunAmmo": (ammo_bp.get("ShotgunAmmo") or 0) + ammo_loaded.get("Shotgun", 0),
        "RifleAmmo": (ammo_bp.get("RifleAmmo") or 0) + ammo_loaded.get("Rifle", 0),
    }

    kills_m = s.get("kills_melee")
    kills_r = s.get("kills_ranged")
    kills = (int(kills_m or 0) + int(kills_r or 0)) if (isinstance(kills_m, int) or isinstance(kills_r, int)) else None
    if kills is None and weapon_kills:
        kills = sum(weapon_kills.values())

    investigated = s["map_items_investigated"] if isinstance(s.get("map_items_investigated"), int) else None

    # Build rich weapons detail
    weapons_detail = []
    owned_weapon_ids = [w for w in WEAPON_ORDER if items.get(w, 0) > 0]
    for wid in owned_weapon_ids:
        ammo_row = WEAPON_AMMO_ROW.get(wid)
        is_ranged = ammo_row is not None
        loaded_n = int(ammo_loaded.get(wid, 0)) if is_ranged else None
        reserve_n = int(items.get(ammo_row, 0)) if is_ranged else None
        weapons_detail.append({
            "id": wid,
            "name": names.get(wid) or wid,
            "kind": "ranged" if is_ranged else "melee",
            "equipped": wid == last_weapon,
            "loaded": loaded_n,
            "reserve": reserve_n,
            "total_ammo": (loaded_n + reserve_n) if is_ranged else None,
            "kills": int(weapon_kills.get(wid, 0)),
            "icon_rel": _icon_rel(wid),
        })

    # All weapons ever used (including WoodenPlank after IronPipe replaces it) for kill breakdown in Dossier
    weapon_kills_list = []
    for wid in WEAPON_ORDER:
        wk = int(weapon_kills.get(wid, 0))
        if wk > 0 or wid in owned_weapon_ids:
            weapon_kills_list.append({
                "id": wid,
                "name": names.get(wid) or wid,
                "kills": wk,
                "owned": wid in owned_weapon_ids,
                "equipped": wid == last_weapon,
                "icon_rel": _icon_rel(wid),
            })

    # Loose ammo boxes picked up before finding the gun itself
    loose_ammo = []
    for wid, arow in WEAPON_AMMO_ROW.items():
        if wid not in owned_weapon_ids and items.get(arow, 0) > 0:
            loose_ammo.append({
                "id": arow,
                "name": names.get(arow) or arow,
                "qty": int(items[arow]),
                "icon_rel": _icon_rel(arow),
            })

    weapons_str = ", ".join(w["name"] for w in weapons_detail) or None

    # Memos
    memos = s.get("memo_ids")
    memo_set = set(memos or ())
    memos_count = len(memos) if memos is not None else None
    last_memo = names.get(memos[-1]) if memos else None
    all_memos = [
        {"id": mid, "name": names.get(mid) or mid, "icon_rel": _icon_rel(mid)}
        for mid in reversed(memos or [])
        if names.get(mid)
    ]
    recent_memos = all_memos[:8]

    # Strange Polaroid Photos (Reflections_Photo_1..26)
    photos_doc = ICONS_DOC.get("photos") or {}
    photos_list = []
    for i in range(1, 27):
        rk = f"Reflections_Photo_{i}"
        if items.get(rk, 0) > 0:
            pm = photos_doc.get(rk) or {}
            title = pm.get(lg) or pm.get("ru") or names.get(rk) or f"#{i}"
            photos_list.append({
                "id": rk,
                "num": i,
                "title": title,
                "icon_rel": _icon_rel(rk),
            })
    photos_count = len(photos_list)
    glimpses_count = int(s.get("glimpses_count") or 0)

    # Maps
    map_rows_set = set(loc_names["map_family_of_row"])
    maps_count, maps_by_building = None, None
    maps_per_building_list = []
    if s["items"] is not None:
        mrows = [r for r, q in items.items() if q > 0 and r in map_rows_set]
        maps_count = len(mrows)
        per: Dict[str, int] = {}
        for r in mrows:
            label = loc_names["map_family_building"][loc_names["map_family_of_row"][r]]
            per[label] = per.get(label, 0) + 1
        maps_by_building = "; ".join(f"{k}: {v}" for k, v in per.items()) or None
        maps_per_building_list = [{"building": k, "count": v} for k, v in per.items()]

    # Pocket items (active puzzle items / keys first, then mementos)
    skip_rows = (
        set(WEAPON_ORDER)
        | set(WEAPON_AMMO_ROW.values())
        | {"HealthDrink", "Syringe", "Radio", "Flashlight"}
        | map_rows_set
        | memo_set
    )
    note_re = re.compile(r"(Note\d*|_Memo|Brochure|Flyer|Postcard|LetterTrailer|LetterWrench|Rifle_Hint)$", re.I)
    active_clues = []
    mementos = []
    for row, q in items.items():
        if q <= 0 or row in skip_rows or row.startswith("Reflections_Photo_") or note_re.search(row):
            continue
        nm = names.get(row)
        if not nm:
            continue
        entry = {
            "id": row,
            "name": nm,
            "qty": int(q),
            "memento": row in MEMENTO_ROWS,
            "icon_rel": _icon_rel(row),
        }
        if row in MEMENTO_ROWS:
            mementos.append(entry)
        else:
            active_clues.append(entry)
    pocket_items = active_clues + mementos

    distance_km = round(float(s["distance_cm"]) / 100_000.0, 1) if isinstance(s.get("distance_cm"), int) else None
    play_sec = s.get("playtime_seconds")
    cdiff = DIFF_LABELS[lg].get(s.get("combat_difficulty_id"))
    pdiff = DIFF_LABELS[lg].get(s.get("puzzle_difficulty_id"))

    sh2_dossier = {
        "place": place,
        "slot_type": s.get("slot_type"),
        "play_seconds": play_sec,
        "combat_difficulty": cdiff,
        "puzzle_difficulty": pdiff,
        "health": health,
        "drinks": drinks if drinks is not None else 0,
        "drinks_icon_rel": _icon_rel("HealthDrink"),
        "syringes": syringes if syringes is not None else 0,
        "syringes_icon_rel": _icon_rel("Syringe"),
        "equipment": {
            "radio": row in items if (row := "Radio") and False else (items.get("Radio", 0) > 0),
            "radio_on": bool(equipment.get("Radio", True)) if items.get("Radio", 0) > 0 else False,
            "radio_icon_rel": _icon_rel("Radio"),
            "flashlight": items.get("Flashlight", 0) > 0,
            "flashlight_on": bool(equipment.get("Flashlight", True)) if items.get("Flashlight", 0) > 0 else False,
            "flashlight_icon_rel": _icon_rel("Flashlight"),
        },
        "weapons": weapons_detail,
        "weapon_kills": weapon_kills_list,
        "loose_ammo": loose_ammo,
        "pocket": pocket_items,
        "photos": {"got": photos_count, "total": 26, "list": photos_list},
        "glimpses": {"got": glimpses_count, "total": 26},
        "memos": {"got": memos_count or 0, "last": last_memo, "recent": recent_memos, "list": all_memos},
        "maps": {"got": maps_count or 0, "by_building": maps_per_building_list},
        "stats": {
            "kills_total": kills,
            "kills_melee": kills_m if isinstance(kills_m, int) else None,
            "kills_ranged": kills_r if isinstance(kills_r, int) else None,
            "shots_fired": s.get("shots_fired") if isinstance(s.get("shots_fired"), int) else None,
            "dodges": s.get("dodges") if isinstance(s.get("dodges"), int) else None,
            "locked_doors": s.get("locked_doors_checked") if isinstance(s.get("locked_doors_checked"), int) else None,
            "broken_glass": s.get("broken_glass") if isinstance(s.get("broken_glass"), int) else None,
            "investigated": investigated,
            "heals_applied": s.get("heals_applied") if isinstance(s.get("heals_applied"), int) else None,
            "damage_received": int(round(s["damage_received"])) if isinstance(s.get("damage_received"), (int, float)) else None,
            "distance_km": distance_km,
        },
    }

    # Build Sally-Face / GoW compatible icon groups for Steam Deck & Hub
    groups = []
    med_people = []
    if health is not None:
        med_people.append({
            "key": "sh2:health",
            "name": "Здоровье" if lg == "ru" else "Health",
            "value": f"{health}%",
            "done": health,
            "total": 100,
            "icon_rel": _icon_rel("_health_cross"),
        })
    if drinks is not None:
        med_people.append({
            "key": "sh2:drinks",
            "name": names.get("HealthDrink") or "Health Drink",
            "value": f"×{drinks}",
            "done": drinks,
            "icon_rel": _icon_rel("HealthDrink"),
        })
    if syringes is not None:
        med_people.append({
            "key": "sh2:syringes",
            "name": names.get("Syringe") or "Syringe",
            "value": f"×{syringes}",
            "done": syringes,
            "icon_rel": _icon_rel("Syringe"),
        })
    if med_people:
        groups.append({
            "kind": "fav",
            "label": "Состояние" if lg == "ru" else "Condition",
            "people": med_people,
        })

    arsenal_people = []
    for w in weapons_detail:
        val = f"{w['loaded']}+{w['reserve']}" if w["kind"] == "ranged" else (f"{w['kills']}" if w["kills"] > 0 else "✓")
        arsenal_people.append({
            "key": f"sh2:w:{w['id']}",
            "name": w["name"],
            "value": val,
            "done": w["total_ammo"] if w["kind"] == "ranged" else 1,
            "icon_rel": w["icon_rel"],
        })
    for la in loose_ammo:
        arsenal_people.append({
            "key": f"sh2:a:{la['id']}",
            "name": la["name"],
            "value": f"+{la['qty']}",
            "done": la["qty"],
            "icon_rel": la["icon_rel"],
        })
    if arsenal_people:
        groups.append({
            "kind": "fav",
            "label": "Арсенал" if lg == "ru" else "Arsenal",
            "people": arsenal_people,
        })

    if pocket_items:
        shown_pocket = pocket_items[:5]
        groups.append({
            "kind": "items",
            "label": (f"В кармане · {len(pocket_items)}" if lg == "ru" else f"In pocket · {len(pocket_items)}"),
            "people": [
                {
                    "key": f"sh2:item:{it['id']}",
                    "name": it["name"] + (f" ×{it['qty']}" if it["qty"] > 1 else ""),
                    "icon_rel": it["icon_rel"],
                }
                for it in shown_pocket
            ],
        })

    progress = {
        "health": health,
        "healing_drinks": drinks,
        "healing_syringes": syringes,
        "ammo_handgun": ammo_total["HandgunAmmo"] if s["items"] is not None else None,
        "ammo_shotgun": ammo_total["ShotgunAmmo"] if s["items"] is not None else None,
        "ammo_rifle": ammo_total["RifleAmmo"] if s["items"] is not None else None,
        "ammo_loaded": ammo_loaded,
        "last_used_weapon": last_weapon,
        "investigated": investigated,
        "kills_total": kills,
        "weapons": weapons_str,
        "memos_count": memos_count,
        "last_memo": last_memo,
        "photos_count": photos_count,
        "glimpses_count": glimpses_count,
        "maps_count": maps_count,
        "maps_by_building": maps_by_building,
        "location_tag": loc_tag,
        "play_seconds": play_sec,
        "collectibles": {
            "total_items": len(items),
            "notes_count": memos_count or 0,
            "photos_count": photos_count,
        },
        "sh2_dossier": sh2_dossier,
    }
    if groups:
        progress["fact_rows"] = [{"id": "sh2_panel", "groups": groups}]

    F = Facts()
    if groups:
        F.items.append({"id": "sh2_panel", "groups": groups})
        F.sources["sh2_panel"] = "health"
    if photos_count > 0:
        F.sfact("photos_count", "camera", "Странные фото" if lg == "ru" else "Strange Photos", f"{photos_count} / 26")
    if glimpses_count > 0:
        F.sfact("glimpses_count", "sparkles", "Отголоски прошлого" if lg == "ru" else "Glimpses of the Past", f"{glimpses_count} / 26")
    if memos_count is not None:
        F.sfact("memos_count", "book", "Подобрано записок" if lg == "ru" else "Memos", memos_count)
    if kills is not None:
        F.sfact("kills_total", "skull", "Убито врагов" if lg == "ru" else "Enemies Killed", kills)

    proven = [
        k for k in (
            "health", "healing_drinks", "healing_syringes",
            "ammo_handgun", "ammo_shotgun", "ammo_rifle",
            "investigated", "kills_total", "weapons",
            "memos_count", "last_memo", "photos_count", "glimpses_count",
            "maps_count", "maps_by_building", "play_seconds", "fact_rows", "sh2_dossier",
        )
        if progress.get(k) is not None
    ]
    if place:
        proven.append("place")

    return finish({
        "place": place,
        "play_seconds": play_sec,
        "chapter": None,
        "objective": None,
        "progress": progress,
        "facts": F.items,
        "fact_sources": F.sources,
        "proven": proven,
        "unproven": ["chapter", "objective", "ending_choices", "registered_ending"],
        "nonmonotonic": {
            k: "consumed or healed during play"
            for k in ("health", "healing_drinks", "healing_syringes", "ammo_handgun", "ammo_shotgun", "ammo_rifle", "maps_count")
        },
    }, path)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(read(sys.argv[1] if len(sys.argv) > 1 else None), ensure_ascii=False, indent=2))
