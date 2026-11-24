"""Steam recordings across Windows accounts, bg sessions and nested saved clips."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest
from public_media_policy import PCMediaManager
from standalone_media import MediaManager


def recording(root, account, relative, age=300):
    folder = root / 'userdata' / account / 'gamerecordings' / relative
    folder.mkdir(parents=True)
    init = folder / 'init-stream0.m4s'
    init.write_bytes(b'fixture-init')
    part = folder / 'chunk-stream0-00001.m4s'
    part.write_bytes(b'fixture-chunk')
    import time
    for path in (init, part):
        os.utime(path, (time.time() - age, time.time() - age))
    return init


def test_windows_registry_root_finds_bg_in_all_userdata(tmp_path, monkeypatch):
    monkeypatch.delenv('ProgramFiles(x86)', raising=False)
    monkeypatch.delenv('ProgramFiles', raising=False)
    steam = tmp_path / 'Steam'
    expected = recording(steam, '77869761', 'video/bg_2172010_20261017_181302')
    (steam / 'userdata/1669070899/gamerecordings/timelines').mkdir(parents=True)
    class Key:
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setitem(sys.modules, 'winreg', SimpleNamespace(
        HKEY_CURRENT_USER=1, OpenKey=lambda *a: Key(), QueryValueEx=lambda *a: (str(steam), 1)))
    monkeypatch.setattr(Path, 'home', lambda: tmp_path / 'profile')
    assert PCMediaManager(tmp_path / 'cache').recording_candidates(2172010) == [expected]


def test_exact_app_nested_clip_and_active_recording_guard(tmp_path, monkeypatch):
    manager = MediaManager(tmp_path / 'cache')
    monkeypatch.setattr(manager, '_steam_roots', lambda: [tmp_path])
    direct = recording(tmp_path, 'first', 'video/bg_2172010_20261005_225034')
    nested = recording(tmp_path, 'second', 'clips/clip_2172010_20261018_120000/video/bg_2172010_20261017_181302')
    recording(tmp_path, 'first', 'video/bg_21720101_20261017_181302')
    recording(tmp_path, 'first', 'video/bg_2172010_20261018_120001', age=0)
    assert set(manager.recording_candidates(2172010)) == {direct, nested}


def test_hevc_steam_input_is_transcoded_but_output_stays_avc(tmp_path, monkeypatch):
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        pytest.skip('ffmpeg needed to create and decode the HEVC regression fixture')
    source = tmp_path / 'hevc.mp4'
    result = subprocess.run([ffmpeg, '-v', 'error', '-f', 'lavfi', '-i',
        'testsrc2=size=160x90:rate=5:duration=22', '-an', '-c:v', 'libx265',
        '-preset', 'ultrafast', '-x265-params', 'log-level=error',
        '-movflags', 'frag_keyframe+empty_moov+default_base_moof', str(source)], capture_output=True)
    assert result.returncode == 0, result.stderr
    from standalone_media import _boxes, _bmff
    with source.open('rb') as stream:
        boxes = list(_boxes(stream, 0, source.stat().st_size))
    raw = source.read_bytes()
    folder = tmp_path / 'video/bg_2172010_20261017_181302'
    folder.mkdir(parents=True)
    init = folder / 'init-stream0.m4s'
    init.write_bytes(b''.join(raw[b[1]:b[3]] for b in boxes if b[0] in (b'ftyp', b'moov')))
    (folder / 'chunk-stream0-00001.m4s').write_bytes(b''.join(raw[b[1]:b[3]] for b in boxes if b[0] in (b'moof', b'mdat')))
    manager = PCMediaManager(tmp_path / 'cache')
    monkeypatch.setattr(manager, 'recording_candidates', lambda _: [init])
    result = manager.build_recording(2172010, 'Until Dawn', {'recording_enabled': True, 'preset': 'light'})
    assert result['ok']
    output = manager.media / '2172010_recording.mp4'
    metadata = _bmff(output)
    assert metadata['codec'] in ('avc1', 'avc3') and 19.5 <= metadata['duration'] <= 20.5
    assert source.read_bytes() == raw


def test_visible_recording_fallback_accepts_menu_but_rejects_blank_frames():
    # Dark games and recorded menus are valid owner footage, without claiming
    # that a pixel heuristic proves gameplay semantics.
    menu = bytes([0] * 6000 + [70, 150, 230] * 720)
    assert MediaManager._frames_visible([menu] * 5)
    assert not MediaManager._frames_visible([bytes(8160)] * 5)
    assert not MediaManager._frames_visible([bytes([255]) * 8160] * 5)
    assert not MediaManager._frames_visible([bytes(8160)] * 4 + [menu])


def test_activity_accepts_dark_play_but_rejects_pause_and_slow_menu():
    import random
    from standalone_media import RECORDING_CONTRAST, RECORDING_MOTION
    rng = random.Random(7)
    # Very dark gameplay: mean ~6 of 255, yet the picture keeps changing.
    play = [bytes(rng.choice((0, 2, 4, 30)) for _ in range(8160)) for _ in range(3)]
    contrast, motion = MediaManager._activity(play)
    assert contrast >= RECORDING_CONTRAST and motion >= RECORDING_MOTION
    pause = [play[0]] * 3
    assert MediaManager._activity(pause)[1] < RECORDING_MOTION
    base = list(play[0])
    # A slow menu: only scattered pixels (snow) change between seconds.
    menu = [bytes(base), bytes(v if i % 40 else 30 - v for i, v in enumerate(base)), bytes(base)]
    assert MediaManager._activity(menu)[1] < RECORDING_MOTION


def test_session_end_window_walks_back_past_menu_tail(tmp_path, monkeypatch):
    manager = MediaManager(tmp_path / 'cache')
    chunks = [tmp_path / f'chunk-stream0-{i:05d}.m4s' for i in range(1, 41)]
    active = set(range(10, 30))  # play, then pause/menu at the end of the session
    monkeypatch.setattr(manager, '_fragment_active', lambda init, chunk: chunks.index(chunk) in active)
    selected = manager._session_end_window(tmp_path / 'init-stream0.m4s', chunks)
    assert [chunks.index(c) for c in selected] == list(range(23, 30))
    monkeypatch.setattr(manager, '_fragment_active', lambda init, chunk: False)
    assert manager._session_end_window(tmp_path / 'init-stream0.m4s', chunks) is None
