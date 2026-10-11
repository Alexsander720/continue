"""Offline, stdlib scan of a public tree. Reports rule/location, never matched secrets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules", "cache", "logs"}
PRIVATE_NAMES = {"deck_saves_" + "private.py", "hub_" + "saves.py", ".env", "sgdb_" + "key.txt"}
RULES = {
    "local-path": re.compile(r"(?i)(?<![a-z])[a-z]:[\\/]{1,2}(?:Scripts|Users|SteamLibrary|Emulators)(?:[\\/]|\b)"),
    "personal-home": re.compile(r"/home/(?!deck(?:/|\b)|steamuser(?:/|\b))[A-Za-z0-9_.-]+/"),
    "lan-address": re.compile(r"\b(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"),
    "mac-address": re.compile(r"(?i)\b[0-9a-f]{2}(?::[0-9a-f]{2}){5}\b"),
    "token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{35}|\d{8,10}:[A-Za-z0-9_-]{35})\b"),
    "steam-account": re.compile(r"\b7656119\d{10}\b"),
    "private-owner": re.compile(r"(?i)\b(?:ban" + r"13|apo" + r"gulay|tailb" + r"81621)\b"),
    "private-platform": re.compile(r"(?i)\b(?:ninten" + r"do|ed" + r"en)\b|\bswitch\b\s*[,)/]|(?<!\\)\(switch\b|\bswitch[- ]?(?:разбор|эмул|сейв|игр)"),
}
AUTHOR_ACCOUNT = "7656119" + "8038135489"
AUTHOR_CREDIT_PATHS = {"README.md", "NOTICE.md", "plugin/NOTICE.md", "site/data.js"}


def approved_author_credit(relative, line, match):
    return (relative.as_posix() in AUTHOR_CREDIT_PATHS
            and match.group() == AUTHOR_ACCOUNT
            and "Doctor_Nerd" in line
            and "https://steamcommunity.com/profiles/" + AUTHOR_ACCOUNT in line)


def approved_donation(relative, line, match):
    # Only the intentionally published PayPal field, not arbitrary owner text.
    if match.group().casefold() != "apo" + "gulay":
        return False
    address = "apo" + r"gulay@gmail\.com"
    if relative.as_posix() == "site/data.js":
        return bool(re.fullmatch(r'\s*paypal:\s*"' + address + r'",\s*', line))
    if relative.as_posix() in {"_readme_preview_dark.html", "_readme_preview_light.html"}:
        return bool(re.fullmatch(r'\s*<strong>PayPal</strong> — <code>' + address + r'</code>\s*', line))
    return False


def scan_tree(root: Path) -> list[dict]:
    root = root.resolve()
    findings = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        if relative.parts[0] == "dist" and path.name.startswith("continue-deck-") and path.suffix in {".zip", ".sha256"}:
            continue
        if path.is_symlink():
            findings.append({"path": relative.as_posix(), "line": 0, "rule": "symlink"})
            continue
        if not path.is_file():
            continue
        if path.name.lower() in PRIVATE_NAMES or path.name.lower().endswith((".key", "_key.txt")):
            findings.append({"path": relative.as_posix(), "line": 0, "rule": "private-file"})
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue  # Existing site screenshots/media are binary, outside text scanning.
        except OSError:
            findings.append({"path": relative.as_posix(), "line": 0, "rule": "unreadable"})
            continue
        for number, line in enumerate(content.splitlines(), 1):
            for rule, pattern in RULES.items():
                matches = list(pattern.finditer(line))
                if rule == "steam-account":
                    matches = [match for match in matches if not approved_author_credit(relative, line, match)]
                if rule == "private-owner":
                    matches = [match for match in matches if not approved_donation(relative, line, match)]
                if matches:
                    findings.append({"path": relative.as_posix(), "line": number, "rule": rule})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    findings = scan_tree(args.root)
    for item in findings:
        print(f"FAIL {item['path']}:{item['line']} {item['rule']} [value redacted]")
    print(f"Private scan: {len(findings)} findings")
    return bool(findings)


if __name__ == "__main__":
    raise SystemExit(main())
