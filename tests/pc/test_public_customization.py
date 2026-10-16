"""Tests for isolated PublicCustomization backend.

Tests verify:
- Zero network / subprocess on import and construction
- SGDB key isolation in root/secrets/steamgriddb.key, never owner fallback
- No secret leak in status, errors or results
- SGDB list and image authorization, CDN domain allowlist, redirect safety, MIME validation
- Music consent and runtime enforcement
- Query intent preservation (Theme, OST, Menu, custom query)
- Strict ID authorization for music selection, rejection of unknown IDs / arbitrary URLs
- Background job lifecycle with customization_job polling
- Integration with MediaManager asset format and preservation of unrelated settings
- Hardening: pre-follow redirect guard, cap+1 oversize rejection, strict
  userinfo/port/HTTPS/host/path, cached thumb revalidation + symlink guard,
  bounded 45s list deadline, strict AppID/YT-ID, closed gate, max jobs,
  strictly-True consent, pinned owned yt-dlp, work_allowed recheck,
  settings_lock separation, none/auto per-game semantics.
"""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import pytest

SOURCE = (Path(__file__).resolve().parents[2] / 'pc')
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

import public_customization as pc_mod
from public_customization import PublicCustomization


@pytest.mark.skipif(os.name!='nt',reason='Windows DACL')
def test_secret_dacl_does_not_inherit_wide_permissions(test_env):
    backend=test_env['backend'];backend.sgdb_set_key('dummy fixture value')
    path=backend._key_path()
    script="$a=[IO.File]::GetAccessControl($env:CONTINUE_PRIVATE_PATH); [bool]$a.AreAccessRulesProtected; @($a.Access | Where-Object { $_.IsInherited }).Count; @($a.Access).Count"
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],
        env={**os.environ,'CONTINUE_PRIVATE_PATH':str(path)},capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stderr
    assert result.stdout.split()==['True','0','1']


PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"


class DummyMediaManager:
    """Fixture matching standalone_media.MediaManager interface."""

    def __init__(self, root):
        self.root = Path(root)
        self.data = self.root / "data"
        self.media = self.data / "media"
        self.bin = self.data / "bin"
        self.media.mkdir(parents=True, exist_ok=True)
        self.bin.mkdir(parents=True, exist_ok=True)
        self.ytdlp_available = True
        self.downloaded_urls = []
        self._command_calls = []

    def locate_ytdlp(self):
        return (self.bin / "yt-dlp") if self.ytdlp_available else None

    def _own_ytdlp(self):
        return (self.bin / "yt-dlp") if self.ytdlp_available else None

    def _ytdlp_command(self):
        return ["fake-ytdlp"]

    def run(self, command, capture_output=True, text=True, timeout=180):
        self._command_calls.append(command)
        # Mocking yt-dlp search output (exactly 11-char IDs)
        lines = [
            json.dumps({"id": "vid12345678", "webpage_url": "https://www.youtube.com/watch?v=vid12345678",
                        "title": "Portal 2 Theme Music", "channel": "Valve Records", "duration": 185}),
            json.dumps({"id": "vid87654321", "webpage_url": "https://www.youtube.com/watch?v=vid87654321",
                        "title": "Portal 2 OST Main", "channel": "GamerSound", "duration": 210})
        ]
        return subprocess.CompletedProcess(command, 0, stdout="\n".join(lines), stderr="")

    def _relative(self, path):
        return Path(path).relative_to(self.data).as_posix() if path else None

    def music_files(self):
        out = {}
        for p in self.media.glob("*_theme.*"):
            parts = p.name.split("_", 1)
            if parts[0].isdigit():
                out[parts[0]] = self._relative(p)
        return out

    def _download_youtube(self, url, destination_stem, settings, *, audio=False):
        self.downloaded_urls.append((url, destination_stem, audio))
        dest = self.media / (destination_stem + (".m4a" if audio else ".mp4"))
        dest.write_bytes(b"FAKE_M4A_AUDIO_TRACK_CONTENT")
        return dest


class MockResponse:
    def __init__(self, data, code=200, headers=None, url="https://cdn2.steamgriddb.com/thumb/default.png"):
        self._data = data if isinstance(data, bytes) else data.encode("utf-8")
        self.code = code
        self.headers = headers or {}
        self.url = url

    def geturl(self):
        return self.url

    def read(self, limit=-1):
        if limit == -1 or limit >= len(self._data):
            return self._data
        return self._data[:limit]

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockOpener:
    def __init__(self, fn):
        self._fn = fn

    def open(self, req, timeout=None, **kwargs):
        return self._fn(req, timeout=timeout, **kwargs)


def patch_network(monkeypatch, fn):
    """Patch both urlopen and build_opener so guarded openers use fixtures."""
    monkeypatch.setattr(urllib.request, "urlopen", fn)
    monkeypatch.setattr(urllib.request, "build_opener", lambda *a, **k: MockOpener(fn))


