"""Build Continue/ zip and checksum from this checkout, with no network or local paths."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _write_entry(zipped, name, data):
    info = zipfile.ZipInfo(name, date_time=ZIP_TIMESTAMP)
    info.create_system = 3
    info.external_attr = (0o100644 << 16)
    zipped.writestr(info, data, compress_type=zipfile.ZIP_STORED)


def build(root: Path, version: str) -> tuple[Path, Path]:
    version = version.removeprefix("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Version must have the form 0.1.0 or v0.1.0")
    root = root.resolve()
    source = root / "plugin"
    for required in ("main.py", "dist/index.js", "plugin.json", "package.json", "py_modules/deck_saves.py"):
        if not (source / required).is_file():
            raise ValueError(f"Missing public source: plugin/{required}")
    spec = importlib.util.spec_from_file_location("continue_private_scan", Path(__file__).with_name("scan_private.py"))
    scanner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scanner)
    findings = scanner.scan_tree(source)
    if findings:
        raise ValueError(f"Plugin private scan failed: {len(findings)} findings (run tools/scan_private.py)")
    destination = root / "dist"
    destination.mkdir(exist_ok=True)
    archive = destination / f"continue-deck-{version}.zip"
    checksum = archive.with_name(archive.name + ".sha256")
    with tempfile.NamedTemporaryFile(dir=destination, suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
    try:
        entries = {}
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_STORED) as zipped:
            for path in sorted(source.rglob("*")):
                if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                    continue
                relative = path.relative_to(source).as_posix()
                if relative == "RELEASE.json":
                    continue
                data = path.read_bytes()
                if relative == "package.json":
                    package = json.loads(data)
                    package["version"] = version
                    data = (json.dumps(package, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
                if relative in ("LICENSE", "NOTICE.md"):
                    continue
                entries["Continue/" + relative] = data
            for name in ("LICENSE", "NOTICE.md"):
                entries["Continue/" + name] = (root / name).read_bytes()
            entries["Continue/RELEASE.json"] = (json.dumps({"version": version, "channel": "public"}, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
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


def get_package_version(root: Path = ROOT) -> str:
    package_json = root / "plugin" / "package.json"
    data = json.loads(package_json.read_text(encoding="utf-8"))
    version = data.get("version")
    if not version or not isinstance(version, str):
        raise ValueError(f"Invalid or missing version in {package_json}")
    return version


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", default=None, help="Release version (defaults to plugin/package.json version)")
    args = parser.parse_args()
    version = args.version or get_package_version(ROOT)
    try:
        build(ROOT, version)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Build failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
