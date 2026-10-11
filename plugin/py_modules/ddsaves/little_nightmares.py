"""Little Nightmares original PC: real AtlasMetaState and cooked RU tables."""
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
if __package__!='ddsaves':
    _here=Path(__file__).resolve().parent
    sys.path.insert(0,str(ROOT.parents[min(2, len(ROOT.parents) - 1)]/'GameHub' if _here.parent.name=='codex' else _here.parent))
from ddsaves._common import localize, select, ui, empty,fact,finish,newest,proton_user
if __package__=='ddsaves':
    from ._nightmares_binary import atlas_meta
else:
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from _nightmares_binary import atlas_meta

APPID=424840
HERE=Path(__file__).resolve().parent
TABLE=HERE.parent/'data/little_nightmares.json' if HERE.parent.name=='codex' else HERE/'data/little_nightmares.json'
T=json.loads(TABLE.read_text(encoding='utf-8'))


def find(path_or_dir=None):
    if path_or_dir is None:
        roots=[Path(os.environ['LOCALAPPDATA'])/'Atlas/Saved/SaveGames'] if os.environ.get('LOCALAPPDATA') else []
        roots += [p/'AppData/Local/Atlas/Saved/SaveGames' for p in proton_user(APPID)]
        return newest(f for root in roots for f in root.glob('*SaveSlot*_meta.sav'))
    p=Path(path_or_dir)
    if p.is_file():
        return p if p.name.endswith('_meta.sav') else p.with_name(p.stem+'_meta.sav')
    return newest(p.rglob('*SaveSlot*_meta.sav')) if p.is_dir() else None


def read(path_or_dir=None):
    T = localize(globals()["T"])
    path=find(path_or_dir)
    if path is None or not path.is_file():return empty('Метаданные Little Nightmares не найдены')
    try:meta=atlas_meta(path.read_bytes())
    except (OSError,ValueError,UnicodeError,IndexError):return finish(empty('Не разобран AtlasMetaState'),path)
    level=Path(meta.get('CPL',[''])[0]).name
    row=T['levels'].get(level)
    # Verify both exact package path and level ID against the cooked table.
    if row and row['asset'].split('.')[0]!=meta['CPL'][0]:row=None
    chapter=row['localized']['ru']['text'] if row else None
    collected=set(meta.get('C',[]));groups=Counter(T['collectibles'][k]['group'] for k in collected if k in T['collectibles'])
    totals=Counter(v['group'] for v in T['collectibles'].values())
    nomes=groups['ECollectibleType::Nome'];statues=groups['ECollectibleType::Statue']
    dlc=sum(v for k,v in groups.items() if k.startswith('ECollectibleType::DLC'))
    dlc_total=sum(v for k,v in totals.items() if k.startswith('ECollectibleType::DLC'))
    progress={'level_asset':level,'meta':meta,'nomes':nomes,'statues':statues,'dlc_collectibles':dlc,
              'nomes_total':totals['ECollectibleType::Nome'],'statues_total':totals['ECollectibleType::Statue'],
              'dlc_collectibles_total':dlc_total,'lights':sorted(k for k in collected if k not in T['collectibles']),
              'tpt_raw':meta.get('TPT'),'td_raw':meta.get('TD')}
    facts=[fact('smile','Номы',f'{nomes} / {progress["nomes_total"]}'),
           fact('gem','Статуэтки',f'{statues} / {progress["statues_total"]}')]
    if dlc:facts.append(fact('star','Предметы DLC',f'{dlc} / {dlc_total}'))
    return finish({'place':chapter,'chapter':chapter,'objective':None,'progress':progress,'facts':facts,
                   'proven':(['place','chapter'] if chapter else [])+['nomes','statues','dlc_collectibles'],
                   'unproven':['objective','lights','tpt_raw','td_raw']},path)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(read(sys.argv[1] if len(sys.argv)>1 else None),ensure_ascii=False,indent=2))
