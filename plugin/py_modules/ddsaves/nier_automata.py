"""NieR:Automata card parser (appid 524220).

Container format: Platinum Games proprietary binary/ASCII structured format.
Names come from antigravity/dumps/nier_automata/ (chapters.json, chapter_events.json,
transporters.json, endings.json, weapons.json, quests.json, experience.json).

Fields:
  chapter: Current story chapter
  place: Current fast travel transporter / save point location
  objective: Current active quest or mission
  active_character: Active playable android (2B, 9S, A2)
  story_route: Story progression route (Route A, Route B, Route C)
  player_level: Current android level (1..99)
  endings_unlocked: Total endings unlocked (out of 26)
  weapons_owned: Total weapons collected (out of 39)
  quests_completed: Side quests completed (out of 66)
  gold: G currency balance
  experience: Experience points (EXP)
  play_time_seconds: In-game play time
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

import importlib.util
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from _card import Facts, empty, finish
from ddsaves._common import localize, select, ui, documents_dirs, newest, proton_user

_reader_path = HERE / "_ag_nier_automata_reader.py"
_spec = importlib.util.spec_from_file_location("agreader_nier_automata", _reader_path)
reader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reader)

APPID = 524220
DUMPS = HERE / "data" / "nier_automata"
SUB = "Documents/My Games/NieR_Automata"

_DATA: Optional[Dict[str, Any]] = None


def get_data() -> dict:
    global _DATA
    if _DATA is None:
        chs = json.loads((DUMPS / "chapters.json").read_text(encoding="utf-8"))["data"]
        trans = json.loads((DUMPS / "transporters.json").read_text(encoding="utf-8"))["data"]
        ends = json.loads((DUMPS / "endings.json").read_text(encoding="utf-8"))["data"]
        wps = json.loads((DUMPS / "weapons.json").read_text(encoding="utf-8"))["data"]
        qts = json.loads((DUMPS / "quests.json").read_text(encoding="utf-8"))["data"]
        _DATA = {
            "chapters": chs,
            "transporters": trans.get("transporters", {}),
            "endings": ends.get("endings", {}),
            "weapons": wps.get("weapons", {}),
            "quests": qts.get("quests", {}),
        }
    return localize(_DATA)


def default_dirs() -> List[Path]:
    roots = []
    for d in documents_dirs():
        cand = d / "My Games/NieR_Automata"
        if cand.is_dir():
            roots.append(cand)
    for p in proton_user(APPID):
        cand = p / "Documents/My Games/NieR_Automata"
        if cand.is_dir():
            roots.append(cand)
    return roots


def find(path_or_dir=None) -> List[Path]:
    if path_or_dir:
        p = Path(path_or_dir)
        if p.is_file():
            return [p]
        if p.is_dir():
            files = sorted(p.rglob("SlotData_*.dat"), key=lambda f: f.stat().st_mtime, reverse=True)
            return files
        return []

    found = []
    for d in default_dirs():
        files = sorted(d.glob("SlotData_*.dat"), key=lambda f: f.stat().st_mtime, reverse=True)
        found.extend(files)
    return found


def read(path_or_dir=None) -> dict:
    try:
        return _read(path_or_dir)
    except Exception as e:
        return empty(f"Сохранение NieR:Automata не прочитано: {e}")


def _read(path_or_dir=None) -> dict:
    files = find(path_or_dir)
    if not files:
        return empty("Файлы сохранений NieR:Automata не найдены")

    target = files[0]
    parsed = reader.dump(target)
    if not parsed.get("has_save"):
        return empty("Не удалось прочитать сохранение NieR:Automata")

    place = parsed.get("location_name")
    chapter = parsed.get("story_chapter")
    objective = parsed.get("target_objective")

    active_character = parsed.get("active_character")
    story_route = parsed.get("story_route")
    player_level = parsed.get("player_level", 1)
    endings_unlocked = parsed.get("endings_unlocked", 0)
    weapons_owned = parsed.get("weapons_owned", 0)
    quests_completed = parsed.get("quests_completed", 0)
    quests_total = parsed.get("quests_total", 66)
    gold = parsed.get("gold", 0)
    experience = parsed.get("experience", 0)
    play_time_seconds = parsed.get("play_time_seconds", 0)

    progress = {
        "story_chapter": chapter,
        "player_level": player_level,
        "endings_unlocked": endings_unlocked,
        "weapons_owned": weapons_owned,
        "quests_completed": quests_completed,
        "gold": gold,
        "experience": experience,
        "play_time_seconds": play_time_seconds,
    }

    F = Facts()
    F.sfact("player_level", "star", "Уровень", f"Lv. {player_level}")
    if story_route:
        F.sfact("story_route", "compass", "Ветка сюжета", story_route)
    if active_character:
        F.sfact("active_character", "user", "Персонаж", active_character)
    F.sfact("endings_unlocked", "trophy", "Концовки", f"{endings_unlocked}/26")
    F.sfact("quests_completed", "check", "Побочные задания", f"{quests_completed}/{quests_total}")
    F.sfact("weapons_owned", "crosshair", "Оружие", f"{weapons_owned}/39")
    F.sfact("gold", "coin", "Деньги (G)", f"{gold} G")

    proven = [
        "player_level",
        "endings_unlocked",
        "weapons_owned",
        "quests_completed",
        "gold",
        "experience",
        "play_time_seconds",
    ]
    if chapter:
        proven.append("chapter")
    if place:
        proven.append("place")
    if story_route:
        proven.append("story_route")
    if active_character:
        proven.append("active_character")

    out = {
        "place": place,
        "chapter": chapter,
        "objective": None,  # не доказано: первое активное побочное
        "progress": progress,
        "facts": F.items,
        "fact_sources": F.sources,
        "proven": proven,
        "unproven": [
            "chips_installed",
            "pod_programs",
            "corpse_recovered",
            "fish_caught",
            "unit_data_percent",
        ],
        "nonmonotonic": {
            "weapons_owned": "Virtuous Treaty left at factory ruins after prologue explosion",
        },
        "active_character": active_character,
        "story_route": story_route,
        "player_level": player_level,
        "endings_unlocked": endings_unlocked,
        "weapons_owned": weapons_owned,
        "quests_completed": quests_completed,
        "gold": gold,
        "experience": experience,
        "play_time_seconds": play_time_seconds,
    }

    return finish(out, target)
