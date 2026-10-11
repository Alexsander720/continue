"""Life is Strange 2 save game reader for GameSave_Slot*.sav files.

Container format:
  - Header: GEVASEND magic (8 bytes) + uncompressed length (uint32 at 0x45)
  - Data: zlib-compressed UE4 GVAS property stream starting at offset 0x4A
  - Structure:
      * Magic: _2S_SIL_
      * HeaderSaveData (StructProperty: LIS2GameSaveHeaderData):
          - EpisodeNumber (IntProperty: 1..5)
          - EpisodeName (TextProperty: localization key)
          - SubContextName (TextProperty: localization key)
          - SubContextId (NameProperty: e.g. E1_9A, E5_9D)
          - CheckpointName (NameProperty or None)
          - bGameStarted (BoolProperty)
      * StatsSaveData (StructProperty: LIS2StatsSaveData):
          - EpisodeCompletion (ArrayProperty of BoolProperty: 5 elements)
      * CurrentSubContextSaveData (StructProperty: LIS2CheckpointSaveData):
          - CollectiblesSaveData: Items (Array of LIS2CollectiblesSaveDataItem)
      * JournalSaveData (StructProperty: LIS2MetaInventoryJournalSaveData):
          - SeenPages (Array of Guid)

No Cyrillic string literals. No card keys.
"""
from __future__ import annotations

import json
from pathlib import Path
import struct
from typing import Any, Dict, Optional, Union
import zlib
from ddsaves._common import localize, select, ui

ROOT = Path(__file__).resolve().parents[2]
DUMPS_DIR = Path(__file__).resolve().parent / "data" / "life_is_strange_2"

_DATA: Optional[Dict[str, Any]] = None


MAX_DECOMPRESSED_BYTES = 64 * 1024 * 1024


def _decompress_save(data):
    inflater = zlib.decompressobj()
    payload = inflater.decompress(data, MAX_DECOMPRESSED_BYTES + 1)
    if len(payload) > MAX_DECOMPRESSED_BYTES or inflater.unconsumed_tail:
        raise ValueError("Save exceeds decompressed size limit (64 MiB)")
    if not inflater.eof:
        raise ValueError("Incomplete compressed save")
    return payload


def _load_data() -> Dict[str, Any]:
    global _DATA
    if _DATA is None:
        ep_p = DUMPS_DIR / "episodes.json"
        ch_p = DUMPS_DIR / "chapters.json"
        col_p = DUMPS_DIR / "collectibles.json"
        _DATA = {
            "episodes": json.loads(ep_p.read_text(encoding="utf-8"))["data"] if ep_p.exists() else {},
            "chapters": json.loads(ch_p.read_text(encoding="utf-8"))["data"] if ch_p.exists() else {},
            "collectibles": json.loads(col_p.read_text(encoding="utf-8"))["data"] if col_p.exists() else {},
        }
    return localize(_DATA)


def _read_fstring(data: bytes, offset: int) -> tuple[Optional[str], int]:
    if offset + 4 > len(data):
        return None, offset
    length = struct.unpack_from("<i", data, offset)[0]
    offset += 4
    if length == 0:
        return "", offset
    if length > 0:
        val = data[offset : offset + length - 1].decode("utf-8", errors="replace")
        return val, offset + length
    length = -length
    val = data[offset : offset + length * 2 - 2].decode("utf-16-le", errors="replace")
    return val, offset + length * 2


def _parse_header(decomp: bytes) -> dict:
    offset = 12
    name, offset = _read_fstring(decomp, offset)
    ptype, offset = _read_fstring(decomp, offset)
    if not name or ptype != "StructProperty":
        return {}
    size = struct.unpack_from("<Q", decomp, offset)[0]
    offset += 8
    stype, offset = _read_fstring(decomp, offset)
    offset += 17  # 16-byte GUID + 1 byte terminator
    sub_end = offset + size
    props = {}
    while offset < sub_end:
        pname, offset = _read_fstring(decomp, offset)
        if not pname or pname == "None":
            break
        ptype, offset = _read_fstring(decomp, offset)
        psize = struct.unpack_from("<Q", decomp, offset)[0]
        offset += 8
        if ptype == "BoolProperty":
            props[pname] = decomp[offset] != 0
            offset += 1
        elif ptype == "StructProperty":
            st, offset = _read_fstring(decomp, offset)
            offset += 16
        offset += 1
        val_bytes = decomp[offset : offset + psize]
        offset += psize
        if ptype == "IntProperty":
            props[pname] = struct.unpack_from("<i", val_bytes, 0)[0]
        elif ptype in ("NameProperty", "StrProperty"):
            props[pname], _ = _read_fstring(val_bytes, 0)
        elif ptype == "TextProperty":
            ns, o = _read_fstring(val_bytes, 5)
            key, _ = _read_fstring(val_bytes, o)
            props[pname] = key
    return props