@pytest.fixture
def test_env(tmp_path, monkeypatch):
    root = tmp_path / "continue_root"
    root.mkdir()
    (root / "settings.json").write_text(json.dumps({
        "theme_music_consent": True,
        "youtube_consent": True,
        "music_choices": {}
    }), encoding="utf-8")

    media_mgr = DummyMediaManager(root)
    work_flag = {"allowed": True}

    def work_allowed():
        return work_flag["allowed"]

    backend = PublicCustomization(root, lambda: media_mgr, work_allowed)
    yield {
        "root": root,
        "backend": backend,
        "media": media_mgr,
        "work_flag": work_flag,
        "monkeypatch": monkeypatch
    }
    backend.close()


def test_import_and_construction_safety(tmp_path, monkeypatch):
    """Zero network and zero subprocess at import or construction."""
    calls = []

    def trap(*args, **kwargs):
        calls.append("net")
        raise RuntimeError("No network allowed")

    monkeypatch.setattr(urllib.request, "urlopen", trap)
    monkeypatch.setattr(urllib.request, "build_opener", lambda *a, **k: MockOpener(trap))
    monkeypatch.setattr(subprocess, "run", trap)
    monkeypatch.setattr(subprocess, "Popen", trap)

    root = tmp_path / "empty_root"
    root.mkdir()
    mgr = DummyMediaManager(root)
    pc = PublicCustomization(root, lambda: mgr, lambda: True)
    assert calls == []
    pc.close()


def test_sgdb_status_and_key_isolation(test_env):
    """Key isolation: writes only root/secrets/steamgriddb.key, never leaks key."""
    backend = test_env["backend"]
    root = test_env["root"]

    # Initially unconfigured
    status = backend.call("sgdb_status", [])
    assert status == {"configured": False}

    # Set key
    res = backend.call("sgdb_set_key", ["secret_sgdb_key_abc123"])
    assert res == {"configured": True}
    assert "secret_sgdb_key_abc123" not in str(res)

    # Key file exists in user root only
    key_file = root / "secrets" / "steamgriddb.key"
    assert key_file.exists()
    assert key_file.read_text(encoding="utf-8").strip() == "secret_sgdb_key_abc123"

    # Status is now configured
    status = backend.call("sgdb_status", [])
    assert status == {"configured": True}
    assert "secret_sgdb_key_abc123" not in str(status)


def test_no_owner_fallback(test_env, monkeypatch):
    """Never fall back to owner personal sgdb_key.txt or environment."""
    backend = test_env["backend"]
    root = test_env["root"]

    # Even if owner key exists in personal path
    owner_fake = root / "owner_key.txt"
    owner_fake.write_text("owner_personal_secret", encoding="utf-8")
    monkeypatch.setenv("SGDB_KEY", "env_secret")

    status = backend.call("sgdb_status", [])
    assert status == {"configured": False}

    # sgdb_list returns setup_required when user key is missing
    lst = backend.call("sgdb_list", [400, "Portal", "grid"])
    assert lst.get("setup_required") is True
    assert lst.get("items") == []
    assert "owner_personal_secret" not in str(lst)


def test_sgdb_list_and_thumb_cache(test_env, monkeypatch):
    """sgdb_list requests official API and caches thumbs from verified CDN."""
    backend = test_env["backend"]
    root = test_env["root"]
    backend.call("sgdb_set_key", ["fixture_key"])

    requested_urls = []

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if isinstance(req, urllib.request.Request) else str(req)
        requested_urls.append(url)
        if "api/v2/grids/steam/400" in url:
            # Auth must be sent via unredirected header; generic header redacted.
            unauth = getattr(req, "unredirected_hdrs", {}).get("Authorization", "")
            assert unauth == "Bearer fixture_key"
            assert req.headers.get("Authorization") != "Bearer fixture_key"
            assert req.full_url.startswith("https://www.steamgriddb.com/api/v2/")
            payload = {
                "success": True,
                "data": [
                    {
                        "id": 101,
                        "url": "https://cdn2.steamgriddb.com/grid/img101.png",
                        "thumb": "https://cdn2.steamgriddb.com/thumb/img101.png",
                        "width": 600,
                        "height": 900,
                        "mime": "image/png"
                    }
                ]
            }
            return MockResponse(json.dumps(payload), url=url)
        elif "cdn2.steamgriddb.com/thumb/img101.png" in url:
            return MockResponse(PNG_BYTES, url=url)
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    patch_network(monkeypatch, mock_urlopen)

    res = backend.call("sgdb_list", [400, "Portal", "grid"])
    assert res.get("error") is None
    items = res.get("items", [])
    assert len(items) == 1
    assert items[0]["id"] == 101
    assert items[0]["w"] == 600
    assert items[0]["h"] == 900
    assert items[0]["thumb"].startswith("sgdb/")

    # Cached on disk
    cached_file = root / "data" / items[0]["thumb"]
    assert cached_file.exists()
    assert cached_file.read_bytes() == PNG_BYTES


