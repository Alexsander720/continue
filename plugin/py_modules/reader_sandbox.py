"""Run a ddsaves reader in a bubblewrap sandbox (Linux), in-process fallback elsewhere.

Readers are plain Python modules; in-process they can do whatever the backend user can.
Here each read() runs in a short-lived child that sees only:

- /usr (read-only) for the system Python and openssl,
- plugin/py_modules (read-only) for the reader code and its tables,
- the save locations this reader may legitimately use (read-only): Proton prefixes, Steam
  userdata and the game's install folder for its appid(s), plus libraryfolders.vdf,
- an empty tmpfs /tmp, no network, no other home content, no write access to any of the above.

The child prints one JSON card; this module validates its shape and size before it is used.
If bwrap or a system Python is missing, or the sandbox itself cannot start (user namespaces
disabled), the reader runs in-process exactly as before and status() says why.
"""
from __future__ import annotations
import ast
import importlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ddsaves import _common

PY_MODULES = Path(__file__).resolve().parent
RUNNER = PY_MODULES / "reader_sandbox_runner.py"
SLUG = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")
APPID_NAME = re.compile(r"^APPIDS?(?:_[A-Z0-9]+)?$")
MAX_OUTPUT = 2 * 1024 * 1024
MAX_STRING = 4096
MAX_DEPTH = 6
TIMEOUT = 10.0
CARD_KEYS = {"place", "chapter", "objective", "progress", "facts", "proven", "unproven",
             "observed_at", "source_path", "reason", "play_seconds", "fact_sources", "nonmonotonic"}

_state: Dict[str, Any] = {"checked": False, "bwrap": None, "python": None, "reason": None, "fallbacks": 0}


def _probe() -> None:
    if _state["checked"]:
        return
    _state["checked"] = True
    if os.name == "nt":
        _state["reason"] = "windows: no bubblewrap"
        return
    bwrap = shutil.which("bwrap") or ("/usr/bin/bwrap" if os.access("/usr/bin/bwrap", os.X_OK) else None)
    if not bwrap:
        _state["reason"] = "bwrap not installed"
        return
    python = next((p for p in ("/usr/bin/python3", shutil.which("python3")) if p and os.access(p, os.X_OK)), None)
    if not python:
        _state["reason"] = "no system python3 for the sandbox"
        return
    _state["bwrap"], _state["python"] = bwrap, python


def status() -> Dict[str, Any]:
    _probe()
    return {"sandboxed": bool(_state["bwrap"]), "bwrap": _state["bwrap"], "python": _state["python"],
            "reason": _state["reason"], "fallbacks": _state["fallbacks"]}


def disable(reason: str) -> None:
    """Fall back to in-process reads from now on (sandbox start failure)."""
    _probe()
    _state["bwrap"], _state["reason"] = None, reason
    _state["fallbacks"] += 1


def _module_file(slug: str) -> Optional[Path]:
    if not SLUG.fullmatch(slug):
        return None
    path = PY_MODULES / "ddsaves" / f"{slug}.py"
    return path if path.is_file() else None


def reader_appids(slug: str) -> List[int]:
    """APPID constants declared by the reader and its sibling `_ag_<slug>_reader.py`, parsed without importing."""
    out: List[int] = []
    files = [PY_MODULES / "ddsaves" / name for name in (f"{slug}.py", f"_ag_{slug}_reader.py", f"_{slug}_reader.py")]
    for path in files:
        if not path.is_file():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, OSError, UnicodeDecodeError):
            continue
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            names = [t.id for t in node.targets if isinstance(t, ast.Name) and APPID_NAME.match(t.id)]
            if not names:
                continue
            values = node.value.elts if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)) else [node.value]
            for v in values:
                if isinstance(v, ast.Constant) and isinstance(v.value, int) and not isinstance(v.value, bool) and 0 < v.value < 2 ** 32:
                    out.append(v.value)
    return sorted(set(out))


def _installdir(appid: int) -> Optional[str]:
    for lib in _common.steam_libraries():
        manifest = lib / "steamapps" / f"appmanifest_{appid}.acf"
        try:
            text = manifest.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = re.search(r'"installdir"\s+"([^"\n]+)"', text)
        if m:
            return m.group(1)
    return None


def bind_targets(appids: List[int]) -> Tuple[List[Path], List[Path]]:
    """Directories and files the sandbox may read for these appids (existing ones only)."""
    dirs: List[Path] = []
    files: List[Path] = []
    for appid in appids:
        try:
            dirs += [p for p in _common.proton_user(appid) if p.is_dir()]
            dirs += [p for p in _common.steam_userdata(appid) if p.is_dir()]
            inst = _installdir(appid)
            if inst:
                dirs += _common.game_dirs(inst)
        except (ValueError, OSError):
            continue
    for root in _common.steam_roots():
        vdf = root / "steamapps/libraryfolders.vdf"
        if vdf.is_file():
            files.append(vdf)
    return _common._uniq(dirs), _common._uniq(files)


