"""Little Nightmares II: bounded custom HeliosSave; exact RU chapter table."""
import json
import math
import os
import sys
from pathlib import Path

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
if __package__!='ddsaves':
    _here=Path(__file__).resolve().parent
    sys.path.insert(0,str(ROOT.parents[min(2, len(ROOT.parents) - 1)]/'GameHub' if _here.parent.name=='codex' else _here.parent))
from ddsaves._common import localize, select, ui, dur,empty,fact,finish,newest,proton_user
if __package__=='ddsaves':from ._nightmares_binary import Cursor,helios
else:
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from _nightmares_binary import Cursor,helios

APPID=860510
HERE=Path(__file__).resolve().parent
TABLE=HERE.parent/'data/little_nightmares_2.json' if HERE.parent.name=='codex' else HERE/'data/little_nightmares_2.json'
T=json.loads(TABLE.read_text(encoding='utf-8'))


def metadata_collections(raw):
    """Bounded original MetaData arrays; collection meaning remains unproven."""
    records=helios(raw)['managers']['__CollectibleProxyManager_<2>']['chalkboard']
    prefix='/Persistent/Collectibles/'
    if set(records)!={prefix+'0',prefix+'1'}:
        raise ValueError('unrecognized global collection records')
    ids={}
    for group in ['0','1']:
        record=records[prefix+group]
        if not isinstance(record,dict) or record.get('raw_type')!=64:
            raise ValueError('unrecognized collection payload type')
        cursor=Cursor(bytes.fromhex(record['raw_hex']))
        values=[cursor.fstr() for _ in range(cursor.count(1000))]
        if cursor.p!=len(cursor.b) or len(values)!=len(set(values)):
            raise ValueError('collection array boundary or duplicate ID')
        ids[group]=values
    return {'ids':ids,'counts':{group:len(values) for group,values in ids.items()}}


def find(path_or_dir=None):
    if path_or_dir is None:
        roots=[Path(os.environ['LOCALAPPDATA'])/'Helios/Saved/SaveGames'] if os.environ.get('LOCALAPPDATA') else []
        roots += [p/'AppData/Local/Helios/Saved/SaveGames' for p in proton_user(APPID)]
        return newest(f for root in roots for f in root.glob('ProgressionMetaData_*.sav'))
    p=Path(path_or_dir)
    if p.is_file():
        if p.name.startswith('ProgressionMetaData_'):return p
        if p.name.startswith('Data_'):return p.with_name('ProgressionMeta'+p.name)
        return newest(p.parent.glob('ProgressionMetaData_*.sav'))
    return newest(p.rglob('ProgressionMetaData_*.sav')) if p.is_dir() else None


def read(path_or_dir=None):
    T = localize(globals()["T"])
    path=find(path_or_dir)
    if path is None or not path.is_file():return empty('Прогресс Little Nightmares II не найден')
    try:
        full=helios(path.read_bytes())
        records=full['managers']['__Manager_<MetaGameProgression>']['MetaGameProgressionChalkboard']
        prefix='/Persistent/MetaGameProgression/'
        slot=records[prefix+'SaveSlotName'];level=slot['text']
    except (OSError,ValueError,UnicodeError,IndexError,KeyError,TypeError):
        return finish(empty('Не разобран настоящий HeliosSave'),path)
    row=T['levels'].get(level);chapter=row['localized']['ru']['text'] if row else None
    play=records.get(prefix+'CurrentPlayTime');ticks=records.get(prefix+'SaveSlotTime')
    progress={'level_asset':level,'slot_name_raw':slot,'level_index_reached':records.get(prefix+'LevelIndexReached'),
              'play_seconds':play,'save_ticks':ticks,'records':records,'hats':None,'remains':None}
    metadata=path.parent/'MetaData.sav'
    collection_data=None;collection_error=None
    if metadata.is_file():
        try:collection_data=metadata_collections(metadata.read_bytes())
        except (OSError,ValueError,UnicodeError,IndexError,KeyError,TypeError):
            collection_error='Глобальные коллекции MetaData.sav не разобраны'
    else:collection_error='MetaData.sav отсутствует'
    progress.update(collection_ids=collection_data['ids'] if collection_data else None,
                    collection_counts=collection_data['counts'] if collection_data else None,
                    collection_metadata_path=str(metadata) if metadata.is_file() else None,
                    collection_metadata_error=collection_error)
    facts=[];proven=[]
    if chapter:proven.extend(['place','chapter'])
    if isinstance(play,(int,float)) and math.isfinite(play) and play>=0:
        proven.append('play_seconds');facts.append(fact('clock','В этом сейве',dur(play)))
    return finish({'place':chapter,'chapter':chapter,'objective':None,'progress':progress,'facts':facts,
                   'proven':proven,'unproven':['objective','level_index_reached','save_ticks','hats','remains','collection_ids','collection_counts']},path)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(read(sys.argv[1] if len(sys.argv)>1 else None),ensure_ascii=False,indent=2))
