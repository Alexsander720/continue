"""Consent-based Linux x86_64 media tools isolated from SteamOS and PATH.

Only pinned official archives are downloaded. Tar links are never extracted;
only the three executable files and the two license files become owned files.
The manifest is the atomic commit point, so a failed setup preserves the prior
generation. No network, directory creation or executable runs occur on import
or construction. Callers must use tool() instead of guessing executable paths.
"""
from __future__ import annotations

import hashlib
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tarfile
import threading
import time
import urllib.parse
import urllib.request
import uuid

from standalone_media import _ssl_context

CHUNK_SIZE = 64 * 1024
OFFICIAL_HOSTS = frozenset({"nodejs.org", "github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"})
TOOLS = {"node": {"node": "node"}, "ffmpeg": {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}}
MAX_COMPRESSED = {"node": 80 * 1024**2, "ffmpeg": 220 * 1024**2}
MAX_DECOMPRESSED = 1024**3
MAX_CACHE = 2 * 1024**3
MAX_ENTRIES = 20000
MAX_LICENSE = 2 * 1024**2
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
GENERATION = re.compile(r"[a-f0-9]{32}\Z")


def _safe_download_url(url, hosts=OFFICIAL_HOSTS):
    try:
        parsed = urllib.parse.urlsplit(url)
        return (parsed.scheme == "https" and parsed.hostname in hosts
                and not parsed.username and not parsed.password
                and parsed.port in (None, 443) and not parsed.fragment)
    except (TypeError, ValueError):
        return False


class RuntimeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts=OFFICIAL_HOSTS):
        super().__init__()
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _safe_download_url(newurl, self.hosts):
            raise ValueError("Untrusted media runtime redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _SafeTarInfo(tarfile.TarInfo):
    @classmethod
    def frombuf(cls, buf, encoding, errors):
        item = super().frombuf(buf, encoding, errors)
        if item.size < 0 or item.size > MAX_DECOMPRESSED:
            raise ValueError("Runtime tar member exceeds size cap")
        if item.type in (tarfile.XHDTYPE, tarfile.XGLTYPE, tarfile.GNUTYPE_LONGNAME, tarfile.GNUTYPE_LONGLINK) and item.size > 1024**2:
            raise ValueError("Runtime tar extension exceeds size cap")
        return item


class _XZReader:
    """Streaming decompressor with bounded dictionary, output and wall time."""
    def __init__(self, raw, limit, check):
        self.raw = raw
        self.decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ, memlimit=256 * 1024**2)
        self.limit = limit
        self.total = 0
        self.check = check
        self.started = time.monotonic()

    def read(self, size=-1):
        if size < 0:
            raise ValueError("Unbounded runtime archive read rejected")
        pieces = []
        remaining = size
        while remaining:
            if not self.check() or time.monotonic() - self.started > 600:
                raise ValueError("Runtime extraction cancelled or timed out")
            if self.decoder.eof:
                if self.decoder.unused_data or self.raw.read(1):
                    raise ValueError("Trailing runtime compressed data rejected")
                break
            compressed = self.raw.read(CHUNK_SIZE) if self.decoder.needs_input else b""
            if not compressed and self.decoder.needs_input:
                raise ValueError("Truncated runtime archive")
            piece = self.decoder.decompress(compressed, max_length=min(remaining, CHUNK_SIZE))
            self.total += len(piece)
            if self.total > self.limit:
                raise ValueError("Runtime decompressed size exceeds cap")
            pieces.append(piece)
            remaining -= len(piece)
        return b"".join(pieces)


