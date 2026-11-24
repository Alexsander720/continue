"""God of War Ragnarök (appid 2322010): GOWRSAVE<N> в «Saved Games/God of War Ragnarök/<id>/».

Перенесено 08.10.2026 из GameHub/gowsave.py — только доказанное (для Continue? и Деки, одна стандартная библиотека):
  • место и задание — строка, которую САМА игра пишет в заголовок сейва на своём языке: «Мир - Область - Задание»
    (0x50..0x190); сверено на 22 слотах: ID строки задания (0x1B0) указывает в r_lang_<язык>.wad ровно на этот текст;
  • время игры (0x190), счётчик сохранений (0x1BC — выбор самого свежего слота);
  • серебро — кошелёк героя, предмет с хешем имени «Hacksilver» 0x5AE80674… (в 0x198 заголовка — накопленное
    за всю игру, не то, что на экране);
  • Вороны Одина — счётчик журнала просьбы «Глаза Одина» (Table 1 сейва, шаг «Убивать воронов Одина», из 48).
    14.11.2026: прежняя формула «предмет 0x482780EF… + 3 × дары 0x28FB7355…» совпадала с экраном лишь в точках
    калибровки (21.09, 02.10); по 22 слотам она расходится со счётчиком (GOWRSAVE17: 27 против 21, текущий 29 против 31)
    и стоит, пока счётчик растёт. Формула осталась запасной — для сейвов, где счётчика ещё нет;
  • счётчики остальных мировых просьб — из той же Table 1 (`journal`), хеши счётчиков взяты из quests_main.dcb
    (GameHub/gow_favors.py) и совпадают с картой хаба: одни и те же байты сейва.
  • ряд «Просьбы Девяти миров» (`favor_row`) — значки с счётчиками этих шагов, вместо отдельного факта воронов;
  • сундуки Норн / яблоки Идунн / рога (`nornir`, кошелёк + сверка с ярусами) и уровни оружия (`weapon_levels`, не
    доказаны — по блоку снаряжения Char_HeroA00, как в хабе; на панель не идут). Ряд — `panel_row`, 15.11.2026.
Не переносится: рукописные описания вех, «уровень» (среднее снаряжения), текст из дневника (ID+1 не всегда описание).
"""
from __future__ import annotations

import os
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ddsaves._common import dur, empty, fact, finish, lang, num, proton_user, read_bytes

