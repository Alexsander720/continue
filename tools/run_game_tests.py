"""Offline portable game tests with the contribution's documented helpers."""
import argparse
import ipaddress
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    folder = (root / "games" / args.slug).resolve()
    if folder.parent != root / "games" or not folder.is_dir():
        parser.error("expected an existing games/<slug> directory")

    def audit(event, arguments):
        if event == "socket.connect":
            try:
                if ipaddress.ip_address(arguments[1][0]).is_loopback:
                    return  # Windows asyncio internal socketpair only.
            except (IndexError, TypeError, ValueError):
                pass
            raise OSError("external network disabled in game tests")
        if event in {"socket.getaddrinfo", "urllib.Request"}:
            raise OSError("network disabled in game tests")

    sys.addaudithook(audit)
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(folder), str(root / "plugin/py_modules"), str(root)]
    suite = unittest.defaultTestLoader.discover(str(folder), pattern="test_reader.py")
    if suite.countTestCases() == 0:
        parser.error("contribution has no reader tests")
    return not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()


if __name__ == "__main__":
    raise SystemExit(main())
