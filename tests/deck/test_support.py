"""Public-release autonomy without a Deck or real network."""
import asyncio
import hashlib
import importlib
import json
import sys
import types
from pathlib import Path


HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1] / "plugin"
PY_MODULES = PLUGIN / "py_modules"
sys.path.insert(0, str(PY_MODULES))

import standalone_media  # noqa: E402


class Response:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def read(self, size=-1):
        if size is None or size < 0:
            size = len(self.data) - self.pos
        out = self.data[self.pos:self.pos + size]
        self.pos += len(out)
        return out

    def close(self):
        pass


def main_module(tmp_path):
    fake = types.ModuleType("decky")
    fake.DECKY_PLUGIN_RUNTIME_DIR = str(tmp_path / "data")
    fake.logger = types.SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None)
    sys.modules["decky"] = fake
    sys.modules.setdefault("aiohttp", types.ModuleType("aiohttp"))
    sys.path[:0] = [str(PLUGIN), str(PY_MODULES)]
    sys.modules.pop("main", None)
    module = importlib.import_module("main")
    module.DATA = fake.DECKY_PLUGIN_RUNTIME_DIR
    return module


def as_release(module, tmp_path):
    root = tmp_path / "release"
    root.mkdir()
    (root / "RELEASE.json").write_text("{}\n", encoding="utf-8")
    module.__file__ = str(root / "main.py")


