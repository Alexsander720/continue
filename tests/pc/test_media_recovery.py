"""Actual media state survives retries without a seven-day failure trap."""
from public_media_policy import PCMediaManager


def failed_manager(tmp_path):
    clock=[10000]
    manager=PCMediaManager(tmp_path,now=lambda:clock[0])
    calls=[]
    def theme(*args):
        calls.append(1)
        raise OSError('temporary offline fixture')
    manager.build_theme=theme
    settings={'theme_music_consent':True,'hub_music':True,'home_music':True,'live_bg':'off'}
    return manager,clock,calls,settings


def test_explicit_retry_bypasses_failed_music_cooldown(tmp_path):
    manager,clock,calls,settings=failed_manager(tmp_path)
    assert not manager.build(42,'Fixture',settings)['theme']['ok']
    manager.build(42,'Fixture',settings,force=True)
    assert len(calls)==2


def test_clear_media_resets_failed_theme_but_keeps_unrelated_state(tmp_path):
    manager,clock,calls,settings=failed_manager(tmp_path)
    manager.build(42,'Fixture',settings)
    state=manager._state();state['unrelated']={'value':'keep'};manager._save_state(state)
    assert manager.clear()['ok']
    manager.build(42,'Fixture',settings)
    assert len(calls)==2 and manager._state()['unrelated']=={'value':'keep'}


def test_automatic_failure_retry_is_short_and_still_throttled(tmp_path):
    manager,clock,calls,settings=failed_manager(tmp_path)
    manager.build(42,'Fixture',settings)
    manager.build(42,'Fixture',settings)
    assert len(calls)==1
    clock[0]+=901
    manager.build(42,'Fixture',settings)
    assert len(calls)==2


def test_updated_loader_allows_failed_theme_to_recover_immediately(tmp_path):
    manager,clock,calls,settings=failed_manager(tmp_path)
    manager._save_state({'yt_dlp':{'version':'old'}})
    manager.build(42,'Fixture',settings)
    state=manager._state();state['yt_dlp']['version']='new';manager._save_state(state)
    manager.build(42,'Fixture',settings)
    assert len(calls)==2


def test_whole_media_job_deadline_stops_work_and_does_not_poison_next_job(tmp_path,monkeypatch):
    import public_media_policy as policy
    clock=[0.0]
    monkeypatch.setattr(policy.time,'monotonic',lambda:clock[0])
    manager=PCMediaManager(tmp_path)
    def theme(*args):
        clock[0]+=601
        manager._checkpoint()
        return {'ok':True}
    manager.build_theme=theme
    settings={'theme_music_consent':True,'hub_music':True,'live_bg':'off'}
    result=manager.build(42,'Fixture',settings)
    assert not result['theme']['ok'] and result['theme']['reason'] == 'theme_timeout'
    manager.build_theme=lambda *args:{'ok':True}
    assert manager.build(42,'Fixture',settings,force=True)['theme']['ok']
