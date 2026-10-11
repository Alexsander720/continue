"""Until Dawn Remake: GVAS, direct game tables and genuine alternative stages.

Discovered tracker entries exclude Locked; counts are NOT tracker length.
Butterfly CurrentValue is an opaque revision, not an index into cause rows.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
IS_CODEX = HERE.parent.name == 'codex'
ROOT = HERE.parents[1] if IS_CODEX else HERE.parent
if __package__ != 'ddsaves':
    GAMEHUB = ROOT.parents[min(2, len(ROOT.parents) - 1)]/'GameHub' if IS_CODEX else HERE.parent
    sys.path.insert(0, str(GAMEHUB))
from ddsaves import gvas
from ddsaves._common import localize, select, ui, empty, fact, finish, newest, proton_user

APPID = 2172010
TABLE_PATH = (HERE.parent/'data' if IS_CODEX else HERE/'data')/'until_dawn.json'
T = json.loads(TABLE_PATH.read_text(encoding='utf-8'))
DISCOVERED = {'Unseen', 'Seen', 'UpdatedUnseen', 'UpdatedSeen'}

def default_files():
    roots = []
    if os.environ.get('USERPROFILE'):
        roots += [Path(os.environ['USERPROFILE'])/d/'My Games/Bates/Saved/SaveGames'
                  for d in ('Documents','OneDrive/Documents','OneDrive/Документы')]
    roots += [u/'Documents/My Games/Bates/Saved/SaveGames' for u in proton_user(APPID)]
    return [f for r in roots if r.is_dir() for f in r.glob('*/SaveGame[0-9]*.sav')]

def find(path_or_dir=None):
    if path_or_dir is None: return newest(default_files())
    p = Path(path_or_dir)
    if p.is_file(): return p
    return newest(p.rglob('SaveGame[0-9]*.sav')) if p.is_dir() else None

def read(path_or_dir=None):
    T = localize(globals()["T"])
    path = find(path_or_dir)
    if path is None: return empty('Сохранение Until Dawn не найдено')
    p = gvas.unwrap(gvas.read(path.read_bytes())['props'])
    g = p.get('GameSaveData') or {}; level = p.get('LevelData') or {}
    if not all(k in g for k in ('TotemTracker','ClueTracker','ButterflyTracker')):
        return empty('Файл не содержит сюжетное сохранение Until Dawn')
    key = (p.get('GameSaveVersionData') or {}).get('ChapterNameKey')
    title = T['titles'].get(key)
    state_entries = (p.get('GlobalStateSaveData') or {}).get('StateBools', [])
    states = {k: v.get('bValue') if isinstance(v,dict) else None for k,v in state_entries}
    progress = {'chapter_key': key, 'chapter_title': title, 'act': level.get('Act'), 'part': level.get('Part'),
                'completed': p.get('bHasCompletedGame'), 'save_stamp': p.get('SaveTimeStamp'),
                'state_bools': states}
    facts = []; proven = []; unproven = ['act','part','completed','butterfly_consequences','objective']
    if title: proven += ['place','chapter']
    else: unproven += ['place','chapter']
    for plural, tracker in [('totems','TotemTracker'), ('clues','ClueTracker')]:
        raw = {k: str(v).split('::')[-1] for k,v in g.get(tracker, [])}
        selected = [k for k,v in raw.items() if v in DISCOVERED]
        table = T[plural]; unmapped = [k for k in selected if k not in table]
        unknown_status = {k:v for k,v in raw.items() if v not in DISCOVERED | {'Locked'}}
        singular = 'totem' if plural == 'totems' else 'clue'
        progress[singular+'_tracker'] = raw
        progress[plural] = len(selected)
        progress['unmapped_'+plural] = unmapped
        progress['unknown_'+singular+'_status'] = unknown_status
        names = [table[k]['title'] if plural=='clues' else table[k]['group_title']+' — '+table[k]['title']
                 for k in selected if k in table]
        progress[singular+'_names'] = names
        if not unmapped and not unknown_status:
            facts.append(fact('eye' if plural=='totems' else 'book', 'Тотемы' if plural=='totems' else 'Улики',
                              f'{len(selected)} / {len(table)}'))
            proven += [plural,singular+'_names']
        else: unproven += [plural,singular+'_names']
    butterflies = dict(g.get('ButterflyTracker', [])); unmapped = [k for k in butterflies if k not in T['butterflies']]
    progress['butterfly_tracker'] = butterflies
    progress['butterflies'] = len(butterflies)
    progress['unmapped_butterflies'] = unmapped
    progress['butterfly_names'] = [T['butterflies'][k]['title'] for k in butterflies if k in T['butterflies']]
    if not unmapped:
        facts.append(fact('leaf', 'Эффекты бабочки', f'{len(butterflies)} / {len(T["butterflies"])}'))
        proven += ['butterflies','butterfly_names']
    else: unproven += ['butterflies','butterfly_names']
    progress['death_flags'] = {k:v for k,v in states.items() if k.endswith('Dead')}
    roster=T['characters']
    occurrences={k:sum(1 for key,_ in state_entries if key==k) for k in roster}
    unknown=[k for k in roster if type(states.get(k)) is not bool or occurrences[k]!=1]
    alive=[row['title'] for k,row in roster.items() if states.get(k) is False]
    dead=[row['title'] for k,row in roster.items() if states.get(k) is True]
    progress.update({'alive':{row['raw_name']:not states[k] for k,row in roster.items()
                              if type(states.get(k)) is bool and occurrences[k]==1},
                     'alive_names':alive,'dead_names':dead,'character_total':len(roster),
                     'alive_count':len(alive) if not unknown else None,
                     'dead_count':len(dead) if not unknown else None,
                     'unknown_death_flags':unknown,
                     'other_death_flags':{k:v for k,v in progress['death_flags'].items() if k not in roster}})
    if not unknown:
        # ПРАВКА Claude 06.10 (владелец: «8 / 8 — Крис, Эшли…» тупо): один факт с массивом персонажей — плагин рисует портреты,
        # погибшие приглушены; «Погибли» отдельно не нужны (повторное подключение Codex это затрёт)
        people=[{'key':row['raw_name'],'name':row['title'],'alive':states.get(k) is False} for k,row in roster.items()]
        facts.append(dict(fact('heart','Живы сейчас',f'{len(alive)} / {len(roster)}'),people=people))
        proven+=['alive','alive_names','dead_names','alive_count','dead_count','character_total']
    else:
        unproven+=['alive','alive_names','dead_names','alive_count','dead_count']
    return finish({'place': title, 'chapter': title, 'objective': None, 'progress': progress,
                   'facts': facts, 'proven': proven, 'unproven': unproven}, path)

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(read(sys.argv[1] if len(sys.argv)>1 else None), ensure_ascii=False, indent=2))
