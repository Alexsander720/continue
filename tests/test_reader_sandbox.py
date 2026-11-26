"""reader_sandbox: appid discovery, card validation, and (where bubblewrap exists) real isolation."""
from __future__ import annotations
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY_MODULES = ROOT / "plugin" / "py_modules"
sys.path.insert(0, str(PY_MODULES))
sys.modules.setdefault("decky", types.SimpleNamespace(DECKY_PLUGIN_RUNTIME_DIR=tempfile.gettempdir(), logger=None))

import reader_sandbox  # noqa: E402

HAVE_BWRAP = reader_sandbox.status()["sandboxed"]
PROBE_APPID = 4000000001
PROBE_SUB = f"steamapps/compatdata/{PROBE_APPID}/pfx/drive_c/users/steamuser/AppData/LocalLow/Probe"
PROBE_READER = f'''"""Synthetic reader used only by the sandbox tests."""
import json
from pathlib import Path
from ddsaves._common import empty, fact, finish, newest, proton_user
APPID = {PROBE_APPID}
def read(path_or_dir=None):
    path = next((p for d in proton_user(APPID) for p in [newest(Path(d, "AppData/LocalLow/Probe").glob("*.json"))] if p), None)
    if path is None:
        return empty("no probe save")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return empty("bad probe save")
    return finish({{"place": None, "chapter": None, "objective": None, "progress": {{"day": data["day"]}},
                   "facts": [fact("sun", "День", data["day"], id="day")], "proven": ["day"], "unproven": []}}, path)
'''


class StaticTests(unittest.TestCase):
    def test_reader_appids_parsed_without_import(self):
        self.assertEqual(reader_sandbox.reader_appids("hollow_knight"), [367520])
        self.assertEqual(reader_sandbox.reader_appids("silent_hill_2"), [2124490])   # declared in the sibling _ag_ reader too
        self.assertEqual(reader_sandbox.reader_appids("no_such_reader"), [])
        self.assertEqual(reader_sandbox.reader_appids("../etc"), [])

    def test_validate_card_caps_and_drops(self):
        raw = {"place": "x" * 10000, "facts": [{"id": "day", "value": 5, "extra": 1}, "junk"], "proven": ["day", 3],
               "progress": {"deep": {"a": {"b": {"c": {"d": {"e": {"f": {"g": 1}}}}}}}, "n": float("inf")},
               "observed_at": "nope", "unknown_key": 1}
        card = reader_sandbox.validate_card(raw)
        self.assertEqual(len(card["place"]), reader_sandbox.MAX_STRING)
        self.assertEqual(card["facts"], [{"id": "day", "icon": "", "label": "", "value": "5"}])
        self.assertEqual(card["proven"], ["day"])
        self.assertIsNone(card["observed_at"])
        self.assertNotIn("unknown_key", card)
        self.assertIsNone(card["progress"]["n"])
        self.assertIsNone(reader_sandbox.validate_card(["not", "a", "dict"]))

    def test_unknown_reader_is_none(self):
        self.assertIsNone(reader_sandbox.read_card("no_such_reader", 1))
        self.assertIsNone(reader_sandbox.read_card("../../etc/passwd", 1))


@unittest.skipUnless(HAVE_BWRAP, "bubblewrap not available")
class SandboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="continue-sandbox-"))
        self.home = self.tmp / "home"
        (self.home / ".local/share/Steam/steamapps").mkdir(parents=True)
        self.save_dir = self.home / ".local/share/Steam" / PROBE_SUB
        self.save_dir.mkdir(parents=True)
        (self.save_dir / "probe.json").write_text(json.dumps({"day": 42}), encoding="utf-8")
        (self.home / ".ssh").mkdir()
        (self.home / ".ssh/canary").write_text("secret", encoding="utf-8")
        # a private py_modules copy with the probe reader, so no shipped game reader is needed
        modules = self.tmp / "py_modules"
        shutil.copytree(PY_MODULES / "ddsaves", modules / "ddsaves", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(PY_MODULES / "reader_sandbox_runner.py", modules / "reader_sandbox_runner.py")
        (modules / "ddsaves/sandbox_probe.py").write_text(PROBE_READER, encoding="utf-8")
        self._saved = (reader_sandbox.PY_MODULES, reader_sandbox.RUNNER, os.environ.get("CONTINUE_HOME"))
        reader_sandbox.PY_MODULES, reader_sandbox.RUNNER = modules, modules / "reader_sandbox_runner.py"
        os.environ["CONTINUE_HOME"] = str(self.home)
        import ddsaves._common as common
        common._LIBS = None   # library cache must not leak between homes

    def tearDown(self):
        reader_sandbox.PY_MODULES, reader_sandbox.RUNNER, old = self._saved
        if old is None:
            os.environ.pop("CONTINUE_HOME", None)
        else:
            os.environ["CONTINUE_HOME"] = old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_reader_runs_sandboxed_and_sees_only_its_save(self):
        card = reader_sandbox.read_card("sandbox_probe", PROBE_APPID)
        self.assertEqual(card["facts"][0]["value"], "42", card)
        self.assertIn("day", card["proven"])
        self.assertTrue(card["source_path"].endswith("probe.json"))
        self.assertEqual(reader_sandbox.status()["fallbacks"], 0)

    def test_child_has_no_network_home_or_write_access(self):
        dirs, files = reader_sandbox.bind_targets([PROBE_APPID])
        probe = (
            "import os, socket, json\n"
            "r = {}\n"
            "r['home'] = sorted(os.listdir(os.environ['HOME']))\n"
            "r['canary'] = os.path.exists(os.path.join(os.environ['HOME'], '.ssh', 'canary'))\n"
            "try:\n socket.create_connection(('1.1.1.1', 53), timeout=1); r['net'] = 'open'\n"
            "except OSError: r['net'] = 'blocked'\n"
            "p = os.path.join(os.environ['HOME'], '.local/share/Steam/%s/x')\n"
            "try:\n open(p, 'w'); r['write'] = 'allowed'\n"
            "except OSError: r['write'] = 'blocked'\n"
            "r['root'] = sorted(os.listdir('/'))\n"
            "print(json.dumps(r))\n" % PROBE_SUB)
        env = {"HOME": str(self.home), "PATH": "/usr/bin:/bin"}
        proc = reader_sandbox.sandbox_exec([reader_sandbox.status()["python"], "-I", "-c", probe], dirs, files, env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        r = json.loads(proc.stdout)
        self.assertEqual(r["home"], [".local"])          # only the bound Steam path exists, no .ssh
        self.assertFalse(r["canary"])
        self.assertEqual(r["net"], "blocked")
        self.assertEqual(r["write"], "blocked")
        self.assertFalse({"root", "var", "opt", "srv", "boot"} & set(r["root"]), r["root"])   # /etc exists only as the localtime mount point

    def test_reader_error_is_reported_not_raised(self):
        (self.save_dir / "probe.json").write_text("{not json", encoding="utf-8")
        card = reader_sandbox.read_card("sandbox_probe", PROBE_APPID)
        self.assertEqual(card["facts"], [])
        self.assertIsNone(card["place"])


if __name__ == "__main__":
    unittest.main()
