"""Standalone Deck music works independently of AC-only video work."""
import asyncio
import json
from pathlib import Path
import sys
import pytest
from test_support import main_module,as_release

MODULES=Path(__file__).resolve().parents[2]/'plugin/py_modules'
sys.path.insert(0,str(MODULES))


def plugin(tmp_path):
    from deck_music_backend import with_music
    module=main_module(tmp_path);as_release(module,tmp_path)
    return with_music(module.Plugin,module.DATA)()


def test_owner_methods_never_construct_optional_deck_runtime(tmp_path):
    from deck_music_backend import with_music
    module=main_module(tmp_path)
    module.__file__=str(tmp_path/'owner/main.py')
    p=with_music(module.Plugin,module.DATA)()
    assert asyncio.run(p.refresh_music(42))=={'ok':False,'standalone':False}
    assert not Path(module.DATA).exists()


def test_music_preparation_on_battery_never_builds_video(tmp_path):
    p=plugin(tmp_path);calls=[]
    p._music_allowed=lambda:True
    p._write_settings({'theme_music_consent':True,'hub_music':True,'home_music':True})
    class Manager:
        def prepare_music(self,*args,**kw):calls.append((args,kw));return {'ok':True}
    p._media=lambda:Manager()
    async def check():
        queued=await p.refresh_music(42,'Fixture');assert queued['pending']
        for _ in range(20):
            state=await p.music_job_status(queued['job'])
            if state['done']:return state
            await asyncio.sleep(.01)
    assert asyncio.run(check())['result']['ok']
    assert len(calls)==1 and calls[0][0][0]==42


def test_music_preferences_validated_and_no_track_blocks_work(tmp_path):
    p=plugin(tmp_path)
    assert asyncio.run(p.set_setting('music_volume',.2))['music_volume']==.2
    assert asyncio.run(p.set_setting('music_volume',float('nan')))['music_volume']==.2
    assert asyncio.run(p.set_music_choice(42,'none'))['ok']
    assert asyncio.run(p.refresh_music(42))['disabled']
    assert not asyncio.run(p.set_music_choice('../42','auto'))['ok']


def test_music_manager_retries_explicitly_and_has_short_auto_cooldown(tmp_path):
    from deck_music_media import DeckMediaManager
    clock=[1000];m=DeckMediaManager(tmp_path,now=lambda:clock[0]);calls=[]
    def broken(*args):calls.append(1);raise OSError('offline fixture')
    m.build_theme=broken
    s={'theme_music_consent':True,'home_music':True}
    m.prepare_music(42,'Fixture',s);m.prepare_music(42,'Fixture',s)
    assert len(calls)==1
    m.prepare_music(42,'Fixture',s,force=True);assert len(calls)==2
    clock[0]+=901;m.prepare_music(42,'Fixture',s);assert len(calls)==3


def test_music_setup_returns_job_without_waiting_for_tools(tmp_path):
    p=plugin(tmp_path);p._music_allowed=lambda:True
    p._media_work_allowed=lambda:True
    p._power_sync=lambda:{'ac':True,'battery':80}
    class Runtime:
        def prepare(self,consent):return {'ok':True}
    class Manager:
        runtime=Runtime()
        def install_ytdlp(self,*args):return {'ok':True}
    p._media=lambda:Manager()
    async def check():
        assert (await p.setup_deck_music(False))['consent_required']
        job=await p.setup_deck_music(True)
        assert job['pending']
        for _ in range(20):
            s=await p.music_job_status(job['job'])
            if s['done']:
                assert s['result']['ok'];break
            await asyncio.sleep(.01)
        settings=await p.get_settings()
        assert settings['theme_music_consent'] and settings['home_music'] and settings['hub_music']
    asyncio.run(check())


def test_heavy_setup_waits_for_charging(tmp_path):
    p=plugin(tmp_path);p._music_allowed=lambda:True;p._media_work_allowed=lambda:False
    p._power_sync=lambda:{'ac':False,'battery':25}
    p._media=lambda:pytest.fail('runtime must not be constructed below the setup battery threshold')
    async def check():
        job=await p.setup_deck_music(True)
        await asyncio.sleep(0)
        return await p.music_job_status(job['job'])
    assert asyncio.run(check())['result']['deferred']=='charging_required'
