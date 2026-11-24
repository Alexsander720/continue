"""Raw save reader for SILENT HILL 2 Remake (pure stdlib)."""
from __future__ import annotations

import re
import struct
import sys
import uuid
import zlib
from pathlib import Path

GAMEHUB_DIR = Path(__file__).resolve().parents[1]
if str(GAMEHUB_DIR) not in sys.path:
    sys.path.insert(0, str(GAMEHUB_DIR))

try:
    from ddsaves.gvas import Reader
except ImportError:
    Reader = None

MAX_DECOMPRESSED_BYTES = 64 * 1024 * 1024


def _decompress_save(data: bytes) -> bytes:
    inflater = zlib.decompressobj()
    payload = inflater.decompress(data, MAX_DECOMPRESSED_BYTES + 1)
    if len(payload) > MAX_DECOMPRESSED_BYTES or inflater.unconsumed_tail:
        raise ValueError("Save exceeds decompressed size limit (64 MiB)")
    if not inflater.eof:
        raise ValueError("Incomplete compressed save")
    return payload


def _read_fstr(buf: bytes, p: int) -> tuple[str, int]:
    if p + 4 > len(buf):
        return "", len(buf)
    ln, = struct.unpack_from("<i", buf, p)
    p += 4
    if ln == 0:
        return "", p
    if ln > 0:
        end = min(len(buf), p + ln)
        return buf[p:max(p, end - 1)].decode("utf-8", errors="replace"), end
    nbytes = (-ln) * 2
    end = min(len(buf), p + nbytes)
    return buf[p:max(p, end - 2)].decode("utf-16-le", errors="replace"), end


def _read_guid_hex(buf: bytes, p: int) -> tuple[str, int]:
    if p + 16 > len(buf):
        return "", len(buf)
    a, b, c, d = struct.unpack_from("<4I", buf, p)
    raw_be = struct.pack(">4I", a, b, c, d)
    return str(uuid.UUID(bytes=raw_be)), p + 16


def _extract_ghca_glimpses(payload: bytes) -> set[str]:
    glimpses: set[str] = set()
    idx = 0
    while True:
        pos = payload.find(b"GHCA", idx)
        if pos == -1 or pos + 8 > len(payload):
            break
        idx = pos + 4
        p = pos + 8
        try:
            while p + 8 <= len(payload):
                sec = payload[p:p + 4]
                cnt, = struct.unpack_from("<i", payload, p + 4)
                p += 8
                if cnt < 0 or cnt > 10000:
                    break
                if sec == b"TNI_":
                    for _ in range(cnt):
                        _, p = _read_fstr(payload, p)
                        p += 4
                elif sec == b"TLF_":
                    for _ in range(cnt):
                        _, p = _read_fstr(payload, p)
                        p += 4
                elif sec == b"LOC_":
                    for _ in range(cnt):
                        nm, p = _read_fstr(payload, p)
                        if p + 4 > len(payload):
                            break
                        gcnt, = struct.unpack_from("<i", payload, p)
                        p += 4
                        if gcnt < 0 or gcnt > 1000:
                            break
                        for _ in range(gcnt):
                            g, p = _read_guid_hex(payload, p)
                            if nm == "GlimpsesOfPast" and g:
                                glimpses.add(g)
                    break
                else:
                    break
        except Exception:
            continue
    return glimpses