APPID = 2322010
MAGIC_VERSION = 0x00660404
STRING_OFFSET, STRING_END = 0x50, 0x190
HERO_WALLET_HASH = 0x00004895C643225F
RAVEN_ITEM, RAVEN_GIFT, RAVENS_TOTAL = 0x482780EFF18ED57E, 0x28FB73555D08478B, 48
HACKSILVER = 0x5AE80674D240529E
TABLE1_OFFSET = 0x08840            # uint32 число записей, далее записи <QQII>: хеш, значение, 2×служебное
TABLE1_BOOL_TRUE = 0x0000A8CE0F4DDD8B
# Счётчики шагов просьб из журнала игры: ключ → (хеш счётчика, всего). Значение в сейве = val >> 11.
JOURNAL_COUNTERS = {
    "odin_ravens": (0x105A6147D2E88AE8, 48),      # Глаза Одина: убито воронов
    "raven_gifts": (0x5828350B43A63BC4, 6),       # Глаза Одина: открыто даров Древа
    "draugr_holes": (0x3464C4E41540373B, 6),      # Рождённый огнём: ямы драугров
    "hel_tears": (0x76EBCCCDE0AFC298, 6),         # Плата Хель: разрывы Хель
    "lindwyrms_caught": (0x372C8AB1144B79B4, 6),  # Заблудившиеся линдвурмы: поймано
    "lindwyrms_returned": (0x778379D9A83DEFDE, 6),  # … возвращено
    "stags": (0xC2EAEC29A54569F6, 4),             # Олень всех времён
    "berserkers": (0xB2C7E8EEBFB1CD22, 12),       # В самый раз для короля: души берсерков
    "flowers": (0x7C7737D8EC5FC8D1, 9),           # Цветущие миры
    "tyr_statue": (0x79F50DA8F445A91E, 4),        # Путеводный свет: статуя Тюра
}
# Ряд «Просьбы Девяти миров» на панели (14.11.2026, вариант Б Alex): ключ счётчика → подпись значка (ru/en/uk).
# Значки — manifest «fav:<ключ>» (steamdeck/icons/out/2322010/fav_*.png); вороны — прежний ворон владельца.
FAVOR_ROW = (
    ("odin_ravens", {"ru": "Вороны Одина", "en": "Odin's Ravens", "uk": "Ворони Одіна"}),
    ("draugr_holes", {"ru": "Ямы драугров", "en": "Draugr Holes", "uk": "Ями драугрів"}),
    ("hel_tears", {"ru": "Разрывы Хель", "en": "Hel Tears", "uk": "Розриви Гель"}),
    ("lindwyrms_caught", {"ru": "Линдвурмы", "en": "Lindwyrms", "uk": "Ліндвурми"}),
    ("stags", {"ru": "Олени Иггдрасиля", "en": "Stags of Yggdrasil", "uk": "Олені Іґґдрасіля"}),
    ("berserkers", {"ru": "Души берсерков", "en": "Berserker Souls", "uk": "Душі берсерків"}),
    ("flowers", {"ru": "Цветы Девяти миров", "en": "Nine Realms in Bloom", "uk": "Квіти Дев'яти світів"}),
)
# Сундуки Норн (15.11.2026, из GameHub/gowsave.py, задача 198): всего открыто и рогов медовой крови — предметы кошелька;
# яблоки Идунн = сундуки − рога. Показываем, только если сходится с ярусами улучшений (части T1..T5 в кошельке).
NORNIR_CHESTS, BLOOD_MEAD_HORNS = 0x554185F25EFB1F0A, 0x2C22FF2C43DDDA89
RAGE_TIERS = (0x6CF01AFB41A1421E, 0x6CF01AFB41A15E6F, 0x6CF01AFB41A15A78, 0x6CF01AFB41A15649, 0x6CF01AFB41A1525A)
HEALTH_TIERS = (0x638E76C7E822F035, 0x638E76C7E822F424, 0x638E76C7E8220BD3, 0x638E76C7E8220FC2, 0x638E76C7E82203F1)
# Уровни оружия — блок снаряжения Char_HeroA00 (хеш предмета, тег 3, int32 ярус; уровень = ярус + 1).
# НЕ доказано (в хабе «proven: false» — по порядку слотов); только в progress, на панель не идёт (решение Alex 15.11).
WEAPONS = (("axe", 0x083E95365CC16313, {"ru": "Топор Левиафан", "en": "Leviathan Axe", "uk": "Сокира Левіафан"}),
           ("blades", 0x5EDA95A2FC221AEE, {"ru": "Клинки Хаоса", "en": "Blades of Chaos", "uk": "Клинки Хаосу"}),
           ("spear", 0xA1E318FD889AD3BA, {"ru": "Копьё Драупнир", "en": "Draupnir Spear", "uk": "Спис Драупнір"}))
ROW_LABELS = {"nornir": {"ru": "Сундуки Норн", "en": "Nornir Chests", "uk": "Скрині Норн"}}
NORNIR_NAMES = {"chests": {"ru": "Открыто сундуков Норн", "en": "Nornir Chests opened", "uk": "Відкрито скринь Норн"},
                "apples": {"ru": "Яблоки Идунн", "en": "Idunn Apples", "uk": "Яблука Ідунн"},
                "horns": {"ru": "Рога медовой крови", "en": "Horns of Blood Mead", "uk": "Роги медової крові"}}
FAVOR_ROW_LABEL = {"ru": "Просьбы Девяти миров", "en": "Nine Realms favors", "uk": "Прохання Дев'яти світів"}
FOLDERS = ("God of War Ragnarök", "God of War Ragnarok")


def _saved_games_dirs() -> List[Path]:
    out: List[Path] = []
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
                out.append(Path(os.path.expandvars(winreg.QueryValueEx(k, "{4C5C32FF-BB9D-43b0-B5B4-2D72E54EAAA4}")[0])))
        except OSError:
            pass
        home = Path(os.environ.get("USERPROFILE") or Path.home())
        out += [home / "Saved Games", home / "OneDrive/Saved Games"]
    out += [u / "Saved Games" for u in proton_user(APPID)]
    return out


def default_dirs() -> List[Path]:
    dirs = []
    for base in _saved_games_dirs():
        for name in FOLDERS:
            root = base / name
            if root.is_dir():
                dirs += [d for d in root.iterdir() if d.is_dir() and any(d.glob("GOWRSAVE*"))]
    return dirs


