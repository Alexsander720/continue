"""Stdlib proof gate for games/<slug>/reader.py, adapted from the research gate.

Input stages are paths relative to games/<slug>; generated name tables are local
data/<slug>.<lang>.json or games/<slug>/data/*.json. It never uses owner directories.
Reader execution occurs in an isolated subprocess with an offline audit guard,
copied stage files, bounded parsing time and (where available) memory limits.
"""
from __future__ import annotations
import argparse
import ast
import contextlib
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
CONTRACT = {"place", "chapter", "objective", "progress", "facts", "proven", "unproven", "fact_sources"}
WORDS = re.compile(r"[^\W\d_]{3,}", re.UNICODE)
SLUG = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")


def static_errors(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, OSError) as error:
        return [f"cannot inspect reader: {type(error).__name__}"]
    errors = []
    display_fields = {"place", "chapter", "objective", "value"}
    bindings = {target.id: node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
                for target in node.targets if isinstance(target, ast.Name)}
    def display_literal(expression, visited=frozenset()):
        if isinstance(expression, ast.Constant):
            return isinstance(expression.value, str) and bool(WORDS.search(expression.value))
        if isinstance(expression, ast.Name) and expression.id in bindings and expression.id not in visited:
            return display_literal(bindings[expression.id], visited | {expression.id})
        if isinstance(expression, (ast.BinOp, ast.BoolOp, ast.JoinedStr, ast.IfExp, ast.FormattedValue)):
            return any(display_literal(child, visited) for child in ast.iter_child_nodes(expression))
        return False  # lookup keys / input paths are not displayed text
    for node in ast.walk(tree):
        pairs = []
        if isinstance(node, ast.Dict):
            pairs = zip(node.keys, node.values)
        elif isinstance(node, ast.Assign):
            pairs = [(target.slice, node.value) for target in node.targets if isinstance(target, ast.Subscript)]
        for key, value in pairs:
            if isinstance(key, ast.Constant) and key.value in display_fields:
                if display_literal(value):
                    errors.append(f"{path.name}:{node.lineno} display literal for {key.value}")
        if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "get" and len(node.args) >= 2:
            fallback = node.args[1]
            if isinstance(fallback, ast.Constant) and isinstance(fallback.value, str) and WORDS.search(fallback.value):
                errors.append(f"reader.py:{node.lineno} text fallback; unknown must remain None")
        if isinstance(node, ast.Import):
            imports = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            imports = [(node.module or "").split(".")[0]]
        else:
            imports = []
        for name in imports:
            if name not in sys.stdlib_module_names and name not in {"ddsaves", "reader", "tables"} and not (path.parent / f"{name}.py").is_file():
                errors.append(f"reader.py:{node.lineno} non-stdlib import {name}")
    return errors


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)


def worker(reader: Path, stage: Path, root: Path) -> int:
    def audit(event, arguments):
        if event in {"socket.connect", "socket.getaddrinfo", "urllib.Request"}:
            raise OSError("Network disabled in proof gate")
    sys.addaudithook(audit)
    if os.name != "nt":
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
        except (ImportError, OSError, ValueError):
            pass
    sys.path[:0] = [str(reader.parent), str(root / "plugin/py_modules"), str(root)]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            spec = importlib.util.spec_from_file_location("contribution_reader", reader)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            output = module.read(stage)
        print(json.dumps({"card": output, "implementation": inspect.getsourcefile(module.read)}, ensure_ascii=False, allow_nan=False))
    except Exception as error:
        print(json.dumps({"error": f"{type(error).__name__}: {error}"}))
    return 0


