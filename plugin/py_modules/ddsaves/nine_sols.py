"""Nine Sols: immutable modern/legacy saves, GUID seal names from game assets."""
from __future__ import annotations
import base64
import json
import os
from pathlib import Path
import re
import sys
import zlib

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if not __package__:
    if Path(__file__).resolve().parent.parent.name == "codex":
        sys.path.insert(0, str(ROOT.parents[min(2, len(ROOT.parents) - 1)] / "GameHub"))
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ddsaves._common import localize, select, ui, aes_ecb_decrypt, dur, empty, fact, finish, msgpack_unpack, newest, proton_user

HERE = Path(__file__).resolve().parent
TABLE_PATH = HERE / "data/nine_sols.json"
if not TABLE_PATH.is_file():
    TABLE_PATH = HERE.parent / "data/nine_sols.json"
T = json.loads(TABLE_PATH.read_text(encoding="utf8"))


def tables():
    """Совместимость с прежним модулем (_ddsaves_test)."""
    T = localize(globals()["T"])
    return T
APPID = 1809540
SUB = "AppData/LocalLow/RedCandleGames/NineSols"
MAX_DECOMPRESSED_BYTES = 64 * 1024 * 1024


def _decompress_save(data):
    inflater = zlib.decompressobj(-15)
    payload = inflater.decompress(data, MAX_DECOMPRESSED_BYTES + 1)
    if len(payload) > MAX_DECOMPRESSED_BYTES or inflater.unconsumed_tail:
        raise ValueError("Save exceeds decompressed size limit (64 MiB)")
    if not inflater.eof:
        raise ValueError("Incomplete compressed save")
    return payload


def find(path_or_dir=None):
    if path_or_dir is not None:
        p = Path(path_or_dir)
        if p.is_file():
            return p
        if p.is_dir():
            return newest(p.glob("flags.sav")) or newest(p.glob("saveslot*/flags.sav")) or newest(p.rglob("flags.txt"))
        return None
    paths = []
    if os.environ.get("USERPROFILE"):
        paths.append(Path(os.environ["USERPROFILE"]) / SUB)
    paths += [p / SUB for p in proton_user(APPID)]
    return newest(p for d in paths for p in d.glob("saveslot*/flags.sav"))


def _legacy_json(path):
    T = localize(globals()["T"])
    cipher = base64.b64decode(Path(path).read_bytes(), validate=True)
    if not cipher or len(cipher) % 16:
        raise ValueError("Legacy AES ciphertext has invalid block length")
    key = bytes.fromhex(T["crypto"]["myKey"])
    iv = bytes.fromhex(T["crypto"]["myIV"])
    # The accepted ECB helper strips at most 16 bytes. An appended real block
    # protects every original decrypted block; only the original prefix is used.
    ecb = aes_ecb_decrypt(key, cipher + cipher[:16])
    if ecb is None or len(ecb) < len(cipher):
        raise ValueError("Legacy AES decryption unavailable")
    plain = bytes(a ^ b for a, b in zip(ecb[:len(cipher)], iv + cipher[:-16]))
    pad = plain[-1]
    if not 1 <= pad <= 16 or plain[-pad:] != bytes([pad]) * pad:
        raise ValueError("Invalid legacy AES padding")
    obj = json.loads(plain[:-pad])
    if not isinstance(obj, dict):
        raise ValueError("Expected legacy JSON object")
    return obj


def unpack(path):
    path = Path(path)
    if path.name in ["flags.txt", "meta.txt"]:
        return _legacy_json(path.parent / "meta.txt"), _legacy_json(path.parent / "flags.txt")
    top = msgpack_unpack(_decompress_save(path.read_bytes()))
    if not isinstance(top, list) or len(top) != 3 or not isinstance(top[1], str) or not isinstance(top[2], dict):
        raise ValueError("Unsupported Nine Sols save structure")
    meta = json.loads(top[1])
    if not isinstance(meta, dict):
        raise ValueError("Expected metadata object")
    return meta, top[2]


def count(flags, cls, field):
    rows = [v for k, v in flags.items() if isinstance(k, str) and re.fullmatch(r"[0-9a-f]{32}" + cls, k) and isinstance(v, dict)]
    return sum(v.get(field) is True for v in rows), len(rows)