def header(buf: bytes) -> Optional[Dict[str, Any]]:
    if len(buf) < 0x1C0:
        return None
    if struct.unpack_from("<I", buf, 0x0C)[0] != MAGIC_VERSION or struct.unpack_from("<I", buf, 0x4C)[0] != MAGIC_VERSION:
        return None
    place = buf[STRING_OFFSET:STRING_END].split(b"\x00")[0].decode("utf-8", "replace").strip()
    return {"place": place,
            "play_seconds": struct.unpack_from("<I", buf, 0x190)[0],
            "objective_string_id": struct.unpack_from("<I", buf, 0x1B0)[0],
            "save_counter": struct.unpack_from("<I", buf, 0x1BC)[0]}


def split_place(place: str) -> Dict[str, Optional[str]]:
    """«Ванахейм - Джунгли - Отправиться в Муспельхейм» → мир / область / задание (разделитель пишет игра)."""
    parts = [p.strip() for p in (place or "").split(" - ") if p.strip()]
    if len(parts) >= 3:
        return {"realm": parts[0], "area": " - ".join(parts[1:-1]), "objective": parts[-1]}
    if len(parts) == 2:
        return {"realm": parts[0], "area": None, "objective": parts[1]}
    return {"realm": parts[0] if parts else None, "area": None, "objective": None}


def wallet(data: bytes) -> Dict[int, int]:
    off = data.find(struct.pack("<Q", HERO_WALLET_HASH))
    if off < 0:
        return {}
    try:
        count = struct.unpack_from("<I", data, off + 8)[0]
    except struct.error:
        return {}
    wallet, cur = {}, off + 20
    for _ in range(min(count, 100000)):
        if cur + 16 > len(data):
            break
        h, q = struct.unpack_from("<QI", data, cur)
        wallet[h] = q
        cur += 16
    return wallet


def journal(data: bytes) -> Dict[str, Dict[str, int]]:
    """Счётчики просьб из Table 1: {ключ: {"done", "total"}}; нет записи (просьба не начата) — ключа нет."""
    if len(data) < TABLE1_OFFSET + 4:
        return {}
    count = struct.unpack_from("<I", data, TABLE1_OFFSET)[0]
    end = TABLE1_OFFSET + 4 + count * 24
    if not 0 < count < 20000 or end > len(data):
        return {}
    ints = {}
    for h, val, _a, _b in struct.iter_unpack("<QQII", data[TABLE1_OFFSET + 4:end]):
        if val != TABLE1_BOOL_TRUE and val < (1 << 32):
            ints[h] = val >> 11
    out = {}
    for key, (h, total) in JOURNAL_COUNTERS.items():
        done = ints.get(h)
        if isinstance(done, int) and 0 <= done <= total:
            out[key] = {"done": done, "total": total}
    return out


