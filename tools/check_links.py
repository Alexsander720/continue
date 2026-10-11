#!/usr/bin/env python3
"""Check repository-local links without accessing the network."""

from __future__ import annotations

import html.parser
import re
import sys
import urllib.parse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
SKIP_SCHEMES = {"http", "https", "mailto", "tel", "data", "javascript"}


class Links(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: list[tuple[int, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if value and name.casefold() in {"href", "src", "poster"}:
                self.values.append((self.getpos()[0], value))


def normalize(raw: str) -> str | None:
    raw = raw.strip()
    if raw.startswith("<") and raw.endswith(">"):
        raw = raw[1:-1]
    # Markdown permits an optional quoted title after the destination.
    raw = re.sub(r'''\s+["'][^"']*["']\s*$''', "", raw).strip()
    if not raw or raw.startswith("#"):
        return None
    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme.casefold() in SKIP_SCHEMES or parsed.netloc:
        return None
    path = urllib.parse.unquote(parsed.path).replace("\\", "/")
    return path or None


def destination(source: Path, raw: str) -> Path | None:
    path = normalize(raw)
    if path is None:
        return None
    if path.startswith("/"):
        # Absolute links in the website are rooted at site/, just like preview.py.
        return ROOT / "site" / path.lstrip("/")
    return source.parent / path


def markdown_links(path: Path) -> list[tuple[int, str]]:
    values: list[tuple[int, str]] = []
    fenced = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        values.extend((number, match.group(1)) for match in MARKDOWN_LINK.finditer(line))
        parser = Links()
        parser.feed(line)
        values.extend((number, value) for _, value in parser.values)
    return values


def html_links(path: Path) -> list[tuple[int, str]]:
    parser = Links()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.values


def main() -> int:
    errors: list[str] = []
    checked = 0
    files = sorted(ROOT.rglob("*.md")) + sorted(ROOT.rglob("*.html"))
    for source in files:
        if ".git" in source.parts or "dist" in source.parts:
            continue
        links = markdown_links(source) if source.suffix.casefold() == ".md" else html_links(source)
        for line, raw in links:
            target = destination(source, raw)
            if target is None:
                continue
            checked += 1
            if not target.exists():
                errors.append(f"{source.relative_to(ROOT)}:{line}: {raw} -> missing {target.relative_to(ROOT) if target.is_relative_to(ROOT) else target}")
    if errors:
        print("BROKEN LOCAL LINKS")
        print("\n".join(errors))
        return 1
    print(f"OK: {checked} local links across {len(files)} Markdown/HTML files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
