"""UNCHARTED LoT: game-written .save descriptor, verified on four LL stages and U4 owner.

Only known keyed chapters and the localized SAVEINFO descriptor are accepted.
The binary time is used solely to cross-check displayed hours/minutes; exact
millisecond semantics, campaign completion flag and icon index stay unproven.
"""
from __future__ import annotations
import os
from pathlib import Path
import re
import struct
from ddsaves._common import empty, finish, lang, proton_user, select, table, ui, fact

APPID = 1659420


def tables():
    return table('uncharted_lot')


def default_dirs():
    home = Path(os.environ['USERPROFILE']) if os.environ.get('USERPROFILE') else Path.home()
    roots = [home / 'Saved Games/Uncharted Legacy of Thieves Collection']
    roots.extend(user / 'Saved Games/Uncharted Legacy of Thieves Collection' for user in proton_user(APPID))
    return [path for root in roots for path in root.glob('users/*/*/saves') if path.is_dir()]


def find(path_or_dir=None):
    if path_or_dir is None:
        candidates = [p for root in default_dirs() for p in root.glob('*.save')]
    else:
        root = Path(path_or_dir)
        candidates = [root] if root.is_file() and root.suffix.lower() == '.save' else list(root.glob('*.save')) if root.is_dir() else []
    return sorted((p for p in candidates if p.is_file()), key=lambda p: p.stat().st_mtime, reverse=True)


def decode(path, names):
    try:
        with path.open('rb') as stream:
            raw = stream.read(0xA20)
        if len(raw) < 0xA20 or raw[:4] != bytes.fromhex('91ea0000'):
            return None
        text = raw[0x108:0x508].split(b'\0', 1)[0].decode('utf-8')
        lines = text.splitlines()
        if len(lines) != 3:
            return None
        matches = [(key, code) for key, values in names['chapters'].items()
                   for code in ('en', 'ru') if values.get(code) == lines[0]]
        keys = {key for key, _ in matches}
        if len(keys) != 1:
            return None
        key, code = matches[0]
        templates = names['templates'][code]
        completion = re.fullmatch(r'(\d{1,3})%\s+' + re.escape(templates['SAVEINFO_COMPLETE']) + r'\s+\(([^)]+)\)', lines[1])
        treasure = next((match for template in ('SAVEINFO_TREASURES', 'SAVEINFO_TREASURE')
                         if (match := re.fullmatch(re.escape(templates[template]).replace(r'\[A\]', r'(\d+)'), lines[2]))), None)
        if not completion or not treasure or int(completion[1]) > 100:
            return None
        time_pattern = re.escape(templates['TIME_HR_MIN']).replace(r'\[A\]', r'(?P<h>[0-9]+)').replace(r'\[B\]', r'(?P<m>[0-9]{1,2})')
        display_time = re.fullmatch(time_pattern, completion[2])
        if display_time is None:
            return None
        counts = [int(display_time['h']), int(display_time['m'])]
        minutes = struct.unpack_from('<I', raw, 0x9F0)[0] // 60000
        hours, minute = divmod(minutes, 60)
        # Verified fixture format includes both hour and minute components.
        # Unknown single-component formats stay empty instead of guessing units.
        if counts[1] >= 60 or counts != [hours, minute]:
            return None
        return {'chapter_key': key, 'completion_percent': int(completion[1]),
                'treasures_collected': int(treasure[1]), 'play_time_minutes': minutes,
                'descriptor_language': code}
    except (OSError, UnicodeError, ValueError, IndexError, struct.error):
        return None


def read(path_or_dir=None):
    names = tables()
    for path in find(path_or_dir):
        progress = decode(path, names)
        if progress is None:
            continue
        key = progress['chapter_key']
        title = select(names['chapters'][key])
        hours, minutes = divmod(progress['play_time_minutes'], 60)
        facts = [fact('pie', 'Прохождение', str(progress['completion_percent']) + '%', id='completion_percent'),
                 fact('gem', 'Найдено сокровищ', progress['treasures_collected'], id='treasures_collected'),
                 fact('clock', 'В этом сейве', ui('hours_minutes', h=hours, m=minutes), id='play_time_minutes')]
        return finish({'place': None, 'chapter': title, 'objective': None, 'progress': progress, 'facts': facts,
                       'proven': ['chapter', 'chapter_key', 'completion_percent', 'treasures_collected', 'play_time_minutes'],
                       'unproven': ['place', 'objective', 'game_completed', 'icon_index', 'play_time_ms', 'treasures_total'],
                       'fact_sources': {f['label']: f['id'] for f in facts}}, path)
    return empty('No verified UNCHARTED gameplay descriptor found')
