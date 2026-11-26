"""Child side of reader_sandbox: import one ddsaves reader, run read(None), print one JSON card."""
import json
import os
import re
import sys

MAX_MEMORY = 512 * 1024 ** 2


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else ""
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", slug):
        sys.stdout.write(json.dumps({"error": "invalid reader slug"}))
        return 2
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY, MAX_MEMORY))
    except (ImportError, OSError, ValueError):
        pass
    sys.dont_write_bytecode = True
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import importlib
        module = importlib.import_module(f"ddsaves.{slug}")
        card = module.read(None)
        payload = json.dumps(card, ensure_ascii=False, default=str, allow_nan=False)
    except Exception as error:  # the reader's failure is reported, never the traceback of the host
        payload = json.dumps({"error": f"{type(error).__name__}: {error}"[:300]})
    sys.stdout.buffer.write(payload.encode("utf-8"))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
