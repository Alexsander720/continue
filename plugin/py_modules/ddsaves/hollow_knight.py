"""Hollow Knight real stages: RU abilities, spells, Dreamers. Stdlib adapter.

No chapter, invented objective, or latest-boss inference from unordered flags.
Shared helpers stay in the accepted ddsaves._common module.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if not __package__:
    if Path(__file__).resolve().parent.parent.name == "codex":
        sys.path.insert(0, str(ROOT.parents[min(2, len(ROOT.parents) - 1)] / "GameHub"))
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ddsaves._common import localize, select, ui, aes_ecb_decrypt, dotnet_b64_string, dur, empty, fact, finish, newest, num, proton_user

APPID = 367520
SUB = "AppData/LocalLow/Team Cherry/Hollow Knight"
KEY = b"UKu52ePUBwetZ9wNX88o54dnfKRu0T1l"
LOCAL_TABLE = (Path(__file__).resolve().parent if Path(__file__).resolve().parent.name == "ddsaves" else Path(__file__).resolve().parents[1]) / "data/hollow_knight.json"
TABLE = LOCAL_TABLE if LOCAL_TABLE.is_file() else Path(__file__).resolve().parent / "data/hollow_knight.json"
T = json.loads(TABLE.read_text(encoding="utf8"))
ZONES = {int(k): v for k, v in localize(T)["zones"].items()}
# Public integer-ID mapping consumed by GameHub saves.py/hub_saves.py.
CHARMS = {int(k): v for k, v in localize(T)["charms"].items()}
CHARMS[36] = localize(T)["royal_charm"]["B"]


def find(path_or_dir=None):
    if path_or_dir is not None:
        p = Path(path_or_dir)
        if p.is_file():
            return p
        return (newest(p.glob("user[1-4].dat")) or newest(p.rglob("user[1-4].dat"))) if p.is_dir() else None
    paths = []
    if os.environ.get("USERPROFILE"):
        paths.append(Path(os.environ["USERPROFILE"]) / SUB)
    paths.extend(p / SUB for p in proton_user(APPID))
    for p in paths:
        save = newest(p.glob("user[1-4].dat"))
        if save:
            return save
    return None


def decrypt(raw):
    dec = aes_ecb_decrypt(KEY, dotnet_b64_string(raw))
    return json.loads(dec.decode("utf8")) if dec else None


def charm_name(cid, pd):
    T = localize(globals()["T"])
    if cid == 36:
        state = pd.get("royalCharmState", 0)
        return T["royal_charm"]["C" if state == 4 else "B" if state == 3 else "A"]
    return T["charms"].get(str(cid))


def read(path_or_dir=None):
    T = localize(globals()["T"])
    path = find(path_or_dir)
    if path is None:
        return empty("Файл сохранения Hollow Knight (user*.dat) не найден")
    try:
        data = decrypt(path.read_bytes())
        pd = data["playerData"]
        if not isinstance(pd, dict):
            return empty("В сейве нет playerData")
    except (ValueError, TypeError, KeyError, IndexError, OSError):
        return empty("Не удалось прочитать user*.dat")
    play = round(float(pd.get("playTime") or 0), 1)
    geo = int(pd.get("geo") or 0)
    masks = int(pd.get("maxHealth") or 0)
    nail_lvl = int(pd.get("nailSmithUpgrades") or 0)
    pct = round(float(pd.get("completionPercentage") or 0), 1)
    grubs = int(pd.get("grubsCollected") or 0)
    owned = sorted(int(k[9:]) for k, v in pd.items() if k.startswith("gotCharm_") and k[9:].isdigit() and v is True)
    equipped = [int(c) for c in pd.get("equippedCharms", []) if str(c).isdigit()]
    ability_flags = {flag: pd.get(flag) is True for flag in [*T["abilities"], *T["dream_nail"]]}
    abilities = [name for flag, name in T["abilities"].items() if ability_flags[flag]]
    if ability_flags["hasDreamNail"]:
        abilities.append(T["dream_nail"]["dreamNailUpgraded" if ability_flags["dreamNailUpgraded"] else "hasDreamNail"])
    if ability_flags["hasDreamGate"]:
        abilities.append(T["dream_nail"]["hasDreamGate"])
    spell_levels = {flag: int(pd.get(flag) or 0) for flag in T["spells"]}
    spells = [names[str(spell_levels[flag])] for flag, names in T["spells"].items() if str(spell_levels[flag]) in names]
    dreamer_flags = {flag: pd.get(flag) is True for flag in T["dreamers"]}
    dreamers = [name for flag, name in T["dreamers"].items() if dreamer_flags[flag]]
    bosses = [name for flag, name in T["bosses"] if pd.get(flag) is True]
    progress = {"active_gameplay_seconds": play, "geo": geo, "max_health": masks, "nail_damage": int(pd.get("nailDamage") or 0), "nail_name": T["nails"][nail_lvl] if 0 <= nail_lvl < len(T["nails"]) else None, "completion_percent": pct, "grubs": grubs, "charms_count": len(owned), "charms_total": T["charms_total"], "charms_equipped_names": [name for c in equipped if (name := charm_name(c, pd))], "dreamers_count": len(dreamers), "dreamers": dreamers, "dreamer_flags": dreamer_flags, "abilities": abilities, "ability_flags": ability_flags, "spells": spells, "spell_levels": spell_levels, "bosses_count": len(bosses), "bosses": bosses, "last_boss": None, "last_journal_item": pd.get("lastJournalItem"), "pale_ore": int(pd.get("ore") or 0), "charm_slots": int(pd.get("charmSlots") or 0), "simple_keys": int(pd.get("simpleKeys") or 0)}
    facts = []
    if pct > 0:
        facts.append(fact("pie", "Пройдено", f"{pct:g}%"))
    facts.append(fact("mask", "Маски", masks))
    if progress["nail_name"]:
        facts.append(fact("sword", "Гвоздь", f"{progress['nail_name']} ({progress['nail_damage']})"))
    facts.append(fact("gem", "Гео", num(geo)))
    if owned:
        facts.append(fact("shield", "Амулеты", f"{len(owned)} / {T['charms_total']}"))
    if abilities:
        facts.append(fact("sword", "Способности", ", ".join(abilities)))
    if spells:
        facts.append(fact("eye", "Заклинания", ", ".join(spells)))
    if dreamers:
        facts.append(fact("eye", "Грезящие", ", ".join(dreamers)))
    if grubs:
        facts.append(fact("smile", "Гусенички", grubs))
    if play >= 60:
        facts.append(fact("clock", "В этом сейве", dur(play)))
    zone = {int(k): v for k, v in T["zones"].items()}.get(pd.get("mapZone"))
    place = (zone  if pd.get("respawnMarkerName") == "RestBench" else zone) if zone else None
    return finish({"place": place, "chapter": None, "objective": None, "play_seconds": play, "progress": progress, "facts": facts, "proven": ["place", "play_seconds", "active_gameplay_seconds", "geo", "max_health", "nail_damage", "nail_name", "completion_percent", "grubs", "charms_count", "charms_equipped_names", "dreamers_count", "dreamers", "dreamer_flags", "abilities", "ability_flags", "spells", "spell_levels"], "unproven": ["bosses", "bosses_count", "last_boss", "last_journal_item", "pale_ore", "charm_slots", "simple_keys"]}, path)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf8")
    print(json.dumps(read(sys.argv[1] if len(sys.argv) > 1 else None), ensure_ascii=False, indent=2))
