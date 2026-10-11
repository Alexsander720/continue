"""Portable release tooling tests; every fixture is synthetic, never a real save."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def load_tool(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleaseTools(unittest.TestCase):
    def test_author_credit_allowance_does_not_allow_account_metadata(self):
        scanner = load_tool("credit_scanner", "tools/scan_private.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            account = "7656119" + "8038135489"
            (root / "NOTICE.md").write_text("Doctor_Nerd (https://steamcommunity.com/profiles/" + account + ")\n")
            (root / "owner.json").write_text(json.dumps({"steamid": account}))
            findings = scanner.scan_tree(root)
            self.assertEqual([(row["path"], row["rule"]) for row in findings], [("owner.json", "steam-account")])

    def test_game_ci_runner_exposes_documented_stdlib_helpers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "games/demo"
            folder.mkdir(parents=True)
            helper = root / "plugin/py_modules/ddsaves"
            helper.mkdir(parents=True)
            (helper / "__init__.py").touch()
            (helper / "_common.py").write_text("VALUE = 42\n")
            (folder / "reader.py").write_text("from ddsaves._common import VALUE\ndef read(): return VALUE\n")
            (folder / "test_reader.py").write_text("import unittest\nfrom reader import read\nclass Helper(unittest.TestCase):\n def test_value(self): self.assertEqual(read(), 42)\n")
            result = subprocess.run([sys.executable, "-I", str(ROOT / "tools/run_game_tests.py"), "demo", "--root", str(root)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_private_scanner_redacts_secrets_and_rejects_local_paths(self):
        scanner = load_tool("private_scanner", "tools/scan_private.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            secret = "gh" + "p_" + "x" * 36
            (root / "unsafe.py").write_text(secret + "\n" + "Q:" + "/Scripts/private\n", encoding="utf-8")
            findings = scanner.scan_tree(root)
            self.assertEqual({item["rule"] for item in findings}, {"token", "local-path"})
            self.assertNotIn(secret, json.dumps(findings))

    def test_private_scanner_catches_private_file_even_when_empty(self):
        scanner = load_tool("private_scanner_names", "tools/scan_private.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ("deck_saves_" + "private.py")).touch()
            self.assertEqual(scanner.scan_tree(root)[0]["rule"], "private-file")

    def test_private_scanner_includes_plugin_frontend_dist(self):
        scanner = load_tool("private_scanner_js", "tools/scan_private.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "dist").mkdir()
            (root / "dist/index.js").write_text("Q:" + "/Scripts/private\n")
            self.assertEqual(scanner.scan_tree(root)[0]["rule"], "local-path")

    def test_sync_accepts_only_sanitized_release_and_excludes_bytecode(self):
        tool = load_tool("plugin_sync", "tools/sync_plugin.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "sanitized"
            source.mkdir()
            (source / "RELEASE.json").write_text(json.dumps({"version": "0.1.0", "channel": "public"}))
            (source / "main.py").write_text("# sanitized\n")
            (source / "__pycache__").mkdir()
            (source / "__pycache__/main.pyc").write_bytes(b"bytecode")
            destination = root / "repo"
            destination.mkdir()
            count = tool.sync(source, destination)
            self.assertEqual(count, 2)
            self.assertTrue((destination / "plugin/main.py").is_file())
            self.assertFalse((destination / "plugin/__pycache__").exists())
            (source / "main.py").write_text("Q:" + "/Scripts/private\n")
            with self.assertRaises(ValueError):
                tool.sync(source, destination)
            self.assertEqual((destination / "plugin/main.py").read_text(), "# sanitized\n")

    def test_new_game_is_blocked_until_real_proof_exists(self):
        tool = load_tool("new_game", "tools/new_game.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = tool.create_game(root, "test_game", 12345)
            expected = {"reader.py", "tables.py", "stages.json", "icons.json", "README.md", "test_reader.py", "proof.md"}
            self.assertTrue(expected.issubset({path.name for path in folder.iterdir()}))
            self.assertEqual(json.loads((folder / "stages.json").read_text())["stages"], [])
            result = subprocess.run([sys.executable, str(ROOT / "tools/gate/check_cards.py"), "test_game", "--root", str(root)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertIn("at least two", result.stdout)
            self.assertIn("blocked", (folder / "proof.md").read_text())
            self.assertTrue(all(b"\r\n" not in path.read_bytes() for path in folder.rglob("*") if path.is_file()))
            with self.assertRaises(ValueError):
                tool.create_game(root, "../outside", 12345)
            with self.assertRaises(FileExistsError):
                tool.create_game(root, "test_game", 12345)

    def test_build_uses_expected_asset_names_and_in_archive_version(self):
        tool = load_tool("public_builder", "tools/build_deck_zip.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plugin = root / "plugin"
            (plugin / "dist").mkdir(parents=True)
            (plugin / "py_modules").mkdir()
            for name in ("main.py", "dist/index.js", "py_modules/deck_saves.py"):
                (plugin / name).write_text("# synthetic\n" if name.endswith(".py") else "// synthetic\n")
            (plugin / "plugin.json").write_text(json.dumps({"name": "Continue?"}))
            (plugin / "package.json").write_text(json.dumps({"version": "0.0.0"}))
            (root / "LICENSE").write_text("synthetic license\n")
            (root / "NOTICE.md").write_text("synthetic notice\n")
            archive, checksum = tool.build(root, "v2.3.4")
            self.assertEqual(archive.name, "continue-deck-2.3.4.zip")
            self.assertEqual(checksum.name, archive.name + ".sha256")
            self.assertEqual(checksum.read_text(), hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n")
            with zipfile.ZipFile(archive) as zipped:
                self.assertEqual(json.loads(zipped.read("Continue/RELEASE.json")), {"version": "2.3.4", "channel": "public"})
                self.assertEqual(json.loads(zipped.read("Continue/package.json"))["version"], "2.3.4")
            self.assertEqual(json.loads((plugin / "package.json").read_text())["version"], "0.0.0")
            with self.assertRaises(ValueError):
                tool.build(root, "../../unsafe")


class CardsGate(unittest.TestCase):
    def test_empty_skeleton_with_two_stages_still_fails(self):
        tool = load_tool("empty_game", "tools/new_game.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = tool.create_game(root, "demo", 12345)
            for name in ("a", "b"):
                (folder / "stages" / name).touch()
            (folder / "stages.json").write_text(json.dumps({"stages": [{"path": "stages/a"}, {"path": "stages/b"}]}))
            result = self.run_gate(root)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("no proven", result.stdout)
    def make_game(self, root, reader=None, counts=(1, 2)):
        folder = root / "games" / "demo"
        (folder / "stages").mkdir(parents=True)
        (root / "data").mkdir()
        (root / "data/demo.en.json").write_text(json.dumps({"place": "Garden"}))
        source = reader or '''import json
from pathlib import Path
def read(path):
    save = json.loads(Path(path).read_text())
    tables = json.loads((Path(__file__).resolve().parents[2] / "data/demo.en.json").read_text())
    return {"place": tables["place"], "chapter": None, "objective": None,
            "progress": {"count": save["count"]}, "facts": [{"id": "count", "icon": "gem", "value": str(save["count"])}],
            "proven": ["count"], "unproven": [], "fact_sources": {"count": "count"}}
'''
        (folder / "reader.py").write_text(source, encoding="utf-8")
        stages = []
        for i, count in enumerate(counts):
            path = folder / "stages" / f"{i}.json"
            path.write_text(json.dumps({"count": count}))
            stages.append({"path": f"stages/{i}.json", "name": str(i)})
        (folder / "stages.json").write_text(json.dumps({"stages": stages}))
        return folder

    def run_gate(self, root, slug="demo", timeout="3"):
        return subprocess.run([sys.executable, str(ROOT / "tools/gate/check_cards.py"), slug, "--root", str(root), "--timeout", timeout], capture_output=True, text=True, timeout=15)

    def test_gate_passes_proven_synthetic_stages(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_game(root)
            result = self.run_gate(root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("2 stage runs", result.stdout)

    def test_gate_rejects_unknown_slug_and_no_games(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = self.run_gate(Path(temporary), "missing")
            self.assertEqual(result.returncode, 1)
            self.assertIn("missing reader", result.stdout)

    def test_gate_rejects_constant_or_decreasing_proof(self):
        for counts, phrase in [((2, 2), "never changes"), ((2, 1), "decreases")]:
            with self.subTest(counts=counts), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                self.make_game(root, counts=counts)
                result = self.run_gate(root)
                self.assertEqual(result.returncode, 1)
                self.assertIn(phrase, result.stdout)

    def test_gate_rejects_english_display_literal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = self.make_game(root)
            source = (folder / "reader.py").read_text().replace('"place": tables["place"]', '"place": "Garden"')
            (folder / "reader.py").write_text(source)
            result = self.run_gate(root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("display literal", result.stdout)

    def test_gate_rejects_fact_from_unproven_field(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = self.make_game(root)
            source = (folder / "reader.py").read_text().replace('"fact_sources": {"count": "count"}', '"fact_sources": {"count": "unknown"}')
            (folder / "reader.py").write_text(source)
            result = self.run_gate(root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("not proven", result.stdout)

    def test_gate_contains_reader_timeout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_game(root, 'def read(path):\n    while True:\n        pass\n')
            result = self.run_gate(root, timeout="0.2")
            self.assertEqual(result.returncode, 1)
            self.assertIn("timeout", result.stdout)

    def test_gate_rejects_display_text_stored_in_variable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = self.make_game(root)
            source = (folder / "reader.py").read_text().replace('def read(path):', 'NAME = "Garden"\ndef read(path):').replace('"place": tables["place"]', '"place": NAME')
            (folder / "reader.py").write_text(source)
            result = self.run_gate(root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("display literal", result.stdout)

    def test_gate_inspects_imported_implementation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = self.make_game(root)
            source = (folder / "reader.py").read_text().replace('"place": tables["place"]', '"place": "Garden"')
            (folder / "implementation.py").write_text(source)
            (folder / "reader.py").write_text("from implementation import read\n")
            result = self.run_gate(root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("display literal", result.stdout)

    def test_gate_rejects_malformed_nonmonotonic_contract_without_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = self.make_game(root, counts=(2, 1))
            source = (folder / "reader.py").read_text().replace('"proven": ["count"]', '"nonmonotonic": [], "proven": ["count"]')
            (folder / "reader.py").write_text(source)
            result = self.run_gate(root)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn("Traceback", result.stderr)
            self.assertIn("contract", result.stdout)


if __name__ == "__main__":
    unittest.main()