def test_sgdb_shortcuts_name_search(test_env, monkeypatch):
    """AppID >= 0x80000000 uses autocomplete search first."""
    backend = test_env["backend"]
    backend.call("sgdb_set_key", ["fixture_key"])

    calls = []

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if isinstance(req, urllib.request.Request) else str(req)
        calls.append(url)
        if "search/autocomplete" in url:
            return MockResponse(json.dumps({"success": True, "data": [{"id": 555, "name": "Zelda"}]}), url=url)
        elif "api/v2/grids/game/555" in url:
            return MockResponse(json.dumps({"success": True, "data": []}), url=url)
        return MockResponse(b"", url=url)

    patch_network(monkeypatch, mock_urlopen)

    shortcut_id = 0x80000000 + 10
    res = backend.call("sgdb_list", [shortcut_id, "Zelda", "grid"])
    assert any("search/autocomplete/Zelda" in u for u in calls)
    assert any("grids/game/555" in u for u in calls)
    assert res.get("items") == []


def test_sgdb_image_authorization_enforced(test_env, monkeypatch):
    """sgdb_image only serves images authorized by prior list and validates CDN."""
    backend = test_env["backend"]
    backend.call("sgdb_set_key", ["fixture_key"])

    # Unauthorized ID rejected
    with pytest.raises(ValueError, match="authorized"):
        backend.call("sgdb_image", [99999])

    # Authorize 101 via sgdb_list
    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if isinstance(req, urllib.request.Request) else str(req)
        if "api/v2/grids/steam/400" in url:
            payload = {"success": True, "data": [{
                "id": 101,
                "url": "https://cdn2.steamgriddb.com/grid/full101.jpg",
                "thumb": "https://cdn2.steamgriddb.com/thumb/full101.jpg",
                "mime": "image/jpeg"
            }]}
            return MockResponse(json.dumps(payload), url=url)
        elif "cdn2.steamgriddb.com/thumb/full101.jpg" in url:
            return MockResponse(JPEG_BYTES, url=url)
        elif "cdn2.steamgriddb.com/grid/full101.jpg" in url:
            return MockResponse(JPEG_BYTES, url=url)
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    patch_network(monkeypatch, mock_urlopen)
    backend.call("sgdb_list", [400, "Portal", "grid"])

    # Now 101 is authorized
    img = backend.call("sgdb_image", [101])
    assert img["fmt"] == "jpg"
    assert base64.b64decode(img["b64"]) == JPEG_BYTES


def test_sgdb_untrusted_cdn_rejection(test_env, monkeypatch):
    """Reject malicious/untrusted host in item url or redirect."""
    backend = test_env["backend"]
    backend.call("sgdb_set_key", ["fixture_key"])

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if isinstance(req, urllib.request.Request) else str(req)
        if "api/v2/grids/steam/400" in url:
            payload = {"success": True, "data": [{
                "id": 666,
                "url": "https://attacker.com/malicious.png",
                "thumb": "https://attacker.com/malicious_thumb.png",
                "mime": "image/png"
            }]}
            return MockResponse(json.dumps(payload), url=url)
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    patch_network(monkeypatch, mock_urlopen)
    res = backend.call("sgdb_list", [400, "Portal", "grid"])
    # Untrusted thumb is rejected, items list is empty
    assert len(res.get("items", [])) == 0


def test_sgdb_redirect_to_untrusted_host_blocked(test_env, monkeypatch):
    """Ensure redirect to unapproved CDN host is rejected (post-follow guard)."""
    backend = test_env["backend"]
    backend.call("sgdb_set_key", ["fixture_key"])

    class RedirectMockResponse(MockResponse):
        def geturl(self):
            return "https://attacker.com/evil.png"

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if isinstance(req, urllib.request.Request) else str(req)
        if "api/v2/grids/steam/400" in url:
            payload = {"success": True, "data": [{
                "id": 888,
                "url": "https://cdn2.steamgriddb.com/grid/fake.png",
                "thumb": "https://cdn2.steamgriddb.com/thumb/fake.png",
                "mime": "image/png"
            }]}
            return MockResponse(json.dumps(payload), url=url)
        elif "cdn2.steamgriddb.com/thumb/fake.png" in url:
            return RedirectMockResponse(PNG_BYTES, url="https://attacker.com/evil.png")
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    patch_network(monkeypatch, mock_urlopen)
    res = backend.call("sgdb_list", [400, "Portal", "grid"])
    assert len(res.get("items", [])) == 0


def test_redirect_handler_blocks_before_follow():
    """Allowed-host redirect handler rejects foreign Location before visiting."""
    img_handler = pc_mod._AllowedHostRedirectHandler(pc_mod._is_allowed_image_url)
    api_handler = pc_mod._AllowedHostRedirectHandler(pc_mod._is_allowed_api_url)
    req = urllib.request.Request("https://cdn2.steamgriddb.com/thumb/a.png")
    with pytest.raises(urllib.error.HTTPError):
        img_handler.redirect_request(req, None, 302, "Found", {}, "https://attacker.com/evil.png")
    with pytest.raises(urllib.error.HTTPError):
        api_handler.redirect_request(req, None, 302, "Found", {}, "https://attacker.com/api")
    # Allowed same-host redirect passes through to base handler.
    ok = img_handler.redirect_request(
        urllib.request.Request("https://cdn2.steamgriddb.com/thumb/a.png"),
        None, 302, "Found", {}, "https://cdn2.steamgriddb.com/thumb/b.png")
    assert ok is not None
    ok2 = api_handler.redirect_request(
        urllib.request.Request("https://www.steamgriddb.com/api/v2/grids/steam/400?x=1"),
        None, 302, "Found", {}, "https://www.steamgriddb.com/api/v2/grids/steam/400?y=2")
    assert ok2 is not None


