"""Read genuine STS autosaves and character preferences; no guessed menu/heart state."""
from __future__ import annotations
import base64
import json
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if not __package__:
    if Path(__file__).resolve().parent.parent.name == "codex":
        sys.path.insert(0, str(ROOT.parents[min(2, len(ROOT.parents) - 1)] / "GameHub"))
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ddsaves._common import localize, select, ui, deck_home, empty, fact, finish, game_dirs, newest, num, proton_user

HERE = Path(__file__).resolve().parent
TABLE_PATH = HERE / "data/slay_the_spire.json"
if not TABLE_PATH.is_file():
    TABLE_PATH = HERE.parent / "data/slay_the_spire.json"
T = json.loads(TABLE_PATH.read_text(encoding="utf8"))


def decode(path):
    raw = Path(path).read_bytes().strip()
    if not raw.startswith(b"{"):
        raw = base64.b64decode(raw, validate=True)
        raw = bytes(v ^ b"key"[i % 3] for i, v in enumerate(raw))
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Expected JSON object")
    return value


def integer(value):
    try:
        return int(value) if not isinstance(value, bool) else None
    except (ValueError, TypeError):
        return None


def _paths(folder):
    folder = Path(folder)
    if folder.name in ["saves", "preferences"]:
        root = folder.parent
    else:
        root = folder
    saves = root / "saves" if (root / "saves").is_dir() else root
    prefs = root / "preferences" if (root / "preferences").is_dir() else root
    return saves, prefs


def find(path_or_dir=None):
    if path_or_dir is not None:
        path = Path(path_or_dir)
        if path.is_file():
            return path
        return path if path.is_dir() else None
    home = deck_home()
    roots = [Path(os.environ.get("USERPROFILE", str(Path.home()))) / "AppData/LocalLow/MegaCrit/SlayTheSpire",
             *game_dirs("SlayTheSpire"),
             home / ".config/SlayTheSpire",
             home / "Library/Application Support/SlayTheSpire"]
    roots += [p / "AppData/LocalLow/MegaCrit/SlayTheSpire" for p in proton_user(646570)]
    found = []
    for root in roots:
        if not root.is_dir():
            continue
        saves, prefs = _paths(root)
        markers = list(saves.glob("*.autosave")) + [p for p in prefs.glob("*STSData*") if not p.name.endswith(".backUp")]
        marker = newest(markers)
        if marker:
            found.append((marker.stat().st_mtime, root))
    return max(found, key=lambda x: x[0])[1] if found else None


def read(path_or_dir=None):
    T = localize(globals()["T"])
    path = find(path_or_dir)
    if path is None or not path.exists():
        return empty("Сохранение Slay the Spire не найдено")
    if path.is_file() and path.suffix == ".run":
        try:
            history = decode(path)
        except (OSError, ValueError) as error:
            return empty(str(error))
        return finish({"place": None, "chapter": None, "objective": None, "progress": {"history": history}, "facts": [], "proven": [], "unproven": ["history", "place", "chapter", "objective"]}, path)
    saves, prefs = _paths(path.parent if path.is_file() else path)
    active = path if path.is_file() and ".autosave" in path.name else newest(saves.glob("*.autosave"))
    # A leftover game backup cannot establish that a resumable run still exists.
    progress = {"current_run_present": active is not None, "profiles": {}}
    facts, proven = [], []
    unproven = ["current_run_present", "chapter", "objective", "best_completed_ascension", "heart_defeated"]
    place, slot, source = None, "", active
    if active:
        match = re.fullmatch(r"(?:(\d+)_)?([A-Z_]+)\.autosave(?:\.backUp)?", active.name)
        if not match:
            return empty("Неизвестное имя файла автосохранения")
        slot, char = (match[1] + "_" if match[1] else ""), match[2]
        try:
            save = decode(active)
        except (OSError, ValueError) as error:
            return empty(str(error))
        progress.update({k: integer(save.get(k)) for k in T["save_fields"] if k != "level_name"})
        progress.update({"character_id": char, "character": T["characters"].get(char, {}).get("name"), "level_name": save.get("level_name"), "source_is_backup": active.name.endswith(".backUp"), "save_raw": save})
        place = T["dungeons"].get(progress["level_name"])
        if place:
            proven.append("place")
        if progress["character"] and char in ["WATCHER", "THE_SILENT"]:
            facts.append(fact("sword", "Персонаж", progress["character"]))
            proven.append("character")
        else:
            unproven.append("character")
        if progress["act_num"] is not None and progress["floor_num"] is not None:
            facts.append(fact("flag", "Акт / этаж", f"{progress['act_num']} / {progress['floor_num']}"))
            proven += ["act_num", "floor_num"]
        if progress["current_health"] is not None and progress["max_health"] is not None:
            facts.append(fact("heart", "ОЗ", f"{progress['current_health']} / {progress['max_health']}"))
            proven += ["current_health", "max_health"]
        if progress["gold"] is not None:
            facts.append(fact("gem", "Золото", num(progress["gold"])))
            proven.append("gold")
        if progress["ascension_level"] is not None:
            facts.append(fact("star", T["labels"]["ascension"], progress["ascension_level"], id="ascension"))
            proven.append("ascension_level")
        unproven += ["seed", "play_time", "source_is_backup", "save_raw", "character_id", "level_name"]
    for char, entry in T["characters"].items():
        file = prefs / (slot + entry["prefs"])
        if not file.is_file():
            continue
        source = source or file
        try:
            raw = decode(file)
        except (OSError, ValueError) as error:
            progress.setdefault("errors", {})[str(file)] = str(error)
            continue
        progress["profiles"][char] = {"name": entry["name"], "wins": integer(raw.get(T["prefs_fields"]["wins"])), "ascension_unlocked": integer(raw.get(T["prefs_fields"]["ascension_unlocked"])), "raw": raw}
    profiles = progress["profiles"]
    wins = {c: p["wins"] for c, p in profiles.items() if p["wins"] is not None}
    asc = {c: p["ascension_unlocked"] for c, p in profiles.items() if p["ascension_unlocked"] is not None}
    if wins:
        progress["wins_by_character"] = wins
        facts.append(fact("trophy", T["labels"]["wins"], " · ".join(f"{profiles[c]['name']}: {v}" for c, v in wins.items()), id="wins"))
        proven.append("wins_by_character")
    if asc:
        progress["ascension_unlocked_by_character"] = asc
        facts.append(fact("star", "Открытое " + T["labels"]["ascension"], " · ".join(f"{profiles[c]['name']}: {v}" for c, v in asc.items()), id="unlocked_ascension"))
        proven.append("ascension_unlocked_by_character")
    unproven.append("profiles")
    if not place:
        unproven.append("place")
    if source is None:
        return empty("Нет автосохранения или статистики персонажа")
    return finish({"place": place, "chapter": None, "objective": None, "progress": progress, "facts": facts, "proven": proven, "unproven": unproven}, source)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf8")
    print(json.dumps(read(sys.argv[1] if len(sys.argv) > 1 else None), ensure_ascii=False, indent=2))
