"""Release-only PC updater. The helper is self-contained and uses only stdlib.

Install layout: ROOT/app/{RELEASE.json,pc/,plugin/}, ROOT/install.json.
The service copies this module outside app, starts --apply, then exits itself.
No Steam process, scheduled task or unrelated service is stopped here.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import re
import shutil
import ssl
import stat
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path

UPDATE_REPO = "Alexsander720/continue"
MAX_DOWNLOAD = 128 * 1024 * 1024
MAX_UNPACKED = 512 * 1024 * 1024
MAX_FILE = 64 * 1024 * 1024
MAX_ENTRIES = 3000
ALLOWED_HOSTS = {"api.github.com", "github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"}
REQUIRED = {"RELEASE.json", "pc/gamehub_bp.py", "plugin/main.py", "plugin/dist/index.js", "LICENSE", "NOTICE.md"}
VERSION = re.compile(r"\d+\.\d+\.\d+\Z")


class UpdateError(Exception):
    """A bounded, actionable update failure; the current install is preserved."""


def _version(value):
    if not isinstance(value, str) or not VERSION.fullmatch(value):
        raise UpdateError("Invalid release version")
    return tuple(int(part) for part in value.split("."))


def _url(value):
    if not isinstance(value, str):
        raise UpdateError("Invalid update URL")
    try:
        parsed = urllib.parse.urlsplit(value)
        if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
                or parsed.port not in (None, 443) or parsed.username or parsed.password or parsed.fragment):
            raise ValueError()
    except ValueError:
        raise UpdateError("Invalid update URL: HTTPS GitHub origin required") from None
    return value


class _Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        _url(newurl)
        return super().redirect_request(request, response, code, message, headers, newurl)


def fetch_https(url, limit):
    """Read bounded HTTPS bytes, validating redirect origins before connecting."""
    _url(url)
    until = time.monotonic() + 120
    request = urllib.request.Request(url, headers={"User-Agent": "Continue-PC", "Accept": "application/vnd.github+json"})
    opener = urllib.request.build_opener(_Redirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    with opener.open(request, timeout=20) as response:
        _url(response.geturl())
        length = response.headers.get("Content-Length")
        if length and (not length.isdigit() or int(length) > limit):
            raise UpdateError("Update download exceeds size limit")
        parts, total = [], 0
        while True:
            if time.monotonic() >= until:
                raise UpdateError("Update download timed out")
            part = response.read(min(65536, limit + 1 - total))
            if not part:
                return b"".join(parts)
            total += len(part)
            if total > limit:
                raise UpdateError("Update download exceeds size limit")
            parts.append(part)


def _json(path):
    try:
        if path.stat().st_size > 65536:
            raise UpdateError("Local update metadata exceeds size limit")
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_json(path, value):
    tmp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _marker(app):
    marker = _json(app / "RELEASE.json")
    if marker.get("channel") != "public":
        raise UpdateError("Updates require a public release marker")
    _version(marker.get("version"))
    return marker["version"]


def _is_link(path):
    if path.is_symlink():
        return True
    try:
        # Junctions are reparse points but are not reported as symlinks.
        return bool(getattr(path.lstat(), "st_file_attributes", 0) & 0x400)
    except FileNotFoundError:
        return False


def pid_alive(pid):
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code)) and code.value == 259)
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def wait_for_pid(pid, timeout=60):
    """Wait for the supplied process to exit; never terminate or signal it."""
    if pid <= 0 or pid == os.getpid():
        raise UpdateError("Invalid service PID")
    until = time.monotonic() + timeout
    while pid_alive(pid):
        if time.monotonic() >= until:
            raise UpdateError("Service did not exit; update cancelled")
        time.sleep(0.2)


class PublicUpdater:
    def __init__(self, root, *, fetch=None, clock=None):
        given = Path(root).absolute()
        if _is_link(given):
            raise UpdateError("Installation root must not be a symlink")
        self.root = given.resolve()
        self.app = self.root / "app"
        self.fetch = fetch or fetch_https
        self.clock = clock or time.time
        self.journal = self.root / "update-journal.json"
        self._child = None
        self._started_at = 0

    def _safe(self, path):
        if path.parent != self.root or _is_link(path):
            raise UpdateError("Unsafe installation path")
        if path.exists() and not path.is_dir():
            raise UpdateError("Installation path is not a directory")

    @contextlib.contextmanager
    def _lock(self):
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / "update.lock"
        if _is_link(path):
            raise UpdateError("Unsafe update lock")
        with path.open("a+b") as stream:
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise UpdateError("Another updater is already running") from None
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def check(self, force=False):
        self._safe(self.app)
        try:
            current = _marker(self.app)
        except UpdateError:
            return {"current": "dev", "available": False, "dev": True}
        cache = _json(self.root / "update.json")
        now = self.clock()
        checked = cache.get("checked_at")
        if not isinstance(checked, (int, float)) or not math.isfinite(checked) or checked > now + 300:
            cache = {}
        if force or not cache or now - cache.get("checked_at", 0) >= 86400:
            cache = {"checked_at": now, "rel": {}}
            try:
                raw = self.fetch(f"https://api.github.com/repos/{UPDATE_REPO}/releases/latest", 1024 * 1024)
                if len(raw) > 1024 * 1024:
                    raise UpdateError("Release metadata exceeds size limit")
                release = json.loads(raw.decode("utf-8"))
                version = str(release.get("tag_name", "")).removeprefix("v")
                _version(version)
                if release.get("draft") or release.get("prerelease"):
                    raise UpdateError("Not a stable release")
                name = f"continue-pc-{version}.zip"
                assets = {a.get("name"): a.get("browser_download_url") for a in release.get("assets", [])}
                url, sha_url = _url(assets.get(name)), _url(assets.get(name + ".sha256"))
                expected = f"https://github.com/{UPDATE_REPO}/releases/download/"
                if not url.startswith(expected) or not sha_url.startswith(expected):
                    raise UpdateError("Unexpected release asset URL")
                checksum = self.fetch(sha_url, 4096)
                if len(checksum) > 4096:
                    raise UpdateError("Checksum metadata exceeds size limit")
                match = re.fullmatch(rb"([0-9a-fA-F]{64})(?:[ \t]+\*?([^\r\n]+))?\s*", checksum)
                if not match or (match[2] and match[2].decode("utf-8") != name):
                    raise UpdateError("Invalid release checksum")
                cache["rel"] = {"version": version, "url": url, "sha256": match[1].decode().lower(),
                    "notes": str(release.get("body") or "")[:1500]}
            except Exception as error:
                cache["error"] = str(error)[:300]
            _write_json(self.root / "update.json", cache)
        rel = cache.get("rel") if isinstance(cache.get("rel"), dict) else {}
        latest = rel.get("version")
        try:
            available = bool(latest and rel.get("sha256") and _version(latest) > _version(current))
        except UpdateError:
            available = False
        result = {"current": current, "latest": latest, "available": available, "url": rel.get("url"),
            "sha256": rel.get("sha256"), "notes": rel.get("notes"), "checked_at": cache.get("checked_at")}
        if cache.get("error"):
            result["error"] = cache["error"]
        return result

    def download(self, info):
        self._safe(self.app)
        _marker(self.app)
        version = info.get("latest") or info.get("version")
        _version(version)
        url = _url(info.get("url"))
        sha = str(info.get("sha256", "")).lower()
        if not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise UpdateError("Invalid release checksum")
        folder = self.root / "downloads"
        self._safe(folder)
        folder.mkdir(exist_ok=True)
        data = self.fetch(url, MAX_DOWNLOAD)
        if len(data) > MAX_DOWNLOAD:
            raise UpdateError("Update download exceeds size limit")
        if hashlib.sha256(data).hexdigest() != sha:
            raise UpdateError("Update checksum mismatch")
        path = folder / f"continue-pc-{version}.zip"
        tmp = folder / (path.name + ".tmp-" + uuid.uuid4().hex)
        try:
            tmp.write_bytes(data)
            self._inspect(tmp, sha, expected_version=version)
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)
        return path

    def _inspect(self, path, sha, expected_version=None):
        if not re.fullmatch(r"[0-9a-fA-F]{64}", str(sha)):
            raise UpdateError("Invalid update checksum")
        if path.stat().st_size > MAX_DOWNLOAD:
            raise UpdateError("Update archive exceeds size limit")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(65536), b""):
                digest.update(chunk)
        if digest.hexdigest() != sha.lower():
            raise UpdateError("Update checksum mismatch")
        try:
            with zipfile.ZipFile(path) as archive:
                entries = archive.infolist()
                if len(entries) > MAX_ENTRIES or sum(item.file_size for item in entries) > MAX_UNPACKED:
                    raise UpdateError("Update archive exceeds unpacked size limit")
                names, seen = {}, set()
                for item in entries:
                    # ZipInfo normalizes backslashes on Windows; validate the
                    # actual central-directory name before that normalization.
                    name = item.orig_filename.rstrip("/")
                    parts = name.split("/")
                    if (not name or "\\" in name or name.startswith("/") or any(
                            part in ("", ".", "..") or part.endswith((".", " ")) or ":" in part
                            or any(ord(char) < 32 for char in part)
                            or re.fullmatch(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part, re.I)
                            for part in parts)):
                        raise UpdateError("Unsafe update archive path")
                    key = name.casefold()
                    if key in seen:
                        raise UpdateError("Duplicate update archive path")
                    seen.add(key)
                    mode = item.external_attr >> 16
                    kind = stat.S_IFMT(mode)
                    if kind not in (0, stat.S_IFREG, stat.S_IFDIR) or (item.external_attr & 0x400):
                        raise UpdateError("Unsupported update archive file type")
                    if item.flag_bits & 1 or item.file_size > MAX_FILE or (item.file_size > 1048576 and item.file_size > max(1, item.compress_size) * 1000):
                        raise UpdateError("Update archive entry exceeds size limit")
                    names[name] = item
                if "RELEASE.json" in names:
                    prefix = ""
                else:
                    roots = {name.split("/", 1)[0] for name in names}
                    if len(roots) != 1:
                        raise UpdateError("Update archive missing release root")
                    prefix = next(iter(roots)) + "/"
                files = {name[len(prefix):]: item for name, item in names.items() if name.startswith(prefix) and not item.is_dir()}
                if not REQUIRED.issubset(files):
                    raise UpdateError("Update archive missing required files")
                if files["RELEASE.json"].file_size > 16384:
                    raise UpdateError("Release marker exceeds size limit")
                marker = json.loads(archive.read(files["RELEASE.json"]).decode("utf-8"))
                version = marker.get("version")
                _version(version)
                if marker.get("channel") != "public" or (expected_version and version != expected_version):
                    raise UpdateError("Release marker version or channel mismatch")
                if _version(version) <= _version(_marker(self.app)):
                    raise UpdateError("Update version must be newer")
                for name in files:
                    ancestors = Path(name).parents
                    if any(str(parent).replace("\\", "/").casefold() in {n.casefold() for n in files} for parent in ancestors if str(parent) != "."):
                        raise UpdateError("Update archive path conflicts with file")
                return version, [(name, item.filename) for name, item in files.items()]
        except (zipfile.BadZipFile, ValueError, KeyError, AttributeError) as error:
            raise UpdateError("Invalid update archive: " + str(error)[:120]) from error

    def _remove(self, path):
        self._safe(path)
        if path.exists():
            shutil.rmtree(path)

    def _stop(self):
        # Only the process this helper itself launched can be terminated.
        if self._child and self._child.poll() is None:
            self._child.terminate()
            try:
                self._child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._child.kill()
                self._child.wait(timeout=5)

    def _pythonw(self):
        manifest = _json(self.root / "install.json")
        exe = manifest.get("pythonw") or manifest.get("pythonw_path")
        if not isinstance(exe, str) or not Path(exe).is_absolute() or not Path(exe).is_file():
            raise UpdateError("Installation manifest has no usable pythonw path")
        return exe

    def _start(self, app, nonce, version):
        env = os.environ.copy()
        env["CONTINUE_UPDATE_NONCE"] = nonce
        env["CONTINUE_HOME"] = str(self.root)
        self._started_at = self.clock()
        options = {"cwd": str(app), "env": env, "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if os.name == "nt":
            options["creationflags"] = subprocess.CREATE_NO_WINDOW
        self._child = subprocess.Popen([self._pythonw(), str(app / "pc" / "gamehub_bp.py"), "run"], **options)

    def ready(self, nonce, version, *, since=0):
        state = _json(self.root / "service_ready.json")
        return bool(state.get("nonce") == nonce and state.get("version") == version
            and isinstance(state.get("at"), (int, float)) and since <= state["at"] <= self.clock() + 5
            and pid_alive(state.get("pid")))

    def _health(self, nonce, version):
        until = time.monotonic() + 30
        while time.monotonic() < until:
            if self._child and self._child.poll() is not None:
                return False
            if self.ready(nonce, version, since=self._started_at):
                return True
            time.sleep(0.2)
        return False

    def _journal_paths(self, journal):
        paths = []
        for key, prefix in (("stage", "app.next-"), ("backup", "app.previous-")):
            name = journal.get(key)
            if not isinstance(name, str) or not re.fullmatch(re.escape(prefix) + r"[a-zA-Z0-9]+", name):
                raise UpdateError("Unsafe update journal path")
            path = self.root / name
            self._safe(path)
            paths.append(path)
        return paths

    def _set_installed_version(self, version):
        """Keep install.json consistent with the atomically selected app tree."""
        _version(version)
        path = self.root / "install.json"
        if not path.exists():
            return
        if _is_link(path) or not path.is_file():
            raise UpdateError("Unsafe installation manifest")
        manifest = _json(path)
        if not manifest:
            raise UpdateError("Installation manifest is unreadable")
        manifest["version"] = version
        manifest["updated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.clock()))
        _write_json(path, manifest)

    def recover(self, *, stop=None, start=None, health=None):
        with self._lock():
            return self._recover(stop or self._stop, start or self._start, health or self._health)

    def _recover(self, stop, start, health):
        if not self.journal.exists():
            return {"recovered": False}
        journal = _json(self.journal)
        stage, backup = self._journal_paths(journal)
        self._safe(self.app)
        state = journal.get("state")
        if state not in ("prepared", "backed_up", "swapped", "confirmed", "rolled_back"):
            raise UpdateError("Invalid update journal state")
        if state == "confirmed":
            confirmed_version = _marker(self.app)
            self._set_installed_version(confirmed_version)
            self._remove(backup)
            self._remove(stage)
            self.journal.unlink()
            return {"recovered": True, "rolled_back": False}
        if backup.exists():
            old_version = _marker(backup)
            stop()
            if self.app.exists():
                _marker(self.app)
                self._remove(self.app)
            os.replace(backup, self.app)
            journal["state"] = "rolled_back"
            _write_json(self.journal, journal)
        elif state == "rolled_back":
            old_version = _marker(self.app)
        elif self.app.exists() and _marker(self.app) == journal.get("current") and state in ("backed_up", "swapped"):
            # A crash between restoring app and recording rolled_back leaves
            # no backup; its public marker proves the original tree is back.
            old_version = _marker(self.app)
        elif state == "prepared" and self.app.exists():
            old_version = _marker(self.app)
        else:
            raise UpdateError("Update recovery needs the previous application")
        self._remove(stage)
        nonce = uuid.uuid4().hex
        journal["state"] = "rolled_back"
        journal["nonce"] = nonce
        _write_json(self.journal, journal)
        start(self.app, nonce, old_version)
        if not health(nonce, old_version):
            raise UpdateError("Previous service restored but did not become ready")
        self._set_installed_version(old_version)
        self.journal.unlink()
        return {"recovered": True, "rolled_back": True, "version": old_version}

    def apply(self, zip_path, sha256, *, expected_version=None, stop=None, start=None, health=None):
        stop, start, health = stop or self._stop, start or self._start, health or self._health
        with self._lock():
            self._recover(stop, start, health)
            self._safe(self.app)
            current = _marker(self.app)
            path = Path(zip_path)
            version, files = self._inspect(path, sha256, expected_version)
            ident = uuid.uuid4().hex
            stage, backup = self.root / ("app.next-" + ident), self.root / ("app.previous-" + ident)
            stage.mkdir()
            try:
                with zipfile.ZipFile(path) as archive:
                    for relative, archived in files:
                        destination = stage.joinpath(*relative.split("/"))
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(archived) as source, destination.open("xb") as target:
                            shutil.copyfileobj(source, target, 65536)
                journal = {"state": "prepared", "stage": stage.name, "backup": backup.name,
                    "current": current, "next": version, "nonce": uuid.uuid4().hex}
                _write_json(self.journal, journal)
                try:
                    stop()
                    os.replace(self.app, backup)
                    journal["state"] = "backed_up"
                    _write_json(self.journal, journal)
                    os.replace(stage, self.app)
                    journal["state"] = "swapped"
                    _write_json(self.journal, journal)
                    start(self.app, journal["nonce"], version)
                    if not health(journal["nonce"], version):
                        raise UpdateError("New service did not become ready")
                    self._set_installed_version(version)
                except Exception as error:
                    recovery = self._recover(stop, start, health)
                    return {"ok": False, "version": current, "rolled_back": recovery.get("rolled_back", False),
                        "error": str(error)[:300]}
                journal["state"] = "confirmed"
                _write_json(self.journal, journal)
                self._remove(backup)
                self.journal.unlink()
                return {"ok": True, "version": version, "rolled_back": False}
            finally:
                if stage.exists() and not self.journal.exists():
                    self._remove(stage)

    def spawn_helper(self, zip_path, sha256, *, wait_pid):
        self._safe(self.app)
        _marker(self.app)
        # Check before asking the live release service to exit.
        self._inspect(Path(zip_path), sha256)
        helper = self.root / "update-helper.py"
        if _is_link(helper):
            raise UpdateError("Unsafe updater helper path")
        shutil.copyfile(Path(__file__), helper)
        options = {"cwd": str(self.root), "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if os.name == "nt":
            options["creationflags"] = subprocess.CREATE_NO_WINDOW
        return subprocess.Popen([self._pythonw(), str(helper), "--apply", str(Path(zip_path).resolve()),
            "--sha256", sha256, "--root", str(self.root), "--wait-pid", str(wait_pid)], **options)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Continue? PC release updater")
    parser.add_argument("--root", required=True)
    parser.add_argument("--apply", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--wait-pid", type=int)
    args = parser.parse_args(argv)
    updater = PublicUpdater(args.root)
    result = None
    waited = False
    try:
        if args.wait_pid:
            wait_for_pid(args.wait_pid)
            waited = True
        if args.apply:
            if not args.sha256:
                raise UpdateError("Missing release checksum")
            result = updater.apply(args.apply, args.sha256)
        else:
            result = updater.recover()
            if waited and updater._child is None:
                version = _marker(updater.app)
                nonce = uuid.uuid4().hex
                updater._start(updater.app, nonce, version)
                if not updater._health(nonce, version):
                    raise UpdateError("Recovered service did not become ready")
        _write_json(updater.root / "update-result.json", {"at": updater.clock(), **result})
        return 0 if result.get("ok", result.get("recovered", True)) else 1
    except Exception as error:
        previous = False
        if waited and args.apply and updater._child is None and not updater.journal.exists():
            # The service already exited after prevalidation; if the archive
            # changed meanwhile, restart its unchanged release installation.
            try:
                version = _marker(updater.app)
                nonce = uuid.uuid4().hex
                updater._start(updater.app, nonce, version)
                previous = updater._health(nonce, version)
            except Exception:
                pass
        _write_json(updater.root / "update-result.json", {"at": updater.clock(), "ok": False,
            "error": str(error)[:300], "restarted_previous": previous})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