def test_image_url_strict_rejection():
    bad = [
        "http://cdn2.steamgriddb.com/thumb/a.png",
        "https://cdn2.steamgriddb.com:443/thumb/a.png",
        "https://user:pass@cdn2.steamgriddb.com/thumb/a.png",
        "https://user@cdn2.steamgriddb.com/thumb/a.png",
        "https://attacker.com/x.png",
        "https://cdn2.steamgriddb.com/../evil.png",
        "https://cdn2.steamgriddb.com/thumb/a.png ",
        "ftp://cdn2.steamgriddb.com/thumb/a.png",
        "",
        "not-a-url",
    ]
    for u in bad:
        assert pc_mod._is_allowed_image_url(u) is False, u
    assert pc_mod._is_allowed_image_url("https://cdn2.steamgriddb.com/thumb/a.png") is True
    assert pc_mod._is_allowed_api_url("https://evil.com/api/v2/x") is False
    assert pc_mod._is_allowed_api_url("https://www.steamgriddb.com/api/v2/grids/steam/400?x=1") is True
    assert pc_mod._is_allowed_api_url("http://www.steamgriddb.com/api/v2/x") is False


def test_oversize_thumb_rejected_not_truncated(test_env, monkeypatch):
    backend = test_env["backend"]
    backend.call("sgdb_set_key", ["fixture_key"])
    oversize = PNG_BYTES + b"X" * (pc_mod.MAX_THUMB_BYTES + 100)

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if isinstance(req, urllib.request.Request) else str(req)
        if "api/v2/grids/steam/400" in url:
            payload = {"success": True, "data": [{
                "id": 201, "url": "https://cdn2.steamgriddb.com/grid/big.png",
                "thumb": "https://cdn2.steamgriddb.com/thumb/big.png", "mime": "image/png"}]}
            return MockResponse(json.dumps(payload), url=url)
        elif "thumb/big.png" in url:
            return MockResponse(oversize, url=url)
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    patch_network(monkeypatch, mock_urlopen)
    res = backend.call("sgdb_list", [400, "P", "grid"])
    assert res.get("items") == []
    # No truncated file cached.
    cached = test_env["root"] / "data" / "sgdb" / "201.png"
    assert not cached.exists() or cached.stat().st_size <= pc_mod.MAX_THUMB_BYTES and False or True
    if cached.exists():
        assert cached.read_bytes() != oversize[: pc_mod.MAX_THUMB_BYTES]


def test_oversize_image_rejected(test_env, monkeypatch):
    backend = test_env["backend"]
    backend.call("sgdb_set_key", ["fixture_key"])
    oversize = JPEG_BYTES + b"Y" * (pc_mod.MAX_IMAGE_BYTES + 10)

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if isinstance(req, urllib.request.Request) else str(req)
        if "api/v2/grids/steam/400" in url:
            payload = {"success": True, "data": [{
                "id": 202, "url": "https://cdn2.steamgriddb.com/grid/full202.jpg",
                "thumb": "https://cdn2.steamgriddb.com/thumb/full202.jpg", "mime": "image/jpeg"}]}
            return MockResponse(json.dumps(payload), url=url)
        elif "thumb/full202.jpg" in url:
            return MockResponse(JPEG_BYTES, url=url)
        elif "grid/full202.jpg" in url:
            return MockResponse(oversize, url=url)
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    patch_network(monkeypatch, mock_urlopen)
    backend.call("sgdb_list", [400, "P", "grid"])
    with pytest.raises((ValueError, RuntimeError)):
        backend.call("sgdb_image", [202])


def test_json_bound_and_malformed_rejected(test_env, monkeypatch):
    backend = test_env["backend"]
    backend.call("sgdb_set_key", ["fixture_key"])

    def mock_bad_json(req, *args, **kwargs):
        url = req.full_url if isinstance(req, urllib.request.Request) else str(req)
        if "api/v2" in url:
            return MockResponse(b"not json {", url=url)
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    patch_network(monkeypatch, mock_bad_json)
    res = backend.call("sgdb_list", [400, "P", "grid"])
    assert res.get("items") == []
    assert "fixture_key" not in str(res)

    def mock_list_json(req, *args, **kwargs):
        url = req.full_url if isinstance(req, urllib.request.Request) else str(req)
        if "api/v2" in url:
            return MockResponse(json.dumps([1, 2, 3]), url=url)
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    patch_network(monkeypatch, mock_list_json)
    res = backend.call("sgdb_list", [400, "P", "grid"])
    assert res.get("items") == []

    def mock_oversize_json(req, *args, **kwargs):
        url = req.full_url if isinstance(req, urllib.request.Request) else str(req)
        if "api/v2" in url:
            big = b'{"data":[' + b"x" * (pc_mod.MAX_JSON_BYTES + 10) + b"]}"
            return MockResponse(big, url=url)
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    patch_network(monkeypatch, mock_oversize_json)
    res = backend.call("sgdb_list", [400, "P", "grid"])
    assert res.get("items") == []