def read(path_or_dir=None):
    T = localize(globals()["T"])
    path = find(path_or_dir)
    if path is None:
        return empty("Файл сохранения Nine Sols не найден")
    try:
        meta, flags = unpack(path)
    except (OSError, ValueError, zlib.error, IndexError) as error:
        return empty(str(error))
    seal_flags = {key: flags.get(key) if isinstance(flags.get(key), dict) else {} for key in T["seals"]}
    seals = [name for key, name in T["seals"].items() if seal_flags[key].get("acquired") is True]
    play = meta.get("playTime")
    level = meta.get("level")
    place = T["scenes"].get(meta.get("atSceneGuid"))
    jades_on_names = [name for key, name in T.get("jades", {}).items() if isinstance(flags.get(key), dict) and flags[key].get("equipped") is True]
    last_node = T.get("teleports", {}).get(meta.get("lastTeleportPointPath"))
    progress = {"seals": seals, "seals_count": len(seals), "seals_total": len(T["seals"]), "seal_flags": seal_flags,
                "last_sol": None, "level": level, "active_gameplay_seconds": play,
                "gold": meta.get("gold"), "deaths": meta.get("deathCount"), "meta": meta,
                "jades_equipped_names": jades_on_names, "last_teleport": last_node,
                "ending": None, "new_game_plus": meta.get("secondTimePlay"),
                "at_scene_guid": meta.get("atSceneGuid"), "last_teleport_guid": meta.get("lastTeleportPointPath"),
                "game_mode": meta.get("gameMode"),
                "map_log": {k: v for k, v in flags.items() if k.endswith("GameLevelMapLog")},
                "seal_collection": {k: v for k, v in flags.items() if k.endswith("ItemDataCollection")}}
    for cls, prefix, field in [("JadeData", "jades", "acquired"), ("SkillNodeData", "skills", "acquired"), ("EncyclopediaItem", "encyclopedia", "acquired"), ("TeleportPointData", "teleports", "unlocked")]:
        progress[prefix + "_count"], progress[prefix + "_records"] = count(flags, cls, field)
        progress[prefix + "_total"] = progress[prefix + "_records"]
    progress["jades_equipped"] = count(flags, "JadeData", "equipped")[0]
    facts = [fact("sun", "Печати Солов", f"{len(seals)} / {len(T['seals'])}")]
    if seals:
        facts.append(fact("sun", "Полученные печати", ", ".join(seals)))
    proven = ["seals", "seals_count"]
    if place:
        proven.append("place")
    if isinstance(level, (int, float)) and not isinstance(level, bool):
        facts.append(fact("level", "Уровень", level))
        proven.append("level")
    if isinstance(play, (int, float)) and not isinstance(play, bool):
        proven.append("active_gameplay_seconds")
        if play >= 60:
            facts.append(fact("clock", "В этом сейве", dur(play)))
    for prefix, icon, label in [("jades", "gem", "Нефриты"), ("skills", "bolt", "Навыки"), ("encyclopedia", "book", "Энциклопедия")]:
        value = progress[prefix + "_count"]
        proven.append(prefix + "_count")
        if value:
            text = value if prefix == "skills" else f"{value} / {progress[prefix + '_records']}"
            facts.append(fact(icon, label, text))
    proven += ["teleports_count", "deaths", "jades_equipped", "jades_equipped_names", "last_teleport"]
    if jades_on_names:
        facts.append(fact("gem", "Надеты нефриты", ", ".join(jades_on_names)))
    if last_node and last_node != place:
        facts.append(fact("map-pin", "Последний узел", last_node))
    if progress["deaths"]:
        facts.append(fact("skull", "Смертей", int(progress["deaths"])))
    unproven = [k for k in progress if k not in proven]
    unproven += ["chapter", "objective"]
    if not place:
        unproven.append("place")
    return finish({"place": place, "chapter": None, "objective": None, "play_seconds": play, "progress": progress,
                   "facts": facts, "proven": proven, "unproven": unproven}, path)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf8")
    print(json.dumps(read(sys.argv[1] if len(sys.argv) > 1 else None), ensure_ascii=False, indent=2))
