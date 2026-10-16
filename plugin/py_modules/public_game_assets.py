"""Public sanitized game icons seeder (stdlib only, offline, no network/subprocess).

Ships the owner-authored custom fact icons/portraits to public PC builds without
touching owner files. Source of truth is the packaged subtree
``public_assets/game_icons/`` (manifest.json + referenced images), itself copied
byte-exact from steamdeck/icons/out (see sheets.py/make_icons.py provenance).

Canonical manifest: {appid: {stable fact id | "person:<key>": "<appid>/<file>"}}.
Russian source labels are translated via the labels/fact mapping used by
plugin/GameHubDeck/main.py::_apply_icons (legacy + labels values). Portrait labels
"Персонаж: <key>" become "person:<key>". Unmapped labels are preserved verbatim;
filenames alone never create associations; missing images are never recorded.

Safety: strict AppIDs, allowlisted IDs only, PNG/SVG/JPG/WebP, bounded count/size,
symlink/traversal rejection, user files preserved (existing bytes win), atomic
manifest merge (user mappings win). No full paths, no network, no subprocess.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict

# IDs shipped in continue-public/plugin/py_modules/deck_saves.py READERS (public only).
# Private/unpublished game icon sets are excluded even if present upstream.
ALLOWED_APPIDS = frozenset({
    367520, 2950340, 245280, 1809540, 1092790, 391540, 646570, 424840,
    2149010, 860510, 2651280, 2129530, 108710, 524220, 532210, 2420110,
    1903340, 2172010, 2124490, 1689620, 1426210, 990080, 1874000, 2322010,
    2531310, 1659420,
})

ALLOWED_EXTS = frozenset({".png", ".svg", ".jpg", ".jpeg", ".webp"})
MAX_ENTRIES = 400
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 150 * 1024 * 1024
MAX_LABEL_LEN = 200
_MAX_APPID = 0xFFFFFFFF
_APPID_STR_RE = re.compile(r"[1-9][0-9]{0,9}")
_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-]*")

# RU/EN/UK label -> stable fact id (from ddsaves/data/_labels.json labels+legacy).
# Generated 2026-10-14 from owner-active _labels.json; embedded so runtime reads no owner files.
_RU_TO_ID = {
    '3D World levels': 'levels_3dworld',
    'Abilities': 'abilities',
    'Achievements': 'achievements',
    'Act / floor': 'act_floor',
    'Active play': 'active_time',
    'Armor': 'armor',
    'Ascension': 'ascension',
    "Brothers' relationship": 'brotherhood',
    'Butterfly effects': 'butterflies',
    'Chapter': 'chapter',
    'Character': 'character',
    'Charms': 'charms',
    'Clues': 'clues',
    'Collectibles': 'collected',
    'Collections': 'collections',
    'Completed': 'completed',
    'Completion': 'game_percent',
    'Currently alive': 'alive_count',
    'DLC items': 'dlc_items',
    "Daniel's morality": 'morality',
    'Deaths': 'deaths',
    'Deck': 'deck',
    'Difficulty': 'difficulty',
    'Divine beasts': 'beasts',
    'Dreamers': 'dreamers',
    'Encyclopedia': 'encyclopedia',
    'Endings': 'endings_unlocked',
    'Enemies killed': 'kills_total',
    'Episode': 'episode',
    'Episodes completed': 'episodes_completed',
    'Equipped jades': 'equipped_jades',
    'G': 'g',
    'Geo': 'geo',
    'Gold': 'gold',
    'Golden flags': 'gold_flags',
    'Green stars': 'green_stars',
    'Grubs': 'grubs',
    'HP': 'hp',
    'Handgun ammo': 'ammo_handgun',
    'Healing drinks': 'healing_drinks',
    'Healing potions': 'healing_potions',
    'Health': 'health',
    'Hearts': 'hearts',
    'House': 'house',
    'In this save': 'save_time',
    'Jades': 'jades',
    'Journal pages': 'journal_pages',
    'Kills': 'kills',
    'Koroks': 'koroks',
    'LV': 'lv',
    'Last memo': 'last_memo',
    'Last node': 'last_node',
    'Level': 'level',
    'Levels': 'levels',
    'Lives': 'lives',
    'Map locations investigated': 'investigated',
    'Maps by building': 'maps_by_building',
    'Maps in inventory': 'maps_count',
    'Masks': 'masks',
    'Max HP': 'max_hp',
    'Memos collected': 'memos_count',
    'Merlin trials': 'merlin_trials',
    'Minigames': 'minigames',
    'Money (G)': 'money_g',
    'Moons': 'moons',
    'Most damage dealt': 'most_damage_dealt',
    'Nail': 'nail',
    'Nomes': 'nomes',
    'Obtained seals': 'obtained_seals',
    "Odin's ravens": 'raven',
    'Part': 'part',
    'Photo locations': 'photos_done',
    'Photos': 'photos_taken',
    'Play time': 'play_time',
    'Posters': 'posters',
    'Prowler stashes': 'prowler_done',
    'Purple coins': 'regional_coins',
    'Quests': 'quests',
    'Rifle ammo': 'ammo_rifle',
    'Rupees': 'rupees',
    'Shotgun ammo': 'ammo_shotgun',
    'Shrines': 'shrines',
    'Side quests': 'quests_completed',
    'Silver': 'silver',
    'Skill points': 'skill_points',
    'Skills': 'skills',
    'Sol seals': 'seals',
    'Souvenirs': 'collectibles_count',
    'Spells': 'spells',
    'Spider-bots': 'spiderbots_done',
    'Spirit orbs': 'spirit_orbs',
    'Stamina': 'stamina',
    'Statues': 'statues',
    'Story': 'story',
    'Story route': 'story_route',
    'Syringes': 'healing_syringes',
    'Teeth': 'teeth',
    'Totems': 'totems',
    'Treasures Found': 'treasures_collected',
    'Unlocked ascension': 'unlocked_ascension',
    'Weapons': 'weapons',
    'Wins': 'wins',
    'Акт / поверх': 'act_floor',
    'Акт / этаж': 'act_floor',
    'Активної гри': 'active_time',
    'Амулети': 'charms',
    'Амулеты': 'charms',
    'Броня': 'armor',
    'В этом сейве': 'save_time',
    'Ветка сюжета': 'story_route',
    'Випробування Мерліна': 'merlin_trials',
    'Витривалість': 'stamina',
    'Возвышение': 'ascension',
    'Вознесіння': 'ascension',
    'Ворони Одіна': 'raven',
    'Вороны Одина': 'raven',
    'Время игры': 'play_time',
    'Выносливость': 'stamina',
    'Відкрите вознесіння': 'unlocked_ascension',
    'Гвоздь': 'nail',
    'Гео': 'geo',
    'Глава': 'chapter',
    'Грезящие': 'dreamers',
    'Гроші (G)': 'money_g',
    'Гусенички': 'grubs',
    'Гусенята': 'grubs',
    'Деньги (G)': 'money_g',
    'Докази': 'clues',
    'Досліджено на мапах': 'investigated',
    'Достижения': 'achievements',
    'Досягнення': 'achievements',
    'Енциклопедія': 'encyclopedia',
    'Епізод': 'episode',
    'Ефекти метелика': 'butterflies',
    'Живы сейчас': 'alive_count',
    'Жизни': 'lives',
    'Життя': 'lives',
    'Завдання': 'quests',
    'Задания': 'quests',
    'Заклинания': 'spells',
    'Заклинання': 'spells',
    'Зараз живі': 'alive_count',
    'Зброя': 'weapons',
    "Здоров'я": 'health',
    'Здоровье': 'health',
    'Здібності': 'abilities',
    'Зелені зірки': 'green_stars',
    'Зелёные звёзды': 'green_stars',
    'Знайдено скарбів': 'treasures_collected',
    'Знахідки': 'collected',
    'Золото': 'gold',
    'Золотые флаги': 'gold_flags',
    'Золоті прапори': 'gold_flags',
    'Зуби': 'teeth',
    'Зубы': 'teeth',
    'Зібрано записок': 'memos_count',
    'Изучено на картах': 'investigated',
    'Испытания Мерлина': 'merlin_trials',
    'Карт в инвентаре': 'maps_count',
    'Карты по зданиям': 'maps_by_building',
    'Колекції': 'collections',
    'Коллекции': 'collections',
    'Колода': 'deck',
    'Концовки': 'endings_unlocked',
    'Короки': 'koroks',
    'Кінцівки': 'endings_unlocked',
    'Лечебные напитки': 'healing_drinks',
    'Луны': 'moons',
    'Лікувальні зілля': 'healing_potions',
    'Лікувальні напої': 'healing_drinks',
    'Макс. HP': 'max_hp',
    'Макс. урон за 1 ход': 'most_damage_dealt',
    'Мап в інвентарі': 'maps_count',
    'Мапи за будівлями': 'maps_by_building',
    'Маски': 'masks',
    'Мини-игры': 'minigames',
    'Мораль Даниэля': 'morality',
    'Мораль Даніеля': 'morality',
    'Мрійники': 'dreamers',
    'Мініігри': 'minigames',
    'Місяці': 'moons',
    'Набої для гвинтівки': 'ammo_rifle',
    'Набої для дробовика': 'ammo_shotgun',
    'Набої для пістолета': 'ammo_handgun',
    'Навички': 'skills',
    'Навыки': 'skills',
    'Надеты нефриты': 'equipped_jades',
    'Найбільша завдана шкода': 'most_damage_dealt',
    'Найдено сокровищ': 'treasures_collected',
    'Находки': 'collected',
    'Нефрити': 'jades',
    'Нефриты': 'jades',
    'Номи': 'nomes',
    'Номы': 'nomes',
    'ОЗ': 'hp',
    'Оружие': 'weapons',
    'Остання записка': 'last_memo',
    'Останній вузол': 'last_node',
    'Открытое Возвышение': 'unlocked_ascension',
    'Отношения братьев': 'brotherhood',
    'Отримані печатки': 'obtained_seals',
    'Очки навичок': 'skill_points',
    'Очки навыков': 'skill_points',
    'Павукоботи': 'spiderbots_done',
    'Патроны для винтовки': 'ammo_rifle',
    'Патроны для дробовика': 'ammo_shotgun',
    'Патроны для пистолета': 'ammo_handgun',
    'Паукоботы': 'spiderbots_done',
    'Перемоги': 'wins',
    'Персонаж': 'character',
    'Печати Солов': 'seals',
    'Печатки Солів': 'seals',
    'Плакати': 'posters',
    'Плакаты': 'posters',
    'Побед': 'wins',
    'Побочные задания': 'quests_completed',
    'Побічні завдання': 'quests_completed',
    'Подобрано записок': 'memos_count',
    'Полученные печати': 'obtained_seals',
    'Последний узел': 'last_node',
    'Последняя записка': 'last_memo',
    'Предмети DLC': 'dlc_items',
    'Предметы DLC': 'dlc_items',
    'Пройдено': 'completed',
    'Пройдено епізодів': 'episodes_completed',
    'Пройдено эпизодов': 'episodes_completed',
    'Проходження': 'game_percent',
    'Прохождение': 'game_percent',
    'Розділ': 'chapter',
    'Рупии': 'rupees',
    'Рупії': 'rupees',
    'Рябиновый отвар': 'healing_potions',
    'Рівень': 'level',
    'Рівні': 'levels',
    'Рівнів 3D World': 'levels_3dworld',
    'Святилища': 'shrines',
    'Світлини': 'photos_taken',
    'Сердца': 'hearts',
    'Серебро': 'silver',
    'Серця': 'hearts',
    'Складність': 'difficulty',
    'Сложность': 'difficulty',
    'Смертей': 'deaths',
    'Снимки': 'photos_taken',
    'Споряджені нефрити': 'equipped_jades',
    'Способности': 'abilities',
    'Срібло': 'silver',
    'Статуетки': 'statues',
    'Статуэтки': 'statues',
    'Сторінки щоденника': 'journal_pages',
    'Стосунки братів': 'brotherhood',
    'Страницы дневника': 'journal_pages',
    'Сувениры': 'collectibles_count',
    'Сувеніри': 'collectibles_count',
    'Сфери духу': 'spirit_orbs',
    'Сферы духа': 'spirit_orbs',
    'Схованки Бродяги': 'prowler_done',
    'Сюжет': 'story',
    'Сюжетна гілка': 'story_route',
    'Тайники Бродяги': 'prowler_done',
    'Тотеми': 'totems',
    'Тотемы': 'totems',
    'У цьому збереженні': 'save_time',
    'Убивства': 'kills',
    'Убийства': 'kills',
    'Убито ворогів': 'kills_total',
    'Убито врагов': 'kills_total',
    'Улики': 'clues',
    'Уровень': 'level',
    'Уровней 3D World': 'levels_3dworld',
    'Уровни': 'levels',
    'Факультет': 'house',
    'Фиолетовые монеты': 'regional_coins',
    'Фотолокації': 'photos_done',
    'Фототочки': 'photos_done',
    'Фіолетові монети': 'regional_coins',
    'Цвях': 'nail',
    'Час гри': 'play_time',
    'Частина': 'part',
    'Часть': 'part',
    'Чистой игры': 'active_time',
    'Чудища': 'beasts',
    'Чудовиська': 'beasts',
    'Шприци': 'healing_syringes',
    'Шприцы': 'healing_syringes',
    'Энциклопедия': 'encyclopedia',
    'Эпизод': 'episode',
    'Эффекты бабочки': 'butterflies',
}


def _strict_appid(value):
    """Strict AppID int 1..0xFFFFFFFF; reject bool/float/else."""
    if isinstance(value, bool):
        raise ValueError("Invalid appid")
    if isinstance(value, int):
        if 1 <= value <= _MAX_APPID:
            return value
        raise ValueError("AppID out of range")
    if isinstance(value, str):
        s = value.strip()
        if _APPID_STR_RE.fullmatch(s) and int(s) <= _MAX_APPID:
            return int(s)
        raise ValueError("Invalid appid")
    raise ValueError("Invalid appid")


def _canonical_key(key):
    """Translate a source label to canonical key; preserve person:/stable ids."""
    if not isinstance(key, str):
        return None
    s = key.strip()
    if not s or len(s) > MAX_LABEL_LEN:
        return None
    if s.startswith("person:"):
        name = s[len("person:"):].strip()
        if not name or len(name) > 64 or not _NAME_RE.fullmatch(name):
            return None
        return "person:" + name
    if s.startswith("Персонаж:"):
        name = s.split(":", 1)[1].strip()
        if not name or len(name) > 64 or not _NAME_RE.fullmatch(name):
            return None
        return "person:" + name
    mapped = _RU_TO_ID.get(s)
    if mapped:
        return mapped
    if _NAME_RE.fullmatch(s) and len(s) <= 64:
        return s
    return s


def _safe_rel(rel, appid):
    """Validate canonical relative path '<appid>/<file>'; return normalized or None."""
    if not isinstance(rel, str) or not rel or len(rel) > 256:
        return None
    if "\\" in rel or rel.startswith("/") or rel.startswith("\\"):
        return None
    norm = rel.replace("\\", "/")
    parts = norm.split("/")
    if len(parts) != 2:
        return None
    dir_part, name = parts
    try:
        if _strict_appid(dir_part) != appid:
            return None
    except ValueError:
        return None
    if not name or name in (".", ".."):
        return None
    if ".." in parts:
        return None
    if len(name) > 128 or not _NAME_RE.fullmatch(name):
        return None
    suf = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if suf not in ALLOWED_EXTS:
        return None
    return str(appid) + "/" + name


def _inside_regular(path, root):
    """Reject every reparse point below the supplied root, including parents."""
    root, path = Path(root).absolute(), Path(path).absolute()
    try:
        path.relative_to(root)
        probe = path
        while True:
            if probe.exists() or probe.is_symlink():
                st = probe.lstat()
                if probe.is_symlink() or getattr(st, 'st_file_attributes', 0) & 0x400:
                    return False
            if probe == root:
                return True
            probe = probe.parent
    except (OSError, ValueError):
        return False


def _read_manifest(path, root):
    if not _inside_regular(path, root):
        raise ValueError('Unsafe icon manifest')
    with Path(path).open('rb') as stream:
        data = stream.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError('Icon manifest too large')
    value = json.loads(data.decode('utf-8'))
    if not isinstance(value, dict):
        raise ValueError('Invalid icon manifest')
    return value


def validate_manifest(packaged_asset_root):
    """Validate packaged game_icons/ root; return canonical {appid: {key: relpath}}.

    Skips private appids, unsafe paths, missing/unreadable files, oversize
    entries. Missing images are never recorded as available. JSON serializable.
    """
    root = Path(packaged_asset_root)
    man_path = root / "manifest.json"
    try:
        raw = _read_manifest(man_path, root)
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out = {}
    total_entries = 0
    total_bytes = 0
    for appid_raw in sorted(raw.keys(), key=str):
        try:
            appid = _strict_appid(appid_raw)
        except ValueError:
            continue
        if appid not in ALLOWED_APPIDS:
            continue
        mapping = raw[appid_raw]
        if not isinstance(mapping, dict):
            continue
        canon = {}
        for key in sorted(mapping.keys(), key=str):
            if total_entries >= MAX_ENTRIES:
                break
            rel = mapping[key]
            ck = _canonical_key(key)
            if ck is None or ck in canon:
                continue
            safe = _safe_rel(rel, appid) if isinstance(rel, str) else None
            if safe is None:
                continue
            fp = root / safe.split("/")[0] / safe.split("/")[1]
            try:
                if not _inside_regular(fp, root) or not fp.is_file():
                    continue
                size = fp.stat().st_size
            except OSError:
                continue
            if size <= 0 or size > MAX_FILE_BYTES:
                continue
            if total_bytes + size > MAX_TOTAL_BYTES:
                continue
            canon[ck] = safe
            total_entries += 1
            total_bytes += size
        if canon:
            out[str(appid)] = dict(sorted(canon.items()))
    return dict(sorted(out.items()))


def seed_game_icons(packaged_asset_root, data_root):
    """Copy packaged images to data_root/icons; atomic manifest merge (user wins).

    Existing destination bytes that differ are preserved (user custom overrides
    win). Only packaged-manifest images are copied. Returns JSON-serializable
    summary dict.
    """
    man = validate_manifest(packaged_asset_root)
    root = Path(packaged_asset_root)
    dest = Path(data_root) / "icons"
    if not _inside_regular(dest, data_root):
        raise ValueError('Unsafe icon destination')
    dest.mkdir(parents=True, exist_ok=True)
    copied = 0
    preserved = 0
    matched = 0
    for appid, mapping in man.items():
        for _key, rel in mapping.items():
            parts = rel.split("/")
            src = root / parts[0] / parts[1]
            dst = dest / parts[0] / parts[1]
            try:
                if not _inside_regular(dst, dest):
                    continue
                if not _inside_regular(src, root) or not src.is_file():
                    continue
                with src.open('rb') as stream:
                    data = stream.read(MAX_FILE_BYTES + 1)
            except OSError:
                continue
            if not data or len(data) > MAX_FILE_BYTES:
                continue
            try:
                if dst.is_file():
                    try:
                        with dst.open('rb') as stream:
                            existing = stream.read(MAX_FILE_BYTES + 1)
                    except OSError:
                        continue
                    if existing == data:
                        matched += 1
                    else:
                        preserved += 1
                    continue
                dst.parent.mkdir(parents=True, exist_ok=True)
                tmp = dst.parent / (dst.name + ".tmp.seed")
                try:
                    if not _inside_regular(tmp, dest):
                        continue
                    tmp.write_bytes(data)
                    os.replace(str(tmp), str(dst))
                    copied += 1
                finally:
                    try:
                        if tmp.exists() and not tmp.is_symlink():
                            tmp.unlink()
                    except OSError:
                        pass
            except OSError:
                continue
    dest_man = dest / "manifest.json"
    try:
        existing_man = _read_manifest(dest_man, dest)
    except FileNotFoundError:
        existing_man = {}
    merged = {a: dict(m) for a, m in man.items()}
    for appid_raw, mapping in existing_man.items():
        if not isinstance(mapping, dict):
            continue
        try:
            _strict_appid(appid_raw)
        except ValueError:
            continue
        cur = merged.setdefault(str(appid_raw), {})
        for k, v in mapping.items():
            if isinstance(k, str) and isinstance(v, str) and k and v:
                cur[k] = v
    ordered = {a: dict(sorted(m.items())) for a, m in sorted(merged.items(), key=lambda kv: kv[0])}
    try:
        tmp_man = dest / "manifest.json.tmp.seed"
        if not _inside_regular(tmp_man, dest) or not _inside_regular(dest_man, dest):
            raise ValueError('Unsafe icon manifest destination')
        tmp_man.write_text(json.dumps(ordered, ensure_ascii=False, indent=1, sort_keys=True),
                           encoding="utf-8")
        os.replace(str(tmp_man), str(dest_man))
    except OSError:
        pass
    finally:
        try:
            if tmp_man.exists() and not tmp_man.is_symlink():
                if tmp_man.read_text(encoding="utf-8") != json.dumps(
                        ordered, ensure_ascii=False, indent=1, sort_keys=True):
                    tmp_man.unlink()
        except OSError:
            pass
    return {"apps": len(man), "icons": sum(len(m) for m in man.values()),
            "copied": copied, "preserved": preserved, "matched": matched,
            "merged_keys": sum(len(m) for m in ordered.values())}
