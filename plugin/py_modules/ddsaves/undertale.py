"""Undertale (391540): genuine file0/file9, source-generated EN names.

Line 4 is maxen, not current HP. The save contains maxhp; loading restores hp=maxhp.
Route/chapter/objective remain absent; a zero kill count does not prove an ending.
Uses only stdlib and the accepted ddsaves._common helpers.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
import json
import math
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
IS_CODEX = HERE.parent.name == 'codex'
ROOT = HERE.parents[1] if IS_CODEX else HERE.parent
if __package__ != 'ddsaves':
    GAMEHUB = ROOT.parents[min(2, len(ROOT.parents) - 1)]/'GameHub' if IS_CODEX else HERE.parent
    sys.path.insert(0, str(GAMEHUB))
from ddsaves._common import localize, select, ui, deck_home, dur, empty, fact, finish, newest, num, proton_user

APPID = 391540
TABLE_PATH = (HERE.parent/'data' if IS_CODEX else HERE/'data')/'undertale.json'
T = json.loads(TABLE_PATH.read_text(encoding='utf-8'))
# 04.10 (Claude): владелец — «всегда с переводом». Официального RU нет; фанатский русификатор (выгрузка Антигравити
# antigravity/dumps/undertale/rooms_ru.json, источник и sha256 там) — названия комнат с точками сохранения.
_RU_PATH = TABLE_PATH.parent / 'undertale_rooms_ru.json'
RU_ROOMS = json.loads(_RU_PATH.read_text(encoding='utf-8'))['data']['rooms'] if _RU_PATH.is_file() else {}

def default_dirs():
    dirs = []
    if os.environ.get('LOCALAPPDATA'):
        dirs.append(Path(os.environ['LOCALAPPDATA'])/'UNDERTALE')
    elif os.environ.get('USERPROFILE'):
        dirs.append(Path(os.environ['USERPROFILE'])/'AppData/Local/UNDERTALE')
    dirs.extend(p/'AppData/Local/UNDERTALE' for p in proton_user(APPID))
    dirs.extend([deck_home()/'.config/UNDERTALE', deck_home()/'.local/share/UNDERTALE'])
    return dirs

def find(path_or_dir=None):
    if path_or_dir is not None:
        p = Path(path_or_dir)
        if p.is_file():
            if p.name in ('file0', 'file9'):
                return p
            if p.name.lower() == 'undertale.ini':
                return find(p.parent)
            return None
        if not p.is_dir():
            return None
        return (newest(p.glob('file0')) or newest(p.rglob('file0'))
                or newest(p.glob('file9')) or newest(p.rglob('file9')))
    for directory in default_dirs():
        candidate = newest(directory.glob('file0')) or newest(directory.glob('file9'))
        if candidate:
            return candidate
    return None

def read(path_or_dir=None):
    RU_ROOMS = localize(globals()["RU_ROOMS"])
    T = localize(globals()["T"])
    path = find(path_or_dir)
    if path is None:
        return empty('Undertale file0/file9 не найден; INI не заменяет данные сохранения')
    try:
        lines = path.read_text(encoding='utf-8-sig').splitlines()
        if len(lines) != len(T['save_schema']):
            return empty(f'Неизвестный формат Undertale: {len(lines)} строк вместо {len(T["save_schema"])}')
        raw = {field: (lines[i].strip() if i == 0 else float(lines[i].strip()))
               for i, field in enumerate(T['save_schema'])}
        if any(not math.isfinite(value) for value in raw.values() if isinstance(value, float)):
            return empty('Undertale: нечисловые или бесконечные значения')
    except (OSError, UnicodeError, ValueError) as exc:
        return empty(f'Не удалось прочитать Undertale: {exc}')
    integer_fields = ('lv', 'maxhp', 'maxen', 'xp', 'gold', 'kills', 'weapon', 'armor', 'currentroom')
    if any(not raw[field].is_integer() for field in integer_fields):
        return empty('Undertale: дробное значение в целочисленном поле')
    ints = {key: int(raw[key]) for key in integer_fields}
    room_id = ints['currentroom']
    room = T['rooms'].get(str(room_id))
    weapon = T['items'].get(str(ints['weapon']))
    armor = T['items'].get(str(ints['armor']))
    seconds = raw['time']/T['time_frames_per_second']
    progress = {
        'player_name': raw['charname'], 'lv': ints['lv'], 'max_hp': ints['maxhp'],
        'hp': None, 'hp_on_load': ints['maxhp'], 'max_en': ints['maxen'],
        'exp': ints['xp'], 'gold': ints['gold'], 'kills': ints['kills'],
        'weapon_id': ints['weapon'], 'armor_id': ints['armor'],
        'weapon_name': weapon['name'] if weapon else None,
        'armor_name': armor['name'] if armor else None,
        'room_id': room_id, 'room_asset': T['room_assets'].get(str(room_id)),
        'inventory_ids': [int(raw[f'item[{i}]']) for i in range(8)],
        'phone_ids': [int(raw[f'phone[{i}]']) for i in range(8)],
        'flags': [raw[f'flag[{i}]'] for i in range(512)],
        'plot': raw['plot'], 'time_frames': raw['time'], 'play_seconds': seconds,
        'route': None,
        'base_attack': raw['at'], 'weapon_strength': raw['wstrength'],
        'base_defense': raw['df'], 'armor_defense': raw['adef'], 'sp': raw['sp'],
        'menuchoice': [raw[f'menuchoice[{i}]'] for i in range(3)], 'current_song_id': raw['currentsong'],
    }
    proven = ['lv','max_hp','exp','gold','kills','weapon_id','armor_id','room_id','play_seconds']
    facts = [fact('level', 'LV', ints['lv']), fact('heart', 'Макс. HP', ints['maxhp']),
             fact('coins', 'G', num(ints['gold']))]
    if weapon:
        proven.append('weapon_name')
        facts.append(fact('sword', 'Оружие', weapon['name']))
    if armor:
        proven.append('armor_name')
        facts.append(fact('shield', 'Броня', armor['name']))
    if ints['kills']:
        facts.append(fact('skull', 'Убийства', ints['kills']))
    if seconds >= 60:
        facts.append(fact('clock', 'В этом сейве', dur(seconds)))
    if room:
        proven.append('place')
    unproven = ['hp','route','chapter','objective','player_name','hp_on_load','max_en',
                'inventory_ids','phone_ids','flags','plot','base_attack','weapon_strength',
                'base_defense','armor_defense','sp','menuchoice','current_song_id']
    if not room:
        unproven.append('place')
    return finish({'place': (RU_ROOMS.get(str(room_id)) or room['name']) if room else None, 'chapter': None, 'objective': None,
                   'progress': progress, 'facts': facts, 'proven': proven, 'unproven': unproven,
                   'play_seconds': seconds}, path)

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(read(sys.argv[1] if len(sys.argv)>1 else None), ensure_ascii=False, indent=2))
