"""Offline safety/ownership tests for the optional Deck media runtime."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import urllib.request

import pytest

MODULE = Path(__file__).resolve().parents[2] / "plugin/py_modules/deck_media_runtime.py"


def load_runtime():
    assert MODULE.is_file(), "Deck media runtime implementation is missing"
    spec = importlib.util.spec_from_file_location("deck_runtime_under_test", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def archive(entries):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:xz") as tf:
        for name, payload, kind in entries:
            info = tarfile.TarInfo(name)
            if kind == "file":
                info.size = len(payload)
                info.mode = 0o755
                tf.addfile(info, io.BytesIO(payload))
            elif kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = payload
                tf.addfile(info)
            elif kind == "hardlink":
                info.type = tarfile.LNKTYPE
                info.linkname = payload
                tf.addfile(info)
            elif kind == "fifo":
                info.type = tarfile.FIFOTYPE
                tf.addfile(info)
    return output.getvalue()


def normal_entries(package):
    tools = ["node"] if package == "node" else ["ffmpeg", "ffprobe"]
    return [(f"{package}/bin/{name}", ("tool:" + name).encode(), "file") for name in tools] + [
        (f"{package}/LICENSE", b"test license", "file")]


class Response(io.BytesIO):
    def __init__(self, body, url, declared=None):
        super().__init__(body)
        self.url = url
        self.declared = len(body) if declared is None else declared

    def getheader(self, name):
        return str(self.declared) if name.lower() == "content-length" else None


@pytest.fixture
def setup_runtime(tmp_path):
    def create(node_entries=None, ffmpeg_entries=None, mutate=None, allowed=None, response_url=None):
        bodies = {"node": archive(node_entries or normal_entries("node")),
                  "ffmpeg": archive(ffmpeg_entries or normal_entries("ffmpeg"))}
        metadata = {"schema_version": "1.0", "platform": "linux-x64",
                    "caps": {"max_decompressed_bytes": 1048576}, "packages": {}}
        for package, body in bodies.items():
            tools = {"node": "node"} if package == "node" else {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}
            metadata["packages"][package] = {
                "version": "fixture", "url": f"https://nodejs.org/{package}.tar.xz",
                "filename": f"{package}.tar.xz", "sha256": hashlib.sha256(body).hexdigest(),
                "size_bytes": len(body), "max_compressed_bytes": 1048576,
                "tools": tools, "license_file": "LICENSE", "target_license": f"LICENSE_{package}.txt"}
        if mutate:
            mutate(metadata)
        metadata_path = tmp_path / "metadata.json"
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
        calls = []

        def opener(req, **kwargs):
            url = req.full_url
            calls.append(url)
            package = "node" if url.endswith("/node.tar.xz") else "ffmpeg"
            return Response(bodies[package], response_url or url)

        runtime = load_runtime().MediaRuntime(tmp_path / "data", metadata_path, urlopen=opener, allowed=allowed)
        return runtime, calls, metadata, bodies
    return create


def test_import_constructor_and_no_consent_do_not_download_or_create_files(setup_runtime):
    runtime, calls, _, _ = setup_runtime()
    assert calls == []
    assert not runtime.data_root.exists()
    for consent in (False, None, 1, "yes"):
        result = runtime.prepare(consent=consent)
        assert result["consent_required"] is True
    assert calls == []
    assert not runtime.data_root.exists()


def test_installs_only_owned_tools_and_licenses_with_hashes(setup_runtime):
    runtime, calls, _, _ = setup_runtime()
    before_env = dict(os.environ)
    result = runtime.prepare(consent=True)
    assert result["ok"] is True, result
    assert runtime.status()["ready"] is True
    assert len(calls) == 2
    assert dict(os.environ) == before_env
    for name in ("node", "ffmpeg", "ffprobe"):
        path = Path(runtime.tool(name))
        assert path.is_absolute()
        assert path.is_relative_to(runtime.data_root / "bin/deck-runtime")
        assert path.read_bytes() == ("tool:" + name).encode()
        assert runtime.wrap_command([name, "--version"])[0] == str(path)
    files = [p.name for p in runtime.runtime_dir.rglob("*") if p.is_file()]
    assert sorted(files) == sorted(["manifest.json", "node", "ffmpeg", "ffprobe", "LICENSE_node.txt", "LICENSE_ffmpeg.txt"])


def test_verified_existing_install_does_not_redownload_and_tampering_is_detected(setup_runtime):
    runtime, calls, _, _ = setup_runtime()
    assert runtime.prepare(True)["ok"]
    assert runtime.prepare(True)["ok"]
    assert len(calls) == 2
    Path(runtime.tool("node")).write_bytes(b"TAMPERED")
    assert runtime.tool("node") is None
    assert runtime.status()["ready"] is False


def test_missing_or_tampered_license_prevents_ready(setup_runtime):
    runtime, _, _, _ = setup_runtime()
    assert runtime.prepare(True)["ok"]
    next(runtime.runtime_dir.rglob("LICENSE_node.txt")).write_bytes(b"tampered")
    assert runtime.status()["ready"] is False


@pytest.mark.parametrize("name", ["../escape", "/tmp/escape", "C:/escape", "node/../../escape", "node\\..\\escape"])
def test_rejects_hostile_archive_paths(setup_runtime, name):
    runtime, _, _, _ = setup_runtime(node_entries=normal_entries("node") + [(name, b"bad", "file")])
    result = runtime.prepare(True)
    assert result["ok"] is False
    assert runtime.tool("node") is None


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "fifo"])
def test_never_extracts_link_or_special_file_as_executable(setup_runtime, kind):
    entries = [("node/bin/node", "../payload" if kind != "fifo" else "", kind), ("node/LICENSE", b"license", "file")]
    runtime, _, _, _ = setup_runtime(node_entries=entries)
    result = runtime.prepare(True)
    assert result["ok"] is False
    assert runtime.tool("node") is None


def test_ignores_safe_unselected_links_present_in_official_node_tar(setup_runtime):
    runtime, _, _, _ = setup_runtime(node_entries=normal_entries("node") + [("node/bin/npm", "../lib/npm.js", "symlink")])
    assert runtime.prepare(True)["ok"]
    assert not list(runtime.runtime_dir.rglob("npm"))


def test_missing_and_duplicate_selected_files_are_rejected(setup_runtime):
    runtime, _, _, _ = setup_runtime(node_entries=[("node/LICENSE", b"license", "file")])
    assert runtime.prepare(True)["ok"] is False
    runtime, _, _, _ = setup_runtime(node_entries=normal_entries("node") + [("other/bin/node", b"fake", "file")])
    assert runtime.prepare(True)["ok"] is False


def test_archive_hash_mismatch_is_rejected(setup_runtime):
    runtime, _, _, _ = setup_runtime(mutate=lambda meta: meta["packages"]["node"].update(sha256="0" * 64))
    assert runtime.prepare(True)["ok"] is False
    assert runtime.tool("node") is None


def test_decompression_and_license_caps_are_enforced(setup_runtime):
    runtime, _, _, _ = setup_runtime(node_entries=normal_entries("node") + [("node/giant", b"0" * 1048577, "file")])
    assert runtime.prepare(True)["ok"] is False
    runtime, _, _, _ = setup_runtime(node_entries=[("node/bin/node", b"node", "file"), ("node/LICENSE", b"0" * (2 * 1048576 + 1), "file")],
                                    mutate=lambda meta: meta["caps"].update(max_decompressed_bytes=4 * 1048576))
    assert runtime.prepare(True)["ok"] is False


@pytest.mark.parametrize("url", ["http://nodejs.org/node.tar.xz", "https://evil.test/node.tar.xz", "https://nodejs.org:444/node.tar.xz", "https://user:pw@nodejs.org/node.tar.xz"])
def test_only_official_https_initial_urls_are_allowed(setup_runtime, url):
    runtime, calls, _, _ = setup_runtime(mutate=lambda meta: meta["packages"]["node"].update(url=url))
    assert runtime.prepare(True)["ok"] is False
    assert calls == []


def test_injected_client_untrusted_redirect_response_is_rejected(setup_runtime):
    runtime, _, _, _ = setup_runtime(response_url="https://evil.test/runtime.tar.xz")
    assert runtime.prepare(True)["ok"] is False


def test_real_redirect_handler_rejects_before_following():
    mod = load_runtime()
    handler = mod.RuntimeRedirectHandler({"nodejs.org"})
    req = urllib.request.Request("https://nodejs.org/archive")
    with pytest.raises(ValueError):
        handler.redirect_request(req, None, 302, "Found", {}, "https://evil.test/archive")


def test_cancel_before_download_leaves_no_runtime(setup_runtime):
    runtime, calls, _, _ = setup_runtime(allowed=lambda: False)
    assert runtime.prepare(True)["ok"] is False
    assert calls == []
    assert runtime.tool("node") is None


def test_failed_setup_keeps_prior_verified_install(setup_runtime):
    runtime, _, _, _ = setup_runtime()
    assert runtime.prepare(True)["ok"]
    old_node = runtime.tool("node")
    old_manifest = runtime.manifest_path.read_bytes()
    runtime._meta = None
    metadata = json.loads(runtime.metadata_path.read_text())
    metadata["packages"]["ffmpeg"]["sha256"] = "1" * 64
    runtime.metadata_path.write_text(json.dumps(metadata))
    assert runtime.prepare(True)["ok"] is False
    assert runtime.manifest_path.read_bytes() == old_manifest
    assert Path(old_node).read_bytes() == b"tool:node"


@pytest.mark.parametrize("location", ["data", "bin", "runtime"])
def test_refuses_symlinked_root_or_parent_without_writing_outside(setup_runtime, tmp_path, location):
    runtime, calls, _, _ = setup_runtime()
    outside = tmp_path / "outside"
    outside.mkdir()
    target = {"data": runtime.data_root, "bin": runtime.data_root / "bin", "runtime": runtime.runtime_dir}[location]
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Creating directory symlinks needs OS privilege")
    assert runtime.prepare(True)["ok"] is False
    assert calls == []
    assert list(outside.iterdir()) == []


def test_trusted_root_may_have_symlinked_home(setup_runtime,tmp_path):
    from deck_media_runtime import MediaRuntime
    runtime,_,_,_=setup_runtime()
    physical=tmp_path/'physical-home';physical.mkdir()
    alias=tmp_path/'home'
    try:alias.symlink_to(physical,target_is_directory=True)
    except OSError:pytest.skip('symlink unavailable')
    linked=MediaRuntime(alias/'data',runtime.metadata_path)
    assert linked.data_root==physical/'data'
    assert linked._safe_path(linked.runtime_dir)
    (physical/'data').mkdir();outside=tmp_path/'outside';outside.mkdir()
    (physical/'data/bin').symlink_to(outside,target_is_directory=True)
    assert not linked._safe_path(linked.runtime_dir)


def test_rejects_escaping_manifest_tool_path(setup_runtime, tmp_path):
    runtime, _, _, _ = setup_runtime()
    assert runtime.prepare(True)["ok"]
    manifest = json.loads(runtime.manifest_path.read_text())
    manifest["tools"]["node"]["filename"] = "../../../../outside"
    runtime.manifest_path.write_text(json.dumps(manifest))
    assert runtime.tool("node") is None


def test_status_does_not_leak_user_paths(setup_runtime):
    runtime, calls, _, _ = setup_runtime()
    status = runtime.status()
    assert status["download_bytes"] > 0
    assert str(runtime.data_root) not in json.dumps(status)
    assert calls == []


def test_nested_node_dependency_licenses_are_not_selected_as_root_license(setup_runtime):
    runtime, calls, metadata, bodies = setup_runtime()
    # Real official Node archives contain many npm dependency LICENSE files.
    # The root license remains the only selected license.
    package=runtime._get_metadata()['packages']['node']
    payload=archive(normal_entries('node')+[('node/lib/node_modules/npm/LICENSE',b'npm license','file')])
    package['size_bytes']=len(payload);package['sha256']=hashlib.sha256(payload).hexdigest()
    bodies['node']=payload
    assert runtime.prepare(True)['ok']


def test_low_space_stops_before_download(setup_runtime,monkeypatch):
    runtime,calls,_,_=setup_runtime()
    import collections
    usage=collections.namedtuple('Usage','total used free')
    monkeypatch.setattr('shutil.disk_usage',lambda _p:usage(100,99,1))
    result=runtime.prepare(True)
    assert not result['ok'] and 'space' in result['reason']
    assert not calls and not runtime.data_root.exists()
