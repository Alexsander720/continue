"""Raw save reader for SILENT HILL 2 Remake."""
from __future__ import annotations

import re
import struct
import zlib
from pathlib import Path
import sys
from ddsaves._common import localize, select, ui

GAMEHUB_DIR = Path(__file__).resolve().parents[1]
if str(GAMEHUB_DIR) not in sys.path:
    sys.path.insert(0, str(GAMEHUB_DIR))

try:
    from ddsaves.gvas import Reader
except ImportError:
    Reader = None


MAX_DECOMPRESSED_BYTES = 64 * 1024 * 1024


def _decompress_save(data):
    inflater = zlib.decompressobj()
    payload = inflater.decompress(data, MAX_DECOMPRESSED_BYTES + 1)
    if len(payload) > MAX_DECOMPRESSED_BYTES or inflater.unconsumed_tail:
        raise ValueError("Save exceeds decompressed size limit (64 MiB)")
    if not inflater.eof:
        raise ValueError("Incomplete compressed save")
    return payload


def dump(path: Path) -> dict:
    target = path / "SaveGameData_0.sav" if path.is_dir() else path
    raw = target.read_bytes()

    res = {}
    zlib_idx = raw.find(b"\x78\x9c")
    if zlib_idx == -1:
        return res

    hdr = raw[:zlib_idx]

    # 1. Clean header parsing
    try:
        dead_idx = hdr.rfind(b"\x01\x00\xad\xde")
        if dead_idx != -1:
            crc, payload_sz, str_len = struct.unpack("<III", hdr[dead_idx + 4 : dead_idx + 16])
            loc = hdr[dead_idx + 16 : dead_idx + 16 + str_len - 1].decode("utf-8", errors="ignore")
            res["location_tag"] = loc

        sp_idx = hdr.find(b"SavePoint\x00")
        if sp_idx != -1:
            res["slot_type"] = "SavePoint"
            ticks_off = sp_idx + len(b"SavePoint\x00") + 16
            if ticks_off + 8 <= len(hdr):
                res["ticks"] = struct.unpack("<q", hdr[ticks_off : ticks_off + 8])[0]
    except Exception:
        pass

    # 2. Decompress GVAS
    try:
        decomp = _decompress_save(raw[zlib_idx:])
    except Exception:
        return res

    # 3. HealthValue
    hv_idx = decomp.find(b"HealthValue\x00")
    if hv_idx != -1:
        fp_idx = decomp.find(b"FloatProperty\x00", hv_idx)
        if fp_idx != -1 and fp_idx - hv_idx < 64:
            off_fp = fp_idx + len(b"FloatProperty\x00") + 9
            if off_fp + 4 <= len(decomp):
                res["health"] = round(struct.unpack("<f", decomp[off_fp : off_fp + 4])[0], 1)

    # 4. Collected items with quantities
    items = {}
    item_pattern = re.compile(rb"ItemRowName\x00\r\x00\x00\x00NameProperty\x00.{9}.{4}([A-Za-z0-9_]+)\x00")
    for m in item_pattern.finditer(decomp):
        item_name = m.group(1).decode("ascii", errors="ignore")
        q_idx = decomp.find(b"Quantity\x00\x0c\x00\x00\x00IntProperty\x00", m.end(), m.end() + 100)
        qty = 1
        if q_idx != -1:
            q_off = q_idx + len(b"Quantity\x00\x0c\x00\x00\x00IntProperty\x00") + 9
            if q_off + 4 <= len(decomp):
                qty = struct.unpack("<i", decomp[q_off : q_off + 4])[0]
        items[item_name] = qty
    res["items"] = items

    # 5. Ammo in weapons
    ammo_loaded = {}
    mac_idx = decomp.find(b"WeaponsAmmoCounts\x00\x0c\x00\x00\x00MapProperty\x00")
    if mac_idx != -1:
        region = decomp[mac_idx : mac_idx + 600]
        for w in [b"Pistol", b"Shotgun", b"Rifle"]:
            w_idx = region.find(w)
            if w_idx != -1:
                off_val = w_idx + len(w) + 1
                if off_val + 4 <= len(region):
                    ammo_loaded[w.decode()] = struct.unpack("<i", region[off_val : off_val + 4])[0]
    res["weapons_ammo"] = ammo_loaded

    # 6. GVAS gameplay properties
    if Reader is not None:
        pattern = re.compile(
            rb"(\x00|^)([\x01-\x40]\x00\x00\x00)([A-Za-z0-9_]{3,40})\x00"
            rb"([\x01-\x20]\x00\x00\x00)"
            rb"(IntProperty|FloatProperty|BoolProperty|StrProperty|NameProperty|EnumProperty|ByteProperty)\x00"
        )
        gameplay_props = {}
        for m in pattern.finditer(decomp):
            name = m.group(3).decode("ascii", errors="ignore")
            if name in ("HealthValue", "ItemRowName", "Quantity", "None"):
                continue
            r = Reader(decomp, ue5=1008)
            r.p = m.start(2)
            try:
                t = r.tag()
                if t and t.get("name") == name:
                    v = r.value(t["tree"], t["size"], t)
                    if isinstance(v, (int, float, bool, str)):
                        gameplay_props[name] = v
            except Exception:
                pass
        res["props"] = gameplay_props

    return res


