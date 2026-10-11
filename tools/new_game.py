"""Create an unproven game contribution skeleton. No guessed fields or game content."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SLUG = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")


def create_game(root: Path, slug: str, appid: int) -> Path:
    if not SLUG.fullmatch(slug) or not 0 < int(appid) < 2**31:
        raise ValueError("Use lowercase_with_underscores and a positive Steam appid")
    folder = root.resolve() / "games" / slug
    folder.mkdir(parents=True, exist_ok=False)
    files = {
        "reader.py": '''"""Read-only, stdlib reader. Implement only after comparing real save stages."""
def read(path_or_dir=None):
    return {"place": None, "chapter": None, "objective": None, "progress": {},
            "facts": [], "proven": [], "unproven": [], "fact_sources": {}}
''',
        "tables.py": f'''"""Generate data/{slug}.<lang>.json from the user's own game files.

Do not commit extracted game content. Implement the format after inspecting it.
"""
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game_files", type=Path)
    parser.add_argument("--language", choices=("en", "ru", "uk"), default="en")
    parser.parse_args()
    raise SystemExit("blocked: source format and generator not implemented")

if __name__ == "__main__":
    main()
''',
        "README.md": f'''# {slug}

Steam appid: `{int(appid)}`. Status: **blocked / unproven**.

## Save locations

Document Windows (Documents / AppData / Saved Games) and Steam Deck / Proton paths
after verifying them. Use `ddsaves/_common.py` helpers; never hard-code a library,
user name or drive. A contribution reader imports helpers as `ddsaves._common`;
the public gate exposes `plugin/py_modules` when that package exists.

## Evidence

No fields are proven yet. Copy at least two stages of one playthrough into the
ignored `stages/` area and list relative paths in `stages.json`, in play order.
Add golden tests with values checked independently against the game.

Names and totals come from the user's game files via `tables.py`; add interface
fact labels under `facts.{slug}.<id>` in `i18n/en.json`. Describe white silhouette
icon subjects in `icons.json`. See `proof.md` and the repository `AGENTS.md`.

Run `python tools/gate/check_cards.py {slug}`. The empty skeleton intentionally
fails the proof gate until actual evidence and a reader have been supplied.
''',
        "test_reader.py": '''"""Replace or extend this with independently verified golden save-stage values."""
import unittest
from reader import read

class ReaderTests(unittest.TestCase):
    def test_unproven_skeleton_displays_nothing(self):
        card = read()
        self.assertEqual(card["facts"], [])
        self.assertEqual(card["proven"], [])
        self.assertIsNone(card["place"])

if __name__ == "__main__":
    unittest.main()
''',
        "proof.md": '''# Evidence record

Status: blocked. Reader and generator not implemented; no facts accepted.

| field | stage 1 | stage 2 | game-visible evidence | source table | decision |
|---|---|---|---|---|---|

Record save ownership/source URL, hashes, ordered stages from one playthrough,
independent expected values, and fields that remain unproven. Downloaded saves
need a local SOURCE.md (URL and stage). Keep saves and extracted content out of Git.
If encryption blocks reading, report blocked; do not bypass it.
''',
        "stages.json": json.dumps({"appid": int(appid), "stages": []}, indent=2) + "\n",
        "icons.json": "{}\n",
        "stages/.gitignore": "*\n!.gitignore\n",
    }
    for relative, content in files.items():
        path = folder / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    return folder


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("appid", type=int)
    args = parser.parse_args()
    try:
        print(create_game(ROOT, args.slug, args.appid).relative_to(ROOT))
    except (ValueError, OSError) as error:
        parser.exit(1, f"Cannot create game: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
