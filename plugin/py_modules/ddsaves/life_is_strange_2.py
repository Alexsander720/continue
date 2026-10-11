"""Life is Strange 2 (appid 532210) card parser.

Save: DONTNOD GEVASEND format (zlib-compressed UE4 GVAS savegames).
Names come from antigravity/dumps/life_is_strange_2/ (episodes.json, chapters.json, loc_ru.json).

Fields:
  place: Russian episode title from episodes.json («Дороги», «Правила», «Глушь», «Вера», «Волки»)
  chapter: Russian chapter (subcontext) title from chapters.json
  objective: Checkpoint name if available, else None
  progress: percentage based on completed episodes (20..100%)
  episode: current episode number (1..5)
  episodes_completed: count of finished episodes (1..5)
  collectibles_count: optional souvenirs found in current context (0..10)
  journal_pages: diary pages seen by Sean (0..98)
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Union

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from _card import Facts, empty, finish
from ddsaves._common import localize, select, ui, newest, proton_user

_reader_path = HERE / "_ag_life_is_strange_2_reader.py"
_spec = importlib.util.spec_from_file_location("agreader_life_is_strange_2", _reader_path)
reader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reader)

APPID = 532210


def default_dirs() -> List[Path]:
    roots: List[Path] = []
    if os.environ.get("LOCALAPPDATA"):
        base = Path(os.environ["LOCALAPPDATA"]) / "Dontnod"
        if base.is_dir():
            for user_dir in base.iterdir():
                cand = user_dir / "LIS2/Saved/SaveGames"
                if cand.is_dir():
                    roots.append(cand)
    for p in proton_user(APPID):
        base = p / "AppData/Local/Dontnod"
        if base.is_dir():
            for user_dir in base.iterdir():
                cand = user_dir / "LIS2/Saved/SaveGames"
                if cand.is_dir():
                    roots.append(cand)
    return roots


def find(path_or_dir: Optional[Union[Path, str]] = None) -> List[Path]:
    if path_or_dir:
        p = Path(path_or_dir)
        if p.is_file():
            return [p]
        if p.is_dir():
            files = sorted(p.rglob("GameSave_Slot*.sav"), key=lambda f: f.stat().st_mtime, reverse=True)
            if not files:
                files = sorted(p.rglob("*.sav"), key=lambda f: f.stat().st_mtime, reverse=True)
            return files
        return []

    found = []
    for d in default_dirs():
        files = sorted(d.glob("GameSave_Slot*.sav"), key=lambda f: f.stat().st_mtime, reverse=True)
        found.extend(files)
    return found


def read(path_or_dir: Optional[Union[Path, str]] = None) -> dict:
    files = find(path_or_dir)
    if not files:
        return empty("Файлы сохранений Life is Strange 2 не найдены")

    target = files[0]
    parsed = reader.dump(target)
    if not parsed.get("has_save"):
        return empty("Не удалось прочитать сохранение Life is Strange 2")

    place = parsed.get("episode_title")
    chapter = parsed.get("story_chapter")
    objective = None

    episode = parsed.get("episode_num")
    episodes_completed = parsed.get("episodes_completed", 0)
    collectibles_count = parsed.get("collectibles_count", 0)
    journal_pages = parsed.get("journal_pages", 0)
    game_progress = parsed.get("game_progress", 0)
    brotherhood = parsed.get("brotherhood")
    morality = parsed.get("morality")

    progress = {
        "story_chapter": chapter,
        "episode": episode,
        "episodes_completed": episodes_completed,
        "collectibles_count": collectibles_count,
        "journal_pages": journal_pages,
        "game_progress": game_progress,
        "brotherhood": brotherhood,
        "morality": morality,
    }

    F = Facts()
    if episode is not None:
        F.sfact("episode", "book", "Эпизод", f"{episode}/5")
    if episodes_completed is not None:
        F.sfact("episodes_completed", "check", "Пройдено эпизодов", f"{episodes_completed}/5")
    F.sfact("collectibles_count", "star", "Сувениры", f"{collectibles_count}/30")
    F.sfact("journal_pages", "pencil", "Страницы дневника", str(journal_pages))
    if brotherhood is not None:
        F.sfact("brotherhood", "heart", "Отношения братьев", f"{brotherhood:+d}")
    if morality is not None:
        F.sfact("morality", "shield", "Мораль Даниэля", f"{morality:+d}")

    proven = [
        "episode",
        "episodes_completed",
        "journal_pages",
        "collectibles_count",
        "game_progress",
    ]
    if chapter is not None:
        proven.append("chapter")
    if place is not None:
        proven.append("place")
    if brotherhood is not None:
        proven.append("brotherhood")
    if morality is not None:
        proven.append("morality")

    out = {
        "place": place,
        "chapter": chapter,
        "objective": objective,
        "progress": progress,
        "facts": F.items,
        "fact_sources": F.sources,
        "proven": proven,
        "unproven": [
            "drawings_count",
            "recap_choices",
        ],
        "nonmonotonic": {
            "collectibles_count": "Sean's backpack and souvenirs were confiscated in Episode 4 hospital",
            "brotherhood": "Relationship score between Sean and Daniel changes dynamically based on player choices",
            "morality": "Daniel's morality score changes dynamically based on Sean's education and choices",
        },
    }
    return finish(out, target)
