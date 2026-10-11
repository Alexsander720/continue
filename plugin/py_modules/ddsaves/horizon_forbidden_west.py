"""Horizon Forbidden West (appid 2420110): game-written GGDS slot caption.

The fixed GGDS header stores ``<quest> - <level> - <play time>`` in the
language used by the game.  No inferred quest/region table is used here.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import struct
import sys
from typing import List, Optional, Union

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from _card import Facts, empty, finish
from ddsaves._common import documents_dirs, proton_user

APPID = 2420110
HEADER_SIZE = 0x194
SAVE_TYPE_ID = 105182377


def default_dirs() -> List[Path]:
    roots: List[Path] = []
    for doc in documents_dirs():
        base = doc / "Horizon Forbidden West Complete Edition"
        if base.is_dir():
            roots.extend(p for p in base.iterdir() if p.is_dir())
    for user in proton_user(APPID):
        base = user / "Documents/Horizon Forbidden West Complete Edition"
        if base.is_dir():
            roots.extend(p for p in base.iterdir() if p.is_dir())
    return roots


def find(path_or_dir: Optional[Union[Path, str]] = None) -> List[Path]:
    if path_or_dir is not None:
        path = Path(path_or_dir)
        if path.is_file():
            return [path]
        roots = [path] if path.is_dir() else []
    else:
        roots = default_dirs()
    files = [file for root in roots for file in root.glob("*.dat")
             if file.name.lower() != "profile.dat"]
    return sorted(files, key=lambda file: file.stat().st_mtime, reverse=True)


def _text(raw: bytes, start: int, end: int) -> Optional[str]:
    field = raw[start:end]
    value, separator, _ = field.partition(b"\0")
    if not separator:
        return None
    try:
        return value.decode("utf-8").strip()
    except UnicodeDecodeError:
        return None


def _level(value: str) -> Optional[int]:
    patterns = (
        r"(?i)^level\s+(\d+)$",
        r"(?i)^(\d+)(?:st|nd|rd|th)\s+level$",
        r"^(\d+)-(?:й|я|е)\s+уровень$",
        r"^(\d+)-(?:й|ша|ге)\s+рівень$",
        r"^Рівень\s+(\d+)$",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, value.strip())
        if match:
            return int(match.group(1))
    return None


def _play_time(value: str) -> Optional[int]:
    match = re.fullmatch(r"(\d+):(\d{2}):(\d{2})", value.strip())
    if not match:
        return None
    hours, minutes, seconds = map(int, match.groups())
    if minutes >= 60 or seconds >= 60:
        return None
    return hours * 3600 + minutes * 60 + seconds


def _slot(path: Path) -> Optional[dict]:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if len(raw) < HEADER_SIZE:
        return None
    magic, version, type_id, payload_size, image_size = struct.unpack_from("<4sIIII", raw)
    if magic != b"GGDS" or version != 1 or type_id != SAVE_TYPE_ID:
        return None
    if HEADER_SIZE + payload_size + image_size != len(raw):
        return None
    caption = _text(raw, 0x14, 0x94)
    description = _text(raw, 0x94, 0x194)
    if not caption:
        return None
    parts = caption.rsplit(" - ", 2)
    if len(parts) != 3 or not parts[0].strip():
        return None
    quest, level_text, time_text = (part.strip() for part in parts)
    play_time_seconds = _play_time(time_text)
    return {
        "quest": quest,
        "caption": caption,
        "description": description,
        "level": _level(level_text),
        "play_time_seconds": play_time_seconds,
        "play_time_text": time_text if play_time_seconds is not None else None,
    }


def read(path_or_dir: Optional[Union[Path, str]] = None) -> dict:
    candidates = find(path_or_dir)
    target = None
    parsed = None
    for candidate in candidates:
        parsed = _slot(candidate)
        if parsed is not None:
            target = candidate
            break
    if target is None or parsed is None:
        return empty("Не найдено корректное сохранение Horizon Forbidden West")

    progress = {}
    proven = ["place", "chapter", "save_title_raw"]
    facts = Facts()
    if parsed["level"] is not None:
        progress["aloy_level"] = parsed["level"]
        facts.sfact("aloy_level", "hero", "Уровень", parsed["level"])
        proven.append("aloy_level")
    if parsed["play_time_seconds"] is not None:
        progress["play_time_seconds"] = parsed["play_time_seconds"]
        facts.sfact("play_time_seconds", "clock", "В этом сейве", parsed["play_time_text"])
        proven.append("play_time_seconds")

    out = {
        "place": parsed["quest"],
        "chapter": parsed["quest"],
        "objective": None,
        "progress": progress,
        "save_title_raw": parsed["caption"],
        "save_type_raw": parsed["description"],
        "facts": facts.items,
        "fact_sources": facts.sources,
        "proven": proven,
        "unproven": [
            "story_progress", "quest_order", "region_name", "skills_unlocked",
            "tallnecks_overridden", "cauldrons_completed", "datapoints_collected",
        ],
    }
    return finish(out, target)