def dump(path: Union[Path, str]) -> Dict[str, Any]:
    p = Path(path)
    if p.is_file():
        save_file = p
    else:
        candidates = sorted(p.rglob("GameSave_Slot*.sav"))
        if not candidates:
            candidates = sorted(p.rglob("*.sav"))
        save_file = candidates[0] if candidates else None

    if not save_file or not save_file.exists():
        return {
            "has_save": False,
            "error": "No save file found",
        }

    raw = save_file.read_bytes()
    if not raw.startswith(b"GEVASEND") or len(raw) < 0x50:
        return {
            "has_save": False,
            "error": "Invalid GEVASEND container",
        }

    try:
        decomp = _decompress_save(raw[0x4A:])
    except Exception as e:
        return {
            "has_save": False,
            "error": f"Decompression failed: {e}",
        }

    hdr = _parse_header(decomp)
    ep_num = hdr.get("EpisodeNumber")
    sub_key = hdr.get("SubContextName")
    sub_id = hdr.get("SubContextId")
    cp_name = hdr.get("CheckpointName")
    if cp_name == "None":
        cp_name = None

    data = _load_data()
    ep_info = data["episodes"].get("by_number", {}).get(str(ep_num)) or {}
    ep_title = ep_info.get("title_ru")

    ch_info = data["chapters"].get("by_key", {}).get(sub_key) or data["chapters"].get("by_subcontext_id", {}).get(sub_id) or {}
    story_chapter = ch_info.get("title_ru")

    # Format place title from game data
    place_title = None
    if ep_num and ep_title:
        place_title = f"{ep_num}: {ep_title}"

    # Stats: completed episodes count
    comp_count = 0
    s_idx = decomp.find(b"StatsSaveData\x00")
    if s_idx != -1:
        arr_idx = decomp.find(b"EpisodeCompletion\x00", s_idx)
        if arr_idx != -1:
            b_idx = decomp.find(b"BoolProperty\x00", arr_idx)
            if b_idx != -1:
                o = b_idx + len(b"BoolProperty\x00") + 1
                cnt = struct.unpack_from("<i", decomp, o)[0]
                o += 4
                comp_count = sum(bool(decomp[o + i]) for i in range(cnt))

    # Collectibles in current context
    col_count = 0
    curr_idx = decomp.find(b"CurrentSubContextSaveData\x00")
    if curr_idx != -1:
        col_idx = decomp.find(b"CollectiblesSaveData\x00", curr_idx)
        if col_idx != -1 and col_idx < curr_idx + 475887:
            items_idx = decomp.find(b"Items\x00", col_idx)
            if items_idx != -1:
                sp_idx = decomp.find(b"StructProperty\x00", items_idx)
                if sp_idx != -1:
                    cnt = struct.unpack_from("<I", decomp, sp_idx + len(b"StructProperty\x00") + 1)[0]
                    if 0 <= cnt < 500:
                        col_count = cnt

    # Journal pages seen
    seen_pages_count = 0
    j_idx = decomp.find(b"JournalSaveData\x00")
    if j_idx != -1:
        sp_arr = decomp.find(b"SeenPages\x00", j_idx)
        if sp_arr != -1 and sp_arr < j_idx + 2000:
            sp_type = decomp.find(b"StructProperty\x00", sp_arr)
            if sp_type != -1:
                o = sp_type + len(b"StructProperty\x00") + 1
                cnt = struct.unpack_from("<i", decomp, o)[0]
                if 0 <= cnt < 500:
                    seen_pages_count = cnt

    game_progress = comp_count * 20 if comp_count else 0

    # Brotherhood and Morality facts from IntFacts
    # F_PROM_GEN_BRTHD: e638760be4e444419a9f2312082a9a12
    # F_PROM_GEN_MLTY: 7cd07b3148616e469292f805cb51cdc2
    brthd_guid = bytes.fromhex("e638760be4e444419a9f2312082a9a12")
    mlty_guid = bytes.fromhex("7cd07b3148616e469292f805cb51cdc2")
    brotherhood = None
    morality = None
    for name, guid in (("brthd", brthd_guid), ("mlty", mlty_guid)):
        pos = decomp.find(guid)
        if pos != -1:
            val_pos = decomp.rfind(b"IntProperty\x00", max(0, pos - 120), pos)
            if val_pos != -1:
                val = struct.unpack_from("<i", decomp, val_pos + len(b"IntProperty\x00") + 8 + 1)[0]
                if name == "brthd":
                    brotherhood = val
                else:
                    morality = val

    return {
        "has_save": True,
        "episode_num": ep_num,
        "episode_title": ep_title,
        "story_chapter": story_chapter,
        "subcontext_id": sub_id,
        "checkpoint_name": cp_name,
        "episodes_completed": comp_count,
        "collectibles_count": col_count,
        "journal_pages": seen_pages_count,
        "game_progress": game_progress,
        "place_title": place_title,
        "brotherhood": brotherhood,
        "morality": morality,
        "save_path": str(save_file),
    }
