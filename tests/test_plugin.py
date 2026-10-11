"""Packaged public plugin checks, with temporary homes and denied network access."""
import asyncio
import importlib
import importlib.util
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


async def exercise_plugin(root, temporary):
    plugin_dir = root / "plugin"
    sys.path[:0] = [str(plugin_dir / "py_modules"), str(plugin_dir)]
    decky = types.ModuleType("decky")
    decky.DECKY_PLUGIN_RUNTIME_DIR = str(temporary / "runtime")
    decky.logger = logging.getLogger("offline-decky")
    sys.modules["decky"] = decky
    # Decky supplies aiohttp. This stdlib CI fixture exposes an unavailable
    # transport rather than installing or allowing a real HTTP client.
    aiohttp = types.ModuleType("aiohttp")
    def unavailable(*args, **kwargs):
        raise OSError("HTTP transport unavailable in offline fixture")
    aiohttp.ClientSession = unavailable
    aiohttp.ClientTimeout = lambda *args, **kwargs: None
    sys.modules["aiohttp"] = aiohttp
    from ddsaves import _common
    for name in ("steam_roots", "steam_libraries", "documents_dirs", "game_dirs", "steam_userdata", "proton_user", "windows_users"):
        if hasattr(_common, name):
            setattr(_common, name, lambda *args, **kwargs: [])
    _common.deck_home = lambda: temporary
    specification = importlib.util.spec_from_file_location("offline_plugin", plugin_dir / "main.py")
    main = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(main)
    plugin = main.Plugin()
    plugin._steam_root = lambda: str(temporary / "Steam")
    await asyncio.wait_for(plugin._main(), 5)
    outputs = {}
    methods = {
        "get_settings": (), "set_setting": ("home_installed_first", True), "set_game_bg": (367520, "image"),
        "get_about": (367520,), "get_power": (), "get_status": (), "get_aliases": (),
        "get_music_map": (), "get_music_files": (), "set_lang": ("english",),
        "get_hltb": (367520, ""), "get_protondb": (367520,), "check_update": (),
        "set_game_source": (367520, "steam"), "get_media_status": (),
        "install_ytdlp": (False,), "refresh_media": (367520, "Fixture", True),
        "clear_media_cache": (), "set_media_context": (True,),
    }
    for name, arguments in methods.items():
        outputs[name] = await asyncio.wait_for(getattr(plugin, name)(*arguments), 5)
        json.dumps(outputs[name], allow_nan=False)
    import deck_saves
    for appid in sorted(deck_saves.READERS):
        card = await asyncio.wait_for(plugin.get_card(appid, ""), 5)
        if not isinstance(card, dict) or card.get("appid") != appid:
            raise AssertionError(f"get_card({appid}) violated card contract")
        json.dumps(card, allow_nan=False)
        result = deck_saves.read(appid, str(temporary))
        if result is not None and not isinstance(result, dict):
            raise AssertionError(f"deck_saves.read({appid}) returned invalid type")
        json.dumps(result, allow_nan=False)
    await asyncio.wait_for(plugin._unload(), 5)
    print(json.dumps({"methods": len(outputs), "readers": len(deck_saves.READERS), "hub_cards": outputs["get_status"].get("hub_cards", 0)}))


def worker():
    root = Path(sys.argv[2]).resolve()
    with tempfile.TemporaryDirectory(prefix="continue-ci-") as directory:
        temporary = Path(directory)
        # Windows creates asyncio's internal socketpair while constructing the loop.
        # Construct it before the audit guard; all plugin code runs under the guard.
        loop = asyncio.new_event_loop()
        def audit(event, arguments):
            if event in {"socket.connect", "socket.getaddrinfo", "urllib.Request"}:
                raise OSError("Network denied in offline plugin tests")
        sys.addaudithook(audit)
        environment = {name: str(temporary) for name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA")}
        try:
            with mock.patch.dict(os.environ, environment), mock.patch("subprocess.Popen", side_effect=OSError("Executables unavailable in clean test")), mock.patch("shutil.which", return_value=None), mock.patch("pathlib.Path.home", return_value=temporary):
                loop.run_until_complete(exercise_plugin(root, temporary))
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.run_until_complete(loop.shutdown_default_executor())
        finally:
            loop.close()


class PublicPlugin(unittest.TestCase):
    def test_plugin_and_all_registered_readers_work_without_hub_or_network(self):
        result = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "--worker", str(ROOT)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        self.assertGreaterEqual(summary["readers"], 20)
        self.assertEqual(summary["hub_cards"], 0)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        worker()
    else:
        unittest.main()