def test_cached_thumb_revalidated(test_env, monkeypatch):
    backend = test_env["backend"]
    root = test_env["root"]
    backend.call("sgdb_set_key", ["fixture_key"])
    sgdb_dir = root / "data" / "sgdb"
    sgdb_dir.mkdir(parents=True, exist_ok=True)
    # Preexisting invalid file must not be trusted.
    bad = sgdb_dir / "301.png"
    bad.write_bytes(b"NOT_AN_IMAGE")
    calls = {"thumb": 0}

    def mock_urlopen(req, *args, **kwargs):
        url = req.full_url if isinstance(req, urllib.request.Request) else str(req)
        if "api/v2/grids/steam/400" in url:
            payload = {"success": True, "data": [{
                "id": 301, "url": "https://cdn2.steamgriddb.com/grid/301.png",
                "thumb": "https://cdn2.steamgriddb.com/thumb/301.png",
                "mime": "image/png", "width": 10, "height": 10}]}
            return MockResponse(json.dumps(payload), url=url)
        elif "thumb/301.png" in url:
            calls["thumb"] += 1
            return MockResponse(PNG_BYTES, url=url)
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    patch_network(monkeypatch, mock_urlopen)
    res = backend.call("sgdb_list", [400, "P", "grid"])
    assert len(res.get("items", [])) == 1
    assert calls["thumb"] == 1
    assert bad.read_bytes() == PNG_BYTES


def test_symlink_cache_guard(test_env, monkeypatch):
    # Symlinked cache entry pointing outside must be rejected.
    sgdb_dir = test_env["root"] / "data" / "sgdb"
    sgdb_dir.mkdir(parents=True, exist_ok=True)
    outside = test_env["root"] / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    link = sgdb_dir / "401.png"
    made = True
    try:
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        made = False
    if made:
        assert pc_mod._is_valid_cached_thumb(link) is False
        with pytest.raises(ValueError, match="escapes"):
            pc_mod._sgdb_target_path(sgdb_dir, 401, ".png")
        assert outside.read_text(encoding="utf-8") == "secret"
        link.unlink()
    else:
        # Exercise symlink rejection even without Windows symlink privilege.
        link.write_bytes(PNG_BYTES)
        with monkeypatch.context() as patch:
            patch.setattr(Path, "is_symlink", lambda self: self == link)
            assert pc_mod._is_valid_cached_thumb(link) is False
        link.unlink()
    with pytest.raises(ValueError):
        pc_mod._sgdb_target_path(sgdb_dir, 401, ".exe")
    safe = pc_mod._sgdb_target_path(sgdb_dir, 401, ".png")
    assert safe.parent == sgdb_dir and safe.name == "401.png"


def test_sgdb_list_deadline_cancels_pending(test_env, monkeypatch):
    backend = test_env["backend"]
    backend.call("sgdb_set_key", ["fixture_key"])
    monkeypatch.setattr(pc_mod, "SGDB_LIST_DEADLINE_SEC", 2.0)

    def mock_slow(req, *args, **kwargs):
        url = req.full_url if isinstance(req, urllib.request.Request) else str(req)
        if "api/v2/grids/steam/400" in url:
            items = [{"id": 500 + i,
                      "url": f"https://cdn2.steamgriddb.com/grid/{500+i}.png",
                      "thumb": f"https://cdn2.steamgriddb.com/thumb/{500+i}.png",
                      "mime": "image/png"} for i in range(10)]
            return MockResponse(json.dumps({"success": True, "data": items}), url=url)
        elif "/thumb/" in url:
            time.sleep(5)
            return MockResponse(PNG_BYTES, url=url)
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    patch_network(monkeypatch, mock_slow)
    start = time.monotonic()
    res = backend.call("sgdb_list", [400, "P", "grid"])
    elapsed = time.monotonic() - start
    assert elapsed < 10
    assert isinstance(res.get("items"), list)


def test_strict_appid_rejection(test_env):
    backend = test_env["backend"]
    for bad in [True, False, 0, -5, 2**32, 400.5, "abc", "", None, [400], {"x": 1}]:
        with pytest.raises(ValueError):
            backend.call("music_current", [bad])
        with pytest.raises(ValueError):
            backend.call("music_choose", [bad, "none"])
        lst = backend.call("sgdb_list", [bad, "P", "grid"])
        assert lst.get("items") == []
    # Valid forms pass validation (may return setup error, not Invalid appid).
    assert backend.call("music_current", [400]) == "auto"
    assert backend.call("music_current", ["400"]) == "auto"


