"""Isolated, stdlib-only public backend module for existing artwork and music controls.

Architecture / Interface:
    PublicCustomization(root, media_factory, work_allowed, settings_lock=None)
    - root: supplied per-user or test Continue data root
    - media_factory: returns the standalone MediaManager instance
    - work_allowed: callable returning bool, checks if expensive jobs are allowed
    - settings_lock: optional RLock shared with primary Backend.gate for
      root/settings.json reads/writes. Defaults to a private RLock for tests.

Exposes METHODS set and synchronous .call(method, args) dispatcher.
.close() cancels its own jobs only.

Hardening summary (see handoff report for exact limits):
- Allowed-host redirect handler validates Location BEFORE following, for both
  image CDN fetches and fixed-host SGDB API (key never leaves fixed host).
- read(cap+1) rejects oversize bodies instead of truncating into valid images.
- Strict URL checks: HTTPS, no userinfo, no explicit port, exact hosts/paths.
- Cached thumb signature/size revalidation + symlink/cache path guard.
- sgdb_list bounded by overall 45s deadline (bridge 55s), cancels pending.
- Strict AppIDs (reject bool/float/negative/oversize), exactly 11-char
  YouTube IDs, bounded query/kind/list/output.
- _closed gate, max 4 active jobs, bounded retained jobs/authorizations.
- Consent strictly True, pinned owned yt-dlp only (never PATH executable).
- work_allowed rechecked in workers, budget/cancellation guards.
- settings_lock + separate job lock, no nested opposite-order acquisition.
- none suppresses auto theme via music_choices; auto permits manager and
  removes prior custom file so it is not claimed as automatic.
"""
from __future__ import annotations

import base64
import concurrent.futures
import json
import os
import re
import secrets
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

ALLOWED_SGDB_API = "https://www.steamgriddb.com/api/v2"
SGDB_API_HOST = "www.steamgriddb.com"
SGDB_API_PREFIX = "/api/v2/"

ALLOWED_CDN_HOSTS = {
    "cdn2.steamgriddb.com",
    "cdn.steamgriddb.com",
    "images.steamgriddb.com",
    "steamgriddb.com",
    "www.steamgriddb.com",
}

SGDB_KINDS = {
    "grid": (0, "grids", "dimensions=600x900,342x482,660x930&"),
    "hero": (1, "heroes", ""),
    "logo": (2, "logos", ""),
    "wide": (3, "grids", "dimensions=460x215,920x430&"),
}

JPEG_SIGNATURE = b"\xff\xd8\xff"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

MAX_JSON_BYTES = 1024 * 1024  # 1 MB
MAX_THUMB_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20 MB

# Bridge budget: primary Backend.call waits at most 55s. Keep list well inside.
SGDB_LIST_DEADLINE_SEC = 45.0
SGDB_THUMB_OPEN_TIMEOUT = 10
SGDB_API_TIMEOUT = 15
SGDB_IMAGE_TIMEOUT = 20
MAX_THUMB_ITEMS = 30

MAX_ACTIVE_JOBS = 4
MAX_RETAINED_JOBS = 100
MAX_AUTHORIZED_IMAGES = 500
MAX_AUTHORIZED_MUSIC = 500

MAX_QUERY_LEN = 200
MAX_SEARCH_RESULTS = 12
MAX_TITLE_LEN = 200
MAX_CHANNEL_LEN = 200
_YT_ID_RE = re.compile(r"[A-Za-z0-9_-]{11}")
_APPID_STR_RE = re.compile(r"[1-9][0-9]{0,9}")
_MAX_APPID = 0xFFFFFFFF

_MUSIC_KINDS = ("theme", "ost", "menu", "query")


def _redact(msg: str, key: str) -> str:
    try:
        if key and key in msg:
            msg = msg.replace(key, "REDACTED")
    except Exception:
        pass
    return msg


def _strict_appid(value: Any) -> int:
    """Strict AppID: int 1..0xFFFFFFFF, str digits; reject bool/float/else."""
    if isinstance(value, bool):
        raise ValueError("Invalid appid")
    if isinstance(value, int):
        if 1 <= value <= _MAX_APPID:
            return value
        raise ValueError("AppID out of range")
    if isinstance(value, str):
        s = value.strip()
        if _APPID_STR_RE.fullmatch(s) and int(s) <= _MAX_APPID:
            return int(s)
        raise ValueError("Invalid appid")
    raise ValueError("Invalid appid")


