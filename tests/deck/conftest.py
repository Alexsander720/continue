"""Offline reproduction of the environment inherited from Decky's frozen loader."""
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULES = ROOT / 'py_modules'
PC = ROOT.parents[1] / 'pc_bp'
if not MODULES.is_dir():
    ROOT = Path(__file__).resolve().parents[2]
    MODULES, PC = ROOT / 'plugin/py_modules', ROOT / 'pc'
sys.path.insert(0, str(PC))
sys.path.insert(0, str(MODULES))


@pytest.fixture
def decky_environment(monkeypatch):
    import standalone_media as sm
    for key in ('PATH', 'HOME', 'LD_LIBRARY_PATH_ORIG'):
        monkeypatch.delenv(key, raising=False)
    for key, value in {'LD_LIBRARY_PATH': '/tmp/_MEIdecky', 'LD_PRELOAD': '/tmp/_MEIdecky/libssl.so',
                       'PYTHONHOME': '/tmp/_MEIdecky', 'PYTHONPATH': '/tmp/_MEIdecky',
                       '_PYI_APPLICATION_HOME_DIR': '/tmp/_MEIdecky', '_PYI_PARENT_PROCESS_LEVEL': '1'}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(sm, '_CHILD_WINDOWS', False, raising=False)
    monkeypatch.setattr(sys, 'executable', '/home/deck/homebrew/services/PluginLoader')
    return dict(os.environ)
