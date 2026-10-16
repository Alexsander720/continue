"""Offline loader transactions: every accepted file is hash-verified, never executed."""
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugin/py_modules"))
import standalone_media as sm

OLD = b"old fixture, never executable\n" * 20000
NEW = b"new fixture, never executable\n" * 20000


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def manager_for(tmp_path, monkeypatch, *, previous=True):
    manager = sm.MediaManager(tmp_path, now=lambda: 1000000,
                              urlopen=lambda *a, **k: pytest.fail("real network"),
                              run=lambda *a, **k: pytest.fail("fixture must not execute"))
    monkeypatch.setattr(manager, "_check_space", lambda *a: None)
    if previous:
        manager.bin.mkdir(parents=True)
        (manager.bin / "yt-dlp").write_bytes(OLD)
        manager._save_state({"yt_dlp": {"version": "old", "sha256": digest(OLD), "checked_at": 0},
                             "games": {"123": {"keep": True}}, "unrelated": [1, 2]})
    calls = []
    def release(url):
        calls.append(url)
        return {"tag_name": "2026.10.15", "assets": [
            {"name": name, "browser_download_url":
             "https://github.com/yt-dlp/yt-dlp/releases/download/2026.10.15/" + name}
            for name in ("yt-dlp", "SHA2-256SUMS")]}
    monkeypatch.setattr(manager, "_json_url", release)
    monkeypatch.setattr(manager, "_bytes", lambda *a, **k: (digest(NEW) + "  yt-dlp\n").encode())
    def stream(url, path, **kwargs):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(NEW)
    monkeypatch.setattr(manager, "_stream", stream)
    return manager, calls


def assert_old_usable(manager):
    own = manager._own_ytdlp()
    assert own is not None
    assert own.read_bytes() == OLD
    assert manager._state()["yt_dlp"]["sha256"] == digest(OLD)
    assert manager._state()["games"] == {"123": {"keep": True}}


def test_success_preserves_previous_and_explicit_rollback(tmp_path, monkeypatch):
    manager, calls = manager_for(tmp_path, monkeypatch)
    result = manager.install_ytdlp(True)
    assert result["status"] == "updated" and result["updated"]
    assert manager._own_ytdlp().read_bytes() == NEW
    assert (manager.bin / "yt-dlp.previous").read_bytes() == OLD
    assert manager._state()["yt_dlp_previous"]["sha256"] == digest(OLD)
    assert manager._state()["unrelated"] == [1, 2]
    assert manager.rollback_ytdlp(False) == {"ok": False, "consent_required": True}
    rolled = manager.rollback_ytdlp(True)
    assert rolled["status"] == "rolled_back" and rolled["rolled_back"]
    assert rolled["sha256"] == digest(OLD)
    assert_old_usable(manager)
    assert (manager.bin / "yt-dlp.previous").read_bytes() == NEW
    assert len(calls) == 1


@pytest.mark.parametrize("failure", ["before_promotion", "after_promotion", "state_commit", "journal"])
def test_update_failure_retains_previous_bytes(tmp_path, monkeypatch, failure):
    manager, _ = manager_for(tmp_path, monkeypatch)
    original_promote = manager._promote
    original_json = manager._atomic_json
    def promote(part, target):
        if target == manager.bin / "yt-dlp":
            if failure == "before_promotion":
                raise OSError("before promotion fixture")
            original_promote(part, target)
            if failure == "after_promotion":
                raise OSError("after promotion fixture")
        else:
            original_promote(part, target)
    def write_json(path, state):
        if failure == "state_commit" and path == manager.state_path and state.get("yt_dlp", {}).get("sha256") == digest(NEW):
            raise OSError("state commit fixture")
        if failure == "journal" and Path(path).name == "yt-dlp.transaction.json":
            raise OSError("journal fixture")
        original_json(path, state)
    monkeypatch.setattr(manager, "_promote", promote)
    monkeypatch.setattr(manager, "_atomic_json", write_json)
    result = manager.install_ytdlp(True)
    assert result["status"] == "usable_old"
    assert result["ok"] and not result["updated"] and result["error"]
    assert_old_usable(manager)


def test_restart_recovers_uncommitted_promotion(tmp_path, monkeypatch):
    manager, _ = manager_for(tmp_path, monkeypatch)
    promote = manager._promote
    def crash_after_promotion(part, target):
        promote(part, target)
        raise SystemExit("simulated process interruption")
    monkeypatch.setattr(manager, "_promote", crash_after_promotion)
    with pytest.raises(SystemExit):
        manager.install_ytdlp(True)
    assert (manager.bin / "yt-dlp").read_bytes() == NEW
    restarted = sm.MediaManager(tmp_path)
    assert_old_usable(restarted)
    assert not (manager.bin / "yt-dlp.transaction.json").exists()


