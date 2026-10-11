"""Marvel's Spider-Man 2 card: current story mission, its objective and district, story / collectibles progress.

Save: DAT1 type 9, systems as serialized DDL (see _sm2_dat1.py). Names come only from
antigravity/dumps/spider_man_2/card_*.json (generator antigravity/tools/sm2_card_dump.py: the game's
mission graph, district and lobby configs, localization). Save keys = Insomniac CRC32 of game names.

Fields (proof in cards/spider_man_2.md):
  current mission  ObjectiveSystem graph node in state kAvailable/kActive whose name is a story mission
                   (GP_*, titled, CompletionWeight > 0 in the mission graph); PlayerSelectedMission breaks ties.
  objective        mission graph UIData.AvailableObjectiveDescription (kAvailable) / MissionDescription (kActive)
  place            mission graph UIData.OverrideDistrict -> district config LocTag
  story_done/total completed story missions / story missions in the graph
  game_percent     SaveFile.GamePercent
  level            HeroSystem.DisplayLevel
  spiderbots/photos/prowler  CollectibleSystemGame NumCompleted under CRC32(group); totals = sum of
                   DistrictCompletionEstimates.TotalNumExpected of that group over all district configs
  district groups  DistrictCompletionMissions lists (config) x mission states (save)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from _card import Facts, empty, finish  # noqa: E402
from _sm2_dat1 import crc32, save_systems  # noqa: E402
from ddsaves._common import localize, select, ui, documents_dirs, proton_user  # noqa: E402

APPID = 2651280
DUMPS = HERE / "data" / "spider_man_2"
DONE = "kCompleteFinished"
OPEN_STATES = ("kAvailable", "kActive")
# collectible groups whose save NumCompleted never exceeded the config total on any stage
COUNTED_GROUPS = ("SpiderBots", "Photos", "ProwlerTech")
# mission groups shown as "N/M" over all districts
MISSION_GROUPS = ("SymbioteBases", "HunterBases", "HunterBlinds", "TalonChases", "Mysterio", "EmilyMay", "FNSM")

_TABLES = None


def tables():
    global _TABLES
    if _TABLES is None:
        ld = lambda n: json.loads((DUMPS / n).read_text(encoding="utf-8"))["data"]
        _TABLES = {"missions": ld("card_missions.json"), "districts": ld("card_districts.json"),
                   "meta": ld("card_meta.json")}
    return localize(_TABLES)


def find(path_or_dir=None):
    roots = [Path(path_or_dir)] if path_or_dir else [d / "Marvel's Spider-Man 2" for d in documents_dirs()]
    if not path_or_dir:
        roots += [p / "Documents" / "Marvel's Spider-Man 2" for p in proton_user(APPID)]
    files = []
    for r in roots:
        if r.is_file():
            files.append(r)
        elif r.is_dir():
            files += [f for f in r.rglob("slot*-*.save") if f.is_file()]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def is_story(m: dict) -> bool:
    return m["mission"].startswith("GP_") and bool((m.get("title") or {}).get("ru")) and (m.get("completion_weight") or 0) > 0


def ru(t):
    return (t or {}).get("ru") or None


def read(path_or_dir=None):
    path = find(path_or_dir)
    if path is None:
        return {**empty("Сохранение Spider-Man 2 не найдено"), "proven": [], "fact_sources": {}}
    try:
        S = save_systems(path.read_bytes())
    except (ValueError, KeyError, IndexError, UnicodeError) as e:
        return finish({**empty(f"Spider-Man 2: неизвестный формат сохранения ({type(e).__name__})"),
                       "proven": [], "fact_sources": {}}, path)
    T = tables()
    M, districts = T["missions"], T["districts"]
    if not all(isinstance(S.get(key), dict) for key in
               ("ObjectiveSystem", "CollectibleSystemGame", "HeroSystem", "SaveFile", "DifficultySystem")):
        return finish({**empty("Spider-Man 2: файл настроек или неполный сюжетный слот"),
                       "proven": [], "fact_sources": {}}, path)
    obj = S["ObjectiveSystem"]
    sysdata = obj["SystemData"]["Obj"]
    graph = next(iter(obj["GraphDataTable"].values()))
    nodes = graph["NodeDataTable"]
    state = {k: (n["NodeData"]["Obj"].get("MissionState")) for k, n in nodes.items()}
    graph_ok = str(graph.get("GraphAsset")) == str(int(T["meta"]["mission_graph_asset"], 16))

    # story progress
    story = {k: m for k, m in M.items() if is_story(m)}
    story_done = sum(1 for k in story if state.get(k) == DONE)

    # current story mission
    open_story = [k for k in story if state.get(k) in OPEN_STATES]
    sel = str(sysdata.get("PlayerSelectedMission") or 0)
    cur = sel if sel in open_story else (open_story[0] if len(open_story) == 1 else None)
    cm = M.get(cur) if cur else None
    cur_state = state.get(cur) if cur else None

    chapter = ru(cm["title"]) if cm else None
    objective = None
    if cm:
        objective = ru(cm["available_objective"]) if cur_state == "kAvailable" else ru(cm["description"])
    dist_by_enum = {d["district"]: d for d in districts if d.get("district")}
    place = None
    if cm and cm.get("override_district") in dist_by_enum:
        place = ru(dist_by_enum[cm["override_district"]]["name"])

    # collectibles
    col = S["CollectibleSystemGame"]["TypeSaveData"]
    collect = {}
    for g in COUNTED_GROUPS:
        total = sum((d["estimates"].get(g) or 0) for d in districts)
        done = (col.get(str(crc32(g))) or {}).get("NumCompleted")
        collect[g] = {"done": done, "total": total}

    # mission groups per district (config lists x save states)
    groups_total, per_district = {}, {}
    for d in districts:
        name = ru(d["name"]) or d["asset_id"]
        row = {}
        for g, ms in d["missions"].items():
            n_done = sum(1 for m in ms if state.get(str(crc32(m))) == DONE)
            row[g] = f"{n_done}/{len(ms)}"
            t = groups_total.setdefault(g, [0, 0])
            t[0] += n_done
            t[1] += len(ms)
        per_district[name] = row

    hero = S["HeroSystem"]
    sf = S["SaveFile"]
    diff_id = S["DifficultySystem"].get("Difficulty")
    difficulty = ru(T["meta"]["difficulty"].get(diff_id)) if diff_id else None

    progress = {
        "story_done": story_done,
        "story_total": len(story),
        "game_percent": round(float(sf["GamePercent"]) * 100, 1),
        "level": hero.get("DisplayLevel"),
        "spiderbots_done": collect["SpiderBots"]["done"],
        "photos_done": collect["Photos"]["done"],
        "prowler_done": collect["ProwlerTech"]["done"],
        "collectible_totals": {g: v["total"] for g, v in collect.items()},
        "mission_groups": {g: f"{v[0]}/{v[1]}" for g, v in groups_total.items()},
        "district_groups": per_district,
        "current_mission_id": cm["mission"] if cm else None,
        "current_mission_state": cur_state,
        "open_story_missions": [M[k]["mission"] for k in open_story],
        "difficulty": difficulty,
        "difficulty_raw": diff_id,
        "act_raw": sysdata.get("CurrentAct"),
        "checkpoint_raw": sf.get("CurrentCheckpointName"),
        "new_game_plus": sf.get("NewGamePlus"),
        "mission_graph_matches_dump": graph_ok,
    }

    F = Facts()
    F.sfact("game_percent", "pie", "Прохождение", f"{progress['game_percent']:g}%")
    F.sfact("story_done", "sword", "Сюжет", f"{story_done}/{len(story)}")
    if progress["level"] is not None:
        F.sfact("level", "shield", "Уровень", progress["level"])
    if collect["SpiderBots"]["done"] is not None:
        F.sfact("spiderbots_done", "gem", "Паукоботы", f"{collect['SpiderBots']['done']}/{collect['SpiderBots']['total']}")
    if collect["Photos"]["done"] is not None:
        F.sfact("photos_done", "eye", "Фототочки", f"{collect['Photos']['done']}/{collect['Photos']['total']}")
    if collect["ProwlerTech"]["done"] is not None:
        F.sfact("prowler_done", "mask", "Тайники Бродяги", f"{collect['ProwlerTech']['done']}/{collect['ProwlerTech']['total']}")

    proven = ["chapter", "objective", "place", "story_done", "game_percent", "level",
              "spiderbots_done", "photos_done", "prowler_done"]
    unproven = ["difficulty", "mission_groups", "district_groups", "act_raw", "checkpoint_raw", "new_game_plus"]
    if not graph_ok:  # different game build: names may not match the save's graph
        unproven += [p for p in ("chapter", "objective", "place") if p in proven]
        proven = [p for p in proven if p not in ("chapter", "objective", "place")]
    return finish({"place": place, "chapter": chapter, "objective": objective, "progress": progress,
                   "facts": F.items, "fact_sources": F.sources, "proven": proven, "unproven": unproven,
                   "difficulty": difficulty}, path)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(read(sys.argv[1] if len(sys.argv) > 1 else None), ensure_ascii=False, indent=1))
