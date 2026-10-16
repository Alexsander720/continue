"""Windows GUI service children must never allocate a visible console."""
import builtins
import importlib.util
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import standalone_media as sm
from public_media_policy import PCMediaManager

NO_WINDOW = 0x08000000

@pytest.mark.parametrize('manager_class', [sm.MediaManager, PCMediaManager])
@pytest.mark.parametrize('platform', ['nt', 'posix'])
@pytest.mark.parametrize('tool', ['ffmpeg', 'ffprobe', 'yt-dlp', 'node', 'powershell'])
def test_media_child_console_policy(monkeypatch, manager_class, platform, tool):
    manager = manager_class.__new__(manager_class)
    manager._injected_run = None
    manager._checkpoint = lambda: None
    manager._child_env = lambda env: {'PATH': 'runtime'}
    manager._check_space = lambda size: None
    child = Mock(returncode=0)
    child.poll.return_value = 0
    popen = Mock(return_value=child)
    monkeypatch.setattr(sm, 'os', SimpleNamespace(name=platform))
    monkeypatch.setattr(sm.subprocess, 'CREATE_NO_WINDOW', NO_WINDOW, raising=False)
    monkeypatch.setattr(sm.subprocess, 'Popen', popen)
    result = manager._run([tool, '--version'], text=True)
    assert result.returncode == 0
    options = popen.call_args.kwargs
    if platform == 'nt':
        assert options.get('creationflags', 0) & NO_WINDOW
    else:
        assert 'creationflags' not in options
        assert 'startupinfo' not in options

def test_media_preserves_flags_for_real_and_injected_runner(monkeypatch):
    manager = sm.MediaManager.__new__(sm.MediaManager)
    manager._checkpoint = lambda: None
    manager._child_env = lambda env: {}
    manager._injected_run = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(sm, 'os', SimpleNamespace(name='nt'))
    monkeypatch.setattr(sm.subprocess, 'CREATE_NO_WINDOW', NO_WINDOW, raising=False)
    manager._run(['node'], creationflags=0x200)
    assert manager._injected_run.call_args.kwargs['creationflags'] == NO_WINDOW | 0x200

@pytest.mark.parametrize('platform', ['nt', 'posix'])
def test_openssl_fallback_console_policy(monkeypatch, platform):
    path = Path(__file__).resolve().parents[2] / 'plugin/py_modules/ddsaves/_common.py'
    spec = importlib.util.spec_from_file_location('r18_save_common', path)
    common = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(common)
    original_import = builtins.__import__
    def without_crypto(name, *args, **kwargs):
        if name.startswith('cryptography'):
            raise ImportError('Exercise system openssl fallback')
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', without_crypto)
    monkeypatch.setattr(common, 'os', SimpleNamespace(name=platform, environ=os.environ))
    monkeypatch.setattr(subprocess, 'CREATE_NO_WINDOW', NO_WINDOW, raising=False)
    run = Mock(return_value=subprocess.CompletedProcess([], 0, b'plain\x01'))
    monkeypatch.setattr(common.subprocess, 'run', run)
    assert common.aes_ecb_decrypt(b'x' * 16, b'y' * 16) == b'plain'
    if platform == 'nt':
        assert run.call_args.kwargs.get('creationflags', 0) & NO_WINDOW
    else:
        assert 'creationflags' not in run.call_args.kwargs