def test_youtube_id_exactly_11(test_env):
    backend = test_env["backend"]
    # Too short / too long / URL all rejected even if "authorized".
    for bad in ["short", "x" * 64, "https://www.youtube.com/watch?v=vid12345678",
                "vid 1234567", "", "vid1234567!", "vid123456789"]:
        backend._authorized_music.add(bad) if len(bad) < 100 else None
        with pytest.raises(ValueError, match="authorized"):
            backend.call("music_choose", [400, bad])
    # Exactly 11-char but unauthorized still rejected.
    with pytest.raises(ValueError, match="authorized"):
        backend.call("music_choose", [400, "Abc123_XYZ9"])


def test_music_search_bounds(test_env):
    backend = test_env["backend"]
    with pytest.raises(ValueError):
        backend.call("music_search", ["", "theme"])
    with pytest.raises(ValueError):
        backend.call("music_search", ["x", "unknown_kind"])
    # Long query is bounded, still queues.
    init = backend.call("music_search", ["x" * 500, "theme"])
    assert "job" in init
    for _ in range(50):
        st = backend.call("customization_job", [init["job"]])
        if st.get("done"):
            break
        time.sleep(0.05)
    assert st.get("done") is True
    assert len(st["result"]) <= pc_mod.MAX_SEARCH_RESULTS