def _extract_ucasave_file(uca_path: Path) -> set[str]:
    if not uca_path.is_file() or uca_path.is_symlink():
        return set()
    try:
        raw = uca_path.read_bytes()
        pos = raw.find(b"VHCA")
        if pos == -1:
            return set()
        p = pos + 8
        for _ in range(struct.unpack_from("<i", raw, p)[0]):
            _, p = _read_fstr(raw, p + 4 if False else p)
        # Simpler direct scan around "GlimpsesOfPast\x00" inside VHCA
    except Exception:
        pass
    try:
        raw = uca_path.read_bytes()
        marker = b"\x0f\x00\x00\x00GlimpsesOfPast\x00"
        pos = raw.find(marker)
        if pos == -1 or pos + len(marker) + 4 > len(raw):
            return set()
        p = pos + len(marker)
        cnt, = struct.unpack_from("<i", raw, p)
        p += 4
        if 0 <= cnt <= 200 and p + cnt * 16 <= len(raw):
            out: set[str] = set()
            for _ in range(cnt):
                g, p = _read_guid_hex(raw, p)
                if g:
                    out.add(g)
            return out
    except Exception:
        pass
    return set()


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
    rd.p += 8
    rd.p += 8  # crc + thumb_len
    if rd.i32() & 0xFFFFFFFF != 0xDEAD0001:
        raise ValueError("unknown header section")
    playtime_ticks = struct.unpack_from("<q", raw, rd.p)[0]
    rd.p += 8
    location = rd.fstr()
    boundary = size + 10
    if rd.p != boundary or raw[boundary + 2:boundary + 6] != b"YDBx":
        raise ValueError("unsupported framing")
    combat_diff = raw[boundary]
    puzzle_diff = raw[boundary + 1]
    compressed, expanded = struct.unpack_from("<II", raw, boundary + 6)
    body = raw[boundary + 14:]
    if len(body) != compressed:
        raise ValueError("compressed size mismatch")
    data = _decompress_save(body)
    if len(data) != expanded or data[:4] != b"GVAS":
        raise ValueError("payload mismatch")
    meta = {
        "location_tag": location,
        "slot_type": kind,
        "ticks": ticks,
        "playtime_seconds": int(playtime_ticks // 10_000_000) if playtime_ticks > 0 else None,
        "combat_difficulty_id": int(combat_diff) if combat_diff in (0, 1, 2) else None,
        "puzzle_difficulty_id": int(puzzle_diff) if puzzle_diff in (0, 1, 2) else None,
    }
    return meta, data


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


def dump(path: Path) -> dict:
    """Legacy compatible dict dump."""
    target = path / "SaveGameData_0.sav" if path.is_dir() else path
    try:
        return state(target)
    except Exception:
        return {}


def state(path: Path) -> dict:
    """Typed gameplay state of one SH2 slot (None for anything not read unambiguously)."""
    target = path / "SaveGameData_0.sav" if path.is_dir() else path
    meta, payload = _header(target.read_bytes())
    if Reader is None:
        raise RuntimeError("ddsaves.gvas is required")
    INT, FLT, NAME = ["IntProperty"], ["FloatProperty"], ["NameProperty"]
    MAP_NAME_INT = ["MapProperty", ["NameProperty"], ["IntProperty"]]
    MAP_NAME_BOOL = ["MapProperty", ["NameProperty"], ["BoolProperty"]]

    collected = _unique(payload, "CollectedItems", ["ArrayProperty", ["StructProperty"]])
    items = None
    if isinstance(collected, list) and all(
        isinstance(v, dict) and isinstance(v.get("ItemRowName"), str) and type(v.get("Quantity")) is int
        for v in collected
    ):
        items = {v["ItemRowName"]: v["Quantity"] for v in collected}
        if len(items) != len(collected):
            items = None

    memos = _unique(payload, "MemosItemsPickedUp", ["ArrayProperty", ["NameProperty"]])
    if not (isinstance(memos, list) and all(isinstance(v, str) for v in memos) and len(set(memos)) == len(memos)):
        memos = None

    wac_raw = _unique(payload, "WeaponsAmmoCounts", MAP_NAME_INT)
    ammo_loaded = (
        {str(k): int(v) for k, v in wac_raw if isinstance(k, str) and type(v) is int}
        if isinstance(wac_raw, list)
        else {}
    )

    wtk_raw = _unique(payload, "WeaponToKillsMap", MAP_NAME_INT)
    weapon_kills = (
        {str(k): int(v) for k, v in wtk_raw if isinstance(k, str) and type(v) is int}
        if isinstance(wtk_raw, list)
        else {}
    )

    eq_raw = _unique(payload, "EquipmentStateValues", MAP_NAME_BOOL)
    equipment = (
        {str(k): bool(v) for k, v in eq_raw if isinstance(k, str) and isinstance(v, bool)}
        if isinstance(eq_raw, list)
        else {}
    )

    last_w = _unique(payload, "LastUsedWeapon", NAME)
    last_melee = _unique(payload, "LastUsedMeleeWeapon", NAME)
    last_ranged = _unique(payload, "LastUsedRangedWeapon", NAME)

    glimpses = _extract_ghca_glimpses(payload)
    glimpses |= _extract_ucasave_file(target.parent / "UcaSave.sav")

    return {
        **meta,
        "items": items,
        "memo_ids": memos,
        "health": _unique(payload, "HealthValue", FLT),
        "ammo_loaded": ammo_loaded,
        "weapon_kills": weapon_kills,
        "equipment": equipment,
        "last_used_weapon": last_w if isinstance(last_w, str) and last_w != "None" else None,
        "last_melee_weapon": last_melee if isinstance(last_melee, str) and last_melee != "None" else None,
        "last_ranged_weapon": last_ranged if isinstance(last_ranged, str) and last_ranged != "None" else None,
        "glimpses_count": len(glimpses),
        "map_items_investigated": _unique(payload, "MapItemsInvestigated", INT),
        "kills_melee": _unique(payload, "MeleeWeaponKillcount", INT),
        "kills_ranged": _unique(payload, "RangedWeaponKillcount", INT),
        "shots_fired": _unique(payload, "RangedShootsFired", INT),
        "dodges": _unique(payload, "PerformedDodges", INT),
        "broken_glass": _unique(payload, "BrokenGlass", INT),
        "locked_doors_checked": _unique(payload, "AutoLockedDoorCheckAnimActionPlayedCount", INT),
        "heals_applied": _unique(payload, "HealsApplied", INT),
        "damage_received": _unique(payload, "ReceivedDamage", FLT),
        "distance_cm": _unique(payload, "DistanceTravelled", INT),
        "consumables_picked": _unique(payload, "ConsumableItemsPickedUp", INT),
        "registered_ending": _unique(payload, "RegisteredEnding", ["EnumProperty", ["ESHEndingType"]]),
    }
