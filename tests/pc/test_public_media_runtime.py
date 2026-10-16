"""Unit tests for public_media_runtime (MediaRuntime) isolated optional tools setup.

All tests run completely offline without external network or subprocess execution.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import sys
import zipfile
import pytest

# Ensure pc_bp directory is in sys.path
PC_BP = (Path(__file__).resolve().parents[2] / 'pc')
if str(PC_BP) not in sys.path:
    sys.path.insert(0, str(PC_BP))

from public_media_runtime import MediaRuntime


def _make_zip_bytes(entries: dict[str, bytes | str]) -> bytes:
    """Create in-memory zip bytes with specified entries."""
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            if isinstance(content, str):
                content = content.encode("utf-8")
            zf.writestr(name, content)
    return bio.getvalue()


class MockHttpResponse:
    def __init__(self, data: bytes, headers: dict | None = None, status: int = 200, url: str = "https://mock.local"):
        self._data = data
        self._io = io.BytesIO(data)
        self.headers = headers or {"Content-Length": str(len(data))}
        self.status = status
        self.url = url

    def read(self, amt: int | None = None) -> bytes:
        if amt is None:
            return self._io.read()
        return self._io.read(amt)

    def getheader(self, name: str, default: str | None = None) -> str | None:
        for k, v in self.headers.items():
            if k.lower() == name.lower():
                return v
        return default

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def _build_test_metadata(tmp_path: Path, node_zip: bytes, ffmpeg_zip: bytes) -> tuple[Path, dict]:
    """Generate valid test metadata pointing to supplied test archives."""
    meta = {
      "schema_version": "1.0",
      "platform": "win-x64",
      "platform_support": {
        "supported_architectures": ["win-x64"],
        "emulated_arm": "Supported on Windows 11 ARM64 via built-in x64 emulation (Prism)",
        "native_arm": "Unsupported: native win-arm64 binaries are not packaged in this runtime"
      },
      "allowed_hosts": [
        "nodejs.org",
        "github.com",
        "objects.githubusercontent.com"
      ],
      "caps": {
        "max_download_node_bytes": 83886080,
        "max_download_ffmpeg_bytes": 230686720,
        "max_decompressed_bytes": 1073741824
      },
      "packages": {
        "node": {
          "name": "node",
          "version": "22.23.3",
          "url": "https://nodejs.org/dist/v22.23.3/node-v22.23.3-win-x64.zip",
          "filename": "node-v22.23.3-win-x64.zip",
          "sha256": hashlib.sha256(node_zip).hexdigest(),
          "size_bytes": len(node_zip),
          "max_compressed_bytes": 83886080,
          "tools": {
            "node": "node.exe"
          },
          "license_file": "LICENSE",
          "target_license": "LICENSE_node.txt"
        },
        "ffmpeg": {
          "name": "ffmpeg",
          "version": "9.0.2",
          "url": "https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-10-13-13-05/ffmpeg-n9.0.2-27-g7e93014c5b-win64-gpl-9.0.zip",
          "filename": "ffmpeg-n9.0.2-27-g7e93014c5b-win64-gpl-9.0.zip",
          "sha256": hashlib.sha256(ffmpeg_zip).hexdigest(),
          "size_bytes": len(ffmpeg_zip),
          "max_compressed_bytes": 230686720,
          "tools": {
            "ffmpeg": "ffmpeg.exe",
            "ffprobe": "ffprobe.exe"
          },
          "license_file": "LICENSE.txt",
          "target_license": "LICENSE_ffmpeg.txt"
        }
      }
    }
    meta_path = tmp_path / "test_metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta_path, meta


@pytest.fixture
def sample_zips():
    node_zip = _make_zip_bytes({
        "node-v22.23.3-win-x64/node.exe": b"MZ_NODE_MOCK_EXE_DATA",
        "node-v22.23.3-win-x64/LICENSE": b"Node.js License Text",
        "node-v22.23.3-win-x64/other_ignore.txt": b"ignore me",
    })
    ffmpeg_zip = _make_zip_bytes({
        "ffmpeg-9.0.2/bin/ffmpeg.exe": b"MZ_FFMPEG_MOCK_EXE_DATA",
        "ffmpeg-9.0.2/bin/ffprobe.exe": b"MZ_FFPROBE_MOCK_EXE_DATA",
        "ffmpeg-9.0.2/LICENSE.txt": b"FFmpeg GPL License Text",
        "ffmpeg-9.0.2/doc/something.html": b"<html>ignore</html>",
    })
    return node_zip, ffmpeg_zip


@pytest.mark.parametrize('failure', ['flush', 'fsync', 'cancel'])
def test_package_cleanup_and_retry_after_manifest_io_or_cancel(tmp_path, sample_zips, monkeypatch, failure):
    import builtins
    import errno
    import public_media_runtime as mod
    meta, _ = _build_test_metadata(tmp_path, *sample_zips)
    calls = []
    def urlopen(req, **kw):
        url = req.full_url
        key = 0 if 'nodejs' in url else 1
        calls.append(key)
        return MockHttpResponse(sample_zips[key], url=url)
    runtime = MediaRuntime(tmp_path / 'data', meta, urlopen=urlopen)
    # Confirm Node first; faults affect the next package and must preserve its receipt.
    extract = runtime._extract_bounded_files
    cancelled = [False]
    def extraction(*args):
        result = extract(*args)
        if 'ffmpeg' in str(args[0]) and failure == 'cancel':
            cancelled[0] = True
        return result
    original_open = builtins.open
    class FlushFailure:
        def __init__(self, stream): self.stream = stream
        def __enter__(self): return self
        def __exit__(self, *args): self.stream.close()
        def __getattr__(self, key): return getattr(self.stream, key)
        def flush(self): raise OSError(errno.ENOSPC, 'No space left on device (injected flush)')
    def open_with_fault(path, *args, **kw):
        stream = original_open(path, *args, **kw)
        if Path(path).name == '.manifest.tmp' and calls == [0, 1] and failure == 'flush':
            return FlushFailure(stream)
        return stream
    original_fsync = mod.os.fsync
    def fsync_with_fault(fd):
        if calls == [0, 1] and failure == 'fsync':
            raise OSError(errno.ENOSPC, 'No space left on device (injected fsync)')
        return original_fsync(fd)
    with monkeypatch.context() as patch:
        patch.setattr(runtime, '_extract_bounded_files', extraction)
        patch.setattr(runtime, '_check_allowed', lambda: not cancelled[0])
        patch.setattr(builtins, 'open', open_with_fault)
        patch.setattr(mod.os, 'fsync', fsync_with_fault)
        result = runtime.prepare(consent=True)
    assert not result['ok'] and result['reason']
    assert ('space' in result['reason'].lower()) if failure != 'cancel' else ('cancel' in result['reason'].lower())
    assert not list(runtime.runtime_dir.glob('.staging_*'))
    assert not (runtime.runtime_dir / '.manifest.tmp').exists()
    assert runtime.tool('node') is not None
    receipt = json.loads(runtime.manifest_path.read_text())
    assert set(receipt['packages']) == {'node'}
    assert runtime.prepare(consent=True)['ok']
    assert calls == [0, 1, 1], 'a confirmed package must not be downloaded again'


def test_low_disk_refuses_before_network(tmp_path,sample_zips,monkeypatch):
    from collections import namedtuple
    import public_media_runtime as mod
    path,_=_build_test_metadata(tmp_path,*sample_zips)
    monkeypatch.setattr(mod.shutil,'disk_usage',lambda _:namedtuple('Usage','total used free')(100,99,1))
    runtime=MediaRuntime(tmp_path/'data',path,urlopen=lambda *a,**k:pytest.fail('network before disk check'))
    assert 'disk space' in runtime.prepare(True)['reason']
    assert not runtime.runtime_dir.exists()


def test_retry_keeps_verified_node_after_ffmpeg_network_failure(tmp_path,sample_zips):
    path,_=_build_test_metadata(tmp_path,*sample_zips);calls=[];fail=[True]
    def request(req,**kwargs):
        node='nodejs.org' in req.full_url;calls.append('node' if node else 'ffmpeg')
        if not node and fail[0]:raise OSError('offline fixture')
        return MockHttpResponse(sample_zips[0 if node else 1],url=req.full_url)
    runtime=MediaRuntime(tmp_path/'data',path,urlopen=request)
    assert not runtime.prepare(True)['ok']
    assert runtime.tool('node')
    fail[0]=False
    assert runtime.prepare(True)['ok']
    assert calls==['node','ffmpeg','ffmpeg']


def test_disk_drop_during_stream_stops_and_cleans(tmp_path,sample_zips,monkeypatch):
    from collections import namedtuple
    import public_media_runtime as mod
    path,_=_build_test_metadata(tmp_path,*sample_zips);calls=[]
    def space(_):
        calls.append(1)
        return namedtuple('Usage','total used free')(10**12,0,10**12 if len(calls)==1 else 1)
    monkeypatch.setattr(mod.shutil,'disk_usage',space)
    runtime=MediaRuntime(tmp_path/'data',path,urlopen=lambda req,**k:MockHttpResponse(sample_zips[0],url=req.full_url))
    assert 'disk space' in runtime.prepare(True)['reason']
    assert not list(runtime.runtime_dir.glob('.staging_*'))


def test_disk_drop_during_extraction_cleans_stage(tmp_path,sample_zips,monkeypatch):
    path,_=_build_test_metadata(tmp_path,*sample_zips);calls=[]
    runtime=MediaRuntime(tmp_path/'data',path,urlopen=lambda req,**k:MockHttpResponse(sample_zips[0],url=req.full_url))
    def space(_):calls.append(1);return len(calls)<3
    monkeypatch.setattr(runtime,'_space_available',space)
    assert 'disk space' in runtime.prepare(True)['reason']
    assert not list(runtime.runtime_dir.glob('.staging_*'))
    assert runtime.tool('node') is None


def test_runtime_init_no_network_no_downloads(tmp_path, sample_zips):
    """Constructor and import must not perform any downloads or network requests."""
    node_zip, ffmpeg_zip = sample_zips
    meta_path, _ = _build_test_metadata(tmp_path, node_zip, ffmpeg_zip)

    def failing_urlopen(*args, **kwargs):
        raise AssertionError("Network access attempted during initialization!")

    data_root = tmp_path / "data"
    mr = MediaRuntime(data_root, meta_path, urlopen=failing_urlopen)
    assert mr.data_root == data_root.resolve()
    assert not (data_root / "bin" / "pc-runtime").exists()


def test_status_not_installed_no_userpaths(tmp_path, sample_zips):
    """Status on clean install reports missing tools and download bytes with no secrets/userpaths."""
    node_zip, ffmpeg_zip = sample_zips
    meta_path, meta = _build_test_metadata(tmp_path, node_zip, ffmpeg_zip)
    data_root = tmp_path / "users" / "secret_user" / "data"

    mr = MediaRuntime(data_root, meta_path)
    status = mr.status()

    assert status["ready"] is False
    assert status["node"] is False
    assert status["ffmpeg"] is False
    assert status["ffprobe"] is False
    assert status["download_bytes"] == len(node_zip) + len(ffmpeg_zip)
    assert isinstance(status["reason"], str) and len(status["reason"]) > 0

    # Ensure no local user paths or secrets in status
    status_str = json.dumps(status)
    assert "secret_user" not in status_str
    assert str(data_root) not in status_str


def test_prepare_consent_false_no_io(tmp_path, sample_zips):
    """Calling prepare with consent=False must not initiate download or create runtime bin."""
    node_zip, ffmpeg_zip = sample_zips
    meta_path, _ = _build_test_metadata(tmp_path, node_zip, ffmpeg_zip)

    def failing_urlopen(*args, **kwargs):
        raise AssertionError("Network attempted when consent=False!")

    data_root = tmp_path / "data"
    mr = MediaRuntime(data_root, meta_path, urlopen=failing_urlopen)
    res = mr.prepare(consent=False)

    assert res["ok"] is False
    assert "consent" in res["reason"].lower()
    assert not (data_root / "bin" / "pc-runtime").exists()


def test_prepare_allowed_callback_false_no_io(tmp_path, sample_zips):
    """Calling prepare when allowed callback returns False must abort immediately."""
    node_zip, ffmpeg_zip = sample_zips
    meta_path, _ = _build_test_metadata(tmp_path, node_zip, ffmpeg_zip)

    def failing_urlopen(*args, **kwargs):
        raise AssertionError("Network attempted when allowed=False!")

    data_root = tmp_path / "data"
    mr = MediaRuntime(data_root, meta_path, urlopen=failing_urlopen, allowed=lambda: False)
    res = mr.prepare(consent=True)

    assert res["ok"] is False
    assert not (data_root / "bin" / "pc-runtime").exists()


def test_prepare_hash_mismatch_rejected(tmp_path, sample_zips):
    """If downloaded file hash does not match pinned digest, abort and clean staging."""
    node_zip, ffmpeg_zip = sample_zips
    meta_path, _ = _build_test_metadata(tmp_path, node_zip, ffmpeg_zip)

    # Provide tampered bytes
    tampered_node = b"TAMPERED_CONTENT_CORRUPT"

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "node" in url:
            return MockHttpResponse(tampered_node, url=url)
        return MockHttpResponse(ffmpeg_zip, url=url)

    data_root = tmp_path / "data"
    mr = MediaRuntime(data_root, meta_path, urlopen=mock_urlopen)
    res = mr.prepare(consent=True)

    assert res["ok"] is False
    assert "checksum" in res["reason"].lower() or "hash" in res["reason"].lower()
    # No executable marked as ready
    assert mr.tool("node") is None
    assert mr.status()["ready"] is False


def test_prepare_corrupt_zip_rejected(tmp_path, sample_zips):
    """Corrupt zip file must be safely handled without partially executable state."""
    _, ffmpeg_zip = sample_zips
    corrupt_zip = b"NOT_A_ZIP_FILE_AT_ALL_JUST_RANDOM_GARBAGE"
    meta_path, _ = _build_test_metadata(tmp_path, corrupt_zip, ffmpeg_zip)

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "node" in url:
            return MockHttpResponse(corrupt_zip, url=url)
        return MockHttpResponse(ffmpeg_zip, url=url)

    data_root = tmp_path / "data"
    mr = MediaRuntime(data_root, meta_path, urlopen=mock_urlopen)
    res = mr.prepare(consent=True)

    assert res["ok"] is False
    assert mr.tool("node") is None


def test_prepare_zip_slip_rejected(tmp_path, sample_zips):
    """Zip slip with path traversal (e.g. ../evil.exe) must be rejected."""
    _, ffmpeg_zip = sample_zips
    malicious_node_zip = _make_zip_bytes({
        "../../evil.exe": b"MALICIOUS_PAYLOAD",
        "node.exe": b"MZ_NODE",
        "LICENSE": b"MIT",
    })
    meta_path, _ = _build_test_metadata(tmp_path, malicious_node_zip, ffmpeg_zip)

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "node" in url:
            return MockHttpResponse(malicious_node_zip, url=url)
        return MockHttpResponse(ffmpeg_zip, url=url)

    data_root = tmp_path / "data"
    mr = MediaRuntime(data_root, meta_path, urlopen=mock_urlopen)
    res = mr.prepare(consent=True)

    assert res["ok"] is False
    assert not (tmp_path / "evil.exe").exists()
    assert mr.tool("node") is None


def test_prepare_symlink_rejected(tmp_path, sample_zips):
    """Zip with symlink entry must be rejected."""
    _, ffmpeg_zip = sample_zips

    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as zf:
        zf.writestr("node.exe", b"MZ_NODE")
        zf.writestr("LICENSE", b"MIT")
        zinfo = zipfile.ZipInfo("symlink_pointer")
        zinfo.create_system = 3  # Unix
        zinfo.external_attr = 0o120777 << 16  # Symlink mode
        zf.writestr(zinfo, b"/etc/passwd")

    symlink_zip = bio.getvalue()
    meta_path, _ = _build_test_metadata(tmp_path, symlink_zip, ffmpeg_zip)

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "node" in url:
            return MockHttpResponse(symlink_zip, url=url)
        return MockHttpResponse(ffmpeg_zip, url=url)

    data_root = tmp_path / "data"
    mr = MediaRuntime(data_root, meta_path, urlopen=mock_urlopen)
    res = mr.prepare(consent=True)

    assert res["ok"] is False
    assert mr.tool("node") is None


def test_prepare_capped_stream_exceeded(tmp_path, sample_zips):
    """Downloads exceeding package max compressed size must be aborted immediately."""
    node_zip, ffmpeg_zip = sample_zips
    meta_path, meta = _build_test_metadata(tmp_path, node_zip, ffmpeg_zip)

    # Set cap lower than actual size
    meta["packages"]["node"]["max_compressed_bytes"] = len(node_zip) - 10
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "node" in url:
            return MockHttpResponse(node_zip, url=url)
        return MockHttpResponse(ffmpeg_zip, url=url)

    data_root = tmp_path / "data"
    mr = MediaRuntime(data_root, meta_path, urlopen=mock_urlopen)
    res = mr.prepare(consent=True)

    assert res["ok"] is False
    assert "cap" in res["reason"].lower() or "limit" in res["reason"].lower() or "exceeded" in res["reason"].lower()
    assert mr.tool("node") is None


def test_prepare_decompressed_size_exceeded(tmp_path, sample_zips):
    """Decompression bomb exceeding decompression cap must be rejected."""
    _, ffmpeg_zip = sample_zips
    # 200MB uncompressed in a small zip
    bomb_zip = _make_zip_bytes({
        "node.exe": b"\0" * (50 * 1024 * 1024),
        "LICENSE": b"MIT",
    })
    meta_path, meta = _build_test_metadata(tmp_path, bomb_zip, ffmpeg_zip)
    meta["caps"]["max_decompressed_bytes"] = 10 * 1024 * 1024  # 10MB limit
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "node" in url:
            return MockHttpResponse(bomb_zip, url=url)
        return MockHttpResponse(ffmpeg_zip, url=url)

    data_root = tmp_path / "data"
    mr = MediaRuntime(data_root, meta_path, urlopen=mock_urlopen)
    res = mr.prepare(consent=True)

    assert res["ok"] is False
    assert "decompressed" in res["reason"].lower() or "limit" in res["reason"].lower()


def test_prepare_cancellation_during_chunk(tmp_path, sample_zips):
    """If allowed() becomes False midway through download chunks, process aborts cleanly."""
    node_zip, ffmpeg_zip = sample_zips
    meta_path, _ = _build_test_metadata(tmp_path, node_zip, ffmpeg_zip)

    chunks_read = [0]
    def allowed_checker():
        # Allow first 2 chunk queries, then cancel
        return chunks_read[0] < 2

    class ChunkedResponse(MockHttpResponse):
        def read(self, amt: int | None = None) -> bytes:
            chunks_read[0] += 1
            if amt is None:
                amt = 8192
            return super().read(min(amt, 1024))

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "node" in url:
            return ChunkedResponse(node_zip, url=url)
        return ChunkedResponse(ffmpeg_zip, url=url)

    data_root = tmp_path / "data"
    mr = MediaRuntime(data_root, meta_path, urlopen=mock_urlopen, allowed=allowed_checker)
    res = mr.prepare(consent=True)

    assert res["ok"] is False
    assert mr.tool("node") is None
    assert mr.status()["ready"] is False


def test_prepare_success_atomic_install_and_reuse(tmp_path, sample_zips):
    """Happy path: atomic download, extract exact files, manifest verification, reuse."""
    node_zip, ffmpeg_zip = sample_zips
    meta_path, _ = _build_test_metadata(tmp_path, node_zip, ffmpeg_zip)

    download_counts = {"node": 0, "ffmpeg": 0}

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "node" in url:
            download_counts["node"] += 1
            return MockHttpResponse(node_zip, url=url)
        elif "ffmpeg" in url:
            download_counts["ffmpeg"] += 1
            return MockHttpResponse(ffmpeg_zip, url=url)
        raise ValueError(f"Unexpected url: {url}")

    data_root = tmp_path / "data"
    initial_path = os.environ.get("PATH", "")

    mr = MediaRuntime(data_root, meta_path, urlopen=mock_urlopen)
    res = mr.prepare(consent=True)

    # 1. Verification of success
    assert res["ok"] is True
    assert "tools" in res
    assert download_counts["node"] == 1
    assert download_counts["ffmpeg"] == 1

    # 2. PATH must not have been mutated
    assert os.environ.get("PATH", "") == initial_path

    # 3. Status is now ready
    st = mr.status()
    assert st["ready"] is True
    assert st["node"] is True
    assert st["ffmpeg"] is True
    assert st["ffprobe"] is True
    assert st["download_bytes"] == 0

    # 4. Tool lookup returns verified absolute paths
    node_path = mr.tool("node")
    ffmpeg_path = mr.tool("ffmpeg")
    ffprobe_path = mr.tool("ffprobe")
    assert node_path is not None and Path(node_path).is_file()
    assert ffmpeg_path is not None and Path(ffmpeg_path).is_file()
    assert ffprobe_path is not None and Path(ffprobe_path).is_file()

    # 5. Exact files extracted: only node.exe, ffmpeg.exe, ffprobe.exe, licenses, and manifest.json
    bin_dir = data_root / "bin" / "pc-runtime"
    filenames = {p.name for p in bin_dir.iterdir()}
    assert filenames == {
        "node.exe",
        "ffmpeg.exe",
        "ffprobe.exe",
        "LICENSE_node.txt",
        "LICENSE_ffmpeg.txt",
        "manifest.json"
    }

    # 6. Verify reuse: second prepare() call must NOT re-download
    res2 = mr.prepare(consent=True)
    assert res2["ok"] is True
    assert download_counts["node"] == 1
    assert download_counts["ffmpeg"] == 1

    # 7. Tampering detection: if binary is altered, tool() must return None and status not ready
    Path(node_path).write_bytes(b"TAMPERED_MODIFIED_BINARY")
    assert mr.tool("node") is None
    assert mr.status()["ready"] is False
    assert mr.status()["node"] is False


def test_root_containment(tmp_path, sample_zips):
    """All generated files must remain strictly within data_root/bin/pc-runtime."""
    node_zip, ffmpeg_zip = sample_zips
    meta_path, _ = _build_test_metadata(tmp_path, node_zip, ffmpeg_zip)

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "node" in url:
            return MockHttpResponse(node_zip, url=url)
        return MockHttpResponse(ffmpeg_zip, url=url)

    data_root = tmp_path / "data"
    mr = MediaRuntime(data_root, meta_path, urlopen=mock_urlopen)
    mr.prepare(consent=True)

    # Check that nothing was written to parent directories of pc-runtime
    assert set(data_root.iterdir()) == {data_root / "bin"}
    assert set((data_root / "bin").iterdir()) == {data_root / "bin" / "pc-runtime"}


def test_wrap_command_and_exe_extension(tmp_path, sample_zips):
    """wrap_command replaces command names with absolute verified tool paths; tool() accepts .exe."""
    node_zip, ffmpeg_zip = sample_zips
    meta_path, _ = _build_test_metadata(tmp_path, node_zip, ffmpeg_zip)

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "node" in url:
            return MockHttpResponse(node_zip, url=url)
        return MockHttpResponse(ffmpeg_zip, url=url)

    data_root = tmp_path / "data"
    mr = MediaRuntime(data_root, meta_path, urlopen=mock_urlopen)
    mr.prepare(consent=True)

    # Both name forms work
    assert mr.tool("ffmpeg") is not None
    assert mr.tool("ffmpeg.exe") == mr.tool("ffmpeg")
    assert mr.tool("node.exe") == mr.tool("node")

    # wrap_command replaces tools with absolute path
    wrapped_ffmpeg = mr.wrap_command(["ffmpeg", "-y", "-i", "in.mp4", "out.mp4"])
    assert wrapped_ffmpeg[0] == mr.tool("ffmpeg")
    assert wrapped_ffmpeg[1:] == ["-y", "-i", "in.mp4", "out.mp4"]

    wrapped_node = mr.wrap_command(["node.exe", "script.js"])
    assert wrapped_node[0] == mr.tool("node")

    # Unrecognized commands are left untouched
    unrelated = ["git", "status"]
    assert mr.wrap_command(unrelated) == ["git", "status"]
    assert mr.wrap_command([]) == []


def test_default_metadata_loading(tmp_path):
    """MediaRuntime without explicit metadata_path loads packaged public_assets/media_runtime.json."""
    data_root = tmp_path / "data"
    mr = MediaRuntime(data_root)
    assert mr.metadata_path.is_file()
    status = mr.status()
    assert "ready" in status
    assert status["ready"] is False
    assert status["download_bytes"] > 0


def test_disallowed_host_rejected(tmp_path, sample_zips):
    """Download URLs targeting unlisted hosts must be rejected."""
    node_zip, ffmpeg_zip = sample_zips
    meta_path, meta = _build_test_metadata(tmp_path, node_zip, ffmpeg_zip)

    # Set disallowed host
    meta["packages"]["node"]["url"] = "https://evil-untrusted-site.com/node.zip"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def mock_urlopen(req, *args, **kwargs):
        raise AssertionError("Disallowed host reached!")

    data_root = tmp_path / "data"
    mr = MediaRuntime(data_root, meta_path, urlopen=mock_urlopen)
    res = mr.prepare(consent=True)

    assert res["ok"] is False
    assert "allowlist" in res["reason"].lower() or "host" in res["reason"].lower()


def test_disallowed_redirect_rejected(tmp_path, sample_zips):
    """HTTP redirects pointing to disallowed hosts must be rejected."""
    node_zip, ffmpeg_zip = sample_zips
    meta_path, _ = _build_test_metadata(tmp_path, node_zip, ffmpeg_zip)

    def mock_urlopen(req, *args, **kwargs):
        # Redirect to untrusted external host
        return MockHttpResponse(node_zip, url="https://malicious-redirect.com/node.zip")

    data_root = tmp_path / "data"
    mr = MediaRuntime(data_root, meta_path, urlopen=mock_urlopen)
    res = mr.prepare(consent=True)

    assert res["ok"] is False
    assert "redirect" in res["reason"].lower() or "untrusted" in res["reason"].lower()