def sandbox_argv(argv: List[str], dirs: List[Path], files: List[Path], env: Dict[str, str]) -> List[str]:
    _probe()
    cmd = [_state["bwrap"], "--unshare-all", "--die-with-parent", "--new-session", "--clearenv",
           "--ro-bind", "/usr", "/usr", "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
           "--symlink", "usr/bin", "/bin", "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
           "--ro-bind-try", "/etc/localtime", "/etc/localtime",   # local time for save timestamps
           "--ro-bind", str(PY_MODULES), str(PY_MODULES)]
    for d in dirs:
        cmd += ["--ro-bind", str(d), str(d)]
    for f in files:
        cmd += ["--ro-bind-try", str(f), str(f)]
    for key, value in env.items():
        cmd += ["--setenv", key, value]
    return cmd + ["--"] + argv


def sandbox_exec(argv: List[str], dirs: List[Path], files: List[Path], env: Dict[str, str], timeout: float = TIMEOUT) -> subprocess.CompletedProcess:
    """Run argv inside the sandbox; raises OSError/TimeoutExpired like subprocess.run."""
    return subprocess.run(sandbox_argv(argv, dirs, files, env), capture_output=True, timeout=timeout,
                          stdin=subprocess.DEVNULL)


def _clean(value: Any, depth: int = 0) -> Any:
    if depth > MAX_DEPTH:
        return None
    if isinstance(value, str):
        return value[:MAX_STRING]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value if value == value and abs(value) < 1e18 else None
    if isinstance(value, list):
        return [_clean(v, depth + 1) for v in value[:512]]
    if isinstance(value, dict):
        return {str(k)[:128]: _clean(v, depth + 1) for k, v in list(value.items())[:256]}
    return str(value)[:MAX_STRING]


def validate_card(raw: Any) -> Optional[Dict[str, Any]]:
    """Shape-check a card that came from the child; unknown keys are dropped, texts are capped."""
    if not isinstance(raw, dict):
        return None
    card: Dict[str, Any] = {}
    for key in ("place", "chapter", "objective", "source_path", "reason"):
        v = raw.get(key)
        card[key] = v[:MAX_STRING] if isinstance(v, str) else None
    obs = raw.get("observed_at")
    card["observed_at"] = float(obs) if isinstance(obs, (int, float)) and not isinstance(obs, bool) else None
    play = raw.get("play_seconds")
    card["play_seconds"] = float(play) if isinstance(play, (int, float)) and not isinstance(play, bool) else None
    progress = raw.get("progress")
    card["progress"] = _clean(progress) if isinstance(progress, dict) else {}
    facts = []
    for f in raw.get("facts") or []:
        if isinstance(f, dict):
            facts.append({k: str(f.get(k, ""))[:MAX_STRING] for k in ("id", "icon", "label", "value")})
    card["facts"] = facts[:64]
    for key in ("proven", "unproven"):
        card[key] = [str(x)[:128] for x in (raw.get(key) or []) if isinstance(x, str)][:256]
    for key in ("fact_sources", "nonmonotonic"):
        v = raw.get(key)
        if isinstance(v, dict):
            card[key] = {str(k)[:128]: str(x)[:128] for k, x in list(v.items())[:128]}
    return card


def _in_process(slug: str) -> Optional[Dict[str, Any]]:
    mod = importlib.import_module(f"ddsaves.{slug}")
    return mod.read(None)


def read_card(slug: str, appid: Optional[int] = None, lang: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Card dict from the reader `ddsaves.<slug>`, sandboxed when possible. None when the reader is absent."""
    if _module_file(slug) is None:
        return None
    _probe()
    if not _state["bwrap"]:
        return _in_process(slug)
    appids = reader_appids(slug)
    if isinstance(appid, int) and not isinstance(appid, bool) and 0 < appid < 2 ** 32:
        appids = sorted(set(appids) | {appid})
    dirs, files = bind_targets(appids)
    home = str(_common.deck_home())
    env = {"HOME": home, "CONTINUE_HOME": home, "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
           "PYTHONDONTWRITEBYTECODE": "1", "CONTINUE_LANG": lang or os.environ.get("CONTINUE_LANG", "en")}
    try:
        proc = sandbox_exec([_state["python"], "-I", "-B", str(RUNNER), slug], dirs, files, env)
    except subprocess.TimeoutExpired:
        return {"error": f"reader timeout after {TIMEOUT:g}s (sandbox)"}
    except OSError as error:
        disable(f"bwrap could not start: {type(error).__name__}")
        return _in_process(slug)
    out = proc.stdout[:MAX_OUTPUT + 1]
    if proc.returncode != 0 and not out.strip():
        err = proc.stderr.decode("utf-8", "replace").strip()
        if err.startswith("bwrap:"):   # the sandbox itself failed (no user namespaces, missing mount) -> fallback
            disable(err.splitlines()[0][:200])
            return _in_process(slug)
        return {"error": f"sandbox exit {proc.returncode}: {err[-300:]}"}
    if len(out) > MAX_OUTPUT:
        return {"error": "reader output exceeds the sandbox limit"}
    try:
        raw = json.loads(out.decode("utf-8", "replace") or "null")
    except ValueError:
        return {"error": "reader returned no JSON card"}
    if isinstance(raw, dict) and isinstance(raw.get("error"), str) and len(raw) == 1:
        return {"error": raw["error"][:300]}
    card = validate_card(raw)
    return card if card is not None else {"error": "reader returned no card"}
