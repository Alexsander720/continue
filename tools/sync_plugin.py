"""Offline maintainer step: stage an already sanitized alpha release into plugin/.

This is never run by GitHub CI. The only input is an explicit release directory,
already containing RELEASE.json with channel=public. No private exporter is imported.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def sync(source: Path, root: Path = ROOT) -> int:
    source, root = source.resolve(), root.resolve()
    marker = json.loads((source / "RELEASE.json").read_text(encoding="utf-8"))
    if marker.get("channel") != "public":
        raise ValueError("Only an already sanitized public release may be staged")
    spec = importlib.util.spec_from_file_location("sync_private_scan", Path(__file__).with_name("scan_private.py"))
    scanner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scanner)
    if scanner.scan_tree(source):
        raise ValueError("Release contains private scan findings; source rejected")
    destination = root / "plugin"
    if destination == source or source.is_relative_to(destination):
        raise ValueError("Source must be outside destination plugin/")
    count = 0
    with tempfile.TemporaryDirectory(prefix=".plugin-stage-", dir=root) as temporary:
        staged = Path(temporary) / "plugin"
        staged.mkdir()
        for path in sorted(source.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            target = staged / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeError:
                shutil.copyfile(path, target)
            else:
                target.write_text(content, encoding="utf-8", newline="\n")
            count += 1
        backup = Path(temporary) / "previous"
        if destination.exists():
            if destination.is_symlink() or destination.resolve().parent != root or destination.name != "plugin":
                raise ValueError("Destination must resolve to this repository's plugin/ directory")
            destination.rename(backup)
        try:
            staged.rename(destination)
        except OSError:
            if backup.exists():
                backup.rename(destination)
            raise
    print(f"Staged {count} sanitized plugin files; release {marker.get('version')}")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sanitized_release", type=Path)
    args = parser.parse_args()
    try:
        sync(args.sanitized_release)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Stage failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