def check_game(root: Path, slug: str, timeout: float) -> tuple[list[str], list[str]]:
    errors, notes = [], []
    if not SLUG.fullmatch(slug):
        return ["invalid game slug"], []
    folder = root / "games" / slug
    reader = folder / "reader.py"
    if not reader.is_file():
        return [f"{slug}: missing reader"], []
    errors.extend(static_errors(reader))
    try:
        config = json.loads((folder / "stages.json").read_text(encoding="utf-8"))
        stages = config["stages"]
        if not isinstance(stages, list) or len(stages) < 2:
            return errors + [f"{slug}: at least two ordered save stages are required"], []
        table_paths = list((root / "data").glob(f"{slug}*.json")) + list((folder / "data").glob("*.json"))
        words = set()
        for path in table_paths:
            for text in strings(json.loads(path.read_text(encoding="utf-8"))):
                words.update(word.casefold() for word in WORDS.findall(text))
        for path in (root / "i18n").glob("*.json"):
            for text in strings(json.loads(path.read_text(encoding="utf-8"))):
                words.update(word.casefold() for word in WORDS.findall(text))
    except (OSError, ValueError, TypeError, KeyError) as error:
        return errors + [f"{slug}: invalid stage/table configuration: {type(error).__name__}"], []
    cards = []
    for index, stage in enumerate(stages):
        try:
            source = (folder / stage["path"]).resolve()
            source.relative_to(folder.resolve())
            if not source.exists():
                raise ValueError("missing save stage")
            with tempfile.TemporaryDirectory(prefix="continue-proof-") as temporary:
                copied = Path(temporary) / source.name
                if source.is_dir():
                    shutil.copytree(source, copied)
                else:
                    shutil.copy2(source, copied)
                result = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "--worker", str(reader), str(copied), str(root)],
                                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
                response = json.loads(result.stdout)
            if result.returncode or "error" in response:
                raise ValueError(response.get("error", "worker failed"))
            implementation = Path(response.get("implementation") or "").resolve()
            implementation.relative_to(root)
            if implementation != reader.resolve():
                errors.extend(static_errors(implementation))
            card = response.get("card")
            if not isinstance(card, dict) or CONTRACT - card.keys():
                raise ValueError("missing card contract keys")
            if not isinstance(card["progress"], dict) or not isinstance(card["fact_sources"], dict) or any(not isinstance(card[key], list) for key in ("facts", "proven", "unproven")):
                raise ValueError("invalid card contract types")
            if any(not isinstance(field, str) for field in card["proven"] + card["unproven"]) or not isinstance(card.get("nonmonotonic", {}), dict):
                raise ValueError("invalid proof contract types")
            for fact in card["facts"]:
                if not isinstance(fact, dict) or not isinstance(fact.get("id"), str):
                    errors.append(f"{slug}: stage {index} fact needs stable id")
                    continue
                field = card["fact_sources"].get(fact["id"])
                if field not in card["proven"]:
                    errors.append(f"{slug}: fact {fact['id']} source is not proven")
            displayed = [card.get(key) for key in ("place", "chapter", "objective")]
            displayed.extend(fact.get("value") for fact in card["facts"] if isinstance(fact, dict))
            for text in displayed:
                if isinstance(text, str):
                    for word in WORDS.findall(text):
                        if word.casefold() not in words:
                            errors.append(f"{slug}: displayed word absent from generated tables: {word}")
            cards.append(card)
        except subprocess.TimeoutExpired:
            errors.append(f"{slug}: stage {index} timeout after {timeout:g}s")
        except (OSError, ValueError, TypeError, KeyError) as error:
            errors.append(f"{slug}: stage {index} {type(error).__name__}: {error}")
    fields = {field for card in cards for field in card["proven"] if isinstance(field, str)}
    if not fields:
        errors.append(f"{slug}: no proven fields; empty skeleton is not a contribution")
    for field in sorted(fields):
        values = [card[field] if field in card else card["progress"].get(field) for card in cards]
        if any(value is None for value in values):
            errors.append(f"{slug}: proven field {field} absent in a stage")
        if len({json.dumps(value, sort_keys=True, ensure_ascii=False) for value in values if value is not None}) < 2:
            errors.append(f"{slug}: proven field {field} never changes")
        numeric = [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
        if any(later < earlier for earlier, later in zip(numeric, numeric[1:])):
            reasons = [card.get("nonmonotonic", {}).get(field) for card in cards]
            if any(isinstance(reason, str) and reason.strip() for reason in reasons):
                notes.append(f"{slug}: {field} decreases; declared nonmonotonic, human review needed")
            else:
                errors.append(f"{slug}: proven field {field} decreases")
    notes.append(f"{slug}: {len(cards)} stage runs, proven {sorted(fields)}")
    return errors, notes


def main() -> int:
    if len(sys.argv) == 5 and sys.argv[1] == "--worker":
        return worker(*(Path(value).resolve() for value in sys.argv[2:]))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slugs", nargs="*")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    if not 0 < args.timeout <= 60:
        parser.error("timeout must be between 0 and 60 seconds")
    root = args.root.resolve()
    slugs = args.slugs or sorted(path.name for path in (root / "games").glob("*") if path.is_dir())
    errors, notes = [], []
    for slug in slugs:
        game_errors, game_notes = check_game(root, slug, args.timeout)
        errors.extend(game_errors)
        notes.extend(game_notes)
    if not slugs:
        errors.append("No games supplied; no proof was checked")
    for message in errors:
        print("FAIL", message)
    for message in notes:
        print("INFO", message)
    print(f"Cards gate: {'FAILED' if errors else 'PASSED'} ({len(errors)} failures)")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