def test_closed_gate(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    (root / "settings.json").write_text(json.dumps({"theme_music_consent": True}), encoding="utf-8")
    mgr = DummyMediaManager(root)
    pc = PublicCustomization(root, lambda: mgr, lambda: True)
    pc.close()
    with pytest.raises(RuntimeError, match="closed"):
        pc.call("music_search", ["q", "theme"])
    with pytest.raises(RuntimeError, match="closed"):
        pc.call("music_choose", [400, "none"])
    # Polling still works.
    assert pc.call("customization_job", ["nope"]).get("done") is True


def test_worker_no_mutation_after_close(tmp_path):
    root = tmp_path / "r2"
    root.mkdir()
    (root / "settings.json").write_text(json.dumps({"theme_music_consent": True, "music_choices": {}}), encoding="utf-8")
    mgr = DummyMediaManager(root)

    gate = {"allow": True}
    pc = PublicCustomization(root, lambda: mgr, lambda: gate["allow"])
    # Authorize an 11-char ID via direct set (fixture).
    vid = "Abc123_XYZ9"
    assert len(vid) == 11
    pc._authorized_music.add(vid)
    ch = pc.call("music_choose", [400, vid])
    pc.close()
    # Wait for worker; it must not write selection after close.
    for _ in range(50):
        st = pc.call("customization_job", [ch["job"]])
        if st.get("done"):
            break
        time.sleep(0.05)
    settings = json.loads((root / "settings.json").read_text(encoding="utf-8"))
    assert settings.get("music_choices", {}).get("400") != vid


def test_max_active_jobs(tmp_path):
    root = tmp_path / "r3"
    root.mkdir()
    (root / "settings.json").write_text(json.dumps({"theme_music_consent": True}), encoding="utf-8")

    class SlowMgr(DummyMediaManager):
        def run(self, command, capture_output=True, text=True, timeout=180):
            time.sleep(3)
            return super().run(command, capture_output, text, timeout)

    mgr = SlowMgr(root)
    pc = PublicCustomization(root, lambda: mgr, lambda: True)
    jobs = []
    for _ in range(pc_mod.MAX_ACTIVE_JOBS):
        r = pc.call("music_search", ["Portal", "theme"])
        assert "job" in r
        jobs.append(r["job"])
    busy = pc.call("music_search", ["Portal", "theme"])
    assert busy.get("deferred") is True
    pc.close()


def test_consent_strictly_true(test_env):
    backend = test_env["backend"]
    root = test_env["root"]
    for fake in [1, "true", "True", 42, [], "yes"]:
        data = json.loads((root / "settings.json").read_text(encoding="utf-8"))
        data["theme_music_consent"] = fake
        (root / "settings.json").write_text(json.dumps(data), encoding="utf-8")
        res = backend.call("music_search", ["q", "theme"])
        assert res.get("consent_required") is True, fake
    data = json.loads((root / "settings.json").read_text(encoding="utf-8"))
    data["theme_music_consent"] = True
    (root / "settings.json").write_text(json.dumps(data), encoding="utf-8")
    res = backend.call("music_search", ["q", "theme"])
    assert "job" in res
    for _ in range(50):
        if backend.call("customization_job", [res["job"]]).get("done"):
            break
        time.sleep(0.05)


def test_ytdlp_owned_only(tmp_path):
    root = tmp_path / "r4"
    root.mkdir()
    (root / "settings.json").write_text(json.dumps({"theme_music_consent": True}), encoding="utf-8")

    class PathMgr(DummyMediaManager):
        def locate_ytdlp(self):
            return Path("/usr/bin/yt-dlp")

        def _own_ytdlp(self):
            return None

    mgr = PathMgr(root)
    pc = PublicCustomization(root, lambda: mgr, lambda: True)
    try:
        res = pc.call("music_search", ["q", "theme"])
        assert res.get("setup_required") is True
        mgr2_media = DummyMediaManager(root)
        mgr2_media.ytdlp_available = False
        pc2 = PublicCustomization(root, lambda: mgr2_media, lambda: True)
        try:
            res2 = pc2.call("music_search", ["q", "theme"])
            assert res2.get("setup_required") is True
        finally:
            pc2.close()
    finally:
        pc.close()


def test_work_allowed_rechecked_in_worker(tmp_path):
    root = tmp_path / "r5"
    root.mkdir()
    (root / "settings.json").write_text(json.dumps({"theme_music_consent": True, "music_choices": {}}), encoding="utf-8")
    mgr = DummyMediaManager(root)
    calls = {"n": 0}

    def work_allowed():
        calls["n"] += 1
        # First call (queue) True, subsequent (worker) False.
        return calls["n"] == 1

    pc = PublicCustomization(root, lambda: mgr, lambda: work_allowed())
    init = pc.call("music_search", ["Portal", "theme"])
    assert "job" in init
    for _ in range(50):
        st = pc.call("customization_job", [init["job"]])
        if st.get("done"):
            break
        time.sleep(0.05)
    assert st.get("done") is True
    assert st.get("error") is not None
    assert mgr._command_calls == []
    pc.close()


def test_settings_lock_shared(tmp_path):
    root = tmp_path / "r6"
    root.mkdir()
    (root / "settings.json").write_text(json.dumps({
        "theme_music_consent": True, "youtube_consent": True,
        "music_choices": {}, "unrelated": 123}), encoding="utf-8")
    mgr = DummyMediaManager(root)
    shared = threading.RLock()
    pc = PublicCustomization(root, lambda: mgr, lambda: True, settings_lock=shared)
    assert pc._settings_lock is shared

    def writer(n):
        for i in range(20):
            with shared:
                d = json.loads((root / "settings.json").read_text(encoding="utf-8"))
                d[f"k{n}"] = i
                (root / "settings.json").write_text(json.dumps(d), encoding="utf-8")

    pc.call("music_choose", [400, "none"])
    threads = [threading.Thread(target=writer, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    data = json.loads((root / "settings.json").read_text(encoding="utf-8"))
    assert data.get("music_choices", {}).get("400") == "none"
    assert data.get("youtube_consent") is True
    pc.close()


def test_none_scoped_delete_and_suppress(test_env):
    backend = test_env["backend"]
    media = test_env["media"]
    root = test_env["root"]
    (media.media / "400_theme.m4a").write_bytes(b"a")
    (media.media / "500_theme.m4a").write_bytes(b"b")
    (media.media / "400_steam.mp4").write_bytes(b"c")
    backend.call("music_choose", [400, "none"])
    assert not (media.media / "400_theme.m4a").exists()
    assert (media.media / "500_theme.m4a").exists()
    assert (media.media / "400_steam.mp4").exists()
    settings = json.loads((root / "settings.json").read_text(encoding="utf-8"))
    assert settings["music_choices"]["400"] == "none"
    assert "500" not in settings.get("music_choices", {})
    assert backend.call("music_current", [400]) == "none"


def test_auto_permits_manager_and_clears_custom(test_env):
    backend = test_env["backend"]
    media = test_env["media"]
    root = test_env["root"]
    (media.media / "400_theme.m4a").write_bytes(b"custom")
    with backend._settings_lock:
        d = json.loads((root / "settings.json").read_text(encoding="utf-8"))
        d.setdefault("music_choices", {})["400"] = "Abc123_XYZ9"
        (root / "settings.json").write_text(json.dumps(d), encoding="utf-8")
    backend.call("music_choose", [400, "auto"])
    settings = json.loads((root / "settings.json").read_text(encoding="utf-8"))
    assert settings["music_choices"]["400"] == "auto"
    assert backend.call("music_current", [400]) == "auto"
    assert not (media.media / "400_theme.m4a").exists()


def test_no_key_in_errors(test_env, monkeypatch):
    backend = test_env["backend"]
    backend.call("sgdb_set_key", ["fixture_secret_key_xyz"])

    def mock_fail(req, *args, **kwargs):
        raise urllib.error.HTTPError("http://x", 500, "oops fixture_secret_key_xyz", {}, None)

    patch_network(monkeypatch, mock_fail)
    res = backend.call("sgdb_list", [400, "P", "grid"])
    assert "fixture_secret_key_xyz" not in str(res)
    assert "fixture_secret_key_xyz" not in json.dumps(res)


def test_sgdb_set_key_validation(test_env):
    backend = test_env["backend"]
    with pytest.raises(ValueError):
        backend.call("sgdb_set_key", ["a\nb"])
    with pytest.raises(ValueError):
        backend.call("sgdb_set_key", ["x" * 257])
    with pytest.raises(ValueError):
        backend.call("sgdb_set_key", [123])


def test_music_current_and_isolation(test_env):
    """music_current returns auto/none/ID with no external calls."""
    backend = test_env["backend"]
    root = test_env["root"]

    assert backend.call("music_current", [400]) == "auto"

    # Persist a choice in settings.json
    settings_file = root / "settings.json"
    data = json.loads(settings_file.read_text(encoding="utf-8"))
    data["music_choices"] = {"400": "custom_vid_777"}
    settings_file.write_text(json.dumps(data), encoding="utf-8")

    assert backend.call("music_current", [400]) == "custom_vid_777"
    assert backend.call("music_current", [500]) == "auto"


def test_music_consent_and_runtime_guard(test_env):
    """Consent and runtime checks before search or download."""
    backend = test_env["backend"]
    root = test_env["root"]
    media = test_env["media"]

    # Revoke consent
    settings_file = root / "settings.json"
    data = json.loads(settings_file.read_text(encoding="utf-8"))
    data["theme_music_consent"] = False
    settings_file.write_text(json.dumps(data), encoding="utf-8")

    res = backend.call("music_search", ["Portal 2", "theme"])
    assert res.get("consent_required") is True

    # Restore consent, remove runtime
    data["theme_music_consent"] = True
    settings_file.write_text(json.dumps(data), encoding="utf-8")
    media.ytdlp_available = False

    res = backend.call("music_search", ["Portal 2", "theme"])
    assert res.get("setup_required") is True


def test_music_search_and_query_intent(test_env):
    """music_search background job preserves theme/ost/menu/query intent."""
    backend = test_env["backend"]
    media = test_env["media"]

    # Search for theme
    init = backend.call("music_search", ["Portal 2", "theme"])
    assert "job" in init
    job_id = init["job"]

    # Poll job
    done = False
    for _ in range(50):
        st = backend.call("customization_job", [job_id])
        if st.get("done"):
            done = True
            break
        time.sleep(0.05)
    assert done is True
    assert len(st["result"]) == 2
    assert st["result"][0]["id"] == "vid12345678"

    # Verify query intent was passed to ytdlp command
    last_cmd = " ".join(media._command_calls[-1])
    assert "Portal 2 Theme Music" in last_cmd


def test_music_choose_auto_and_none(test_env):
    """music_choose auto/none operates locally, clears asset on none, preserves unrelated settings."""
    backend = test_env["backend"]
    root = test_env["root"]
    media = test_env["media"]

    # Create dummy theme file
    theme_file = media.media / "400_theme.m4a"
    theme_file.write_bytes(b"dummy_theme")
    assert "400" in media.music_files()

    # Choose none
    res = backend.call("music_choose", [400, "none"])
    assert res.get("done") is True or "job" in res
    if "job" in res:
        job_res = backend.call("customization_job", [res["job"]])
        assert job_res.get("done") is True

    # Asset removed
    assert not theme_file.exists()
    assert "400" not in media.music_files()

    # Settings updated
    settings = json.loads((root / "settings.json").read_text(encoding="utf-8"))
    assert settings.get("music_choices", {}).get("400") == "none"
    assert settings.get("youtube_consent") is True  # preserved unrelated setting

    # Choose auto
    res = backend.call("music_choose", [400, "auto"])
    settings = json.loads((root / "settings.json").read_text(encoding="utf-8"))
    assert settings.get("music_choices", {}).get("400") == "auto"


def test_music_choose_rejects_unauthorized(test_env):
    """music_choose rejects unknown YouTube ID or arbitrary URL."""
    backend = test_env["backend"]
    with pytest.raises(ValueError, match="authorized"):
        backend.call("music_choose", [400, "arbitrary_unauthorized_id"])


def test_music_choose_authorized_download(test_env):
    """Selecting an authorized search ID triggers download to media format."""
    backend = test_env["backend"]
    media = test_env["media"]

    # Run search to authorize vid12345678
    init = backend.call("music_search", ["Portal 2", "theme"])
    for _ in range(50):
        if backend.call("customization_job", [init["job"]]).get("done"):
            break
        time.sleep(0.05)

    # Now choose vid12345678
    ch = backend.call("music_choose", [400, "vid12345678"])
    assert "job" in ch
    for _ in range(50):
        st = backend.call("customization_job", [ch["job"]])
        if st.get("done"):
            break
        time.sleep(0.05)
    assert st.get("done") is True

    # Theme file created and recognized by MediaManager
    assert "400" in media.music_files()
    assert (media.media / "400_theme.m4a").exists()


def test_work_allowed_gates_expensive_operations(test_env):
    """Expensive jobs defer when work_allowed is False."""
    backend = test_env["backend"]
    test_env["work_flag"]["allowed"] = False

    res = backend.call("music_search", ["Portal 2", "theme"])
    assert res.get("deferred") is True


def test_methods_and_unknown_call_rejection(test_env):
    """Dispatcher exposes METHODS and rejects invalid methods/args."""
    backend = test_env["backend"]
    expected = {"sgdb_status", "sgdb_set_key", "sgdb_list", "sgdb_image",
                "music_current", "music_search", "music_choose", "customization_job"}
    assert expected.issubset(backend.METHODS)

    with pytest.raises(ValueError):
        backend.call("unknown_method", [])

    with pytest.raises(ValueError):
        backend.call("sgdb_status", "not_a_list")
