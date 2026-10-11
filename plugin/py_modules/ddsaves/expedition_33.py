"""Stdlib-only read() for Expedition 33; exact cooked DataTable mappings.

Validation: 38 real author-labelled Kelsh Act1/2/3 stages and two independent
backup sequences. Currency, difficulty and NG+ remain unproven.
Copy the generated table to ddsaves/data when integrating this candidate.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
_HERE = Path(__file__).resolve().parent
if __package__ != "ddsaves":
    sys.path.insert(0, str(ROOT.parents[min(2, len(ROOT.parents) - 1)] / "GameHub" if _HERE.parent.name == "codex" else _HERE.parent))
from ddsaves import gvas
from ddsaves._common import localize, select, ui, dur, empty, fact, finish, newest, proton_user

APPID = 1903340
_TABLE_PATH = (_HERE.parent / "data/expedition_33.json" if _HERE.parent.name == "codex"
               else _HERE / "data/expedition_33.json")
T = json.loads(_TABLE_PATH.read_text(encoding="utf-8"))


def default_files():
    roots = []
    if os.environ.get("LOCALAPPDATA"):
        roots.append(Path(os.environ["LOCALAPPDATA"]) / "Sandfall/Saved/SaveGames")
    roots += [user / "AppData/Local/Sandfall/Saved/SaveGames" for user in proton_user(APPID)]
    return [path for root in roots for pattern in ["EXPEDITION_*.sav", "*/EXPEDITION_*.sav"]
            for path in root.glob(pattern)]


def find(path_or_dir=None):
    if path_or_dir is None:
        return newest(default_files())
    path = Path(path_or_dir)
    if path.is_file():
        return path
    if path.is_dir():
        return newest(path.glob("EXPEDITION_*.sav")) or newest(path.rglob("EXPEDITION_*.sav"))
    return None


def level_candidates(asset):
    T = localize(globals()["T"])
    return [{"row": row, **entry} for row, entry in T["level_rows"].items() if entry["asset"] == asset]


def level_name(asset):
    values = {entry["text"] for entry in level_candidates(asset) if entry["text"]}
    return next(iter(values)) if len(values) == 1 else None


def _status(value):
    T = localize(globals()["T"])
    allowed = {entry["enum_name"]: entry["source"] for entry in T["quest_status_enum"].values()}
    return allowed.get(value)


def story_state(stages):
    """Latest Started ahead of latest Completed; older Started may persist.

    BP_FL_MainQuestHelper requests the last objective with a given status.
    DT_MainQuestData records act/step to apply on completion. A completed
    higher step supersedes old Started entries, without inventing a new goal.
    """
    T = localize(globals()["T"])
    order = T["objective_order"]
    valid = len(stages) == len(order) and {row for row, _ in stages} == set(order)
    states = dict(stages) if valid else {}
    names = {row: _status(states[row]) for row in order} if valid else {}
    valid = valid and all(value in {"NotStarted", "Started", "Completed"} for value in names.values())
    completed = [row for row in order if names.get(row) == "Completed"] if valid else []
    started = [row for row in order if names.get(row) == "Started"] if valid else []
    last_done = completed[-1] if completed else None
    frontier = order.index(last_done) if last_done else -1
    ahead = [row for row in started if order.index(row) > frontier]
    active = ahead[-1] if ahead else None
    # No observed frontier: do not turn an all-NotStarted snapshot into Act I.
    valid = valid and bool(last_done or active)
    act_value = T["main_quest_rows"][last_done]["act_on_completed"] if last_done else 0
    act = T["act_enum"].get(str(act_value), {}) if valid else {}
    chapter = T["act_texts"].get(str(act_value), {}).get("text") if valid else None
    return {"valid": valid, "active": active, "last_completed": last_done,
            "completed": len(completed) if valid else None,
            "current_step_on_completed": T["main_quest_rows"][last_done]["step_on_completed"] if valid and last_done else 1 if valid else None,
            "stage": T["main_quest_rows"][active or last_done]["step_on_completed"] if valid and (active or last_done) else None,
            "stale_started": [row for row in started if row != active],
            "act_value": act_value if valid else None, "act_id": act.get("source"), "chapter": chapter}


def read(path_or_dir=None):
    T = localize(globals()["T"])
    path = find(path_or_dir)
    if path is None:
        return empty("Сохранение Expedition 33 (EXPEDITION_*.sav) не найдено")
    try:
        props = gvas.unwrap(gvas.read(path.read_bytes())["props"])
    except (ValueError, KeyError, IndexError, OSError):
        return finish(empty("Сохранение Expedition 33 не разобрано"), path)

    asset = props.get("MapToLoad") or ""
    place = level_name(asset)
    stages = next((quest.get("ObjectivesStatus") or [] for key, quest in props.get("QuestStatuses", [])
                   if key == "Main_GoldenPath" and isinstance(quest, dict)), [])
    known = set(T["objectives"])
    story = story_state(stages)
    story_valid, active = story["valid"], story["active"]
    objective = T["objectives"].get(active, {}).get("text")
    done, stage, chapter = story["completed"], story["stage"], story["chapter"]

    roster, character_levels, unknown = [], {}, []
    for key, data in props.get("CharactersCollection", []):
        if not isinstance(data, dict):
            continue
        identifier = data.get("CharacterHardcodedName") or key
        entry = T["characters"].get(identifier)
        level = data.get("CurrentLevel")
        if not entry or not entry["text"] or not isinstance(level, int) or level < 1:
            unknown.append({"identifier": identifier, "level": level})
            continue
        roster.append({"id": identifier, "name": entry["text"], "level": level,
                       "excluded": data.get("IsExcluded")})
        character_levels[entry["text"]] = level
    play = props.get("TimePlayed")
    progress = {
        "map_asset": asset, "place_candidates": level_candidates(asset),
        "active_objective_id": active, "objective_desc": objective,
        "story_statuses": stages, "story_stage": stage, "story_completed": done,
        "story_stages_total": len(known), "story_pattern_valid": story_valid,
        "last_completed_objective_id": story["last_completed"],
        "stale_started_objective_ids": story["stale_started"],
        "act_value": story["act_value"], "act_id": story["act_id"],
        "current_step_on_completed": story["current_step_on_completed"],
        "character_levels": character_levels, "characters": roster, "unknown_characters": unknown,
        "current_party": props.get("CurrentParty"),
        "active_gameplay_seconds": play, "gold": props.get("Gold"),
        "new_game_plus": props.get("FinishedGameCount"), "difficulty_raw": props.get("GameDifficultyData"),
    }
    facts, proven = [], []
    if place:
        proven.append("place")
    if objective:
        proven.append("objective")
    if story_valid and isinstance(stage, int):
        proven.append("story_stage")
        facts.append(fact("scroll", "Сюжет", ui("story_stage", n=stage, total=len(known))))
    if chapter:
        proven.append("chapter")
    if character_levels:
        proven.append("character_levels")
        facts.append(fact("level", "Уровни", ", ".join(f'{entry["name"]} {entry["level"]}' for entry in roster)))
    if isinstance(play, (int, float)) and play >= 60:
        proven.append("active_gameplay_seconds")
        facts.append(fact("clock", "В этом сейве", dur(play)))
    unproven = ["gold", "new_game_plus", "difficulty_raw", "current_party"]
    if not chapter:
        unproven.append("chapter")
    if unknown:
        unproven.append("unknown_characters")
    if not place:
        unproven.append("place")
    if not story_valid or stage is None:
        unproven.extend(["story_stage", "objective"])
    return finish({"place": place, "chapter": chapter, "objective": objective,
                   "progress": progress, "facts": facts, "proven": proven,
                   "unproven": unproven}, path)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(read(sys.argv[1] if len(sys.argv) > 1 else None), ensure_ascii=False, indent=2))
