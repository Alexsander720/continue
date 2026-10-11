"""Read actual LastSaveChapter; catalog totals generated from game INI rows."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
if __package__ != "ddsaves":
    sys.path.insert(0, str(HERE.parents[4] / "GameHub" if HERE.parent.name == "codex" else HERE.parent))
from ddsaves._common import localize, select, ui, empty, fact, finish, newest, proton_user

APPID = 1426210
TABLE = HERE.parent / "data/it_takes_two.json" if HERE.parent.name == "codex" else HERE / "data/it_takes_two.json"


def tables():
    return localize(json.loads(TABLE.read_text(encoding="utf-8")))


def default_files():
    roots = [Path(os.environ["LOCALAPPDATA"]) / "ItTakesTwo"] if os.environ.get("LOCALAPPDATA") else []
    roots += [user / "AppData/Local/ItTakesTwo" for user in proton_user(APPID)]
    return [root / "SaveData.Nuts" for root in roots]


def find(path_or_dir=None):
    if path_or_dir is None:
        return newest(default_files())
    path = Path(path_or_dir)
    if path.is_file():
        return path
    return newest(path.rglob("SaveData.Nuts")) if path.is_dir() else None


def read(path_or_dir=None):
    path = find(path_or_dir)
    if path is None:
        return empty("It Takes Two save not found")
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(raw, dict):
            raise ValueError("Expected save JSON object")
        data = tables()
        current_key = raw.get("LastSaveChapter")
        current = data["by_key"].get(current_key)
        if current is None:
            out = empty("Profile has no recognized saved chapter; EULA/settings do not prove gameplay progress")
            out["progress"] = {"last_save_chapter": current_key, "furthest_unlocked_chapter": raw.get("FurthestUnlockedChapter")}
            out["unproven"] = ["chapter_num", "minigames_unlocked", "place", "chapter", "objective"]
            return finish(out, path)
        mini_values = {key.split(".", 1)[1]: value for key, value in raw.items() if key.startswith("Minigame.")}
        unlocked = sorted(key for key in data["minigames"] if mini_values.get(key) is True or mini_values.get(key) == "true")
        unknown = sorted(key for key in mini_values if key not in data["minigames"])
        progress = {"chapter_num": current["chapter_num"], "chapters_total": len(data["playable_groups"]),
                    "minigames_unlocked": len(unlocked), "minigames_total": len(data["minigames"]), "minigames_list": unlocked,
                    "last_save_chapter": current_key, "last_save_progress_point": raw.get("LastSaveProgressPoint"),
                    "furthest_unlocked_chapter": raw.get("FurthestUnlockedChapter"), "unknown_minigame_ids": unknown}
        return finish({"place": current["text"], "chapter": current["chapter_text"], "objective": None,
                       "progress": progress, "facts": [fact("flag", "Глава", f"{current['chapter_num']} / {len(data['playable_groups'])}"),
                                                      fact("trophy", "Мини-игры", f"{len(unlocked)} / {len(data['minigames'])}")],
                       "proven": ["place", "chapter", "chapter_num", "chapters_total", "minigames_unlocked", "minigames_total", "minigames_list"],
                       "unproven": ["objective", "last_save_progress_point", "unknown_minigame_ids"],
                       "place_semantics": "Title stored in LastSaveChapter; LastSaveProgressPoint is a separate saved field"}, path)
    except (OSError, ValueError, KeyError) as error:
        return finish(empty(str(error)), path)


if __name__ == "__main__":
    print(json.dumps(read(sys.argv[1] if len(sys.argv) > 1 else None), ensure_ascii=False, indent=2))
