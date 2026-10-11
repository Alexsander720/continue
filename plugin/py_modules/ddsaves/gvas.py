"""Читатель Unreal GVAS (SaveGame) без внешних пакетов: UE4, UE5 и UE 5.4+ (полные имена типов в тегах).

read(bytes) -> {"header": {...}, "class": str, "props": {имя: значение}}
Значения: числа/строки/bool; структуры — dict; массивы — list; map — список пар [ключ, значение].
Неизвестное/нераспознанное значение пропускается по размеру из тега (тег всегда несёт размер),
поэтому один странный тип не ломает разбор остального.
"""
from __future__ import annotations

import struct
from typing import Any, Dict, List, Optional, Tuple

COMPLETE_TYPE_NAME = 1012  # EUnrealEngineObjectUE5Version::PROPERTY_TAG_COMPLETE_TYPE_NAME

# структуры, которые пишутся двоично (а не списком свойств): имя → (формат struct, размер)
NATIVE = {
    "Vector": "<3d", "Rotator": "<3d", "Quat": "<4d", "Vector2D": "<2d", "Vector4": "<4d",
    "LinearColor": "<4f", "Color": "<4B", "IntPoint": "<2i", "IntVector": "<3i",
    "DateTime": "<q", "Timespan": "<q", "Guid": "<16s",
}


class Reader:
    def __init__(self, b: bytes, ue5: int = 0):
        self.b, self.p, self.ue5 = b, 0, ue5

    def i32(self):
        v = struct.unpack_from("<i", self.b, self.p)[0]
        self.p += 4
        return v

    def u8(self):
        v = self.b[self.p]
        self.p += 1
        return v

    def fstr(self) -> str:
        n = self.i32()
        if n == 0:
            return ""
        if n < 0:
            s = self.b[self.p:self.p - n * 2 - 2].decode("utf-16-le", "replace")
            self.p += -n * 2
            return s
        s = self.b[self.p:self.p + n - 1].decode("utf-8", "replace")
        self.p += n
        return s

    # ── тип свойства ──
    def type_tree(self):
        """UE 5.4+: FPropertyTypeName — узел (имя, число детей) рекурсивно."""
        name = self.fstr()
        n = self.i32()
        return [name] + [self.type_tree() for _ in range(n)]

    def tag(self) -> Optional[Dict[str, Any]]:
        name = self.fstr()
        if name == "None" or name == "":
            return None
        t: Dict[str, Any] = {"name": name}
        if self.ue5 >= COMPLETE_TYPE_NAME:
            tree = self.type_tree()
            t["tree"] = tree
            t["type"] = tree[0]
            t["size"] = self.i32()
            flags = self.u8()
            if flags & 0x01:
                t["index"] = self.i32()
            if flags & 0x02:
                self.p += 16
            if flags & 0x04:
                ext = self.u8()
                if ext & 0x02:  # OverridableInformation
                    self.p += 2
            t["bool"] = bool(flags & 0x10)
        else:
            t["type"] = self.fstr()
            t["size"] = self.i32()
            t["index"] = self.i32()
            ty = t["type"]
            if ty == "StructProperty":
                t["tree"] = [ty, [self.fstr()]]
                self.p += 16
            elif ty == "BoolProperty":
                t["bool"] = bool(self.u8())
                t["tree"] = [ty]
            elif ty in ("ByteProperty", "EnumProperty"):
                t["tree"] = [ty, [self.fstr()]]
            elif ty in ("ArrayProperty", "SetProperty"):
                t["tree"] = [ty, [self.fstr()]]
            elif ty == "MapProperty":
                t["tree"] = [ty, [self.fstr()], [self.fstr()]]
            else:
                t["tree"] = [ty]
            if self.u8():
                self.p += 16
        return t

    # ── значения ──
    def props(self, end: Optional[int] = None) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        while end is None or self.p < end:
            t = self.tag()
            if t is None:
                break
            start = self.p
            try:
                v = self.value(t["tree"], t["size"], t)
            except Exception:
                v = None
            self.p = start + t["size"]
            key = t["name"] if "index" not in t or not t.get("index") else f"{t['name']}[{t['index']}]"
            out[key] = v
        return out

    def struct_name(self, tree) -> str:
        if len(tree) > 1 and tree[1]:
            return tree[1][0]
        return ""

    def value(self, tree, size: int, t: Optional[dict] = None, in_container: bool = False):
        ty = tree[0]
        if ty == "BoolProperty":
            return bool(t.get("bool")) if (t and not in_container) else bool(self.u8())
        if ty == "IntProperty":
            return self.i32()
        if ty in ("UInt32Property",):
            v = struct.unpack_from("<I", self.b, self.p)[0]; self.p += 4; return v
        if ty in ("Int64Property",):
            v = struct.unpack_from("<q", self.b, self.p)[0]; self.p += 8; return v
        if ty in ("UInt64Property",):
            v = struct.unpack_from("<Q", self.b, self.p)[0]; self.p += 8; return v
        if ty == "Int16Property":
            v = struct.unpack_from("<h", self.b, self.p)[0]; self.p += 2; return v
        if ty == "Int8Property":
            v = struct.unpack_from("<b", self.b, self.p)[0]; self.p += 1; return v
        if ty == "FloatProperty":
            v = struct.unpack_from("<f", self.b, self.p)[0]; self.p += 4; return v
        if ty == "DoubleProperty":
            v = struct.unpack_from("<d", self.b, self.p)[0]; self.p += 8; return v
        if ty in ("StrProperty", "NameProperty", "ObjectProperty", "SoftObjectProperty", "EnumProperty"):
            s = self.fstr()
            if ty == "SoftObjectProperty":
                self.fstr()
            return s
        if ty == "ByteProperty":
            enum = self.struct_name(tree)
            if enum and enum != "None":
                return self.fstr()
            if not in_container and size and size > 1:
                return self.fstr()
            return self.u8()
        if ty == "TextProperty":
            return self.text()
        if ty == "StructProperty":
            sname = self.struct_name(tree)
            if sname in NATIVE:
                fmt = NATIVE[sname]
                v = struct.unpack_from(fmt, self.b, self.p)
                self.p += struct.calcsize(fmt)
                return v[0] if len(v) == 1 else list(v)
            return self.props(self.p + size if (size and not in_container) else None)
        if ty in ("ArrayProperty", "SetProperty"):
            if ty == "SetProperty":
                self.i32()
            n = self.i32()
            inner = tree[1] if len(tree) > 1 else ["?"]
            if self.ue5 < COMPLETE_TYPE_NAME and inner[0] == "StructProperty" and ty == "ArrayProperty":
                # старый формат: перед элементами — фиктивный тег с именем структуры
                self.fstr(); self.fstr(); self.i32(); self.i32()
                sname = self.fstr()
                self.p += 16 + 1
                inner = ["StructProperty", [sname]]
            return [self.value(inner, 0, None, True) for _ in range(n)]
        if ty == "MapProperty":
            self.i32()  # удалённые
            n = self.i32()
            kt = tree[1] if len(tree) > 1 else ["?"]
            vt = tree[2] if len(tree) > 2 else ["?"]
            return [[self.value(kt, 0, None, True), self.value(vt, 0, None, True)] for _ in range(n)]
        raise ValueError(ty)

    def text(self):
        flags = struct.unpack_from("<I", self.b, self.p)[0]; self.p += 4
        ht = self.b[self.p]; self.p += 1
        if ht == 0xFF:  # None
            if self.i32():
                return self.fstr()
            return ""
        if ht == 0:  # Base: namespace, key, source
            ns, key, src = self.fstr(), self.fstr(), self.fstr()
            return {"ns": ns, "key": key, "src": src}
        if ht == 11:  # StringTableEntry
            return {"table": self.fstr(), "key": self.fstr()}
        raise ValueError(f"FText history {ht}")


