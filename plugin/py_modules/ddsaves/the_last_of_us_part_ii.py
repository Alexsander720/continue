"""The Last of Us Part II Remastered (appid 2531310), proven slot metadata.

The game writes the chapter text and a compact descriptor tag to both
``params.json`` and ``USR-DATA``.  Only values that agree between those two
game-written representations are exposed: chapter, collectibles and save
time.  Chapter percentage and any inferred collectible total are excluded.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import List, Optional, Union

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from _card import Facts, empty, finish
from ddsaves._common import documents_dirs, proton_user, read_bytes

APPID = 2531310
DESC_OFFSET = 0x05A4
DESC_END = 0x1000
TAG = re.compile(r"\[([0-9A-Fa-f]{24})\]")


def default_dirs() -> List[Path]:
    roots: List[Path] = []
    for documents in documents_dirs():
        base = documents / "The Last of Us Part II"
        if base.is_dir():
            roots.extend(path / "savedata" for path in base.iterdir()
                         if path.is_dir() and (path / "savedata").is_dir())
    for user in proton_user(APPID):
        base = user / "Documents/The Last of Us Part II"
        if base.is_dir():
            roots.extend(path / "savedata" for path in base.iterdir()
                         if path.is_dir() and (path / "savedata").is_dir())
    return roots


def _story_slot(path: Path) -> bool:
    name = path.name.upper()
    return name.startswith("SAVEFILE") and not name.startswith("SAVEFILER") and not name.endswith(("0P", "1P", "PROFILE"))


def find(path_or_dir: Optional[Union[Path, str]] = None) -> List[Path]:
    if path_or_dir is not None:
        path = Path(path_or_dir)
        if path.is_file():
            roots = ([path.parent] if path.name in ("params.json", "USR-DATA")
                     and _story_slot(path.parent) else [])
        elif path.is_dir() and _story_slot(path):
            roots = [path]
        elif path.is_dir():
            roots = [slot for slot in path.glob("SAVEFILE*") if slot.is_dir() and _story_slot(slot)]
        else:
            roots = []
    else:
        roots = [slot for root in default_dirs() for slot in root.glob("SAVEFILE*")
                 if slot.is_dir() and _story_slot(slot)]
    return sorted(roots, key=lambda slot: (slot / "USR-DATA").stat().st_mtime
                  if (slot / "USR-DATA").is_file() else 0, reverse=True)


def _tag(text: str) -> Optional[dict]:
    match = TAG.search(text)
    if not match:
        return None
    raw = bytes.fromhex(match.group(1))
    flags = int.from_bytes(raw[4:6], "big")
    if raw[0] != 2 or flags not in (0x0000, 0x0004, 0x000C):
        return None
    return {
        "raw": match.group(1).upper(),
        "collected": int.from_bytes(raw[6:8], "big"),
        "play_seconds": int.from_bytes(raw[8:12], "big"),
    }


def _descriptor(text: str) -> Optional[dict]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    visible = [line for line in lines if not line.startswith("[")]
    parsed_tag = _tag(text)
    if not visible or parsed_tag is None:
        return None
    return {"chapter": visible[0], **parsed_tag}


def _slot(path: Path) -> Optional[dict]:
    params = path / "params.json"
    data_file = path / "USR-DATA"
    try:
        document = json.loads(params.read_text(encoding="utf-8"))
        raw = read_bytes(data_file)
    except (OSError, UnicodeError, ValueError):
        return None
    if not isinstance(document, dict) or len(raw) < DESC_END:
        return None
    json_text = document.get("detail")
    if not isinstance(json_text, str):
        return None
    try:
        binary_text = raw[DESC_OFFSET:DESC_END].split(b"\0", 1)[0].decode("utf-8", "strict")
    except UnicodeError:
        return None
    if json_text != binary_text:
        return None
    return _descriptor(json_text)


def read(path_or_dir: Optional[Union[Path, str]] = None) -> dict:
    try:
        return _read(path_or_dir)
    except Exception as e:
        return empty(f"Сохранение The Last of Us Part II не прочитано: {e}")


def _read(path_or_dir: Optional[Union[Path, str]] = None) -> dict:
    target = None
    parsed = None
    for slot in find(path_or_dir):
        parsed = _slot(slot)
        if parsed is not None:
            target = slot / "USR-DATA"
            break
    if target is None or parsed is None:
        return empty("Не найдено согласованное сюжетное сохранение The Last of Us Part II")

    hours, minutes = divmod(parsed["play_seconds"] // 60, 60)
    facts = Facts()
    facts.sfact("collected", "gem", "Находки", parsed["collected"])
    facts.sfact("play_time_seconds", "clock", "В этом сейве", f"{hours}:{minutes:02d}")
    out = {
        "place": parsed["chapter"],
        "chapter": parsed["chapter"],
        "objective": None,
        "progress": {
            "collected": parsed["collected"],
            "play_time_seconds": parsed["play_seconds"],
        },
        "facts": facts.items,
        "fact_sources": facts.sources,
        "proven": ["place", "chapter", "collected", "play_time_seconds"],
        "unproven": [
            "chapter_percent", "collectibles_total", "chapter_id", "difficulty",
            "completed_acts_count", "milestones_count",
        ],
        "descriptor_tag": parsed["raw"],
    }
    return finish(out, target)