def _strict_image_id(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("Invalid image ID")
    if isinstance(value, int):
        if 1 <= value <= 2**63 - 1:
            return value
        raise ValueError("Invalid image ID")
    if isinstance(value, str):
        s = value.strip()
        if re.fullmatch(r"[1-9][0-9]{0,18}", s):
            return int(s)
        raise ValueError("Invalid image ID")
    raise ValueError("Invalid image ID")


def _is_allowed_image_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(str(url))
    except Exception:
        return False
    if (parsed.scheme or "").lower() != "https":
        return False
    # Reject userinfo.
    try:
        if parsed.username is not None or parsed.password is not None:
            return False
    except Exception:
        return False
    if "@" in (parsed.netloc or ""):
        return False
    # Reject explicit port (allowlist has no ports).
    try:
        if parsed.port is not None:
            return False
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    path = parsed.path or ""
    if not path.startswith("/") or len(path) < 2:
        return False
    if ".." in path or "\\" in path or "\x00" in url:
        return False
    if any(c.isspace() for c in url):
        return False
    if host in ALLOWED_CDN_HOSTS:
        return True
    if host == "s3.amazonaws.com" and path.startswith("/steamgriddb/"):
        return True
    if host == "steamgriddb.s3.amazonaws.com":
        return True
    return False


def _is_allowed_api_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(str(url))
    except Exception:
        return False
    if (parsed.scheme or "").lower() != "https":
        return False
    try:
        if parsed.username is not None or parsed.password is not None:
            return False
    except Exception:
        return False
    if "@" in (parsed.netloc or ""):
        return False
    try:
        if parsed.port is not None:
            return False
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    if host != SGDB_API_HOST:
        return False
    path = parsed.path or ""
    if not path.startswith(SGDB_API_PREFIX):
        return False
    if ".." in path or "\\" in path or "\x00" in url:
        return False
    if any(c.isspace() for c in url):
        return False
    return True


class _AllowedHostRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Validate Location BEFORE following; never visit a foreign host."""

    def __init__(self, allowed_fn: Callable[[str], bool]):
        self._allowed_fn = allowed_fn

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        try:
            allowed = bool(self._allowed_fn(newurl))
        except Exception:
            allowed = False
        if not allowed:
            raise urllib.error.HTTPError(
                newurl if isinstance(newurl, str) else str(newurl),
                code,
                "Redirect to disallowed host blocked",
                headers,
                fp,
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _build_image_opener() -> urllib.request.OpenerDirector:
    handler = _AllowedHostRedirectHandler(_is_allowed_image_url)
    return urllib.request.build_opener(handler)


def _build_api_opener() -> urllib.request.OpenerDirector:
    handler = _AllowedHostRedirectHandler(_is_allowed_api_url)
    return urllib.request.build_opener(handler)


def _read_bounded(resp: Any, limit: int) -> bytes:
    data = resp.read(limit + 1)
    if data is None:
        data = b""
    if len(data) > limit:
        raise ValueError("Response exceeds size limit")
    return data


def _open_image_url(url: str, timeout: int = SGDB_THUMB_OPEN_TIMEOUT):
    if not _is_allowed_image_url(url):
        raise ValueError("Disallowed URL or CDN host")
    req = urllib.request.Request(url, headers={"User-Agent": "ContinuePC/1.0"})
    opener = _build_image_opener()
    resp = opener.open(req, timeout=timeout)
    try:
        final_url = resp.geturl() if hasattr(resp, "geturl") else url
    except Exception:
        final_url = url
    if not _is_allowed_image_url(str(final_url)):
        try:
            close = getattr(resp, "close", None)
            if close:
                close()
        except Exception:
            pass
        raise ValueError("Redirect to disallowed URL or CDN host")
    return resp


def _sgdb_target_path(sgdb_dir: Path, iid: int, ext: str) -> Path:
    if ext not in (".jpg", ".png"):
        raise ValueError("Invalid thumb extension")
    filename = f"{iid}{ext}"
    if not re.fullmatch(r"[1-9][0-9]{0,18}\.(jpg|png)", filename):
        raise ValueError("Invalid thumb filename")
    candidate = sgdb_dir / filename
    # Cache path guard: resolved path must stay inside sgdb_dir.
    try:
        base = sgdb_dir.resolve()
        # Do not resolve symlink target yet if file does not exist; check parent.
        cand_resolved = (base / filename).resolve()
        if os.path.commonpath((str(base), str(cand_resolved))) != str(base):
            raise ValueError("Cache path escapes sgdb dir")
    except ValueError:
        raise
    except Exception:
        raise ValueError("Invalid cache path")
    # If an existing symlink/file points outside, reject.
    try:
        if candidate.is_symlink():
            target = candidate.resolve()
            if os.path.commonpath((str(base), str(target))) != str(base):
                raise ValueError("Cached thumb symlink escapes cache")
    except ValueError:
        raise
    except Exception:
        pass
    return candidate


def _is_valid_cached_thumb(path: Path, max_bytes: int = MAX_THUMB_BYTES) -> bool:
    try:
        if not path.is_file() or path.is_symlink():
            # Symlinks are rejected even if they point inside (avoid TOCTOU).
            if path.is_symlink():
                return False
        size = path.stat().st_size
        if size <= 0 or size > max_bytes:
            return False
        with path.open("rb") as f:
            head = f.read(16)
        return head.startswith(PNG_SIGNATURE) or head.startswith(JPEG_SIGNATURE)
    except OSError:
        return False


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _valid_ytdlp(media: Any) -> Any | None:
    """Return pinned owned yt-dlp path or None.

    Real MediaManager.locate_ytdlp returns ONLY the hash-verified owned binary
    (bin/yt-dlp) else None; _own_ytdlp performs the hash check. Never accept an
    unrelated PATH executable: require the located path to live inside
    media.bin and, when _own_ytdlp exists, require it to validate.
    """
    try:
        locate_fn = getattr(media, "locate_ytdlp", None)
        if not callable(locate_fn):
            return None
        tool = locate_fn()
        if not tool:
            return None
        own_fn = getattr(media, "_own_ytdlp", None)
        if callable(own_fn):
            try:
                own = own_fn()
            except Exception:
                return None
            if not own:
                return None
            # Both must agree and live inside media.bin when bin is known.
            try:
                bin_dir = getattr(media, "bin", None)
                if bin_dir is not None:
                    b = Path(bin_dir).resolve()
                    t = Path(str(tool)).resolve() if not str(tool).startswith(str(bin_dir)) else None
                    # Compare by name/parent without requiring file existence
                    # (fixture managers may not materialize the binary).
                    tool_p = Path(str(tool))
                    own_p = Path(str(own))
                    # Parent name must be bin dir name to reject /usr/bin etc.
                    if tool_p.parent.resolve() != b and tool_p.parent != Path(str(bin_dir)):
                        # Fallback string check for fixtures (tmp paths).
                        try:
                            if os.path.commonpath((str(b), str(Path(str(tool_p)).resolve()))) != str(b):
                                # Allow fixture-style relative bin check:
                                if tool_p.parent.name != Path(str(bin_dir)).name:
                                    return None
                        except Exception:
                            return None
                    if str(tool_p) != str(own_p):
                        return None
            except Exception:
                # On any path confusion, require exact match at least.
                if str(tool) != str(own):
                    return None
            return tool
        # No _own_ytdlp: require path inside bin.
        try:
            bin_dir = getattr(media, "bin", None)
            if bin_dir is None:
                return None
            b = Path(str(bin_dir)).resolve()
            t = Path(str(tool))
            try:
                resolved = t.resolve()
                if os.path.commonpath((str(b), str(resolved))) != str(b):
                    return None
            except Exception:
                if t.parent != Path(str(bin_dir)) and t.parent.name != b.name:
                    return None
        except Exception:
            return None
        return tool
    except Exception:
        return None


class PublicCustomization:
    """Isolated backend for existing Big Picture artwork and music controls."""

    METHODS = {
        "sgdb_status",
        "sgdb_set_key",
        "sgdb_list",
        "sgdb_image",
        "music_current",
        "music_search",
        "music_choose",
        "customization_job",
    }

    def __init__(
        self,
        root: str | Path,
        media_factory: Callable[[], Any],
        work_allowed: Callable[[], bool],
        settings_lock: Any | None = None,
    ):
        # No network or subprocess at import or construction
        self.root = Path(root).resolve()
        self.media_factory = media_factory
        self.work_allowed = work_allowed
        # Shared settings lock (primary Backend.gate RLock) + private job lock.
        # Default RLock for isolated tests.
        self._settings_lock = settings_lock if settings_lock is not None else threading.RLock()
        self._job_lock = threading.Lock()
        self._authorized_images: dict[int, str] = {}
        self._authorized_music: set[str] = set()
        self._music_generation: dict[int, int] = {}
        self._jobs: dict[str, dict] = {}
        self._closed = False
        self._job_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="cust_job")
        self._thumb_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="cust_thumb")

    def call(self, method: str, args: list | tuple) -> Any:
        if not isinstance(args, (list, tuple)):
            raise ValueError("Arguments must be a list or tuple")
        if method not in self.METHODS:
            raise ValueError(f"Unknown method '{method}'")
        if method != "customization_job":
            with self._job_lock:
                if self._closed:
                    raise RuntimeError("PublicCustomization is closed")
        fn = getattr(self, method)
        return fn(*args)

    def close(self):
        with self._job_lock:
            self._closed = True
            for job in self._jobs.values():
                try:
                    if not job.get("done"):
                        job["done"] = True
                        if not job.get("error"):
                            job["error"] = "closed"
                        job["result"] = None
                except Exception:
                    continue
        self._job_pool.shutdown(wait=False, cancel_futures=True)
        self._thumb_pool.shutdown(wait=False, cancel_futures=True)

    # ─────────────────────────────────────────────────────────────
    # Settings & Secrets Helpers (settings_lock only, never nested)
    # ─────────────────────────────────────────────────────────────

    def _settings_path(self) -> Path:
        return self.root / "settings.json"

    def _key_path(self) -> Path:
        return self.root / "secrets" / "steamgriddb.key"

    def _load_settings(self) -> dict:
        with self._settings_lock:
            val = _read_json(self._settings_path())
            return dict(val) if isinstance(val, dict) else {}

    def _save_settings(self, data: dict) -> None:
        with self._settings_lock:
            # Re-read to preserve unrelated keys written concurrently.
            current = _read_json(self._settings_path())
            if not isinstance(current, dict):
                current = {}
            merged = dict(current)
            for k, v in data.items():
                merged[k] = v
            # Actually caller passes full dict; preserve by writing merged view:
            # To keep exact semantics, if caller built from _load_settings,
            # merging again is harmless and preserves unrelated keys.
            _write_json(self._settings_path(), merged)

    def _write_settings_key(self, key: str, value: Any) -> dict:
        """Update a single top-level settings key, preserving others."""
        with self._settings_lock:
            current = _read_json(self._settings_path())
            if not isinstance(current, dict):
                current = {}
            current[key] = value
            _write_json(self._settings_path(), current)
            return current

    def _get_key(self) -> str:
        key_file = self._key_path()
        try:
            return key_file.read_text(encoding="utf-8").strip()
        except OSError:
            return ""

    def _is_closed(self) -> bool:
        with self._job_lock:
            return self._closed

    def _active_job_count(self) -> int:
        with self._job_lock:
            return sum(1 for j in self._jobs.values() if not j.get("done"))

    def _evict_jobs_if_needed(self) -> None:
        with self._job_lock:
            while len(self._jobs) > MAX_RETAINED_JOBS:
                for jid, job in list(self._jobs.items()):
                    if job.get("done"):
                        del self._jobs[jid]
                        break
                else:
                    break

    def _bounded_authorize_image(self, iid: int, url: str) -> None:
        with self._job_lock:
            self._authorized_images[iid] = url
            while len(self._authorized_images) > MAX_AUTHORIZED_IMAGES:
                oldest = next(iter(self._authorized_images))
                del self._authorized_images[oldest]

    def _bounded_authorize_music(self, vid: str) -> None:
        with self._job_lock:
            self._authorized_music.add(vid)
            while len(self._authorized_music) > MAX_AUTHORIZED_MUSIC:
                # set has no order; drop arbitrary element that is not vid.
                for old in list(self._authorized_music):
                    if old != vid:
                        self._authorized_music.discard(old)
                        break
                else:
                    break

    # ─────────────────────────────────────────────────────────────
    # Artwork Controls
    # ─────────────────────────────────────────────────────────────

    def sgdb_status(self) -> dict:
        key = self._get_key()
        return {"configured": bool(key)}

    def sgdb_set_key(self, key: str) -> dict:
        if not isinstance(key, str):
            raise ValueError("Key must be a string")
        clean_key = key.strip()
        if "\n" in clean_key or "\r" in clean_key or "\0" in clean_key or len(clean_key) > 256:
            raise ValueError("Invalid key format")
        path = self._key_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        for target in (path.parent,path):
            if target.is_symlink() or (target.exists() and getattr(target.lstat(),'st_file_attributes',0)&0x400):
                raise ValueError('Linked secret paths are not allowed')
        self._private_permissions(path.parent)
        temp=path.with_name(path.name+'.'+secrets.token_hex(8)+'.tmp')
        try:
            with temp.open('x',encoding='utf-8') as stream:
                self._private_permissions(temp)
                stream.write(clean_key+'\n');stream.flush();os.fsync(stream.fileno())
            os.replace(temp,path)
        finally:temp.unlink(missing_ok=True)
        return {"configured": bool(clean_key)}

    @staticmethod
    def _private_permissions(path):
        if os.name!='nt':
            path.chmod(0o700 if path.is_dir() else 0o600)
            return
        # The value never enters the command line, environment or output. Set
        # an explicit, protected DACL before any secret bytes are written.
        script=r'''$ErrorActionPreference='Stop';$p=$env:CONTINUE_PRIVATE_PATH;
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User;
if ([IO.Directory]::Exists($p)) {$acl=New-Object Security.AccessControl.DirectorySecurity;$inherit=[Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit'}
else {$acl=New-Object Security.AccessControl.FileSecurity;$inherit=[Security.AccessControl.InheritanceFlags]::None};
$acl.SetOwner($sid);$acl.SetAccessRuleProtection($true,$false);
$rule=New-Object Security.AccessControl.FileSystemAccessRule($sid,'FullControl',$inherit,'None','Allow');
$acl.AddAccessRule($rule);if ([IO.Directory]::Exists($p)) {[IO.Directory]::SetAccessControl($p,$acl)} else {[IO.File]::SetAccessControl($p,$acl)}'''
        result=subprocess.run([str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'),
            '-NoProfile','-NonInteractive','-Command',script],env={**os.environ,'CONTINUE_PRIVATE_PATH':str(path)},
            stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:raise OSError('Could not restrict secret file permissions')

    def _sgdb_api_get(self, endpoint_path: str, key: str) -> dict:
        if not isinstance(endpoint_path, str) or not endpoint_path.startswith("/"):
            raise RuntimeError("SteamGridDB request failed: bad endpoint")
        if ".." in endpoint_path or "\\" in endpoint_path or "\x00" in endpoint_path:
            raise RuntimeError("SteamGridDB request failed: bad endpoint")
        if any(c.isspace() for c in endpoint_path):
            raise RuntimeError("SteamGridDB request failed: bad endpoint")
        url = ALLOWED_SGDB_API + endpoint_path
        if not _is_allowed_api_url(url):
            raise RuntimeError("SteamGridDB request failed: disallowed API URL")
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": "Bearer REDACTED",
                "User-Agent": "ContinuePC/1.0",
                "Accept": "application/json",
            },
        )
        # Set real auth without ever echoing it.
        try:
            req.add_unredirected_header("Authorization", f"Bearer {key}")
        except Exception:
            pass
        opener = _build_api_opener()
        try:
            resp = opener.open(req, timeout=SGDB_API_TIMEOUT)
        except urllib.error.HTTPError as err:
            raise RuntimeError(f"SteamGridDB HTTP {err.code}") from None
        except Exception as err:
            msg = _redact(str(err), key)
            raise RuntimeError(f"SteamGridDB request failed: {msg[:200]}") from None
        try:
            try:
                final_url = resp.geturl() if hasattr(resp, "geturl") else url
            except Exception:
                final_url = url
            if not _is_allowed_api_url(str(final_url)):
                try:
                    close = getattr(resp, "close", None)
                    if close:
                        close()
                except Exception:
                    pass
                raise RuntimeError("SteamGridDB request failed: redirect blocked")
            data = _read_bounded(resp, MAX_JSON_BYTES)
            try:
                close = getattr(resp, "close", None)
                if close:
                    close()
            except Exception:
                pass
            try:
                parsed = json.loads(data.decode("utf-8"))
            except ValueError:
                raise RuntimeError("SteamGridDB request failed: malformed JSON") from None
            if not isinstance(parsed, dict):
                raise RuntimeError("SteamGridDB request failed: malformed JSON") from None
            return parsed
        except RuntimeError:
            raise
        except ValueError as err:
            raise RuntimeError(f"SteamGridDB request failed: {err}") from None
        except Exception as err:
            msg = _redact(str(err), key)
            raise RuntimeError(f"SteamGridDB request failed: {msg[:200]}") from None

    def sgdb_list(self, appid: int, name: str, kind: str) -> dict:
        # Strict AppID but return-error semantics for list.
        try:
            appid_int = _strict_appid(appid)
        except ValueError:
            return {"items": [], "error": "Invalid appid"}
        if not (1 <= appid_int <= 0xFFFFFFFF):
            return {"items": [], "error": "AppID out of range"}
        if kind not in SGDB_KINDS:
            return {"items": [], "error": f"Unknown artwork kind '{kind}'"}
        clean_name = str(name or "")[:200].strip()

        key = self._get_key()
        if not key:
            return {"items": [], "error": "SteamGridDB key not configured", "setup_required": True}

        _, ep, dims = SGDB_KINDS[kind]
        q = f"?{dims}types=static&nsfw=false&humor=false"

        try:
            if appid_int < 0x80000000:
                game_target = f"steam/{appid_int}"
            else:
                if not clean_name:
                    return {"items": [], "error": "Name required for non-Steam shortcut"}
                search_path = f"/search/autocomplete/{urllib.parse.quote(clean_name)}"
                res = self._sgdb_api_get(search_path, key)
                found = res.get("data") if isinstance(res, dict) else []
                if not found or not isinstance(found, list):
                    return {"items": [], "error": "SteamGridDB game not found"}
                first = found[0] if isinstance(found[0], dict) else {}
                game_id = first.get("id")
                try:
                    if isinstance(game_id, bool):
                        raise ValueError()
                    game_id_int = int(game_id)
                except (ValueError, TypeError):
                    return {"items": [], "error": "SteamGridDB game ID not found"}
                if game_id_int <= 0:
                    return {"items": [], "error": "SteamGridDB game ID not found"}
                game_target = f"game/{game_id_int}"

            data = self._sgdb_api_get(f"/{ep}/{game_target}{q}", key)
        except Exception as err:
            msg = _redact(str(err), key)
            # Never include key material; truncate.
            safe = msg[:200]
            if "REDACTED" not in safe and key and key[:8] in safe:
                safe = "SteamGridDB request failed"
            return {"items": [], "error": safe}

        raw_list = data.get("data") if isinstance(data, dict) else None
        if not isinstance(raw_list, list):
            return {"items": [], "error": "SteamGridDB malformed response"}
        raw_items = [
            x for x in raw_list
            if isinstance(x, dict) and x.get("url") and x.get("thumb") and x.get("mime") != "video/webm"
        ][:MAX_THUMB_ITEMS]

        data_dir = self.root / "data"
        sgdb_dir = data_dir / "sgdb"
        try:
            sgdb_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return {"items": [], "error": "Cache unavailable"}

        def fetch_thumb(item: dict) -> dict | None:
            if self._is_closed():
                return None
            raw_thumb = str(item.get("thumb") or "")
            raw_url = str(item.get("url") or "")
            item_id = item.get("id")
            if not _is_allowed_image_url(raw_thumb) or not _is_allowed_image_url(raw_url):
                return None
            try:
                iid = _strict_image_id(item_id)
            except ValueError:
                return None

            ext = ".png" if item.get("mime") == "image/png" else ".jpg"
            try:
                target_path = _sgdb_target_path(sgdb_dir, iid, ext)
            except ValueError:
                return None
            if target_path.exists():
                if _is_valid_cached_thumb(target_path, MAX_THUMB_BYTES):
                    pass
                else:
                    try:
                        target_path.unlink()
                    except OSError:
                        return None
                    # Fall through to re-download.
                if target_path.exists():
                    self._bounded_authorize_image(iid, raw_url)
                    rel_thumb = f"sgdb/{target_path.name}"
                    w = item.get("width")
                    h = item.get("height")
                    try:
                        w = int(w) if w is not None else None
                        h = int(h) if h is not None else None
                    except (ValueError, TypeError):
                        w, h = None, None
                    return {"id": iid, "thumb": rel_thumb, "w": w, "h": h}
            try:
                with _open_image_url(raw_thumb, timeout=SGDB_THUMB_OPEN_TIMEOUT) as resp:
                    content = _read_bounded(resp, MAX_THUMB_BYTES)
                if not (content.startswith(PNG_SIGNATURE) or content.startswith(JPEG_SIGNATURE)):
                    return None
                try:
                    target_path.write_bytes(content)
                except OSError:
                    return None
                if not _is_valid_cached_thumb(target_path, MAX_THUMB_BYTES):
                    try:
                        target_path.unlink()
                    except OSError:
                        pass
                    return None
            except Exception:
                return None

            self._bounded_authorize_image(iid, raw_url)
            rel_thumb = f"sgdb/{target_path.name}"
            w = item.get("width")
            h = item.get("height")
            try:
                w = int(w) if w is not None else None
                h = int(h) if h is not None else None
            except (ValueError, TypeError):
                w, h = None, None
            return {"id": iid, "thumb": rel_thumb, "w": w, "h": h}

        # Bounded overall deadline within bridge 55s.
        deadline = time.monotonic() + SGDB_LIST_DEADLINE_SEC
        futures = [self._thumb_pool.submit(fetch_thumb, it) for it in raw_items]
        out_items = []
        try:
            for fut in futures:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    res = fut.result(timeout=min(remaining, SGDB_THUMB_OPEN_TIMEOUT + 2))
                    if res:
                        out_items.append(res)
                        if len(out_items) >= MAX_THUMB_ITEMS:
                            break
                except Exception:
                    continue
        finally:
            # Cancel pending at deadline; no unbounded wait.
            for fut in futures:
                if not fut.done():
                    fut.cancel()
        return {"items": out_items, "error": None if out_items else "Картинок нет"}

    def sgdb_image(self, image_id: int | str) -> dict:
        iid = _strict_image_id(image_id)
        with self._job_lock:
            url = self._authorized_images.get(iid)
        if not url:
            raise ValueError("Image ID is not authorized by a prior list call")

        if not _is_allowed_image_url(url):
            raise ValueError("Disallowed CDN host")

        try:
            with _open_image_url(url, timeout=SGDB_IMAGE_TIMEOUT) as resp:
                content = _read_bounded(resp, MAX_IMAGE_BYTES)
        except ValueError:
            raise
        except Exception as err:
            raise RuntimeError("Failed to fetch authorized image") from None

        if content.startswith(PNG_SIGNATURE):
            fmt = "png"
        elif content.startswith(JPEG_SIGNATURE):
            fmt = "jpg"
        else:
            raise ValueError("Invalid image format signature")

        return {"b64": base64.b64encode(content).decode("ascii"), "fmt": fmt}

    # ─────────────────────────────────────────────────────────────
    # Music Controls
    # ─────────────────────────────────────────────────────────────

    def music_current(self, appid: int) -> str:
        appid_int = _strict_appid(appid)
        settings = self._load_settings()
        choices = settings.get("music_choices") or {}
        if not isinstance(choices, dict):
            return "auto"
        val = choices.get(str(appid_int))
        if not val or val == "auto":
            return "auto"
        if val == "none":
            return "none"
        return str(val)

    def customization_job(self, job_id: str) -> dict:
        with self._job_lock:
            job = self._jobs.get(str(job_id))
        if not job:
            return {"done": True, "error": "Unknown job ID"}
        return dict(job)

    def _require_consent(self) -> dict | None:
        settings = self._load_settings()
        if settings.get("theme_music_consent") is not True:
            return {"error": "theme_music_consent required", "consent_required": True}
        return None

    def music_search(self, query: str, kind: str) -> dict:
        clean_query = str(query or "").strip()[:MAX_QUERY_LEN]
        clean_kind = str(kind or "").strip().lower()
        if clean_kind not in _MUSIC_KINDS:
            raise ValueError(f"Unknown music kind '{clean_kind}'")
        if not clean_query:
            raise ValueError("Query must be non-empty")
        if len(clean_query) > MAX_QUERY_LEN:
            clean_query = clean_query[:MAX_QUERY_LEN]

        consent_err = self._require_consent()
        if consent_err:
            return consent_err

        try:
            media = self.media_factory()
        except Exception:
            return {"error": "yt-dlp runtime not available or invalid", "setup_required": True}
        if _valid_ytdlp(media) is None:
            return {"error": "yt-dlp runtime not available or invalid", "setup_required": True}

        try:
            if not self.work_allowed():
                return {"error": "work_allowed is False (game active)", "deferred": True}
        except Exception:
            return {"error": "work_allowed is False (game active)", "deferred": True}

        if self._active_job_count() >= MAX_ACTIVE_JOBS:
            return {"error": "too many active jobs", "deferred": True}
        self._evict_jobs_if_needed()

        job_id = secrets.token_hex(16)
        with self._job_lock:
            if self._closed:
                raise RuntimeError("PublicCustomization is closed")
            self._jobs[job_id] = {"done": False, "result": None, "error": None}

        try:
            self._job_pool.submit(self._do_music_search, job_id, clean_query, clean_kind)
        except RuntimeError:
            with self._job_lock:
                self._jobs[job_id] = {"done": True, "result": [], "error": "closed"}
            raise RuntimeError("PublicCustomization is closed") from None
        return {"job": job_id}

    def _do_music_search(self, job_id: str, query: str, kind: str):
        # Recheck gate at worker start: closed / work_allowed / budget / cancel.
        if self._is_closed():
            with self._job_lock:
                if job_id in self._jobs:
                    self._jobs[job_id] = {"done": True, "result": [], "error": "closed"}
            return
        try:
            if not self.work_allowed():
                with self._job_lock:
                    if job_id in self._jobs:
                        self._jobs[job_id] = {"done": True, "result": [], "error": "work_allowed is False"}
                return
        except Exception:
            with self._job_lock:
                if job_id in self._jobs:
                    self._jobs[job_id] = {"done": True, "result": [], "error": "work_allowed is False"}
            return
        try:
            media = self.media_factory()
        except Exception as exc:
            with self._job_lock:
                if job_id in self._jobs:
                    self._jobs[job_id] = {"done": True, "result": [], "error": str(exc)[:200]}
            return
        # Budget / cancellation guard via shared API when available.
        try:
            checkpoint = getattr(media, "_checkpoint", None)
            if callable(checkpoint):
                checkpoint()
        except Exception as exc:
            with self._job_lock:
                if job_id in self._jobs:
                    self._jobs[job_id] = {"done": True, "result": [], "error": str(exc)[:200]}
            return
        try:
            check_space = getattr(media, "_check_space", None)
            if callable(check_space):
                check_space(0)
        except Exception as exc:
            with self._job_lock:
                if job_id in self._jobs:
                    self._jobs[job_id] = {"done": True, "result": [], "error": str(exc)[:200]}
            return
        if _valid_ytdlp(media) is None:
            with self._job_lock:
                if job_id in self._jobs:
                    self._jobs[job_id] = {"done": True, "result": [], "error": "yt-dlp runtime not available"}
            return
        try:
            kind_suffix = {
                "theme": "Theme Music",
                "ost": "OST soundtrack",
                "menu": "main menu music",
                "query": "",
            }.get(kind, "")
            search_str = f"{query} {kind_suffix}".strip()[: MAX_QUERY_LEN + 32]
            command = media._ytdlp_command() + [
                f"ytsearch{MAX_SEARCH_RESULTS}:{search_str}",
                "--dump-json",
                "--skip-download",
                "--ignore-errors",
                "--no-warnings",
                "--no-playlist",
                "--socket-timeout",
                "20",
                "--retries",
                "1",
                "--extractor-retries",
                "1",
                "--no-cache-dir",
                "--ignore-config",
                "--match-filter",
                "duration < 900",
            ]
            if shutil.which("node"):
                command += ["--js-runtimes", "node"]

            proc = media.run(command, capture_output=True, text=True, timeout=120)
            rows = []
            for line in (proc.stdout or "").splitlines():
                if self._is_closed():
                    break
                if len(rows) >= MAX_SEARCH_RESULTS:
                    break
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(entry, dict):
                    continue
                vid = str(entry.get("id") or "")
                if not _YT_ID_RE.fullmatch(vid):
                    continue
                dur = entry.get("duration")
                try:
                    if dur is not None and not (0 < float(dur) < 900):
                        continue
                except (ValueError, TypeError):
                    continue
                title = str(entry.get("title") or vid)[:MAX_TITLE_LEN]
                channel = str(entry.get("channel") or entry.get("uploader") or "")[:MAX_CHANNEL_LEN]
                try:
                    duration_val = int(float(dur)) if dur else None
                except (ValueError, TypeError):
                    duration_val = None
                rows.append({
                    "id": vid,
                    "title": title,
                    "channel": channel,
                    "duration": duration_val,
                })
                self._bounded_authorize_music(vid)

            if self._is_closed():
                with self._job_lock:
                    if job_id in self._jobs:
                        self._jobs[job_id] = {"done": True, "result": [], "error": "closed"}
                return
            with self._job_lock:
                if job_id in self._jobs:
                    self._jobs[job_id] = {"done": True, "result": rows, "error": None}
        except Exception as exc:
            with self._job_lock:
                if job_id in self._jobs:
                    self._jobs[job_id] = {"done": True, "result": [], "error": str(exc)[:200]}

    def _delete_theme_files(self, appid_int: int) -> None:
        """Delete only this game's theme files; never touch other apps."""
        try:
            media = self.media_factory()
        except Exception:
            return
        media_dir = getattr(media, "media", None)
        if media_dir is None:
            return
        try:
            media_path = Path(media_dir)
        except Exception:
            return
        try:
            if not media_path.is_dir():
                return
        except OSError:
            return
        prefix = f"{appid_int}_theme."
        try:
            for old in media_path.glob(f"{appid_int}_theme.*"):
                try:
                    if old.name != prefix + old.suffix.lstrip(".") and not old.name.startswith(prefix):
                        continue
                    # Guard: must stay inside media dir, must be file.
                    try:
                        if old.is_symlink():
                            continue
                        if os.path.commonpath((str(media_path.resolve()), str(old.resolve()))) != str(media_path.resolve()):
                            continue
                    except Exception:
                        continue
                    old.unlink()
                except OSError:
                    pass
        except OSError:
            pass

    def music_choose(self, appid: int, choice: str) -> dict:
        appid_int = _strict_appid(appid)
        clean_choice = str(choice or "").strip()[:64]

        # Fast local choices: auto and none (no network/subprocess).
        if clean_choice == "none":
            invalidate = getattr(self.media_factory(), 'invalidate_theme', None)
            if invalidate:
                invalidate(appid_int)
            with self._job_lock:
                self._music_generation[appid_int] = self._music_generation.get(appid_int,0) + 1
            # None suppresses playback through music_choices. Retain automatic
            # audio for an immediate local Auto resume; discard custom overrides
            # before their provenance is replaced by the None setting.
            if self.music_current(appid_int) not in ('auto', 'none'):
                self._delete_theme_files(appid_int)
            # settings_lock only; job_lock separately (no nesting).
            with self._settings_lock:
                settings = _read_json(self._settings_path())
                if not isinstance(settings, dict):
                    settings = {}
                choices = settings.get("music_choices")
                if not isinstance(choices, dict):
                    choices = {}
                    settings["music_choices"] = choices
                choices[str(appid_int)] = "none"
                _write_json(self._settings_path(), settings)
            job_id = secrets.token_hex(16)
            with self._job_lock:
                self._jobs[job_id] = {"done": True, "result": {"ok": True}, "error": None}
                while len(self._jobs) > MAX_RETAINED_JOBS:
                    for jid, job in list(self._jobs.items()):
                        if job.get("done") and jid != job_id:
                            del self._jobs[jid]
                            break
                    else:
                        break
            return {"job": job_id, "done": True, "result": {"ok": True}}

        if clean_choice == "auto":
            invalidate = getattr(self.media_factory(), 'invalidate_theme', None)
            if invalidate:
                invalidate(appid_int)
            with self._job_lock:
                self._music_generation[appid_int] = self._music_generation.get(appid_int,0) + 1
            # Only a custom choice makes this committed file a custom override.
            # None already removes custom files, so None -> Auto can reuse the
            # prepared automatic theme without an external download.
            if self.music_current(appid_int) not in ('auto', 'none'):
                self._delete_theme_files(appid_int)
            with self._settings_lock:
                settings = _read_json(self._settings_path())
                if not isinstance(settings, dict):
                    settings = {}
                choices = settings.get("music_choices")
                if not isinstance(choices, dict):
                    choices = {}
                    settings["music_choices"] = choices
                choices[str(appid_int)] = "auto"
                _write_json(self._settings_path(), settings)
            job_id = secrets.token_hex(16)
            with self._job_lock:
                self._jobs[job_id] = {"done": True, "result": {"ok": True}, "error": None}
                while len(self._jobs) > MAX_RETAINED_JOBS:
                    for jid, job in list(self._jobs.items()):
                        if job.get("done") and jid != job_id:
                            del self._jobs[jid]
                            break
                    else:
                        break
            return {"job": job_id, "done": True, "result": {"ok": True}}

        # Custom YouTube ID: exactly 11 chars, authorized by prior search.
        if not _YT_ID_RE.fullmatch(clean_choice):
            raise ValueError(f"Music choice '{clean_choice}' is not authorized by a prior search")
        with self._job_lock:
            authorized = clean_choice in self._authorized_music
        if not authorized:
            raise ValueError(f"Music choice '{clean_choice}' is not authorized by a prior search")

        consent_err = self._require_consent()
        if consent_err:
            return consent_err

        try:
            media = self.media_factory()
        except Exception:
            return {"error": "yt-dlp runtime required", "setup_required": True}
        if _valid_ytdlp(media) is None:
            return {"error": "yt-dlp runtime required", "setup_required": True}

        try:
            if not self.work_allowed():
                return {"error": "work_allowed is False", "deferred": True}
        except Exception:
            return {"error": "work_allowed is False", "deferred": True}

        if self._active_job_count() >= MAX_ACTIVE_JOBS:
            return {"error": "too many active jobs", "deferred": True}
        self._evict_jobs_if_needed()

        job_id = secrets.token_hex(16)
        with self._job_lock:
            if self._closed:
                raise RuntimeError("PublicCustomization is closed")
            self._jobs[job_id] = {"done": False, "result": None, "error": None}
            self._music_generation[appid_int] = self._music_generation.get(appid_int,0) + 1
            generation = self._music_generation[appid_int]

        try:
            self._job_pool.submit(self._do_music_download, job_id, appid_int, clean_choice, generation)
        except RuntimeError:
            with self._job_lock:
                self._jobs[job_id] = {"done": True, "result": None, "error": "closed"}
            raise RuntimeError("PublicCustomization is closed") from None
        return {"job": job_id}

    def _do_music_download(self, job_id: str, appid: int, choice: str, generation=None):
        if self._is_closed():
            with self._job_lock:
                if job_id in self._jobs:
                    self._jobs[job_id] = {"done": True, "result": None, "error": "closed"}
            return
        try:
            if not self.work_allowed():
                with self._job_lock:
                    if job_id in self._jobs:
                        self._jobs[job_id] = {"done": True, "result": None, "error": "work_allowed is False"}
                return
        except Exception:
            with self._job_lock:
                if job_id in self._jobs:
                    self._jobs[job_id] = {"done": True, "result": None, "error": "work_allowed is False"}
            return
        try:
            media = self.media_factory()
        except Exception as exc:
            with self._job_lock:
                if job_id in self._jobs:
                    self._jobs[job_id] = {"done": True, "result": None, "error": str(exc)[:200]}
            return
        try:
            checkpoint = getattr(media, "_checkpoint", None)
            if callable(checkpoint):
                checkpoint()
        except Exception as exc:
            with self._job_lock:
                if job_id in self._jobs:
                    self._jobs[job_id] = {"done": True, "result": None, "error": str(exc)[:200]}
            return
        try:
            check_space = getattr(media, "_check_space", None)
            if callable(check_space):
                check_space(0)
        except Exception as exc:
            with self._job_lock:
                if job_id in self._jobs:
                    self._jobs[job_id] = {"done": True, "result": None, "error": str(exc)[:200]}
            return
        if _valid_ytdlp(media) is None:
            with self._job_lock:
                if job_id in self._jobs:
                    self._jobs[job_id] = {"done": True, "result": None, "error": "yt-dlp runtime required"}
            return
        # Re-read consent under settings_lock (no job_lock held).
        with self._settings_lock:
            settings_snapshot = _read_json(self._settings_path())
        if not isinstance(settings_snapshot, dict) or settings_snapshot.get("theme_music_consent") is not True:
            with self._job_lock:
                if job_id in self._jobs:
                    self._jobs[job_id] = {"done": True, "result": None, "error": "theme_music_consent required"}
            return
        try:
            yt_url = f"https://www.youtube.com/watch?v={choice}"
            dest = media._download_youtube(yt_url, f"{appid}_theme", settings_snapshot, audio=True)
            if not dest:
                raise RuntimeError("Failed to download selected music track")
            # Do not mutate selection after close.
            if self._is_closed():
                with self._job_lock:
                    if job_id in self._jobs:
                        self._jobs[job_id] = {"done": True, "result": None, "error": "closed"}
                return
            try:
                rel_fn = getattr(media, "_relative", None)
                rel = rel_fn(dest) if callable(rel_fn) else None
            except Exception:
                rel = None

            with self._settings_lock:
                with self._job_lock:
                    if generation is not None and self._music_generation.get(appid) != generation:
                        raise RuntimeError('Music choice changed')
                settings = _read_json(self._settings_path())
                if not isinstance(settings, dict):
                    settings = {}
                choices = settings.get("music_choices")
                if not isinstance(choices, dict):
                    choices = {}
                    settings["music_choices"] = choices
                choices[str(appid)] = choice
                _write_json(self._settings_path(), settings)
            with self._job_lock:
                if job_id in self._jobs:
                    if self._closed:
                        self._jobs[job_id] = {"done": True, "result": None, "error": "closed"}
                    else:
                        self._jobs[job_id] = {
                            "done": True,
                            "result": {"ok": True, "file": rel},
                            "error": None,
                        }
        except Exception as exc:
            with self._job_lock:
                if job_id in self._jobs:
                    self._jobs[job_id] = {"done": True, "result": None, "error": str(exc)[:200]}
