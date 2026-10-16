"""Tests for public PC builder (tools/build_pc_zip.py); all fixtures synthetic."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PC_ALLOWLIST = (
    "bp_prelude.js",
    "bp_suffix.js",
    "gamehub_bp.py",
    "hltb_stdlib.py",
    "install.ps1",
    "pc_cdp.py",
    "public_update.py",
    "public_bootstrap.py", "recover-install.ps1",
    "python_runtime.json",
    "setup.cmd",
    "status.ps1",
    "uninstall.ps1",
    "windows_common.ps1",
    "ws_min.py",
    "bp_public_controls.js", "public_customization.py", "public_themes.py", "public_theme_cdp.py", "public_visuals.py",
    "bp_public_settings.js", "public_game_assets.py", "public_preferences.py", "public_media_policy.py", "public_media_runtime.py",
)


def load_pc_builder():
    spec = importlib.util.spec_from_file_location("public_pc_builder", ROOT / "tools/build_pc_zip.py")
    if spec is None or not (ROOT / "tools/build_pc_zip.py").is_file():
        raise FileNotFoundError("tools/build_pc_zip.py not found")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def create_fixture(root: Path):
    plugin = root / "plugin"
    (plugin / "dist").mkdir(parents=True, exist_ok=True)
    (plugin / "py_modules").mkdir(parents=True, exist_ok=True)
    (plugin / "main.py").write_text(
        '# synthetic main\nctx = ssl.create_default_context(cafile="/etc/ssl/certs/ca-certificates.crt")\n',
        encoding="utf-8",
        newline="\n",
    )
    (plugin / "dist/index.js").write_text("// synthetic js\n", encoding="utf-8", newline="\n")
    (plugin / "plugin.json").write_text(json.dumps({"name": "Continue?"}), encoding="utf-8", newline="\n")
    (plugin / "package.json").write_text(json.dumps({"version": "0.0.0"}), encoding="utf-8", newline="\n")
    (plugin / "py_modules/deck_saves.py").write_text("# synthetic deck_saves\n", encoding="utf-8", newline="\n")
    (plugin / "py_modules/hltb.py").write_text("# synthetic deck hltb\n", encoding="utf-8", newline="\n")

    pc = root / "pc"
    pc.mkdir(parents=True, exist_ok=True)
    for name in PC_ALLOWLIST:
        content = "# synthetic pc\n" if name.endswith(".py") else ("// synthetic pc\n" if name.endswith(".js") else "{}\n")
        if name == "hltb_stdlib.py":
            content = "# windows hltb stdlib\n"
        elif name == "setup.cmd":
            content = "@echo off\n"
        (pc / name).write_text(content, encoding="utf-8", newline="\n")

    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    for name in ("install-pc.md", "install-pc.ru.md", "install-pc.uk.md", "pc-first-start.md", "pc-first-start.ru.md", "pc-first-start.uk.md"):
        (docs / name).write_text(f"# doc {name}\n", encoding="utf-8", newline="\n")

    (root / "LICENSE").write_text("synthetic license\n", encoding="utf-8", newline="\n")
    (root / "NOTICE.md").write_text("synthetic notice\n", encoding="utf-8", newline="\n")


class PcBuildTests(unittest.TestCase):
    def test_build_expected_shape_and_version_and_docs_and_licenses(self):
        tool = load_pc_builder()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_fixture(root)
            archive, checksum = tool.build(root, "v0.1.2")
            self.assertEqual(archive.name, "continue-pc-0.1.2.zip")
            self.assertEqual(checksum.name, "continue-pc-0.1.2.zip.sha256")
            expected_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            self.assertEqual(checksum.read_text(encoding="utf-8"), f"{expected_digest}  {archive.name}\n")

            with zipfile.ZipFile(archive) as zipped:
                names = set(zipped.namelist())
                # Marker
                self.assertIn("Continue/RELEASE.json", names)
                marker = json.loads(zipped.read("Continue/RELEASE.json").decode("utf-8"))
                self.assertEqual(marker, {"version": "0.1.2", "channel": "public", "platform": "windows"})
                self.assertIn("Continue/plugin/RELEASE.json", names, "Shared backend needs its own public-mode marker")
                backend_marker = json.loads(zipped.read("Continue/plugin/RELEASE.json"))
                self.assertEqual(backend_marker, {"version": "0.1.2", "channel": "public"})

                # Plugin version rewrite
                pkg = json.loads(zipped.read("Continue/plugin/package.json").decode("utf-8"))
                self.assertEqual(pkg["version"], "0.1.2")
                # Source package.json unmodified
                orig_pkg = json.loads((root / "plugin/package.json").read_text(encoding="utf-8"))
                self.assertEqual(orig_pkg["version"], "0.0.0")

                # Windows adaptations
                main_code = zipped.read("Continue/plugin/main.py").decode("utf-8")
                self.assertIn("ssl.create_default_context()", main_code)
                self.assertNotIn('cafile="/etc/ssl/certs/ca-certificates.crt"', main_code)

                hltb_code = zipped.read("Continue/plugin/py_modules/hltb.py").decode("utf-8")
                self.assertEqual(hltb_code, "# windows hltb stdlib\n")

                # Setup forwarding
                setup_code = zipped.read("Continue/setup.cmd").decode("utf-8")
                self.assertIn('call "%~dp0pc\\setup.cmd"', setup_code)

                # Licenses & docs
                self.assertEqual(zipped.read("Continue/LICENSE").decode("utf-8"), "synthetic license\n")
                self.assertEqual(zipped.read("Continue/NOTICE.md").decode("utf-8"), "synthetic notice\n")
                self.assertIn("Continue/docs/install-pc.md", names)
                self.assertIn("Continue/docs/install-pc.ru.md", names)
                self.assertIn("Continue/docs/install-pc.uk.md", names)

                # PC allowlist exactly 13
                pc_names = {name for name in names if name.startswith("Continue/pc/")}
                expected_pc = {f"Continue/pc/{item}" for item in PC_ALLOWLIST}
                self.assertEqual(pc_names, expected_pc)

    def test_build_excludes_pyc_and_bytecode_and_unallowlisted_pc_files(self):
        tool = load_pc_builder()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_fixture(root)

            # Leakage attempts
            (root / "plugin/__pycache__").mkdir()
            (root / "plugin/__pycache__/main.pyc").write_bytes(b"bytecode")
            (root / "pc/__pycache__").mkdir()
            (root / "pc/__pycache__/extra.pyc").write_bytes(b"bytecode")
            (root / "pc/extra_helper.py").write_text("# extra\n")
            (root / "pc/dangerous.exe").write_bytes(b"MZ\x00\x00")

            archive, _ = tool.build(root, "0.1.2")
            with zipfile.ZipFile(archive) as zipped:
                names = zipped.namelist()
                for name in names:
                    self.assertNotIn("__pycache__", name)
                    self.assertFalse(name.endswith(".pyc"))
                    self.assertFalse(name.endswith(".exe"))
                    self.assertNotIn("extra_helper.py", name)
                    self.assertNotIn("dangerous.exe", name)

    def test_build_rejects_malformed_version_and_missing_required_sources(self):
        tool = load_pc_builder()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_fixture(root)

            for bad_ver in ("invalid", "0.1", "0.1.2.3", "../../unsafe", ""):
                with self.subTest(bad_ver=bad_ver):
                    with self.assertRaises(ValueError):
                        tool.build(root, bad_ver)

            # Missing required plugin file
            (root / "plugin/main.py").unlink()
            with self.assertRaises(ValueError):
                tool.build(root, "0.1.2")
            create_fixture(root)

            # Missing allowlisted PC file
            (root / "pc/gamehub_bp.py").unlink()
            with self.assertRaises(ValueError):
                tool.build(root, "0.1.2")
            create_fixture(root)

            # Missing doc file
            (root / "docs/install-pc.md").unlink()
            with self.assertRaises(ValueError):
                tool.build(root, "0.1.2")
            create_fixture(root)

            # Missing root LICENSE
            (root / "LICENSE").unlink()
            with self.assertRaises(ValueError):
                tool.build(root, "0.1.2")

    def test_build_privacy_scanner_refusal(self):
        tool = load_pc_builder()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_fixture(root)

            # Inject a secret into pc/
            secret = "gh" + "p_" + "s" * 36
            (root / "pc/ws_min.py").write_text(f"{secret}\n", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                tool.build(root, "0.1.2")
            self.assertIn("scan failed", str(ctx.exception).lower())

            # Ensure candidate archive was not created
            dist = root / "dist"
            if dist.exists():
                self.assertFalse((dist / "continue-pc-0.1.2.zip").exists())

    def test_build_deterministic_reproducible_metadata(self):
        tool = load_pc_builder()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_fixture(root)

            archive1, _ = tool.build(root, "0.1.2")
            bytes1 = archive1.read_bytes()

            # Alter mtimes of all files in root
            future_time = time.time() + 100000
            for path in root.rglob("*"):
                if path.is_file():
                    os.utime(path, (future_time, future_time))

            archive2, _ = tool.build(root, "0.1.2")
            bytes2 = archive2.read_bytes()
            self.assertEqual(bytes1, bytes2, "PC archive build must be byte-for-byte deterministic")

            with zipfile.ZipFile(archive1) as zipped:
                infos = zipped.infolist()
                names = [info.filename for info in infos]
                self.assertEqual(names, sorted(names), "ZIP entries must be sorted")
                for info in infos:
                    self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                    self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                    self.assertEqual(info.create_system, 3)
                    self.assertEqual(info.external_attr, (0o100644 << 16))
                    self.assertFalse(info.filename.endswith("/"))

    def test_build_atomic_failure_preserves_previous_artifacts(self):
        tool = load_pc_builder()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_fixture(root)

            archive, checksum = tool.build(root, "0.1.2")
            orig_bytes = archive.read_bytes()
            orig_checksum = checksum.read_text(encoding="utf-8")

            # Inject a secret to fail scanner
            secret = "gh" + "p_" + "x" * 36
            (root / "pc/ws_min.py").write_text(f"{secret}\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                tool.build(root, "0.1.2")

            # Previous archive and checksum are still intact
            self.assertEqual(archive.read_bytes(), orig_bytes)
            self.assertEqual(checksum.read_text(encoding="utf-8"), orig_checksum)


if __name__ == "__main__":
    unittest.main()
