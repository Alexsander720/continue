"""Inscryption FullSerializer save: mode, permanent story history and Kaycee stats.

The game skips currentScene updates in Ascension; the owner's GBC scene is stale.
Names and enum values come only from codex/tools/inscryption_tables.py.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
IS_CODEX=HERE.parent.name=='codex'
ROOT=HERE.parents[1] if IS_CODEX else HERE.parent
if __package__!='ddsaves':
    GAMEHUB=ROOT.parents[min(2, len(ROOT.parents) - 1)]/'GameHub' if IS_CODEX else HERE.parent
    sys.path.insert(0,str(GAMEHUB))
from ddsaves._common import localize, select, ui, empty, fact, finish, game_dirs, newest, num, proton_user

APPID=1092790
TABLE_PATH=(HERE.parent/'data' if IS_CODEX else HERE/'data')/'inscryption.json'
T=json.loads(TABLE_PATH.read_text(encoding='utf-8'))

class _FullSerializer:
    """JSON plus actual $iref:N and unnamed vector components; preserves references."""
    def __init__(self,text):self.text=text;self.pos=0;self.decoder=json.JSONDecoder()
    def ws(self):
        while self.pos<len(self.text) and self.text[self.pos].isspace():self.pos+=1
    def value(self):
        self.ws()
        if self.pos>=len(self.text):raise ValueError('Truncated FullSerializer')
        c=self.text[self.pos]
        if self.text.startswith('$iref:',self.pos):
            m=re.match(r'\$iref:(\d+)',self.text[self.pos:])
            if m is None:raise ValueError('Invalid reference')
            self.pos+=len(m.group());return {'$ref':int(m.group(1))}
        if c=='{':
            self.pos+=1;out={};values=[];self.ws()
            while self.pos<len(self.text) and self.text[self.pos]!='}':
                if self.text[self.pos]=='"':
                    key,self.pos=self.decoder.raw_decode(self.text,self.pos);self.ws()
                    if self.text[self.pos]!=':':raise ValueError('Object key without colon')
                    self.pos+=1;out[key]=self.value()
                else:
                    v=self.value()
                    if not isinstance(v,(int,float)) or isinstance(v,bool):raise ValueError('Invalid vector component')
                    values.append(v)
                self.ws()
                if self.text[self.pos]==',':self.pos+=1;self.ws()
                elif self.text[self.pos]!='}':raise ValueError('Object separator absent')
            if self.pos>=len(self.text):raise ValueError('Unclosed object')
            self.pos+=1
            if values:out['$values']=values
            return out
        if c=='[':
            self.pos+=1;out=[];self.ws()
            while self.pos<len(self.text) and self.text[self.pos]!=']':
                out.append(self.value());self.ws()
                if self.text[self.pos]==',':self.pos+=1;self.ws()
                elif self.text[self.pos]!=']':raise ValueError('Array separator absent')
            if self.pos>=len(self.text):raise ValueError('Unclosed array')
            self.pos+=1;return out
        value,self.pos=self.decoder.raw_decode(self.text,self.pos);return value

def load(path):
    reader=_FullSerializer(Path(path).read_text(encoding='utf-8-sig'));data=reader.value();reader.ws()
    if reader.pos!=len(reader.text):raise ValueError('Trailing save content')
    refs={}
    def register(v):
        if isinstance(v,dict):
            if '$id' in v:refs[int(v['$id'])]=v
            for x in v.values():register(x)
        elif isinstance(v,list):
            for x in v:register(x)
    register(data)
    return data,refs

def _resolve(value,refs):
    seen=set()
    while isinstance(value,dict) and set(value)=={'$ref'}:
        key=value['$ref']
        if key in seen or key not in refs:raise ValueError('Unresolved/cyclic save reference')
        seen.add(key);value=refs[key]
    return value

def _list(value,refs):
    value=_resolve(value,refs)
    if isinstance(value,list):return value
    if not isinstance(value,dict):return []
    key='$pcontent' if '$pcontent' in value else '$rcontent'
    items=value.get(key,[])
    if not isinstance(items,list):raise ValueError('Invalid FullSerializer array')
    length=value.get('$plength' if key=='$pcontent' else '$rlength')
    if length is not None and length!=len(items):raise ValueError('FullSerializer array length mismatch')
    return items

def default_files():
    roots=game_dirs('Inscryption')   # все библиотеки Steam (другие диски ПК, microSD Деки)
    files=[r/'SaveFile.gwsave' for r in roots if (r/'SaveFile.gwsave').is_file()]
    # Actual game SaveFolderPath is Application.dataPath + '/../': installation
    # roots above are primary. Also support a supplied or nonstandard Proton tree.
    if not files:
        for user in proton_user(APPID):
            prefix=user.parents[3]
            if prefix.is_dir():files.extend(prefix.rglob('SaveFile.gwsave'))
    return files

def find(path_or_dir=None):
    if path_or_dir is None:return newest(default_files())
    p=Path(path_or_dir)
    if p.is_file():return p
    if not p.is_dir():return None
    main=p/'SaveFile.gwsave'
    return main if main.is_file() else newest(p.rglob('SaveFile.gwsave'))

def _stats(value,refs):
    """Missing stat entry is zero in actual GetStatValue, not missing save data."""
    T = localize(globals()["T"])
    value=_resolve(value,refs)
    if not isinstance(value,(dict,list)):return None
    result={meta['enum_name']:0 for meta in T['stat_types'].values()}
    seen=set()
    for row in _list(value,refs):
        row=_resolve(row,refs)
        key=str(row.get('type'))
        if key in seen:raise ValueError('Duplicate ascension stat')
        seen.add(key)
        if key in T['stat_types']:result[T['stat_types'][key]['enum_name']]=row.get('value')
    return result

def _run_summary(run,refs,seed=None):
    T = localize(globals()["T"])
    run=_resolve(run,refs)
    if not isinstance(run,dict):return None
    deck=_resolve(run.get('playerDeck') or run.get('deck') or {},refs)
    ids=_list(deck.get('cardIds'),refs)
    names=[T['cards'].get(cid,{}).get('name') for cid in ids]
    replacements=[]
    for entry in _list(deck.get('cardIdModInfos'),refs):
        entry=_resolve(entry,refs)
        for mod in _list(entry.get('$v'),refs):
            mod=_resolve(mod,refs)
            if mod.get('nameReplacement'):replacements.append({'card_key':entry.get('$k'),'name':mod['nameReplacement']})
    nodes=_list((run.get('map') or {}).get('nodeData'),refs)
    node=next((_resolve(v,refs) for v in nodes if _resolve(v,refs).get('id')==run.get('currentNodeId')),None)
    return {**{k:run.get(k) for k in ('currency','skullTeeth','playerLives','maxPlayerLives','regionTier',
                                    'currentNodeId','completed','gaveUp','runIntroCompleted')},
            'regionOrder':_list(run.get('regionOrder'),refs),'seed':seed,
            'card_ids':ids,'deck_count':len(ids),'card_names':names,'card_name_replacements':replacements,
            'unknown_card_ids':[cid for cid,name in zip(ids,names) if name is None],
            'current_node':{k:node.get(k) for k in ('id','gridX','gridY')} if node else None}

def _read_data(data,refs,path):
    T = localize(globals()["T"])
    ascension=bool(data.get(T['ascension_flag'],False))
    label=T['ascension_label']['ru'] or T['ascension_label']['en']
    scene=data.get('currentScene')
    predicates={name:needle in str(scene or '').lower() for name,needle in T['scene_predicates'].items()}
    story_raw=_list((data.get('storyEvents') or {}).get('completedEvents'),refs)
    story=[T['story_event_enum'].get(str(x),x) for x in story_raw]
    dialogue=_list((data.get('dialogueData') or {}).get('eventData'),refs)
    asc=data.get('ascensionData') or {}
    run=_run_summary(asc.get('currentRun'),refs,asc.get('currentRunSeed'))
    can_continue=run is not None and isinstance(run['playerLives'],int) and run['playerLives']>0
    completion=T['story_completion']
    achievement_raw=_list(data.get('unlockedAchievements'),refs)
    achievement_ids=sorted({x for x in achievement_raw if str(x) in T['achievement_enum']})
    # Achievement 9 is granted at the START of the finale. On its own it does
    # not prove the ending was watched. ChapterSelectUnlocked is permanent and
    # is set with FullGameCompleted after the ending video; require both after
    # a chapter reset. The game also has a debug shortcut for chapter selection.
    full_event=completion['completed_event'] in story_raw
    permanent=completion['chapter_select_event'] in story_raw and completion['finale_achievement'] in achievement_ids
    story_completed=True if full_event or permanent else None
    basis='FullGameCompleted' if full_event else 'permanent_event_and_achievement' if permanent else None
    stats=asc.get('stats') or {}
    all_time=_stats(stats.get('allTimeStats'),refs)
    current_stats=_stats(stats.get('currentRunStats'),refs)
    level=asc.get('challengeLevel')
    challenges=_list(asc.get('activeChallenges'),refs)
    challenge_rows=[T['challenges'].get(str(x)) for x in challenges]
    unlocked=[tier for tier in T['unlock_schedule'] if isinstance(level,int) and tier['index']<level]
    gbc=data.get('gbcData') or {}
    progress={'ascension_active':ascension,'mode_name':label if ascension else None,
              'saved_scene':scene,'saved_scene_predicates':predicates,
              'saved_scene_is_current':False if ascension else None,
              'play_seconds':data.get('playTime'),'story_events_raw':story_raw,'story_events':story,
              'last_story_event_raw':story[-1] if story else None,
              'dialogue_events':dialogue,'dialogue_names_mapped':sum(v.get('eventId') in T['dialogue_events'] for v in dialogue),
              'last_new_dialogue_id_raw':dialogue[-1].get('eventId') if dialogue else None,
              'ascension_dialogue_events':_list((asc.get('dialogueData') or {}).get('eventData'),refs),
              'story_ever_completed':story_completed,'story_completion_basis':basis,
              'achievement_ids':achievement_ids,'achievements_count':len(achievement_ids),
              'achievements_total':T['achievement_total'],
              'current_run':_run_summary(data.get('currentRun'),refs),
              'ascension_run':run,'ascension_run_available':run is not None,
              'ascension_run_continue_available':can_continue,
              'ascension_stats':{'all_time':all_time,'current_run':current_stats},
              'ascension_challenge_level':level,'ascension_active_challenges':challenges,
              'ascension_active_challenge_names':[row['title']['name'] if row else None for row in challenge_rows],
              'ascension_active_challenge_points':sum(row['points'] for row in challenge_rows) if all(challenge_rows) else None,
              'ascension_unlocked_challenges':sorted({x for tier in unlocked for x in tier['challenges']}),
              'ascension_unlocked_bonus_cards':[x for tier in unlocked for x in tier['cards']],
              'ascension_conquered_challenges':_list(asc.get('conqueredChallenges'),refs),
              'ascension_conquered_starter_decks':_list(asc.get('conqueredStarterDecks'),refs),
              'gbc_cards_collected':_list(data.get('gbcCardsCollected'),refs),
              'gbc':{'currency':gbc.get('currency'),'overworld_scene':gbc.get('overworldScene'),
                     'overworld_node':gbc.get('overworldNode'),'card_ids':_list((gbc.get('deck') or {}).get('cardIds'),refs)},
              'part3':_run_summary(data.get('part3Data'),refs)}
    facts=[]  # ПРАВКА Claude 06.10 (владелец): «Режим» не нужен
    proven=['ascension_active']+(['mode_name','saved_scene_is_current'] if ascension else [])
    unproven=['act','place','chapter','objective','last_event','play_seconds','story_events',
              'dialogue_events','current_run','gbc','part3','ascension_challenge_level',
              'ascension_active_challenges','ascension_active_challenge_names','ascension_active_challenge_points',
              'ascension_unlocked_challenges','ascension_unlocked_bonus_cards','ascension_conquered_challenges',
              'ascension_conquered_starter_decks','gbc_cards_collected']
    if story_completed:
        pass  # ПРАВКА Claude 06.10 (владелец): «Основной сюжет: Пройден» не нужен
        proven+=['story_ever_completed','story_completion_basis']
    else:unproven+=['story_ever_completed','story_completion_basis']
    if 'unlockedAchievements' in data:
        pass  # ПРАВКА Claude 05.10: «Достижения 29 / 40» уже в строке Steam на карточке — дубль убран
        proven+=['achievements_count','achievements_total','achievement_ids']
    if ascension:
        proven+=['ascension_run_available','ascension_run_continue_available']
        if run is not None:
            proven += ['ascension_run.'+k for k in ('deck_count','currency','playerLives','maxPlayerLives')]
            if not run['unknown_card_ids'] and not run['card_name_replacements']:proven.append('ascension_run.card_names')
            else:unproven.append('ascension_run.card_names')
            unproven+=['ascension_run.'+k for k in ('regionTier','regionOrder','currentNodeId','current_node','seed','skullTeeth')]
        # The menu's own RunExists requires lives>0; never show a dead run as
        # current playable resources, and never fall back to the story branch.
        if can_continue and not run['completed'] and not run['gaveUp']:
            facts.append(fact('book','Колода',ui("cards", n=run["deck_count"])))
            if isinstance(run['currency'],int):facts.append(fact('coin','Зубы',num(run['currency'])))
            if isinstance(run['playerLives'],int) and isinstance(run['maxPlayerLives'],int):
                facts.append(fact('heart','Жизни',f"{run['playerLives']} / {run['maxPlayerLives']}"))
        if all_time is not None:
            # Only stats which actually change in the real 06.09 -> Deck series
            # get facts. Unchanging Victories=0 and MostBones=30 stay debug.
            proven_stats={'Losses','BossesDefeated','CardsDrawn','MostDamageDealt','SquirrelsKilled',
                          'SacrificesMade','PeltsTraded','TeethPulled','MantisGodsPicked','Misplays'}
            for meta in T['stat_types'].values():
                name=meta['enum_name'];key='ascension_stats.all_time.'+name
                (proven if name in proven_stats else unproven).append(key)
                if name == 'MostDamageDealt':   # ПРАВКА Claude 06.10: поражения/боссы/оплошности владелец убрал, оставлен только рекорд урона
                    icon='skull' if name=='Losses' else 'sword' if name in ('BossesDefeated','MostDamageDealt') else 'eye'
                    facts.append(fact(icon,meta['label']['name'],num(all_time[name]), id='most_damage_dealt'))
            unproven.append('ascension_stats.current_run')
    progress['resume_summary']=' · '.join(x for x in (ui('story_completed') if story_completed else None,label if ascension else None) if x) or None
    if progress['resume_summary']:proven.append('resume_summary')
    return finish({'place':None,'chapter':None,'objective':None,'progress':progress,
                   'facts':facts,'proven':proven,'unproven':unproven},path)

def read(path_or_dir=None):
    path=find(path_or_dir)
    if path is None:return empty('Сохранение Inscryption не найдено')
    try:
        data,refs=load(path)
        if not isinstance(data,dict) or str(data.get('$type','')).split('|')[-1]!='SaveFile, Assembly-CSharp':
            return empty('Файл не содержит SaveFile Inscryption')
        return _read_data(data,refs,path)
    except (ValueError,OSError,IndexError,TypeError,AttributeError,KeyError) as e:
        return empty('Не удалось прочитать Inscryption: '+str(e))

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(read(sys.argv[1] if len(sys.argv)>1 else None),ensure_ascii=False,indent=2))