def test_restart_finishes_committed_backup_rotation(tmp_path, monkeypatch):
    manager, _ = manager_for(tmp_path, monkeypatch)
    original = manager._atomic_json
    def crash_after_state(path, value):
        original(path, value)
        if path == manager.state_path and value.get("yt_dlp", {}).get("sha256") == digest(NEW):
            raise SystemExit("after durable state")
    monkeypatch.setattr(manager, "_atomic_json", crash_after_state)
    with pytest.raises(SystemExit):
        manager.install_ytdlp(True)
    restarted = sm.MediaManager(tmp_path)
    assert restarted._own_ytdlp().read_bytes() == NEW
    assert (restarted.bin / "yt-dlp.previous").read_bytes() == OLD
    assert restarted.rollback_ytdlp(True)["rolled_back"]
    assert_old_usable(restarted)


def test_bad_checksum_never_promotes_and_weekly_success_throttle(tmp_path, monkeypatch):
    manager, calls = manager_for(tmp_path, monkeypatch)
    monkeypatch.setattr(manager, "_bytes", lambda *a, **k: ("0" * 64 + "  yt-dlp\n").encode())
    bad = manager.install_ytdlp(True)
    assert bad["status"] == "usable_old" and "sha256" in bad["error"]
    assert_old_usable(manager)
    manager.install_ytdlp(True)
    assert len(calls) == 1
    monkeypatch.setattr(manager, "_bytes", lambda *a, **k: (digest(NEW) + "  yt-dlp\n").encode())
    assert manager.install_ytdlp(True, force=True)["updated"]
    assert manager.install_ytdlp(True)["updated"] is False
    assert len(calls) == 2


def test_modified_backup_refuses_rollback_without_execution(tmp_path, monkeypatch):
    manager, _ = manager_for(tmp_path, monkeypatch)
    assert manager.install_ytdlp(True)["ok"]
    (manager.bin / "yt-dlp.previous").write_bytes(OLD + b"modified")
    result = manager.rollback_ytdlp(True)
    assert not result["rolled_back"] and result["error"]
    assert manager._own_ytdlp().read_bytes() == NEW


def test_persistent_state_failure_before_network_retains_current(tmp_path, monkeypatch):
    manager, calls = manager_for(tmp_path, monkeypatch)
    def fail(*a):
        raise OSError("read-only state fixture")
    monkeypatch.setattr(manager, "_atomic_json", fail)
    result = manager.install_ytdlp(True)
    assert not result["updated"] and result["status"] == "usable_old"
    assert not calls
    assert_old_usable(manager)


def test_first_install_failed_commit_does_not_leave_executable_new_file(tmp_path, monkeypatch):
    manager, _ = manager_for(tmp_path, monkeypatch, previous=False)
    original = manager._atomic_json
    def fail_commit(path, value):
        if path == manager.state_path and value.get("yt_dlp", {}).get("sha256") == digest(NEW):
            raise OSError("state commit fixture")
        original(path, value)
    monkeypatch.setattr(manager, "_atomic_json", fail_commit)
    result = manager.install_ytdlp(True)
    assert not result["ok"] and result["status"] == "error"
    assert manager._own_ytdlp() is None
    assert not (manager.bin / "yt-dlp").exists()


@pytest.mark.parametrize("name", ["yt-dlp", "yt-dlp.previous", "yt-dlp.transaction.json", "yt-dlp.download.part"])
def test_owned_loader_paths_reject_symlink(tmp_path, monkeypatch, name):
    manager, _ = manager_for(tmp_path, monkeypatch)
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.write_bytes(b"unchanged")
    link = manager.bin / name
    if link.exists():
        link.unlink()
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink unavailable")
    result = manager.install_ytdlp(True)
    assert not result["updated"] and result.get("error")
    assert outside.read_bytes() == b"unchanged"
    assert link.is_symlink()


def test_cancel_after_download_does_not_replace_old_loader(tmp_path, monkeypatch):
    manager, _ = manager_for(tmp_path, monkeypatch)
    def stream(url, path, **kwargs):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(NEW)
        manager.cancel()
    monkeypatch.setattr(manager, "_stream", stream)
    result = manager.install_ytdlp(True)
    assert not result["updated"] and "cancel" in result["error"]
    assert_old_usable(manager)
