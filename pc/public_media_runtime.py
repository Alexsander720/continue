"""Public PC Media Runtime for Continue? Big Picture PC.

Automated, isolated setup and verification of optional media tools (Node.js, FFmpeg, FFprobe).
Features:
- Pure Python standard library implementation.
- Zero network activity or file downloads on import or constructor.
- Strict user consent requirement (never downloads without explicit consent).
- Download and unpack containment strictly inside <data_root>/bin/pc-runtime.
- Zero mutation of global environment or PATH (primary uses absolute tool paths).
- Strict HTTPS and host allowlist enforcement (including redirects).
- Download size caps (Node <= 80MB, FFmpeg <= 220MB compressed).
- Pre-extraction SHA-256 integrity verification against pinned official metadata.
- Security protection against zip-slip, symlinks, and decompression bombs.
- Bounded extraction: unpacks ONLY node.exe, ffmpeg.exe, ffprobe.exe and licenses.
- Atomic staging and manifest-based verification with reuse of valid existing tools.
- Chunk-gated cancellation checkpoints via allowed callback.
- Privacy preservation: status reports never expose local user paths or secrets.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import threading
from pathlib import Path
import shutil
import sys
import time
from typing import Any, Callable, Dict, List, Optional
import urllib.parse
import urllib.request
import zipfile

CHUNK_SIZE = 64 * 1024  # 64 KB per stream chunk


def _safe_download_url(url, allowed_hosts):
    try:
        parsed=urllib.parse.urlsplit(url)
        return parsed.scheme=='https' and parsed.hostname in allowed_hosts and not parsed.username and not parsed.password and parsed.port in (None,443)
    except (TypeError,ValueError):
        return False


class RuntimeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts):
        super().__init__()
        self.hosts=hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _safe_download_url(newurl,self.hosts):
            raise ValueError('Untrusted media runtime redirect')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


class MediaRuntime:
    """Manages isolated public media runtime tools (ffmpeg, ffprobe, node)."""

    def __init__(
        self,
        data_root: str | Path,
        metadata_path: Optional[str | Path] = None,
        *,
        urlopen: Optional[Callable[..., Any]] = None,
        allowed: Optional[Callable[[], bool]] = None,
    ) -> None:
        """Initialize MediaRuntime without performing any I/O or downloads."""
        self.data_root = Path(data_root).resolve()
        if metadata_path is not None:
            self.metadata_path = Path(metadata_path).resolve()
        else:
            parent = Path(__file__).resolve().parent
            self.metadata_path = parent / ('public_assets' if parent.name=='pc_bp' else 'assets') / 'media_runtime.json'
        self._urlopen = urlopen if urlopen is not None else urllib.request.urlopen
        self._injected_urlopen = urlopen is not None
        self.allowed = allowed

        # Runtime files are strictly contained inside <data_root>/bin/pc-runtime
        self.runtime_dir = self.data_root / "bin" / "pc-runtime"
        self.manifest_path = self.runtime_dir / "manifest.json"

        # Lazy-loaded metadata
        self._meta: Optional[Dict[str, Any]] = None
        self._prepare_lock = threading.Lock()
        self._verified = {}

    def _safe_path(self, path):
        try:
            path = Path(path).absolute()
            path.relative_to(self.data_root)
            while True:
                if path.exists() or path.is_symlink():
                    st = path.lstat()
                    if path.is_symlink() or getattr(st,'st_file_attributes',0)&0x400:
                        return False
                if path == self.data_root:
                    return True
                path = path.parent
        except (OSError,ValueError):
            return False

    def _space_available(self, required):
        # The selected data volume may differ from the system volume. Include
        # archives and bounded extraction at peak, plus a fixed working reserve.
        target = self.runtime_dir
        while not target.exists():
            target = target.parent
        try:
            return shutil.disk_usage(target).free >= required + 128 * 1024**2
        except OSError:
            return False

    def _get_metadata(self) -> Dict[str, Any]:
        """Load and cache metadata from metadata_path."""
        if self._meta is None:
            if not self.metadata_path.is_file():
                raise FileNotFoundError(f"Metadata file not found: {self.metadata_path.name}")
            with self.metadata_path.open('rb') as f:
                raw = f.read(65537)
            if len(raw)>65536:
                raise ValueError('Runtime metadata too large')
            self._meta = json.loads(raw.decode('utf-8'))
            if not isinstance(self._meta,dict) or set(self._meta.get('packages',{})) != {'node','ffmpeg'}:
                raise ValueError('Invalid runtime packages')
            for key,pkg in self._meta['packages'].items():
                if not isinstance(pkg,dict) or not re.fullmatch(r'[a-f0-9]{64}',str(pkg.get('sha256',''))):
                    raise ValueError('Invalid runtime checksum')
                for name in [pkg.get('filename'),pkg.get('target_license'),*pkg.get('tools',{}).values()]:
                    if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,160}',name) or name in ('.','..'):
                        raise ValueError('Invalid runtime filename')
        return self._meta

    def _check_allowed(self) -> bool:
        """Evaluate allowed callback checkpoint."""
        if self.allowed is not None:
            try:
                return bool(self.allowed())
            except Exception:
                return False
        return True

    def _hash_file(self, path: Path) -> str:
        """Compute SHA-256 hex digest of a local file."""
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _load_manifest(self) -> Dict[str, Any]:
        """Load manifest.json if valid, else return empty dict."""
        if not self._safe_path(self.manifest_path) or not self.manifest_path.is_file():
            return {}
        try:
            with self.manifest_path.open('rb') as f:
                raw = f.read(65537)
            if len(raw)>65536:
                return {}
            data = json.loads(raw.decode('utf-8'))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _verify_tool_file(self, tool_name: str, expected_filename: str) -> Optional[Path]:
        """Check if a tool file exists, is in manifest, and matches its recorded sha256."""
        target = self.runtime_dir / expected_filename
        if not self._safe_path(target) or not target.is_file():
            return None

        manifest = self._load_manifest()
        tools_meta = manifest.get("tools", {})
        info = tools_meta.get(tool_name)
        if not isinstance(info, dict):
            return None

        expected_hash = info.get("sha256")
        if not isinstance(expected_hash,str) or not re.fullmatch(r'[a-f0-9]{64}',expected_hash):
            return None

        try:
            stat = target.stat()
            fingerprint = (stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns,expected_hash)
            if self._verified.get(str(target)) == fingerprint:
                return target.resolve()
            actual_hash = self._hash_file(target)
            if actual_hash.lower() == expected_hash.lower():
                self._verified[str(target)] = fingerprint
                return target.resolve()
        except Exception:
            return None
        return None

    def tool(self, name: str) -> Optional[str]:
        """Return hash-verified absolute path to tool executable, or None if not ready/tampered."""
        tool_name = name.lower().strip()
        if tool_name.endswith(".exe"):
            tool_name = tool_name[:-4]

        filename_map = {
            "node": "node.exe",
            "ffmpeg": "ffmpeg.exe",
            "ffprobe": "ffprobe.exe",
        }
        expected_filename = filename_map.get(tool_name)
        if not expected_filename:
            return None

        verified = self._verify_tool_file(tool_name, expected_filename)
        return str(verified) if verified else None

    def wrap_command(self, cmd: List[str]) -> List[str]:
        """Wrap command by replacing first token with verified tool absolute path if available."""
        if not cmd:
            return []
        result = list(cmd)
        first = str(result[0]).lower().strip()
        if first.endswith(".exe"):
            first = first[:-4]
        if first in ("ffmpeg", "ffprobe", "node"):
            tool_path = self.tool(first)
            if tool_path:
                result[0] = tool_path
        return result

    def status(self) -> Dict[str, Any]:
        """Inspect and return current runtime status without leaking user paths or secrets."""
        try:
            meta = self._get_metadata()
            packages = meta.get("packages", {})
        except Exception:
            return {
                "ready": False,
                "node": False,
                "ffmpeg": False,
                "ffprobe": False,
                "reason": "Media runtime metadata unavailable",
                "download_bytes": 0,
            }

        node_ok = self.tool("node") is not None
        ffmpeg_ok = self.tool("ffmpeg") is not None
        ffprobe_ok = self.tool("ffprobe") is not None
        all_ready = node_ok and ffmpeg_ok and ffprobe_ok

        download_bytes = 0
        if not node_ok:
            download_bytes += int((packages.get("node") or {}).get("size_bytes", 0))
        if not (ffmpeg_ok and ffprobe_ok):
            download_bytes += int((packages.get("ffmpeg") or {}).get("size_bytes", 0))

        if all_ready:
            reason = "Optional media runtime tools ready (ffmpeg, ffprobe, node)"
        elif download_bytes > 0:
            mb = max(1, download_bytes // (1024 * 1024))
            missing = []
            if not node_ok:
                missing.append("node")
            if not (ffmpeg_ok and ffprobe_ok):
                missing.append("ffmpeg")
            reason = f"Media runtime not installed ({', '.join(missing)} missing; ~{mb}MB download required with consent)"
        else:
            reason = "Media runtime verification failed"

        return {
            "ready": all_ready,
            "node": node_ok,
            "ffmpeg": ffmpeg_ok,
            "ffprobe": ffprobe_ok,
            "reason": reason,
            "download_bytes": download_bytes if not all_ready else 0,
        }

    def _tools_dict(self) -> Dict[str, Optional[str]]:
        """Return dict of tool names to absolute path or None."""
        return {
            "node": self.tool("node"),
            "ffmpeg": self.tool("ffmpeg"),
            "ffprobe": self.tool("ffprobe"),
        }

    def _download_stream(
        self,
        url: str,
        dest_archive: Path,
        expected_sha256: str,
        max_bytes: int,
        allowed_hosts: set[str],
    ) -> tuple[bool, str]:
        """Download URL to dest_archive with strict security controls."""
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme.lower() != "https" or parsed.username or parsed.password or parsed.port not in (None,443):
            return False, f"Insecure download scheme rejected: {parsed.scheme}"
        if parsed.hostname and parsed.hostname.lower() not in allowed_hosts:
            return False, f"Host not in official allowlist: {parsed.hostname}"

        if not self._check_allowed():
            return False, "Cancelled by allowed checkpoint before download"

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Continue-PC-MediaRuntime/1.0",
                "Accept": "*/*",
            },
        )

        try:
            if not self._safe_path(dest_archive):
                return False,'Unsafe runtime download destination'
            opener = self._urlopen if self._injected_urlopen else urllib.request.build_opener(RuntimeRedirectHandler(allowed_hosts)).open
            with opener(req, timeout=30) as resp:
                # Validate redirect host
                resp_url = getattr(resp, "url", None) or (resp.geturl() if hasattr(resp, "geturl") else url)
                resp_parsed = urllib.parse.urlparse(resp_url)
                if resp_parsed.scheme!='https' or resp_parsed.username or resp_parsed.password or resp_parsed.hostname not in allowed_hosts:
                    return False, f"Redirect to untrusted host rejected: {resp_parsed.hostname}"

                # Content-Length check if available
                content_len = resp.getheader("Content-Length") if hasattr(resp, "getheader") else None
                if content_len:
                    try:
                        if int(content_len) > max_bytes:
                            return False, f"Download Content-Length ({content_len} B) exceeds security cap ({max_bytes} B)"
                    except ValueError:
                        pass

                hasher = hashlib.sha256()
                total_bytes = 0
                started = time.monotonic()

                with open(dest_archive, "wb") as out_f:
                    while True:
                        if time.monotonic()-started>600:
                            return False,'Runtime download deadline exceeded'
                        if not self._check_allowed():
                            return False, "Download aborted by allowed checkpoint"

                        chunk = resp.read(CHUNK_SIZE)
                        if not chunk:
                            break

                        total_bytes += len(chunk)
                        if total_bytes > max_bytes:
                            return False, f"Download stream exceeded maximum byte cap ({max_bytes} B)"
                        if not self._space_available(len(chunk)):
                            return False, 'Not enough free disk space for media tools'

                        hasher.update(chunk)
                        out_f.write(chunk)

                digest = hasher.hexdigest().lower()
                if digest != expected_sha256.lower():
                    return False, f"Checksum mismatch: expected {expected_sha256[:12]}..., got {digest[:12]}..."

                return True, "Download verified"

        except Exception as e:
            return False, f"Download failed: {type(e).__name__}: {e}"

    def _extract_bounded_files(
        self,
        archive_path: Path,
        staging_dir: Path,
        tool_specs: Dict[str, str],
        license_entry: str,
        target_license: str,
        max_decompressed_bytes: int,
    ) -> tuple[bool, Dict[str, str], str]:
        """Extract only specified executable and license files, enforcing zip safety."""
        if not zipfile.is_zipfile(archive_path):
            return False, {}, "Corrupt or invalid zip archive"

        extracted_hashes: Dict[str, str] = {}
        try:
            with zipfile.ZipFile(archive_path, "r") as zf:
                infolist = zf.infolist()
                if len(infolist)>20000:
                    return False,{},'Too many runtime archive entries'

                # 1. Security scan: zip slip, symlinks, decompression bombs
                total_uncompressed = 0
                for zinfo in infolist:
                    filename = zinfo.filename
                    # Reject path traversal / zip-slip
                    if filename.startswith("/") or filename.startswith("\\") or ".." in filename.replace("\\", "/").split("/"):
                        return False, {}, f"Malicious path traversal entry in archive: {filename}"
                    if len(filename) > 1 and filename[1] == ":":
                        return False, {}, f"Drive letter path entry in archive: {filename}"

                    # Reject symlinks (Unix mode 0120000)
                    if (zinfo.external_attr >> 16) & 0o170000 == 0o120000:
                        return False, {}, f"Symlink rejected in archive: {filename}"

                    total_uncompressed += zinfo.file_size
                    if total_uncompressed > max_decompressed_bytes:
                        return False, {}, f"Decompressed size exceeds safety cap ({max_decompressed_bytes} B)"

                # 2. Extract only targeted tools
                for tool_key, dest_name in tool_specs.items():
                    target_entry: Optional[zipfile.ZipInfo] = None
                    for zinfo in infolist:
                        norm = zinfo.filename.replace("\\", "/")
                        if norm == dest_name or norm.endswith("/" + dest_name):
                            target_entry = zinfo
                            break
                        if Path(norm).name.lower() == dest_name.lower():
                            target_entry = zinfo
                            break

                    if target_entry is None:
                        return False, {}, f"Required executable {dest_name} not found in archive"

                    dest_file = staging_dir / dest_name
                    with zf.open(target_entry) as src, open(dest_file, "wb") as dst:
                        hasher = hashlib.sha256()
                        while chunk := src.read(CHUNK_SIZE):
                            if not self._space_available(len(chunk)):
                                return False, {}, 'Not enough free disk space for extraction'
                            if not self._check_allowed():
                                return False, {}, "Extraction aborted by allowed checkpoint"
                            hasher.update(chunk)
                            dst.write(chunk)
                    extracted_hashes[dest_name] = hasher.hexdigest()

                # 3. Extract license file
                lic_entry: Optional[zipfile.ZipInfo] = None
                for zinfo in infolist:
                    norm = zinfo.filename.replace("\\", "/")
                    if Path(norm).name.lower() == license_entry.lower():
                        lic_entry = zinfo
                        break

                if lic_entry is None:
                    return False,{},'Runtime license missing'
                if lic_entry.file_size>2*1024**2:
                    return False,{},'Runtime license too large'
                if lic_entry is not None:
                    dest_lic = staging_dir / target_license
                    with zf.open(lic_entry) as src, open(dest_lic, "wb") as dst:
                        hasher = hashlib.sha256()
                        while chunk := src.read(CHUNK_SIZE):
                            if not self._space_available(len(chunk)):
                                return False, {}, 'Not enough free disk space for extraction'
                            if not self._check_allowed():
                                return False,{},'Runtime extraction cancelled'
                            hasher.update(chunk)
                            dst.write(chunk)
                    extracted_hashes[target_license] = hasher.hexdigest()

                return True, extracted_hashes, "Extraction successful"

        except Exception as e:
            return False, {}, f"Extraction failed: {type(e).__name__}: {e}"

    def prepare(self, consent: bool = False) -> Dict[str, Any]:
        if consent is not True:
            return {'ok':False,'consent_required':True,'reason':'Consent required'}
        if not self._prepare_lock.acquire(blocking=False):
            return {'ok':False,'deferred':'busy','reason':'Media setup in progress'}
        try:
            if not self._safe_path(self.runtime_dir):
                return {'ok':False,'reason':'Unsafe media runtime directory'}
            return self._prepare_locked(consent)
        except OSError as exc:
            reason = ('Not enough free disk space for media tools' if exc.errno == 28
                      else 'Could not write media tools: ' + str(exc.strerror or type(exc).__name__))
            return {'ok': False, 'tools': self._tools_dict(), 'reason': reason}
        finally:
            self._prepare_lock.release()

    def _prepare_locked(self, consent: bool = False) -> Dict[str, Any]:
        """Download and unpack media runtime tools with consent and safety bounds."""
        if not consent:
            return {
                "ok": False,
                "tools": self._tools_dict(),
                "reason": "Consent is required to download optional media runtime tools",
            }

        if not self._check_allowed():
            return {
                "ok": False,
                "tools": self._tools_dict(),
                "reason": "Operation cancelled by allowed checkpoint",
            }

        try:
            meta = self._get_metadata()
        except Exception as e:
            return {
                "ok": False,
                "tools": self._tools_dict(),
                "reason": f"Failed to load media runtime metadata: {e}",
            }

        allowed_hosts = {'nodejs.org','github.com','objects.githubusercontent.com','release-assets.githubusercontent.com'}
        if self._urlopen is not urllib.request.urlopen:
            allowed_hosts |= {h.lower() for h in meta.get('allowed_hosts',[])}  # injected offline client
        caps = meta.get("caps", {})
        max_decompressed = int(caps.get("max_decompressed_bytes", 1024 * 1024 * 1024))
        packages = meta.get("packages", {})

        # Check existing installation
        st = self.status()
        if st["ready"]:
            return {
                "ok": True,
                "tools": self._tools_dict(),
                "reason": "Media runtime tools are already installed and verified",
            }

        peak = max_decompressed + max(min(int(pkg.get('max_compressed_bytes', 250*1024**2)),
                   80*1024**2 if key=='node' else 220*1024**2) for key,pkg in packages.items())
        if not self._space_available(peak):
            return {'ok':False, 'tools':self._tools_dict(), 'reason':'Not enough free disk space for media tools',
                    'required_free_bytes':peak + 128*1024**2}

        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        manifest = self._load_manifest()
        manifest_tools = manifest.get("tools", {})
        manifest_packages = manifest.get("packages", {})

        # Process packages
        for pkg_key, pkg_info in packages.items():
            if not self._check_allowed():
                return {
                    "ok": False,
                    "tools": self._tools_dict(),
                    "reason": "Operation cancelled by allowed checkpoint",
                }

            # Check if all tools in this package are already valid
            tools_spec: Dict[str, str] = pkg_info.get("tools", {})
            pkg_tools_ready = all(
                self._verify_tool_file(t_name, t_fname) is not None
                for t_name, t_fname in tools_spec.items()
            )
            if pkg_tools_ready:
                continue

            staging_dir = self.runtime_dir / f".staging_{pkg_key}"
            if not self._safe_path(staging_dir):
                return {'ok':False,'reason':'Unsafe runtime staging directory'}
            try:
                if staging_dir.exists():
                    shutil.rmtree(staging_dir, ignore_errors=True)
                staging_dir.mkdir(parents=True, exist_ok=True)

                archive_file = staging_dir / pkg_info.get("filename", f"{pkg_key}.zip")
                url = pkg_info.get("url", "")
                sha256 = pkg_info.get("sha256", "")
                max_comp = int(pkg_info.get("max_compressed_bytes", 250 * 1024 * 1024))
                max_comp = min(max_comp,80*1024**2 if pkg_key=='node' else 220*1024**2)

                # Step 1: Download
                ok, msg = self._download_stream(url, archive_file, sha256, max_comp, allowed_hosts)
                if not ok:
                    return {
                        "ok": False,
                        "tools": self._tools_dict(),
                        "reason": f"Failed downloading {pkg_key}: {msg}",
                    }

                # Step 2: Extract bounded files
                ok, extracted_hashes, msg = self._extract_bounded_files(
                    archive_file,
                    staging_dir,
                    tools_spec,
                    pkg_info.get("license_file", "LICENSE"),
                    pkg_info.get("target_license", f"LICENSE_{pkg_key}.txt"),
                    max_decompressed,
                )
                if not ok:
                    return {
                        "ok": False,
                        "tools": self._tools_dict(),
                        "reason": f"Failed extracting {pkg_key}: {msg}",
                    }

                # Remove archive to save disk space before promoting
                if archive_file.exists():
                    archive_file.unlink(missing_ok=True)

                # Step 3: Promote atomically
                for tool_key, dest_name in tools_spec.items():
                    staged_tool = staging_dir / dest_name
                    final_tool = self.runtime_dir / dest_name
                    if not self._safe_path(final_tool) or not self._check_allowed():
                        return {'ok':False,'reason':'Runtime promotion cancelled or unsafe'}
                    os.replace(staged_tool,final_tool)

                    manifest_tools[tool_key] = {
                        "filename": dest_name,
                        "sha256": extracted_hashes.get(dest_name),
                        "package": pkg_key,
                    }

                lic_name = pkg_info.get("target_license", f"LICENSE_{pkg_key}.txt")
                staged_lic = staging_dir / lic_name
                if staged_lic.is_file():
                    final_lic = self.runtime_dir / lic_name
                    if not self._safe_path(final_lic):
                        return {'ok':False,'reason':'Unsafe runtime license destination'}
                    os.replace(staged_lic,final_lic)

                manifest_packages[pkg_key] = {
                    "version": pkg_info.get("version"),
                    "installed_at": time.time(),
                }

                # Keep the verified Node receipt if the later FFmpeg setup fails.
                self._write_manifest(manifest_tools,manifest_packages)

            finally:
                if self._safe_path(staging_dir):
                    shutil.rmtree(staging_dir, ignore_errors=True)

        st_after = self.status()
        if st_after["ready"]:
            return {"ok":True,"tools":self._tools_dict(),"reason":"Media runtime successfully installed and verified"}
        return {"ok":False,"tools":self._tools_dict(),"reason":f"Media runtime install incomplete: {st_after['reason']}"}

    def _write_manifest(self,manifest_tools,manifest_packages):
        manifest_data = {
            "schema_version": "1.0",
            "installed_at": time.time(),
            "tools": manifest_tools,
            "packages": manifest_packages,
        }
        temp_manifest = self.runtime_dir / ".manifest.tmp"
        if not self._safe_path(temp_manifest) or not self._safe_path(self.manifest_path):
            raise ValueError('Unsafe runtime manifest destination')
        try:
            with open(temp_manifest, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)
                f.flush();os.fsync(f.fileno())
            temp_manifest.replace(self.manifest_path)
        finally:
            temp_manifest.unlink(missing_ok=True)
