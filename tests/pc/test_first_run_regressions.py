"""Regressions from the owner's rejected trial, using real runtime helpers."""
import json,hashlib
import sys
from pathlib import Path
from unittest.mock import patch
import pytest

SOURCE = Path(__file__).resolve().parents[2] / "pc"
sys.path.insert(0,str(SOURCE))
from public_game_assets import seed_game_icons
from public_preferences import PublicPreferences
from public_media_policy import PCMediaManager, get_game_media_status


def test_missing_video_does_not_block_home_only_music(tmp_path,monkeypatch):
    m=PCMediaManager(tmp_path,run=lambda *a,**k:None,urlopen=lambda *a,**k:None)
    monkeypatch.setattr(m,'build_steam',lambda *a:(_ for _ in ()).throw(RuntimeError('No trailer')))
    themes=[]
    monkeypatch.setattr(m,'build_theme',lambda appid,name,settings:themes.append(appid) or {'ok':True,'file':'media/42_theme.m4a'})
    r=m.build(42,'Fixture',{'theme_music_consent':True,'home_music':True,'hub_music':False})
    assert r['theme']['ok'] and themes==[42]
    assert m._state()['attempts']['42:steam']['ok'] is False


def test_youtube_permission_does_not_override_disabled_fallback(tmp_path,monkeypatch):
    m=PCMediaManager(tmp_path)
    monkeypatch.setattr(m,'build_steam',lambda *a:(_ for _ in ()).throw(RuntimeError('No trailer')))
    monkeypatch.setattr(m,'build_youtube',lambda *a:pytest.fail('Disabled fallback contacted YouTube'))
    r=m.build(42,'Fixture',{'youtube_consent':True,'media_fallback':False})
    assert not r['ok']


def test_seed_maps_all_eight_portraits_and_owner_raven(tmp_path):
    seed_game_icons(SOURCE/'assets/game_icons',tmp_path)
    manifest=json.loads((tmp_path/'icons/manifest.json').read_text(encoding='utf-8'))
    roster=['Sam','Mike','Jessica','Emily','Matt','Ashley','Chris','Josh']
    for name in roster:
        assert (tmp_path/'icons'/manifest['2172010']['person:'+name]).is_file()
    assert hashlib.sha256((tmp_path/'icons'/manifest['2322010']['raven']).read_bytes()).hexdigest()=='70a4e5f7005c1c3684f228ea5c75171e67ef2933de8f37bdb9fccdedf1eb2750'


def test_corrupt_preferences_write_keeps_existing_file(tmp_path):
    p=tmp_path/'settings.json';p.write_bytes(b'{corrupted')
    prefs=PublicPreferences(tmp_path)
    with pytest.raises(ValueError,match='Malformed'):
        prefs.set_card_preference(None,'characters',False)
    assert p.read_bytes()==b'{corrupted'


def test_stale_theme_cannot_pass_promotion_checkpoint(tmp_path):
    m=PCMediaManager(tmp_path)
    m._active_theme=(42,0)
    m.invalidate_theme(42)
    with pytest.raises(RuntimeError,match='choice changed'):
        m._checkpoint()


def test_home_only_music_status_is_not_disabled(tmp_path,monkeypatch):
    m=PCMediaManager(tmp_path)
    monkeypatch.setattr(m,'music_files',lambda **kwargs:{'42':'media/42_theme.m4a'})
    status=get_game_media_status(m,42,'Fixture',{'theme_music_consent':True,'hub_music':False,'home_music':True})
    assert status['music']['status']=='ready'


def test_cache_clear_does_not_race_with_music_download(tmp_path):
    import threading
    m=PCMediaManager(tmp_path)
    ready=threading.Event();release=threading.Event()
    def download():
        with m.music_lock:
            ready.set();release.wait(3)
    worker=threading.Thread(target=download);worker.start();assert ready.wait(1)
    try:
        assert m.clear()=={'ok':False,'deferred':'busy'}
    finally:
        release.set();worker.join(3)