# ---------------------------------------------------------------------------
# Typed reader (round 5): header is parsed strictly, each wanted property must match
# exactly one tag of the expected type with the exact consumed size, otherwise None.
# ---------------------------------------------------------------------------
def _header(raw: bytes):
    if raw[:4] != b"VASb":
        raise ValueError("not a gameplay slot")
    rd = Reader(raw, ue5=1008)
    rd.p = 4
    size = rd.i32()
    if rd.i32() & 0xFFFFFFFF != 0xDEAD0001 or rd.fstr() != "/Script/SHProto.SHSaveGame":
        raise ValueError("unknown header")
    rd.i32()
    kind = rd.fstr()
    rd.p += 16
    ticks = struct.unpack_from("<q", raw, rd.p)[0]
    rd.p += 16
    if rd.i32() & 0xFFFFFFFF != 0xDEAD0001:
        raise ValueError("unknown header section")
    rd.i32()
    rd.i32()
    location = rd.fstr()
    boundary = size + 10
    if rd.p != boundary or raw[boundary:boundary + 6] != b"\x01\x01YDBx":
        raise ValueError("unsupported framing")
    compressed, expanded = struct.unpack_from("<II", raw, boundary + 6)
    body = raw[boundary + 14:]
    if len(body) != compressed:
        raise ValueError("compressed size mismatch")
    data = _decompress_save(body)
    if len(data) != expanded or data[:4] != b"GVAS":
        raise ValueError("payload mismatch")
    return {"location_tag": location, "slot_type": kind, "ticks": ticks}, data


def _unique(payload: bytes, name: str, expected):
    pattern = struct.pack("<i", len(name) + 1) + name.encode("ascii") + b"\x00"
    found = []
    for m in re.finditer(re.escape(pattern), payload):
        rd = Reader(payload, ue5=1008)
        rd.p = m.start()
        try:
            tag = rd.tag()
            if tag and tag["name"] == name and tag["tree"] == expected:
                start = rd.p
                if tag["size"] < 0 or start + tag["size"] > len(payload):
                    continue
                value = rd.value(tag["tree"], tag["size"], tag)
                if rd.p == start + tag["size"]:
                    found.append(value)
        except (ValueError, IndexError, KeyError, struct.error):
            pass
    return found[0] if len(found) == 1 else None


def state(path: Path) -> dict:
    """Typed gameplay state of one SH2 slot (None for anything not read unambiguously)."""
    target = path / "SaveGameData_0.sav" if path.is_dir() else path
    meta, payload = _header(target.read_bytes())
    if Reader is None:
        raise RuntimeError("ddsaves.gvas is required")
    INT, FLT = ["IntProperty"], ["FloatProperty"]
    collected = _unique(payload, "CollectedItems", ["ArrayProperty", ["StructProperty"]])
    items = None
    if isinstance(collected, list) and all(
            isinstance(v, dict) and isinstance(v.get("ItemRowName"), str) and type(v.get("Quantity")) is int
            for v in collected):
        items = {v["ItemRowName"]: v["Quantity"] for v in collected}
        if len(items) != len(collected):
            items = None
    memos = _unique(payload, "MemosItemsPickedUp", ["ArrayProperty", ["NameProperty"]])
    if not (isinstance(memos, list) and all(isinstance(v, str) for v in memos) and len(set(memos)) == len(memos)):
        memos = None
    return {
        **meta,
        "items": items,
        "memo_ids": memos,
        "health": _unique(payload, "HealthValue", FLT),
        "map_items_investigated": _unique(payload, "MapItemsInvestigated", INT),
        "kills_melee": _unique(payload, "MeleeWeaponKillcount", INT),
        "kills_ranged": _unique(payload, "RangedWeaponKillcount", INT),
        "dodges": _unique(payload, "PerformedDodges", INT),
        "heals_applied": _unique(payload, "HealsApplied", INT),
        "damage_received": _unique(payload, "ReceivedDamage", FLT),
        "registered_ending": _unique(payload, "RegisteredEnding", ["EnumProperty", ["ESHEndingType"]]),
    }
