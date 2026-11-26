"""Graveyard Keeper 2 (appid 4358690): read-only, stdlib reader for the save metadata sidecar.

Each slot writes two files next to each other: ``<slot>.dat`` (binary Unity/C# world state,
~12 MB) and ``<slot>.info`` (small JSON written by the game). Only the ``.info`` sidecar is
parsed here; the ``.dat`` is never opened.

Proof (4 stages of one playthrough, see proof.md): ``day`` grows 110 -> 111 -> 113 -> 114 and
``saveDateTime`` changes with it. ``graveyardQuality``, ``churchQuality``, ``villageRep`` and
``townCitizens`` were constant across all stages and therefore stay unproven and hidden.
"""
from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path

try:
    from ddsaves._common import proton_user, newest, read_bytes
except ImportError:  # pragma: no cover - the proof gate always exposes plugin/py_modules
    proton_user = None

    def newest(paths):
        best = None
        for p in paths:
            if p.is_file() and (best is None or p.stat().st_mtime > best.stat().st_mtime):
                best = p
        return best

    def read_bytes(path):
        return Path(path).read_bytes()

APPID = 4358690
SUB = "AppData/LocalLow/Lazy Bear Games/Graveyard Keeper 2"
INFO_GLOB = "*.info"
TIME_FORMAT = "%m/%d/%Y %I:%M:%S %p"


def _empty() -> dict:
    return {"place": None, "chapter": None, "objective": None, "progress": {},
            "facts": [], "proven": [], "unproven": [], "fact_sources": {}}


def _candidate_dirs() -> list:
    out = []
    if os.environ.get("USERPROFILE"):
        out.append(Path(os.environ["USERPROFILE"]) / SUB)
    if proton_user is not None:
        out.extend(p / SUB for p in proton_user(APPID))
    return out


def find(path_or_dir=None):
    if path_or_dir is not None:
        p = Path(path_or_dir)
        if p.is_file():
            return p
        if p.is_dir():
            return newest(p.glob(INFO_GLOB)) or newest(p.rglob(INFO_GLOB))
        return None
    for folder in _candidate_dirs():
        found = newest(folder.glob(INFO_GLOB))
        if found:
            return found
    return None


def _parse_time(text):
    try:
        return datetime.strptime(str(text), TIME_FORMAT).timestamp()
    except (TypeError, ValueError):
        return None


def read(path_or_dir=None) -> dict:
    path = find(path_or_dir)
    if path is None:
        return _empty()
    try:
        info = json.loads(read_bytes(path).decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return _empty()
    if not isinstance(info, dict):
        return _empty()
    day = info.get("day")
    if not isinstance(day, int) or isinstance(day, bool):
        return _empty()
    saved_at = _parse_time(info.get("saveDateTime"))
    progress = {
        "day": day,
        "saved_at": saved_at,
        "is_autosave": info.get("isAutoSave") is True,
        "game_save_version": info.get("gameSaveVersion"),
        "graveyard_quality": info.get("graveyardQuality"),
        "church_quality": info.get("churchQuality"),
        "village_rep": info.get("villageRep"),
        "town_citizens": info.get("townCitizens"),
    }
    facts = [{"id": "day", "icon": "day", "value": str(day)}]
    out = _empty()
    out.update({
        "progress": progress,
        "facts": facts,
        "proven": ["day", "saved_at"],
        "unproven": ["graveyard_quality", "church_quality", "village_rep", "town_citizens",
                     "is_autosave", "game_save_version"],
        "fact_sources": {"day": "day"},
        "observed_at": saved_at if saved_at is not None else path.stat().st_mtime,
        "source_path": str(path),
    })
    return out


if __name__ == "__main__":
    import sys
    print(json.dumps(read(sys.argv[1] if len(sys.argv) > 1 else None), ensure_ascii=False, indent=2))
