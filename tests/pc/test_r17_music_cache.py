"""Regressions for PC None -> Auto using an already prepared automatic theme."""
import json
import pytest
from test_public_customization import test_env


def test_automatic_cache_survives_none_auto_cycles(test_env, monkeypatch):
    backend, media = test_env['backend'], test_env['media']
    asset = media.media / '400_theme.m4a'
    content = b'prepared automatic theme'
    asset.write_bytes(content)
    cancelled = []
    monkeypatch.setattr(media, 'invalidate_theme', cancelled.append, raising=False)
    for choice in ('none', 'auto', 'none', 'auto', 'auto'):
        result = backend.music_choose(400, choice)
        assert result['result']['ok']
        assert backend.music_current(400) == choice
        assert asset.exists(), 'mode changes must retain the prepared automatic cache'
        assert asset.read_bytes() == content
    assert cancelled == [400] * 5
    assert not media.downloaded_urls


@pytest.mark.parametrize('choice', ['none', 'auto'])
def test_custom_cache_cannot_become_automatic(test_env, choice):
    backend, media, root = (test_env[k] for k in ('backend', 'media', 'root'))
    asset = media.media / '400_theme.m4a'
    asset.write_bytes(b'custom theme')
    settings = json.loads((root / 'settings.json').read_text())
    settings.setdefault('music_choices', {})['400'] = 'Abc123_XYZ9'
    (root / 'settings.json').write_text(json.dumps(settings))
    unrelated = media.media / '500_theme.m4a'
    unrelated.write_bytes(b'other game')
    backend.music_choose(400, choice)
    assert not asset.exists(), 'custom audio must never be relabelled automatic'
    backend.music_choose(400, 'auto')
    assert not asset.exists()
    assert unrelated.read_bytes() == b'other game'
