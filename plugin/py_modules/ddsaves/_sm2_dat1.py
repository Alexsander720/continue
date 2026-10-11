"""Stdlib reader for Insomniac DAT1 / serialized-DDL blobs (Spider-Man 2 saves and config assets).

Format notes (verified on owner saves, PlayGround saves and game config/nodegraph assets):
  DAT1 header: magic 0x44415431, type, size, section count, unknown count; then 12-byte section
  table (tag, offset, size), 8*unknown bytes, then a NUL-terminated strings block (field names).
  Serialized object: u32 0, u32 0x03150044, u32 field count, u32 payload size; descriptors
  (u32 name crc, u16 flags, u8 reserved, u8 kind) and u32 name offsets into the strings block;
  values start 4-aligned. Kinds: 0 u8, 1 u16, 2 u32, 4 i8, 5 i16, 6 i32, 8 f32, 9 opaque 8 bytes,
  10 string (u32 len, u32 crc32, u64 crc64, bytes, NUL, pad 4), 13 nested object, 15 bool,
  17 u64, 19 null.
The object layout follows Codex's draft parser (codex/ddsaves/spider_man_2.py); re-checked here.
String crc32 is Insomniac CRC32 (reflected 0xEDB88320 table, init 0xEDB88320, no final xor),
the same value the saves use as dict keys (e.g. mission SaveHash = crc32(MissionName)).
"""
from __future__ import annotations

import struct
import zlib

MAGIC = 0x44415431
OBJ_MARK = 0x03150044
_FMT = {0: "<B", 1: "<H", 2: "<I", 4: "<b", 5: "<h", 6: "<i", 8: "<f", 17: "<Q"}


def crc32(s: str) -> int:
    """Insomniac CRC32 of a UTF-8 string (verified against stored string crcs in saves)."""
    return zlib.crc32(s.encode("utf-8"), 0xEDB88320 ^ 0xFFFFFFFF) ^ 0xFFFFFFFF


class Dat1:
    def __init__(self, blob: bytes, strict: bool = True):
        self.b = blob
        magic, self.type, size, count, unknown = struct.unpack_from("<IIIHH", blob)
        if magic != MAGIC or count > 4096 or (strict and size != len(blob)):
            raise ValueError("not a DAT1 blob")
        self.sections: dict[int, tuple[int, int]] = {}
        for i in range(count):
            tag, off, sz = struct.unpack_from("<III", blob, 16 + 12 * i)
            if off + sz > len(blob):
                raise ValueError("DAT1 section out of range")
            self.sections[tag] = (off, sz)
        self.strings_start = 16 + 12 * count + 8 * unknown
        self.strings_end = min(off for off, _ in self.sections.values()) if self.sections else len(blob)

    def name(self, off: int) -> str:
        if not self.strings_start <= off < self.strings_end:
            raise ValueError("field name outside strings block")
        end = self.b.find(b"\x00", off, self.strings_end)
        if end < 0:
            raise ValueError("unterminated field name")
        return self.b[off:end].decode("utf-8")

    def section(self, tag: int):
        off, sz = self.sections[tag]
        return self.obj(off, off + sz)[0]

    def obj(self, offset: int, bound: int, depth: int = 0):
        if depth > 64:
            raise ValueError("DDL nesting too deep")
        zero, mark, count, size = struct.unpack_from("<IIII", self.b, offset)
        end, p = offset + 16 + size, offset + 16
        if zero or mark != OBJ_MARK or count > 1_000_000 or size < 12 * count or end > bound:
            raise ValueError("invalid serialized object")
        desc = [struct.unpack_from("<IHBB", self.b, p + 8 * i) for i in range(count)]
        p += 8 * count
        noffs = struct.unpack_from(f"<{count}I", self.b, p)
        p += 4 * count
        if count:
            p = (p + 3) & ~3
        out = {}
        for (_crc, flags, reserved, kind), noff in zip(desc, noffs):
            nm = self.name(noff)
            n, is_arr = flags >> 4, bool(flags & 1)
            if nm in out or reserved or flags & 14 or (not is_arr and n != 1):
                raise ValueError("unknown DDL descriptor")
            if is_arr and n == 0:
                if self.b[p] != 0:
                    raise ValueError("nonzero empty array")
                out[nm], p = [], p + 1
                continue
            vals = []
            for _ in range(n if is_arr else 1):
                v, p = self.node(kind, p, end, depth + 1)
                vals.append(v)
            out[nm] = vals if is_arr else vals[0]
        if p > end or any(self.b[p:end]):
            raise ValueError("unparsed nonzero DDL tail")
        return out, end

    def node(self, kind: int, p: int, bound: int, depth: int):
        if kind in _FMT:
            fmt = _FMT[kind]
            e = p + struct.calcsize(fmt)
            if e > bound:
                raise ValueError("truncated value")
            return struct.unpack_from(fmt, self.b, p)[0], e
        if kind == 9:
            if p + 8 > bound:
                raise ValueError("truncated type9")
            return self.b[p:p + 8].hex(), p + 8
        if kind in (15, 19):
            v = self.b[p]
            if v not in (0, 1) or (kind == 19 and v):
                raise ValueError("invalid bool/null")
            return (bool(v) if kind == 15 else None), p + 1
        if kind == 10:
            ln = struct.unpack_from("<I", self.b, p)[0]
            e = p + 16 + ((ln + 4) & ~3)
            if ln > 1_000_000 or e > bound or self.b[p + 16 + ln] != 0:
                raise ValueError("invalid string")
            return self.b[p + 16:p + 16 + ln].decode("utf-8"), e
        if kind == 13:
            return self.obj(p, bound, depth)
        raise ValueError(f"unsupported DDL kind {kind}")


def save_systems(blob: bytes) -> dict:
    """{SaveName: SaveData.Obj} for every system in every section of a SM2 save."""
    d = Dat1(blob)
    if d.type != 9:
        raise ValueError("not a SM2 save DAT1")
    out = {}
    for tag in d.sections:
        root = d.section(tag)
        for s in root["Systems"].values():
            out[s["SaveName"]] = s["SaveData"]["Obj"]
    return out
