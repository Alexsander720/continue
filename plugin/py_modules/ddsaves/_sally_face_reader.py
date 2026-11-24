"""Data-only Sally Face AC.SaveData/AC.OptionsData reader (standard library)."""
from __future__ import annotations
import sys
import struct
from pathlib import Path

from ddsaves import _nrbf

SAVE_NAME = "SallyFaceGameSave_0.save"
PREFS_NAME = "AC_SallyFaceGameSave_0.prefs"
ACH_IDS = {str(x) for x in [24,25,26,27,29,30,31,45,46,47,48,49,50,51,64,65,66,67,68,69,70,96,97,98,99,100,101,102,112,113,114,115,116,117,118]}


def variable_map(text):
    if not isinstance(text, str):
        raise ValueError("AC variable data must be a string")
    return dict(item.split(":", 1) for item in text.split("|") if ":" in item and item.split(":", 1)[0].isdigit())


def _split_ac_string(raw_value):
    text, sep, line = raw_value.rpartition(":")
    has_id = bool(sep and line and line.isascii()
                  and (line.isdecimal() or line.startswith("-") and line[1:].isdecimal()))
    clean = text.strip() if has_id else raw_value.strip()
    speech_id = int(line) if has_id else None
    return clean, (speech_id if speech_id is not None and speech_id >= 0 else None)


def decode_save(path):
    target = Path(path)
    if target.is_symlink():
        raise ValueError("Symlinked save files are not supported")
    if target.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Save exceeds the supported size bound")
    return decode_save_bytes(target.read_bytes())


def decode_save_bytes(blob):
    """Validate the complete shipped SaveData || scene-cache file.

    The shared NRBF decoder intentionally reads only the first stream. Using it
    on the whole file would silently accept a paused write in the scene cache.
    All genuine research saves use this two-stream layout; other layouts
    remain unsupported rather than being accepted as historical stages.
    """
    if len(blob) > 16 * 1024 * 1024:
        raise ValueError("Save exceeds the supported size bound")
    parts = blob.split(b"||")
    if len(parts) != 2 or not all(parts):
        raise ValueError("Expected SaveData and complete scene-cache streams")
    obj = _nrbf.decode(parts[0])
    if not isinstance(obj, dict) or obj.get("__class__") != "AC.SaveData":
        raise ValueError("Not AC.SaveData")
    levels = _nrbf.decode(b"Binary" + parts[1])
    if not isinstance(levels, dict) or not levels.get("__class__", "").startswith(
            "System.Collections.Generic.List`1[[AC.SingleLevelData,"):
        raise ValueError("Not an AC.SingleLevelData list")
    items, size = levels.get("_items"), levels.get("_size")
    if not isinstance(items, list) or type(size) is not int or not 0 <= size <= len(items):
        raise ValueError("Invalid scene-cache list")
    if any(not isinstance(item, dict) or item.get("__class__") != "AC.SingleLevelData"
           for item in items[:size]):
        raise ValueError("Invalid scene-cache entry")
    return obj


def _parse_save(path):
    return _state_from_obj(decode_save(path))


def _state_from_obj(obj):
    main = obj["mainData"]
    player_list = obj["playerData"]
    if not isinstance(main, dict) or not isinstance(player_list, dict):
        raise ValueError("Invalid AC main or player data")
    items, size = player_list.get("_items"), player_list.get("_size")
    if not isinstance(items, list) or type(size) is not int or not 0 <= size <= len(items):
        raise ValueError("Invalid AC player list bounds")
    players = items[:size]
    selected = [p for p in players if isinstance(p, dict) and p.get("playerID") == main["currentPlayerID"]]
    if len(selected) != 1:
        raise ValueError("Active player is missing or ambiguous")
    player = selected[0]
    scene_name = player.get("currentSceneName")
    scene_id = player.get("currentScene")
    if not isinstance(scene_name, str) or not scene_name:
        raise ValueError("Invalid AC currentSceneName")
    if type(scene_id) is not int or scene_id < 0:
        raise ValueError("Invalid AC currentScene")
    variables = variable_map(main["runtimeVariablesData"])
    inventory = []
    inventory_text = player.get("inventoryData", "")
    if not isinstance(inventory_text, str):
        raise ValueError("AC inventory data must be a string")
    for pair in inventory_text.split("|"):
        if not pair:
            continue
        parts = pair.split(":")
        if len(parts) != 2:
            raise ValueError("Unsupported AC inventory instance encoding")
        iid, quantity = map(int, parts)
        if iid < 0 or quantity <= 0:
            raise ValueError("Invalid AC inventory quantity")
        inventory.append(dict(id=iid, quantity=quantity))
    raw_version = variables.get("71")
    game_version = None
    if isinstance(raw_version, str) and raw_version:
        clean_version, _ = _split_ac_string(raw_version)
        game_version = clean_version or None
    result = dict(scene_name=scene_name, scene_id=scene_id,
                  previous_scene_name=player.get("previousSceneName"), previous_scene_id=player.get("previousScene"),
                  active_player_id=main["currentPlayerID"], game_version=game_version,
                  variables=variables, inventory=inventory,
                  inventory_count=sum(i["quantity"] for i in inventory))
    goal = variables.get("23")
    if goal:
        goal_text, speech_id = _split_ac_string(goal)
        result["goal"] = goal_text
        result["goal_speech_id"] = speech_id
    for field, vid in [("current_floor", "10"), ("room_number", "3"), ("puzzle1", "41"),
                       ("puzzle2", "42"), ("puzzle3", "43"), ("seals", "44")]:
        value = variables.get(vid)
        if value is not None:
            try:
                value = int(value)
            except ValueError:
                pass
            result[field] = value
    return result


def decode_prefs_bytes(blob):
    if len(blob) > 1024 * 1024:
        raise ValueError("Profile exceeds the supported size bound")
    obj = _nrbf.decode(blob)
    if not isinstance(obj, dict) or obj.get("__class__") != "AC.OptionsData":
        raise ValueError("Not AC.OptionsData")
    variable_map(obj.get("linkedVariables", ""))
    return obj


def _parse_prefs(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Symlinked profile files are not supported")
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("Profile exceeds the supported size bound")
    obj = decode_prefs_bytes(path.read_bytes())
    linked = variable_map(obj.get("linkedVariables", ""))
    return dict(linked_variables=linked,
                menu_episode_number=linked.get("32"),
                achievement_flags_set=sum(linked.get(vid) == "1" for vid in ACH_IDS))


def dump(path):
    path = Path(path)
    is_dir = path.is_dir()
    folder = path if is_dir else path.parent
    save = folder / SAVE_NAME if is_dir else path
    # Only pair AC_SallyFaceGameSave_0.prefs when reading a folder or the matching slot 0 save.
    prefs = (folder / PREFS_NAME) if (is_dir or path.name == SAVE_NAME) else None
    result = {}
    if save.is_file():
        try:
            result["progress"] = _parse_save(save)
        except (ValueError, KeyError, TypeError, OSError, IndexError, OverflowError, struct.error, RecursionError) as error:
            result["save_error"] = type(error).__name__ + ": " + str(error)
    if prefs is not None and prefs.is_file():
        try:
            result["profile"] = _parse_prefs(prefs)
        except (ValueError, KeyError, TypeError, OSError, IndexError, OverflowError, struct.error, RecursionError) as error:
            result["profile_error"] = type(error).__name__ + ": " + str(error)
    return result
