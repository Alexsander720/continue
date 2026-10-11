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


def run(command, cwd=ROOT, timeout=120):
    display = ["python" if part == sys.executable else part for part in command]
    print("$ " + " ".join(display), flush=True)
    result = subprocess.run(command, cwd=cwd, timeout=timeout, env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
    if result.returncode:
        raise SystemExit(result.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="0.1.0")
    args = parser.parse_args()
    # These are the workflow steps. Unit tests contain synthetic proof stages only.
    run([sys.executable, "tools/scan_private.py"])
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run(["node", "--check", "plugin/dist/index.js"])
    folders = sorted(path for path in (ROOT / "games").glob("*") if path.is_dir())
    for folder in folders:
        run([sys.executable, "-I", "tools/run_game_tests.py", folder.name])
        run([sys.executable, "tools/gate/check_cards.py", folder.name])
    if not folders:
        print("Contribution proof gate: no games/ contributions present; gate behavior tested with synthetic stages", flush=True)
    run([sys.executable, "tools/build_deck_zip.py", args.version])
    version = args.version.removeprefix("v")
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
    print("Local CI: PASSED. GitHub upload is a workflow-only draft step and was not executed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
