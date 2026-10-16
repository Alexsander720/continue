import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest

def module():
    spec=importlib.util.spec_from_file_location('pc_visual_test',Path(__file__).parents[2]/'pc/public_visuals.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def test_cached_hero_and_busy_do_not_start_network(tmp_path,monkeypatch):
    mod=module();media=tmp_path/'data/media';media.mkdir(parents=True)
    calls=[]
    monkeypatch.setattr(mod.urllib.request,'build_opener',lambda *a: calls.append(a))
    manager=SimpleNamespace(media=media,_relative=lambda p:p.relative_to(tmp_path/'data').as_posix())
    service=mod.PublicVisuals(tmp_path,lambda:manager,lambda:False)
    try:
        assert service.call('get_hero4k',[42])=={'file':None,'pending':False}
        (media/'42_hero.jpg').write_bytes(b'\xff\xd8\xff'+b'x'*50001)
        assert service.call('get_hero4k',[42])['file']=='media/42_hero.jpg'
        assert calls==[]
        for bad in (True,-1,0,1.5,2**32,'42'):
            with pytest.raises(ValueError):service.call('get_hero4k',[bad])
    finally:service.close()

def test_redirects_are_rejected_before_following():
    mod=module();handler=mod.SteamOnlyRedirect()
    for url in ('https://evil.invalid/a','http://shared.steamstatic.com/a','https://user@shared.steamstatic.com/a','https://shared.steamstatic.com:444/a'):
        with pytest.raises(ValueError):handler.redirect_request(None,None,302,'',{},url)