def _tier(total: int):
    """Ярус и части по сумме: ярус t требует t частей (1, 2, 3 …) — как в gowsave._compute_tier_from_total."""
    if total <= 0:
        return (0, 0)
    t = 1
    while (t + 1) * t // 2 <= total:
        t += 1
    return (t, total - t * (t - 1) // 2)


def nornir(w: Dict[int, int]) -> Optional[Dict[str, int]]:
    """Сундуки Норн, яблоки, рога — только если сумма сходится с частями ярусов в кошельке."""
    if NORNIR_CHESTS not in w:
        return None
    chests, horns = w.get(NORNIR_CHESTS, 0), w.get(BLOOD_MEAD_HORNS, 0)
    apples = chests - horns
    if apples < 0:
        return None

    def wallet_tier(hashes):
        return next(((i + 1, w[h]) for i, h in enumerate(hashes) if w.get(h, 0) > 0), (0, 0))

    for total, hashes in ((horns, RAGE_TIERS), (apples, HEALTH_TIERS)):
        t, q = _tier(total)
        if q and wallet_tier(hashes) != (t, q):
            return None
    return {"chests": chests, "apples": apples, "horns": horns}


def weapon_levels(data: bytes) -> Dict[str, int]:
    pos = data.find(b"Char_HeroA00")
    if pos < 0:
        return {}
    want = {h: key for key, h, _ in WEAPONS}
    out, cur, end = {}, pos, min(len(data), pos + 0x2000)
    while cur + 13 <= end:
        if data[cur + 8] == 3:
            h = struct.unpack_from("<Q", data, cur)[0]
            lvl = struct.unpack_from("<i", data, cur + 9)[0]
            if 0 <= lvl <= 9 and h != 0:
                if h in want and want[h] not in out:
                    out[want[h]] = lvl + 1
                cur += 13
                continue
        cur += 1
    return out


def _cell(key, name, value, done=None, total=None):
    return {"key": key, "name": name, "value": str(value), "done": done if done is not None else value, "total": total}


def favor_row(j: Dict[str, Dict[str, int]], lang: str = "ru") -> Optional[Dict[str, Any]]:
    """Факт-ряд значков с счётчиками («groups», как у Sally Face): не начатая просьба — 0 из N."""
    if not j:
        return None
    people = []
    for key, names in FAVOR_ROW:
        total = JOURNAL_COUNTERS[key][1]
        done = (j.get(key) or {}).get("done", 0)
        people.append({"key": "fav:" + key, "name": names.get(lang) or names["ru"],
                       "done": done, "total": total, "value": f"{done}/{total}"})
    return {"kind": "fav", "label": FAVOR_ROW_LABEL.get(lang) or FAVOR_ROW_LABEL["ru"], "people": people}


def panel_row(j, n, lang: str = "ru") -> Optional[Dict[str, Any]]:
    """Один факт-ряд из групп значков: сундуки Норн · просьбы Девяти миров."""
    pick = lambda d: d.get(lang) or d["ru"]
    groups = []
    if n:
        groups.append({"kind": "fav", "label": pick(ROW_LABELS["nornir"]), "people": [
            _cell("nornir:" + k, pick(NORNIR_NAMES[k]), n[k]) for k in ("chests", "apples", "horns")]})
    # уровень оружия на панель не выводим (15.11 Alex: «лишнее, без него лучше и один ряд») — только в progress
    fr = favor_row(j, lang)
    if fr:
        groups.append(fr)
    return {"id": "gow_favors", "groups": groups} if groups else None


def find(path_or_dir: Optional[Union[str, Path]] = None) -> Optional[Path]:
    """Самый свежий слот: по счётчику сохранений игры (mtime у старых копий бывает перепутан)."""
    if path_or_dir is not None and Path(path_or_dir).is_file():
        return Path(path_or_dir)
    dirs = [Path(path_or_dir)] if path_or_dir is not None else default_dirs()
    best, key = None, None
    for d in dirs:
        for p in d.glob("GOWRSAVE*"):
            try:
                with p.open("rb") as f:
                    h = header(f.read(0x1C0))
            except OSError:
                continue
            if h and h["place"]:
                k = (h["save_counter"], p.stat().st_mtime)
                if key is None or k > key:
                    best, key = p, k
    return best


def read(path_or_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    try:
        return _read(path_or_dir)
    except Exception as e:
        return empty(f"сохранение God of War Ragnarök не прочитано: {e}")


def _read(path_or_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    path = find(path_or_dir)
    if not path:
        return empty("сохранения God of War Ragnarök не найдены")
    data = read_bytes(path)
    h = header(data)
    if not h:
        return empty("заголовок сейва не распознан")
    sp = split_place(h["place"])
    facts = []
    w = wallet(data)
    j = journal(data)
    rv = (j["odin_ravens"]["done"] if "odin_ravens" in j else
          w.get(RAVEN_ITEM, 0) + 3 * w.get(RAVEN_GIFT, 0) if (RAVEN_ITEM in w or RAVEN_GIFT in w) else None)
    silver = w.get(HACKSILVER)
    nn, wl = nornir(w), weapon_levels(data)
    row = panel_row(j, nn, lang())
    if rv is not None and not j:   # вороны есть в ряду просьб — отдельным фактом не повторяем
        facts.append(fact("raven", "Вороны Одина", f"{rv} / {RAVENS_TOTAL}"))
    if silver is not None:
        facts.append(fact("coins", "Серебро", num(silver)))
    if dur(h["play_seconds"]):
        facts.append(fact("clock", "Время игры", dur(h["play_seconds"])))
    if row:
        facts.append(row)
    return finish({
        "place": h["place"],   # как пишет игра: карточка делит по последнему « - » на место и задание
        "objective": None,   # задание уже в place; иначе карточка повторит его строкой пояснения
        "progress": {"realm": sp["realm"], "area": sp["area"], "objective": sp["objective"],
                     "hacksilver": silver, "odin_ravens": rv, "save_counter": h["save_counter"],
                     "objective_string_id": h["objective_string_id"], "journal": j,
                     "nornir": nn, "weapon_levels": wl},
        "facts": facts,
        "play_seconds": h["play_seconds"],
        "proven": ["place", "objective", "hacksilver", "odin_ravens", "play_seconds", "journal", "nornir"],
        "unproven": ["weapon_levels"],
    }, path)


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(read(sys.argv[1] if len(sys.argv) > 1 else None), ensure_ascii=False, indent=1, default=str))