class MediaRuntime:
    def __init__(self, data_root, metadata_path=None, *, urlopen=None, allowed=None):
        # The caller supplies the trusted install root. Resolve its mount/home
        # aliases once; links created inside this root remain forbidden.
        self.data_root = Path(data_root).resolve()
        self.runtime_dir = self.data_root / "bin" / "deck-runtime"
        self.manifest_path = self.runtime_dir / "manifest.json"
        self.metadata_path = (Path(os.path.abspath(os.fspath(metadata_path))) if metadata_path is not None
                              else Path(__file__).absolute().parents[1] / "assets" / "deck_media_runtime.json")
        self.allowed = allowed
        self._urlopen = urlopen
        self._meta = None
        self._verified = {}
        self._prepare_lock = threading.Lock()
        self._cancelled = threading.Event()
        self._allowed_cache = None

    def cancel(self):
        """Explicit cancellation is cheap and bypasses the expensive policy cache."""
        self._cancelled.set()

    def _check_allowed(self):
        if self._cancelled.is_set():
            return False
        now = time.monotonic()
        cached = self._allowed_cache
        if cached is not None and (not cached[1] or now - cached[0] < 1.0):
            return cached[1]
        try:
            allowed = self.allowed is None or bool(self.allowed())
        except Exception:
            allowed = False
        self._allowed_cache = (now, allowed)
        return allowed and not self._cancelled.is_set()

    def _safe_path(self, path):
        try:
            target = Path(os.path.abspath(os.fspath(path)))
            target.relative_to(self.data_root)
            for parent in (target, *target.parents):
                try:
                    attrs = parent.lstat()
                except FileNotFoundError:
                    continue
                if stat.S_ISLNK(attrs.st_mode) or getattr(attrs, "st_file_attributes", 0) & 0x400:
                    return False
                if parent==self.data_root:break
            return True
        except (OSError, ValueError):
            return False

    def _mkdir(self, path):
        if not self._safe_path(path):
            raise ValueError("Unsafe media runtime directory")
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not self._safe_path(path) or not path.is_dir():
            raise ValueError("Unsafe media runtime directory")

    def _open_new(self, path, mode=0o600):
        if not self._safe_path(path):
            raise ValueError("Unsafe media runtime destination")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        return os.fdopen(os.open(path, flags, mode), "wb")

    def _check_space(self, additional=0):
        parent=self.data_root
        while not parent.exists():parent=parent.parent
        if shutil.disk_usage(parent).free < 128*1024**2 + additional:
            raise ValueError('Insufficient free space for media tools')

    def _get_metadata(self):
        if self._meta is not None:
            return self._meta
        with self.metadata_path.open("rb") as handle:
            raw = handle.read(65537)
        if len(raw) > 65536:
            raise ValueError("Runtime metadata too large")
        meta = json.loads(raw.decode("utf-8"))
        if not isinstance(meta, dict) or meta.get("platform") != "linux-x64" or set(meta.get("packages", {})) != set(TOOLS):
            raise ValueError("Invalid Linux runtime metadata")
        for name, package in meta["packages"].items():
            if (not isinstance(package, dict) or not SHA256.fullmatch(str(package.get("sha256", "")))
                    or package.get("tools") != TOOLS[name]
                    or package.get("target_license") != f"LICENSE_{name}.txt"):
                raise ValueError("Invalid Linux runtime package")
            for field in ("filename", "license_file"):
                value = package.get(field)
                if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", value) or value in (".", ".."):
                    raise ValueError("Invalid Linux runtime filename")
            if not _safe_download_url(package.get("url")):
                raise ValueError("Untrusted media runtime URL")
            size = package.get("size_bytes")
            if isinstance(size, bool) or not isinstance(size, int) or not 0 < size <= MAX_COMPRESSED[name]:
                raise ValueError("Invalid media runtime download size")
        self._meta = meta
        return meta

    def _load_manifest(self):
        try:
            if not self._safe_path(self.manifest_path):
                return {}
            with self.manifest_path.open("rb") as handle:
                raw = handle.read(65537)
            if len(raw) > 65536:
                return {}
            value = json.loads(raw.decode("utf-8"))
            if not isinstance(value, dict) or value.get("schema_version") != "1.0" or not GENERATION.fullmatch(str(value.get("generation", ""))):
                return {}
            return value
        except (OSError, ValueError, UnicodeError):
            return {}

    def _verified_file(self, relative, expected_hash):
        if not isinstance(relative, str) or not SHA256.fullmatch(str(expected_hash)):
            return None
        if not re.fullmatch(r"versions/[a-f0-9]{32}/(?:node|ffmpeg|ffprobe|LICENSE_node\.txt|LICENSE_ffmpeg\.txt)", relative):
            return None
        target = self.runtime_dir / relative
        try:
            if not self._safe_path(target):
                return None
            attrs = target.stat()
            if not stat.S_ISREG(attrs.st_mode) or attrs.st_size > MAX_DECOMPRESSED:
                return None
            fingerprint = (attrs.st_dev, attrs.st_ino, attrs.st_size, attrs.st_mtime_ns, attrs.st_ctime_ns, expected_hash)
            if self._verified.get(str(target)) != fingerprint:
                digest = hashlib.sha256()
                with target.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
                        digest.update(chunk)
                if digest.hexdigest() != expected_hash:
                    return None
                self._verified[str(target)] = fingerprint
            return target
        except OSError:
            return None

    def _package_ready(self, name, manifest):
        try:
            package = self._get_metadata()["packages"][name]
            installed = manifest["packages"][name]
            if installed.get("sha256") != package["sha256"]:
                return False
            generation = manifest["generation"]
            for tool in TOOLS[name]:
                info = manifest["tools"][tool]
                relative = f"versions/{generation}/{tool}"
                if info.get("filename") != relative or info.get("package") != name or not self._verified_file(relative, info.get("sha256")):
                    return False
            license_name = package["target_license"]
            info = manifest["licenses"][name]
            relative = f"versions/{generation}/{license_name}"
            return info.get("filename") == relative and self._verified_file(relative, info.get("sha256")) is not None
        except (KeyError, TypeError, ValueError, OSError):
            return False

    def tool(self, name):
        if not isinstance(name, str) or name not in ("node", "ffmpeg", "ffprobe"):
            return None
        manifest = self._load_manifest()
        package = "node" if name == "node" else "ffmpeg"
        if not self._package_ready(package, manifest):
            return None
        return str(self.runtime_dir / manifest["tools"][name]["filename"])

    def wrap_command(self, command):
        result = list(command)
        if result and result[0] in ("node", "ffmpeg", "ffprobe"):
            owned = self.tool(result[0])
            if owned:
                result[0] = owned
        return result

    def status(self):
        try:
            metadata = self._get_metadata()
            manifest = self._load_manifest()
            packages = {name: self._package_ready(name, manifest) for name in TOOLS}
            node = packages["node"]
            ffmpeg = packages["ffmpeg"]
            ready = node and ffmpeg
            download = sum(metadata["packages"][name]["size_bytes"] for name in TOOLS if not packages[name])
            return {"ready": ready, "node": node, "ffmpeg": ffmpeg, "ffprobe": ffmpeg,
                    "download_bytes": download,
                    "reason": "Optional media runtime ready" if ready else "Optional media tools need setup with consent"}
        except Exception:
            return {"ready": False, "node": False, "ffmpeg": False, "ffprobe": False,
                    "download_bytes": 0, "reason": "Linux media runtime metadata unavailable"}

    def _cache_size(self):
        total = 0
        if not self.runtime_dir.exists():
            return total
        for root, dirs, files in os.walk(self.runtime_dir, followlinks=False):
            for name in (*dirs, *files):
                path = Path(root) / name
                if not self._safe_path(path):
                    raise ValueError("Unsafe existing media runtime cache")
                attrs = path.lstat()
                if stat.S_ISREG(attrs.st_mode):
                    total += attrs.st_size
                elif not stat.S_ISDIR(attrs.st_mode):
                    raise ValueError("Special file in media runtime cache")
                if total > MAX_CACHE:
                    raise ValueError("Media runtime cache exceeds size cap")
        return total

    def _download(self, package, archive):
        if not _safe_download_url(package["url"]) or not self._check_allowed():
            raise ValueError("Runtime download cancelled or untrusted")
        opener = self._urlopen or urllib.request.build_opener(
            RuntimeRedirectHandler(), urllib.request.HTTPSHandler(context=_ssl_context())).open
        request = urllib.request.Request(package["url"], headers={"User-Agent": "Continue-Deck-MediaRuntime/1.0", "Accept": "*/*"})
        cap = min(package.get("max_compressed_bytes", MAX_COMPRESSED[package["name"]]), MAX_COMPRESSED[package["name"]])
        started = time.monotonic()
        with opener(request, timeout=30) as response:
            final_url = getattr(response, "url", None) or response.geturl()
            if not _safe_download_url(final_url):
                raise ValueError("Untrusted runtime redirect")
            declared = response.getheader("Content-Length") if hasattr(response, "getheader") else None
            if declared is not None and (not str(declared).isdigit() or int(declared) > cap or int(declared) != package["size_bytes"]):
                raise ValueError("Runtime response size differs from pinned metadata")
            digest = hashlib.sha256()
            total = 0
            with self._open_new(archive) as output:
                while True:
                    if not self._check_allowed() or time.monotonic() - started > 600:
                        raise ValueError("Runtime download cancelled or timed out")
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > cap or total > package["size_bytes"]:
                        raise ValueError("Runtime download exceeds size cap")
                    self._check_space(len(chunk))
                    output.write(chunk)
                    digest.update(chunk)
            if total != package["size_bytes"] or digest.hexdigest() != package["sha256"]:
                raise ValueError("Runtime download checksum or size mismatch")

    @staticmethod
    def _safe_member_name(name):
        return (isinstance(name, str) and 0 < len(name) <= 4096 and "\\" not in name
                and not name.startswith("/") and not re.match(r"^[A-Za-z]:", name)
                and ".." not in PurePosixPath(name).parts and "\x00" not in name)

    def _extract(self, archive, staging, package, limit):
        wanted = {**{value: value for value in package["tools"].values()}, package["license_file"]: package["target_license"]}
        hashes = {}
        with archive.open("rb") as raw:
            stream = _XZReader(raw, limit, self._check_allowed)
            with tarfile.open(fileobj=stream, mode="r|", tarinfo=_SafeTarInfo) as tf:
                for count, member in enumerate(tf, 1):
                    if count > MAX_ENTRIES or not self._check_allowed():
                        raise ValueError("Runtime archive count exceeded or cancelled")
                    if not self._safe_member_name(member.name) or member.size < 0 or member.size > limit:
                        raise ValueError("Unsafe runtime tar member")
                    basename = PurePosixPath(member.name).name
                    target_name = wanted.get(basename)
                    parts = PurePosixPath(member.name).parts
                    # Node contains many third-party LICENSE files under npm.
                    # Accept only the archive root's license and bin executables.
                    if target_name is not None:
                        selected = (len(parts) == 2 if basename == package['license_file']
                                    else len(parts) == 3 and parts[1] == 'bin')
                        if not selected:
                            continue
                    if target_name is None:
                        # Official Node archives contain npm/corepack symlinks.
                        # They are deliberately skipped, never followed or copied.
                        continue
                    if target_name in hashes or not member.isfile() or member.issparse():
                        raise ValueError("Runtime tool/license must be a unique regular file")
                    if target_name.startswith("LICENSE_") and member.size > MAX_LICENSE:
                        raise ValueError("Runtime license exceeds size cap")
                    if member.size == 0:
                        raise ValueError("Empty runtime tool or license")
                    output_path = staging / target_name
                    digest = hashlib.sha256()
                    copied = 0
                    with tf.extractfile(member) as source, self._open_new(output_path) as output:
                        while True:
                            if not self._check_allowed():
                                raise ValueError("Runtime extraction cancelled")
                            chunk = source.read(CHUNK_SIZE)
                            if not chunk:
                                break
                            copied += len(chunk)
                            if copied > member.size:
                                raise ValueError("Runtime extracted member exceeds declared size")
                            digest.update(chunk)
                            self._check_space(len(chunk))
                            output.write(chunk)
                    if copied != member.size:
                        raise ValueError("Truncated runtime extracted member")
                    output_path.chmod(0o644 if target_name.startswith("LICENSE_") else 0o700)
                    hashes[target_name] = digest.hexdigest()
            # Verify xz end marker/output budget beyond tar's own end marker.
            while stream.read(CHUNK_SIZE):
                pass
        if set(hashes) != set(wanted.values()):
            raise ValueError("Required runtime executable or license missing")
        return hashes

    def _remove_staging(self, staging):
        # Only the freshly generated direct child can be removed here.
        if staging.parent == self.runtime_dir and staging.name.startswith(".staging-") and self._safe_path(staging) and staging.is_dir():
            shutil.rmtree(staging)

    def prepare(self, consent=False):
        if consent is not True:
            return {"ok": False, "consent_required": True, "reason": "Consent required"}
        if not self._prepare_lock.acquire(blocking=False):
            return {"ok": False, "deferred": "busy", "reason": "Media setup in progress"}
        staging = None
        promoted = None
        temporary = None
        committed = False
        self._allowed_cache = None
        try:
            if not self._check_allowed():
                raise ValueError("Runtime setup cancelled")
            if not self._safe_path(self.runtime_dir):
                raise ValueError("Unsafe media runtime directory")
            metadata = self._get_metadata()
            if self.status()["ready"]:
                return {"ok": True, "tools": {name: self.tool(name) for name in ("node", "ffmpeg", "ffprobe")}, "reason": "Media runtime already verified"}
            existing_size = self._cache_size()
            limit = min(int(metadata.get("caps", {}).get("max_decompressed_bytes", MAX_DECOMPRESSED)), MAX_DECOMPRESSED)
            if limit <= 0 or existing_size + sum(p["size_bytes"] for p in metadata["packages"].values()) + limit > MAX_CACHE:
                raise ValueError("Media runtime setup exceeds cache budget")
            self._check_space(sum(p['size_bytes'] for p in metadata['packages'].values())+limit)
            self._mkdir(self.runtime_dir)
            generation = uuid.uuid4().hex
            staging = self.runtime_dir / (".staging-" + generation)
            self._mkdir(staging)
            prior = self._load_manifest()
            hashes = {}
            for name in TOOLS:
                package = dict(metadata["packages"][name], name=name)
                if self._package_ready(name, prior):
                    for filename in (*TOOLS[name].values(), package["target_license"]):
                        old = self.runtime_dir / f"versions/{prior['generation']}/{filename}"
                        if not self._safe_path(old) or not self._check_allowed():
                            raise ValueError("Runtime reuse cancelled or unsafe")
                        digest = hashlib.sha256()
                        with old.open("rb") as source, self._open_new(staging / filename) as output:
                            while True:
                                if not self._check_allowed():
                                    raise ValueError("Runtime reuse cancelled")
                                chunk = source.read(CHUNK_SIZE)
                                if not chunk:
                                    break
                                digest.update(chunk)
                                output.write(chunk)
                        (staging / filename).chmod(0o644 if filename.startswith("LICENSE_") else 0o700)
                        hashes[filename] = digest.hexdigest()
                    continue
                archive = staging / package["filename"]
                self._download(package, archive)
                hashes.update(self._extract(archive, staging, package, limit))
                archive.unlink()
            if not self._check_allowed():
                raise ValueError("Runtime setup cancelled before promotion")
            versions = self.runtime_dir / "versions"
            self._mkdir(versions)
            promoted = versions / generation
            if not self._safe_path(promoted) or promoted.exists():
                raise ValueError("Unsafe runtime generation destination")
            os.replace(staging, promoted)
            staging = None
            manifest = {"schema_version": "1.0", "platform": "linux-x64", "generation": generation,
                        "installed_at": time.time(), "tools": {}, "licenses": {}, "packages": {}}
            for name in TOOLS:
                package = metadata["packages"][name]
                manifest["packages"][name] = {"version": package.get("version"), "sha256": package["sha256"]}
                for tool in TOOLS[name]:
                    manifest["tools"][tool] = {"filename": f"versions/{generation}/{tool}", "sha256": hashes[tool], "package": name}
                license_name = package["target_license"]
                manifest["licenses"][name] = {"filename": f"versions/{generation}/{license_name}", "sha256": hashes[license_name]}
            temporary = self.runtime_dir / (".manifest-" + generation + ".tmp")
            with self._open_new(temporary) as output:
                output.write(json.dumps(manifest, sort_keys=True, indent=2).encode("utf-8"))
                output.flush()
                os.fsync(output.fileno())
            if not self._safe_path(self.manifest_path) or not self._check_allowed():
                temporary.unlink()
                raise ValueError("Runtime manifest promotion cancelled or unsafe")
            os.replace(temporary, self.manifest_path)
            committed = True
            ready = self.status()["ready"]
            return {"ok": ready, "tools": {name: self.tool(name) for name in ("node", "ffmpeg", "ffprobe")},
                    "reason": "Media runtime installed and verified" if ready else "Runtime verification failed"}
        except Exception as error:
            if self._cancelled.is_set():
                return {'ok': False, 'error': 'cancelled', 'reason': 'cancelled'}
            # Never include arbitrary exception text containing user paths/URLs.
            safe_reason = str(error) if isinstance(error, ValueError) else type(error).__name__
            return {"ok": False, "reason": "Media runtime setup failed: " + safe_reason}
        finally:
            if temporary is not None and self._safe_path(temporary):
                temporary.unlink(missing_ok=True)
            if staging is not None:
                self._remove_staging(staging)
            if promoted is not None and not committed and self._safe_path(promoted) and promoted.is_dir():
                shutil.rmtree(promoted)
            self._prepare_lock.release()


DeckMediaRuntime = MediaRuntime
