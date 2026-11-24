"""Sally Face (541570): эпизод, цель, предметы и достижения эпизода из сейва (Claude, 04.11.2026).

Источник — `SallyFaceGameSave_0.save` (Adventure Creator, BinaryFormatter) + `AC_SallyFaceGameSave_0.prefs`;
названия — из файлов игры (ddsaves/data/sally_face.json, генератор deep_dig/tools/sally_face_hub_table.py).

Статус «прочитано из сейва», НЕ «доказано по трём этапам» (правило deep_dig): эпизод/сцена/цель/предметы — прямое чтение
полей и таблиц игры, подтверждены двумя этапами одного прохождения; счётчики Seals/F/Puzzle/J/K игра переиспользует в
каждом эпизоде — они сюда не попадают. Достижения: флаг ACH* в .prefs ≡ разблокировка в Steam (11 из 11 совпало 04.11).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from ddsaves import _sally_face_reader as reader
from ddsaves._common import deck_home, empty, fact, finish, newest, proton_user

APPID = 541570
SUB = Path("AppData/LocalLow/Steve Gabry/Sally Face")
TABLE = Path(__file__).resolve().parent / "data/sally_face.json"
UNPROVEN = ["seals", "secrets", "mini_games", "episode_completion_percent"]
# 04.11.2026 решение Alex («да, логично»): прямые чтения полей показываем сейчас, счётчики Seals/F/J/K — после 3 этапов.
# Хаб (hub_cards) выводит на карточку только поля из proven.
PROVEN = ["chapter", "objective", "episode", "inventory", "inventory_count", "achievements_unlocked",
          "achievements_total", "episode_achievements_left", "episode_achievements_total",
          "episode_achievements_left_count", "fact_rows"]


def find(path_or_dir=None):
    if path_or_dir is not None:
        path = Path(path_or_dir)
        return path / reader.SAVE_NAME if path.is_dir() else path
    dirs = []
    if os.environ.get("USERPROFILE"):
        dirs.append(Path(os.environ["USERPROFILE"]) / SUB)
    dirs.append(deck_home() / ".config/unity3d/Steve Gabry/Sally Face")   # нативный Linux-билд на Деке
    dirs.extend(user / SUB for user in proton_user(APPID))
    return newest(d / reader.SAVE_NAME for d in dirs)


def _item_icons():
    try:
        doc = json.loads((TABLE.parent / "sally_face_icons/index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: "ddsaves/data/sally_face_icons/" + v["file"] for k, v in doc["items"].items()}


def _t(row, lang):
    return row["en"] if lang == "en" else row["ru"]


def read(path_or_dir=None):
    path = find(path_or_dir)
    if path is None or path.is_symlink() or not path.is_file():
        return empty("Sally Face: файл сохранения не найден")
    parsed = reader.dump(path)
    state = parsed.get("progress")
    if not state:
        return finish(empty("Sally Face: сохранение не расшифровано"), path)
    data = json.loads(TABLE.read_text(encoding="utf-8"))
    lang = "en" if os.environ.get("CONTINUE_LANG", "ru").strip().lower() == "en" else "ru"   # UK в игре нет
    scene = data["scenes"].get(str(state["scene_id"]))
    episode = scene["episode"] if scene and scene["name"] == state["scene_name"] else None
    ep_row = data["episodes"].get(str(episode)) if episode else None
    goal_row = data["goals"].get(str(state.get("goal_speech_id")))
    items = []
    for it in state["inventory"]:
        row = data["items"].get(str(it["id"]))
        if row:
            items.append(_t(row, lang) if it["quantity"] == 1 else f"{_t(row, lang)} ×{it['quantity']}")
    out = empty()
    # «Глава» отдельно не отдаём: её название уже в «месте» (Эпизод 4 · Суд) — иначе на карточке повтор (06.11.2026)
    # В игре нет названий локаций (только имена сцен вроде 04_F3), поэтому «где остановился» = эпизод + его название из строк игры
    if ep_row:
        out["place"] = (f"Эпизод {episode} · " if lang == "ru" else f"Episode {episode} · ") + _t(ep_row, lang)
    out["objective"] = _t(goal_row, lang) if goal_row and _t(goal_row, lang) != "???" else None
    prog = dict(episode=episode, scene_name=state["scene_name"], game_version=state.get("game_version"),
                goal_speech_id=state.get("goal_speech_id"), inventory=items, inventory_count=len(items))
    facts = []
    if ep_row:
        facts.append(fact("flag", "Эпизод" if lang == "ru" else "Episode", f"{episode} · {_t(ep_row, lang)}", id="episode"))
    flags = (parsed.get("profile") or {}).get("linked_variables") or {}
    if flags:
        unlocked = {str(a["var"]) for a in data["achievements"] if flags.get(str(a["var"])) == "1"}
        total = len(data["achievements"])
        prog.update(achievements_unlocked=len(unlocked), achievements_total=total)
        facts.append(fact("trophy", "Достижения" if lang == "ru" else "Achievements", f"{len(unlocked)} / {total}", id="achievements"))
        if episode:
            here = [a for a in data["achievements"] if a["episode"] == episode]
            left = [a for a in here if str(a["var"]) not in unlocked]
            prog["episode_achievements_left"] = [dict(api=a["api"], name=a["ru"] if lang == "ru" else a["en"],
                                                      condition=a["ru_desc"] if lang == "ru" else a["en_desc"]) for a in left]
            prog["episode_achievements_total"] = len(here)
            prog["episode_achievements_left_count"] = len(left)
    # Одна «стеклянная» панель как на макете C (06.11.2026): слева достижения N/M с полосой, справа — значки достижений
    # эпизода и предметы в кармане. Серые иконки Steam подставляет витрина по ach_key, предметы — из файлов игры.
    groups = []
    left = prog.get("episode_achievements_left")
    if episode and left is not None:
        n = len(left)
        if lang == "ru":
            label = f"Осталось в эпизоде · {n}" if n else "Эпизод: все достижения"
        else:
            label = f"Left this episode · {n}" if n else "Episode: all achievements"
        groups.append(dict(kind="ach", label=label,
                           people=[dict(key=a["api"], name=a["name"], ach_key=a["api"]) for a in left]))
    icons = _item_icons()
    pocket = [dict(key=f"item:{it['id']}", name=(_t(data["items"][str(it["id"])], lang) + (f" ×{it['quantity']}" if it["quantity"] > 1 else "")),
                   icon_rel=icons.get(str(it["id"]))) for it in state["inventory"] if str(it["id"]) in data["items"]]
    if pocket:
        groups.append(dict(kind="items", label=(f"В кармане · {len(pocket)}" if lang == "ru" else f"In pocket · {len(pocket)}"), people=pocket))
    if groups:
        row = dict(id="sf_panel", groups=groups, label="Достижения" if lang == "ru" else "Achievements",
                   ach_got=prog.get("achievements_unlocked"), ach_total=prog.get("achievements_total"))
        prog["fact_rows"] = [row]
        facts.append(dict(id="sf_panel", groups=groups))
    out.update(progress=prog, facts=facts,
               proven=list(PROVEN), unproven=list(UNPROVEN), evidence_status="read_from_save")
    return finish(out, path)


if __name__ == "__main__":
    import sys
    print(json.dumps(read(sys.argv[1] if len(sys.argv) > 1 else None), ensure_ascii=False, indent=2))