def read(b: bytes) -> Dict[str, Any]:
    if b[:4] != b"GVAS":
        raise ValueError("не GVAS")
    r = Reader(b)
    r.p = 4
    h: Dict[str, Any] = {"save_version": r.i32(), "ue4": r.i32()}
    if h["save_version"] >= 3:
        h["ue5"] = r.i32()
    h["engine"] = struct.unpack_from("<HHH", b, r.p)
    r.p += 6 + 4
    h["branch"] = r.fstr()
    h["custom_format"] = r.i32()
    n = r.i32()
    r.p += n * 20
    cls = r.fstr()
    r.ue5 = h.get("ue5", 0)
    # UE 5.4+ (ue5 >= 1012) пишет после класса ещё байт (флаги сериализации) — пропускаем, если там 0
    if r.ue5 >= COMPLETE_TYPE_NAME and b[r.p] == 0 and 0 < struct.unpack_from("<i", b, r.p + 1)[0] < 256:
        r.p += 1
    return {"header": h, "class": cls, "props": r.props()}


def unwrap(v):
    """Убрать суффиксы «_0», «_12_GUID» в ключах для удобства (QuestStatuses_0 → QuestStatuses)."""
    import re
    if isinstance(v, dict):
        return {re.sub(r"_\d+(_[0-9A-F]{32})?$", "", k): unwrap(x) for k, x in v.items()}
    if isinstance(v, list):
        return [unwrap(x) for x in v]
    return v


def records(b: bytes) -> Dict[str, Any]:
    """Свои контейнеры поверх GVAS (REANIMAL SaveSystem: пустой корень «None», затем записи
    FString имя, int32 размер, u8 флаг, список свойств). Ищем такие записи и разбираем каждую."""
    import re
    if b[:4] != b"GVAS":
        raise ValueError("не GVAS")
    head = read(b)
    r = Reader(b, head["header"].get("ue5", 0))
    out: Dict[str, Any] = {}
    for m in re.finditer(rb"(.{4})([A-Za-z][A-Za-z0-9_]{2,63})\x00(.{4})\x00", b, re.S):
        L = struct.unpack("<i", m.group(1))[0]
        size = struct.unpack("<i", m.group(3))[0]
        name = m.group(2).decode()
        if L != len(name) + 1 or not (0 < size <= len(b) - m.end()) or name in out:
            continue
        r.p = m.end()
        try:
            t0 = r.p
            nm = r.fstr()
            ty = r.fstr()
            if not ty.endswith("Property"):
                continue
            r.p = t0
            out[name] = r.props(m.end() + size)
        except Exception:
            continue
    return out
