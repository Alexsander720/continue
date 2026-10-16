"""Run every offline CI/build step. It never creates or uploads a GitHub Release."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def run(command, cwd=ROOT, timeout=900):
    display = ["python" if part == sys.executable else part for part in command]
    print("$ " + " ".join(display), flush=True)
    result = subprocess.run(command, cwd=cwd, timeout=timeout, env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
    if result.returncode:
        raise SystemExit(result.returncode)


def get_package_version(root: Path = ROOT) -> str:
    package_json = root / "plugin" / "package.json"
    data = json.loads(package_json.read_text(encoding="utf-8"))
    version = data.get("version")
    if not version or not isinstance(version, str):
        raise ValueError(f"Invalid or missing version in {package_json}")
    return version


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default=None, help="Release version (defaults to plugin/package.json version)")
    args = parser.parse_args()
    version = args.version or get_package_version(ROOT)
    # These are the workflow steps. Unit tests contain synthetic proof stages only.
    run([sys.executable, "tools/scan_private.py"])
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run([sys.executable, "-m", "pytest", "-q", "tests/pc", "tests/deck"])
    run(["node", "--check", "plugin/dist/index.js"])
    run(["node", "--check", "pc/bp_public_controls.js"])
    run(["node", "--check", "pc/bp_public_settings.js"])
    run(["node", "--check", "pc/bp_suffix.js"])
    folders = sorted(path for path in (ROOT / "games").glob("*") if path.is_dir())
    for folder in folders:
        run([sys.executable, "-I", "tools/run_game_tests.py", folder.name])
        run([sys.executable, "tools/gate/check_cards.py", folder.name])
    if not folders:
        print("Contribution proof gate: no games/ contributions present; gate behavior tested with synthetic stages", flush=True)
    run([sys.executable, "tools/build_deck_zip.py", version])
    version = version.removeprefix("v")
    archive = ROOT / "dist" / f"continue-deck-{version}.zip"
    checksum = archive.with_name(archive.name + ".sha256")
    expected = hashlib.sha256(archive.read_bytes()).hexdigest()
    if checksum.read_text(encoding="utf-8") != f"{expected}  {archive.name}\n":
        raise SystemExit("Checksum mismatch")
    with zipfile.ZipFile(archive) as zipped:
        if zipped.testzip() is not None:
            raise SystemExit("ZIP CRC check failed")
        marker = json.loads(zipped.read("Continue/RELEASE.json"))
        if marker != {"version": version, "channel": "public"}:
            raise SystemExit("RELEASE.json mismatch")
        if any("__pycache__" in name or name.endswith(".pyc") for name in zipped.namelist()):
            raise SystemExit("Bytecode in release")
        print(f"Release readback: {len(zipped.namelist())} files; marker and checksum verified", flush=True)
    run([sys.executable, "tools/build_pc_zip.py", version])
    pc_archive = ROOT / "dist" / f"continue-pc-{version}.zip"
    pc_checksum = pc_archive.with_name(pc_archive.name + ".sha256")
    pc_expected = hashlib.sha256(pc_archive.read_bytes()).hexdigest()
    if pc_checksum.read_text(encoding="utf-8") != f"{pc_expected}  {pc_archive.name}\n":
        raise SystemExit("PC checksum mismatch")
    with zipfile.ZipFile(pc_archive) as zipped:
        if zipped.testzip() is not None:
            raise SystemExit("PC ZIP CRC check failed")
        pc_marker = json.loads(zipped.read("Continue/RELEASE.json"))
        if pc_marker != {"version": version, "channel": "public", "platform": "windows"}:
            raise SystemExit("PC RELEASE.json mismatch")
        if json.loads(zipped.read("Continue/plugin/RELEASE.json")) != {"version": version, "channel": "public"}:
            raise SystemExit("PC shared backend public-mode marker mismatch")
        names = set(zipped.namelist())
        for req in (
            "Continue/pc/ws_min.py",
            "Continue/pc/install.ps1",
            "Continue/pc/uninstall.ps1",
            "Continue/pc/gamehub_bp.py",
            "Continue/plugin/main.py",
            "Continue/plugin/py_modules/hltb.py",
            "Continue/setup.cmd",
            "Continue/LICENSE",
            "Continue/NOTICE.md",
            "Continue/docs/install-pc.md",
        ):
            if req not in names:
                raise SystemExit(f"PC package missing {req}")
        if any("__pycache__" in name or name.endswith(".pyc") for name in names):
            raise SystemExit("Bytecode in PC release")
        print(f"PC release readback: {len(names)} files; marker and checksum verified", flush=True)
    print("Local CI: PASSED. GitHub upload is a workflow-only draft step and was not executed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
