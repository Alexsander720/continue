"""Build Continue/ PC Big Picture zip and checksum from this checkout, with no network or local paths."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
_helper_spec = importlib.util.spec_from_file_location("continue_public_zip_helpers", HERE / "build_deck_zip.py")
_helpers = importlib.util.module_from_spec(_helper_spec)
_helper_spec.loader.exec_module(_helpers)
_write_entry, get_package_version = _helpers._write_entry, _helpers.get_package_version

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
    "bp_public_controls.js", "public_customization.py", "public_themes.py", "public_theme_cdp.py",
    "public_visuals.py",
    "bp_public_settings.js", "public_game_assets.py", "public_preferences.py", "public_media_policy.py",
    "public_media_runtime.py",
)


def build(root: Path, version: str) -> tuple[Path, Path]:
    version = version.removeprefix("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Version must have the form 0.1.0 or v0.1.0")
    root = root.resolve()
    plugin_source = root / "plugin"
    pc_source = root / "pc"
    docs_source = root / "docs"

    for required in ("main.py", "dist/index.js", "plugin.json", "package.json", "py_modules/deck_saves.py"):
        if not (plugin_source / required).is_file():
            raise ValueError(f"Missing public source: plugin/{required}")

    for required in PC_ALLOWLIST:
        if not (pc_source / required).is_file():
            raise ValueError(f"Missing allowlisted PC source: pc/{required}")

    if not (root / "LICENSE").is_file():
        raise ValueError("Missing root file: LICENSE")

    notice_name = "NOTICE.md" if (root / "NOTICE.md").is_file() else ("NOTICE" if (root / "NOTICE").is_file() else None)
    if not notice_name:
        raise ValueError("Missing root file: NOTICE.md or NOTICE")

    for required in ("install-pc.md", "install-pc.ru.md", "install-pc.uk.md"):
        if not (docs_source / required).is_file():
            raise ValueError(f"Missing docs source: docs/{required}")

    spec = importlib.util.spec_from_file_location("continue_private_scan", HERE / "scan_private.py")
    scanner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scanner)
    findings = scanner.scan_tree(plugin_source) + scanner.scan_tree(pc_source)
    if findings:
        raise ValueError(f"PC private scan failed: {len(findings)} findings (run tools/scan_private.py)")

    destination = root / "dist"
    destination.mkdir(exist_ok=True)
    archive = destination / f"continue-pc-{version}.zip"
    checksum = archive.with_name(archive.name + ".sha256")
    with tempfile.NamedTemporaryFile(dir=destination, suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
    try:
        entries: dict[str, bytes] = {}
        # 1. Plugin shared source under Continue/plugin/
        for path in sorted(plugin_source.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            relative = path.relative_to(plugin_source).as_posix()
            if relative in ("RELEASE.json", "LICENSE", "NOTICE.md", "NOTICE"):
                continue
            data = path.read_bytes()
            if relative == "package.json":
                package = json.loads(data)
                package["version"] = version
                data = (json.dumps(package, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            elif relative == "main.py":
                text = data.decode("utf-8").replace(
                    'ssl.create_default_context(cafile="/etc/ssl/certs/ca-certificates.crt")',
                    "ssl.create_default_context()",
                )
                data = text.encode("utf-8")
            entries[f"Continue/plugin/{relative}"] = data

        # Windows backend adaptation: hltb_stdlib.py replaces plugin/py_modules/hltb.py
        entries["Continue/plugin/py_modules/hltb.py"] = (pc_source / "hltb_stdlib.py").read_bytes()

        # 2. Allowlisted PC files under Continue/pc/
        for name in sorted(PC_ALLOWLIST):
            entries[f"Continue/pc/{name}"] = (pc_source / name).read_bytes()
        for path in sorted((pc_source / 'assets').rglob('*')):
            if not path.is_file():
                continue
            if path.is_symlink() or path.suffix not in ('.css','.json','.txt','.png','.jpg','.jpeg','.webp','.svg') and path.name != 'LICENSE' or path.name == 'config_USER.json':
                raise ValueError('Unexpected PC visual asset')
            relative = path.relative_to(pc_source).as_posix()
            entries[f"Continue/pc/{relative}"] = path.read_bytes()

        # 3. Root files and metadata
        marker = {"version": version, "channel": "public", "platform": "windows"}
        entries["Continue/RELEASE.json"] = (json.dumps(marker) + "\n").encode("utf-8")
        entries["Continue/plugin/RELEASE.json"] = (json.dumps({"version": version, "channel": "public"}, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        entries["Continue/LICENSE"] = (root / "LICENSE").read_bytes()
        entries["Continue/NOTICE.md"] = (root / notice_name).read_bytes()
        entries["Continue/plugin/LICENSE"] = entries["Continue/LICENSE"]
        entries["Continue/plugin/NOTICE.md"] = entries["Continue/NOTICE.md"]
        entries["Continue/setup.cmd"] = b'@echo off\ncall "%~dp0pc\\setup.cmd"\n'

        # 4. Docs
        for name in ("install-pc.md", "install-pc.ru.md", "install-pc.uk.md", "pc-first-start.md", "pc-first-start.ru.md", "pc-first-start.uk.md"):
            entries[f"Continue/docs/{name}"] = (docs_source / name).read_bytes()

        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_STORED) as zipped:
            for name, data in sorted(entries.items()):
                _write_entry(zipped, name, data)

        with zipfile.ZipFile(temporary) as zipped:
            if zipped.testzip() is not None:
                raise ValueError("Built ZIP failed CRC verification")

        temporary.replace(archive)
    except Exception:
        # Retain a failed build for inspection; never remove previous artifacts.
        raise

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8", newline="\n")
    print(f"Built {archive.name}: {archive.stat().st_size} bytes")
    print(f"SHA256 {digest}")
    return archive, checksum


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", default=None, help="Release version (defaults to plugin/package.json version)")
    parser.add_argument("--version", dest="version_flag", default=None, help="Release version flag")
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root")
    args = parser.parse_args()
    root = args.root.resolve()
    version = args.version or args.version_flag or get_package_version(root)
    try:
        build(root, version)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Build failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
