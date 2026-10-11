"""Horizon Forbidden West save game reader for GGDS container saves.

Container format (GGDS):
  - Magic: b'GGDS' at offset 0x00 (4 bytes)
  - Version: uint32 at 0x04 (version 1)
  - Type ID: uint32 at 0x08 (0 for profile, 105182377 for regular saves)
  - Save file length: uint32 at 0x0c
  - Image file length: uint32 at 0x10
  - Title string: 128 bytes at 0x14..0x94 (null-terminated UTF-8)
      Format: "<Quest Name> - <Level> - <Play Time>"
  - Description string: 256 bytes at 0x94..0x194 (null-terminated UTF-8)
      Format: "<Save Type>" (e.g. Autosave / Quick Save / Manual Save / User Profile)
  - Decima save payload: save_file_len bytes at 0x194..0x194+save_file_len
  - Screenshot thumbnail: image_file_len bytes (PNG format)

Zero Cyrillic literals in code. No card keys.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import struct
import sys
from typing import Any, Dict, Optional, Union

ROOT = Path(__file__).resolve().parents[2]
DUMP_DIR = Path(__file__).resolve().parent / "data" / "horizon_forbidden_west"

_DATA: Optional[Dict[str, Any]] = None


def _load_data() -> Dict[str, Any]:
    global _DATA
    if _DATA is None:
        q_path = DUMP_DIR / "quests.json"
        st_path = DUMP_DIR / "save_types.json"
        loc_path = DUMP_DIR / "loc_ru.json"
        _DATA = {
            "quests": json.loads(q_path.read_text(encoding="utf-8"))["quests"] if q_path.exists() else [],
            "save_types": json.loads(st_path.read_text(encoding="utf-8"))["save_types"] if st_path.exists() else {},
            "loc_ru": json.loads(loc_path.read_text(encoding="utf-8")) if loc_path.exists() else {},
        }
    return _DATA


def _doc_dirs() -> list[Path]:
    try:
        sys.path.insert(0, str(ROOT / "GameHub"))
        from ddsaves._common import localize, select, ui, documents_dirs
        return list(documents_dirs())
    except Exception:
        dirs = []
        up = os.environ.get("USERPROFILE")
        if up:
            dirs.append(Path(up) / "Documents")
            dirs.append(Path(up) / "OneDrive" / "Documents")
        return [d for d in dirs if d.is_dir()]


def find_save(source: Optional[Union[str, Path]] = None) -> Optional[Path]:
    """Find a valid GGDS save file."""
    if source is not None:
        p = Path(source)
        if p.is_file():
            return p
        if p.is_dir():
            candidates = sorted(
                [f for f in p.glob("*.dat") if f.name.lower() != "profile.dat"],
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            )
            if candidates:
                return candidates[0]
            all_dat = sorted(p.glob("*.dat"), key=lambda x: x.stat().st_mtime, reverse=True)
            if all_dat:
                return all_dat[0]
        return None

    # Check documents directories
    for doc in _doc_dirs():
        hfw_base = doc / "Horizon Forbidden West Complete Edition"
        if hfw_base.exists():
            for user_dir in sorted(hfw_base.iterdir()):
                if user_dir.is_dir():
                    candidates = sorted(
                        [f for f in user_dir.glob("*.dat") if f.name.lower() != "profile.dat"],
                        key=lambda x: x.stat().st_mtime,
                        reverse=True,
                    )
                    if candidates:
                        return candidates[0]

    # Check Proton prefix
    home = os.environ.get("HOME")
    if home:
        proton_doc = (
            Path(home)
            / ".steam"
            / "steam"
            / "steamapps"
            / "compatdata"
            / "2420110"
            / "pfx"
            / "drive_c"
            / "users"
            / "steamuser"
            / "Documents"
            / "Horizon Forbidden West Complete Edition"
        )
        if proton_doc.exists():
            for user_dir in sorted(proton_doc.iterdir()):
                if user_dir.is_dir():
                    candidates = sorted(
                        [f for f in user_dir.glob("*.dat") if f.name.lower() != "profile.dat"],
                        key=lambda x: x.stat().st_mtime,
                        reverse=True,
                    )
                    if candidates:
                        return candidates[0]

    return None


def dump(path: Union[Path, str]) -> Dict[str, Any]:
    """Dump parsed Horizon Forbidden West save data from file or directory."""
    save_file = find_save(path)
    if not save_file or not save_file.exists():
        return {"has_save": False}

    try:
        with open(save_file, "rb") as f:
            header = f.read(0x194)
            if len(header) < 0x194:
                return {"has_save": False}

            magic, version, const_id, save_len, img_len = struct.unpack_from("<4sIIII", header, 0)
            if magic != b"GGDS":
                return {"has_save": False}

            title_raw = header[0x14:0x94].split(b"\x00")[0].decode("utf-8", errors="replace").strip()
            desc_raw = header[0x94:0x194].split(b"\x00")[0].decode("utf-8", errors="replace").strip()

            build_data = f.read(32)
            build_str = build_data.split(b"\x00")[0].decode("ascii", errors="replace") if build_data else None

        data = _load_data()
        quests = data.get("quests", [])
        save_types = data.get("save_types", {})

        # Parse title: "<Quest Name> - <Level> - <Play Time>"
        parts = title_raw.split(" - ")
        quest_name = parts[0].strip() if parts else None
        level = None
        play_time_sec = None
        play_time_str = None

        if len(parts) >= 3:
            quest_name = " - ".join(parts[:-2]).strip()
            lvl_match = re.search(r"(\d+)", parts[-2])
            if lvl_match:
                level = int(lvl_match.group(1))
            time_part = parts[-1].strip()
            t_split = time_part.split(":")
            if len(t_split) == 3:
                try:
                    h, m, s = int(t_split[0]), int(t_split[1]), int(t_split[2])
                    play_time_sec = h * 3600 + m * 60 + s
                    play_time_str = time_part
                except ValueError:
                    pass
        elif len(parts) == 2:
            quest_name = parts[0].strip()
            lvl_match = re.search(r"(\d+)", parts[1])
            if lvl_match:
                level = int(lvl_match.group(1))

        # Match quest metadata and region
        quest_id = None
        quest_order = None
        progress = None
        region_name = None
        for q in quests:
            candidates = [q.get("ru", "").lower(), q.get("en", "").lower()]
            for alias in q.get("aliases", []):
                candidates.append(alias.lower())
            if quest_name and quest_name.lower() in candidates:
                quest_id = q.get("id")
                quest_order = q.get("order")
                progress = q.get("progress")
                reg = q.get("region", {})
                region_name = reg.get("ru")
                break

        # Match save type key
        save_type_key = None
        for k, v in save_types.items():
            if desc_raw in (v.get("ru"), v.get("en")):
                save_type_key = k
                break

        return {
            "has_save": True,
            "save_path": str(save_file),
            "magic": magic.decode("ascii", errors="replace"),
            "version": version,
            "type_id": const_id,
            "save_size": save_len,
            "screenshot_size": img_len,
            "has_screenshot": img_len > 0,
            "save_title_raw": title_raw,
            "save_type_raw": desc_raw,
            "save_type_key": save_type_key,
            "quest_name": quest_name,
            "quest_id": quest_id,
            "quest_order": quest_order,
            "region_name": region_name,
            "aloy_level": level,
            "play_time_str": play_time_str,
            "play_time_seconds": play_time_sec,
            "story_progress": progress,
            "build_string": build_str,
        }
    except Exception:
        return {"has_save": False}


def read(source: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Read Horizon Forbidden West save data."""
    if source is None:
        save_file = find_save(None)
        if not save_file:
            return {"has_save": False}
        return dump(save_file)
    return dump(source)
