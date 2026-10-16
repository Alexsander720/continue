"""Tests for isolated PC media policy and PCMediaManager runtime adapter."""
import copy
from pathlib import Path
import sys
import threading
import time
import pytest

# Ensure source is on sys.path
SOURCE = (Path(__file__).resolve().parents[2] / 'pc')
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

import public_media_policy as pmp
from public_media_policy import (
    PCMediaManager,
    PC_PRESETS,
    PC_DEFAULT_QUALITY,
    PC_DISK_BUDGETS_GB,
    PC_DEFAULT_DISK_BUDGET_GB,
    is_music_enabled,
    enable_music_setup,
    get_media_capabilities,
    get_game_media_status,
)
import standalone_media as sm


def test_music_only_evicts_full_cache_before_download_and_returns_failure(tmp_path,monkeypatch):
    m=PCMediaManager(tmp_path/'data');m.media.mkdir(parents=True)
    old=m.media/'1_steam.mp4';old.write_bytes(b'fixture')
    monkeypatch.setattr(m,'_cache_bytes',lambda:3*1024**3 if old.exists() else 0)
    def prepare(*args):
        assert not old.exists()
        return {'ok':False,'error':'fixture download failure'}
    m.build_theme=prepare
    result=m.build(2,'Fixture',{'theme_music_consent':True,'home_music':True,'live_bg':'off','disk_limit_gb':2})
    assert not result['ok'] and not result['theme']['ok']


def test_budget_counts_private_runtime_without_evicting_it(tmp_path):
    m=PCMediaManager(tmp_path/'data');m.media.mkdir(parents=True)
    (m.media/'1_theme.m4a').write_bytes(b'12')
    runtime=m.data/'bin/pc-runtime';runtime.mkdir(parents=True);(runtime/'node.exe').write_bytes(b'123')
    assert m._cache_bytes()==5


class MockMediaHarness:
    """Mock harness providing injected run, urlopen, and file mocks."""

    def __init__(self, tmp_path):
        self.tmp_path = tmp_path
        self.data_dir = tmp_path / "data"
        self.media_dir = self.data_dir / "media"
        self.bin_dir = self.data_dir / "bin"
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        self.calls = []

    def make_manager(self, shared_lock=None):
        return PCMediaManager(
            self.data_dir,
            shared_lock=shared_lock,
            urlopen=self.mock_urlopen,
            run=self.mock_run,
        )

    def mock_urlopen(self, request, timeout=20, **kwargs):
        self.calls.append(("urlopen", getattr(request, "full_url", str(request))))
        raise OSError("Offline test harness - no network")

    def mock_run(self, command, **kwargs):
        self.calls.append(("run", command))
        class MockProc:
            returncode = 0
            stdout = ""
            stderr = ""
        return MockProc()


# ─────────────────────────────────────────────────────────────
# 1. Subclass and Preset Isolation Tests
# ─────────────────────────────────────────────────────────────

def test_subclass_does_not_mutate_global_presets():
    """Verify PCMediaManager subclasses sm.MediaManager and PRESETS is untouched."""
    assert issubclass(PCMediaManager, sm.MediaManager)

    # Global PRESETS must only have original keys
    assert set(sm.PRESETS.keys()) == {"light", "balanced", "maximum"}
    assert "2160" not in sm.PRESETS
    assert "1080" not in sm.PRESETS
    assert "720" not in sm.PRESETS

    # PC_PRESETS contains 720, 1080, 2160
    assert "720" in PC_PRESETS
    assert "1080" in PC_PRESETS
    assert "2160" in PC_PRESETS
    assert PC_PRESETS["2160"]["height"] == 2160
    assert PC_PRESETS["1080"]["height"] == 1080
    assert PC_PRESETS["720"]["height"] == 720


def test_preset_retrieval_and_defaults(tmp_path):
    harness = MockMediaHarness(tmp_path)
    mgr = harness.make_manager()

    p2160 = mgr.get_preset("2160")
    assert p2160["height"] == 2160

    p1080 = mgr.get_preset("1080")
    assert p1080["height"] == 1080

    # Default fallback is 1080
    p_unknown = mgr.get_preset("unknown_preset")
    assert p_unknown["height"] == 1080


# ─────────────────────────────────────────────────────────────
# 2. 4K Capability & Runtime Inspection Tests
# ─────────────────────────────────────────────────────────────

def test_capabilities_honest_4k_reporting():
    """A selected ceiling cannot establish the resolution of any game's source."""
    caps = get_media_capabilities({"media_quality": 2160})
    assert caps["supported_qualities"] == [720, 1080, 2160]
    assert caps["default_quality"] == 1080
    assert caps["selected_quality"] == 2160

    assert caps["max_effective_quality"] is None
    assert caps["real_4k_available"] is None
    assert caps["provider_bounded"] is True
    assert "specific source" in caps["reason"]


def test_capabilities_include_verified_owned_tools(monkeypatch):
    monkeypatch.setattr(pmp.shutil, "which", lambda _name: None)
    caps = get_media_capabilities(
        {"media_quality": 2160},
        tool_lookup=lambda name: "owned/" + name if name in ("ffmpeg", "node") else None,
    )
    assert caps["ffmpeg"] is True and caps["node"] is True
    assert caps["ffprobe"] is False
    assert caps["real_4k_available"] is None


# ─────────────────────────────────────────────────────────────
# 3. Media Fallback (Steam -> YouTube) Tests
# ─────────────────────────────────────────────────────────────

def test_media_fallback_blocked_without_youtube_consent(tmp_path, monkeypatch):
    """Fallback from Steam to YouTube is strictly blocked if youtube_consent is False."""
    harness = MockMediaHarness(tmp_path)
    mgr = harness.make_manager()

    # Mock build_steam to simulate absence of Steam trailer
    def mock_build_steam(appid, name, settings):
        raise RuntimeError("Steam Store has no suitable movie")
    monkeypatch.setattr(mgr, "build_steam", mock_build_steam)

    yt_called = []
    def mock_build_youtube(appid, name, settings):
        yt_called.append(appid)
        return {"ok": True, "source": "youtube"}
    monkeypatch.setattr(mgr, "build_youtube", mock_build_youtube)

    settings = {
        "youtube_consent": False,
        "bg_source": "steam",
    }

    result = mgr.build(2172010, "Until Dawn", settings)
    assert result["ok"] is False
    assert result["source"] == "steam"
    assert result.get("fallback_blocked") == "youtube_consent required"
    assert len(yt_called) == 0  # YouTube was NEVER called!


def test_media_fallback_allowed_with_youtube_consent(tmp_path, monkeypatch):
    """Fallback from Steam to YouTube succeeds when youtube_consent is True."""
    harness = MockMediaHarness(tmp_path)
    mgr = harness.make_manager()

    def mock_build_steam(appid, name, settings):
        raise RuntimeError("Steam Store has no suitable movie")
    monkeypatch.setattr(mgr, "build_steam", mock_build_steam)

    yt_called = []
    def mock_build_youtube(appid, name, settings):
        yt_called.append(appid)
        return {"ok": True, "source": "youtube", "video": "https://youtube.com/v123"}
    monkeypatch.setattr(mgr, "build_youtube", mock_build_youtube)

    settings = {
        "youtube_consent": True,
        "media_fallback": True,
        "bg_source": "steam",
    }

    result = mgr.build(2172010, "Until Dawn", settings)
    assert result["ok"] is True
    assert result["source"] == "youtube"
    assert result.get("fallback_from") == "steam"
    assert len(yt_called) == 1


# ─────────────────────────────────────────────────────────────
# 4. Music Policy: Consent, Toggles, and Setup Tests
# ─────────────────────────────────────────────────────────────

def test_music_enabled_requires_both_consent_and_toggles():
    """Music is enabled iff theme_music_consent is True AND hub_music/home_music is True."""
    # Failed trial diagnostic condition: consent True but hub_music False
    assert is_music_enabled({"theme_music_consent": True, "hub_music": False}, context="hub") is False
    assert is_music_enabled({"theme_music_consent": False, "hub_music": True}, context="hub") is False
    assert is_music_enabled({"theme_music_consent": True, "hub_music": True}, context="hub") is True

    # Home context
    assert is_music_enabled({"theme_music_consent": True, "home_music": False}, context="home") is False
    assert is_music_enabled({"theme_music_consent": True, "home_music": True}, context="home") is True


def test_enable_music_setup():
    """One-time setup enables both consent and playback toggles."""
    initial = {"theme_music_consent": False, "hub_music": False, "home_music": False}
    updated = enable_music_setup(initial)
    assert updated["theme_music_consent"] is True
    assert updated["hub_music"] is True
    assert updated["home_music"] is True
    assert is_music_enabled(updated, context="hub") is True
    assert is_music_enabled(updated, context="home") is True


# ─────────────────────────────────────────────────────────────
# 5. Automatic Themes per Visited Game & Per-Game Suppression
# ─────────────────────────────────────────────────────────────

def test_automatic_theme_suppressed_by_none_choice(tmp_path, monkeypatch):
    """Explicit 'none' per-game choice suppresses automatic theme download."""
    harness = MockMediaHarness(tmp_path)
    mgr = harness.make_manager()

    downloaded = []
    def mock_build_theme(appid, name, settings):
        downloaded.append(appid)
        return {"ok": True, "source": "theme", "file": f"media/{appid}_theme.m4a"}
    monkeypatch.setattr(mgr, "build_theme", mock_build_theme)

    settings = {
        "theme_music_consent": True,
        "hub_music": True,
        "music_choices": {
            "2172010": "none",
        },
    }

    # Should be suppressed
    res = mgr._maybe_theme(2172010, "Until Dawn", settings)
    assert res is None
    assert len(downloaded) == 0

    # Another game with auto choice should proceed
    res2 = mgr._maybe_theme(2322010, "God of War", settings)
    assert res2 is not None
    assert res2.get("ok") is True
    assert downloaded == [2322010]


def test_music_files_filters_out_none_choice(tmp_path, monkeypatch):
    """music_files(settings) filters out tracks where choice is 'none'."""
    harness = MockMediaHarness(tmp_path)
    mgr = harness.make_manager()
    monkeypatch.setattr(mgr, "_valid_audio", lambda p: True)

    # Create dummy theme files on disk
    f1 = harness.media_dir / "2172010_theme.m4a"
    f2 = harness.media_dir / "2322010_theme.m4a"
    f1.write_bytes(b"dummy_m4a_audio")
    f2.write_bytes(b"dummy_m4a_audio")

    # Without settings, returns all files
    raw = mgr.music_files(settings=None)
    assert "2172010" in raw
    assert "2322010" in raw

    # With settings where 2172010 is 'none'
    settings = {
        "theme_music_consent": True,
        "hub_music": True,
        "music_choices": {"2172010": "none"},
    }
    filtered = mgr.music_files(settings=settings)
    assert "2172010" not in filtered
    assert "2322010" in filtered

    # If hub_music is False, returns empty map
    disabled_settings = {
        "theme_music_consent": True,
        "hub_music": False,
        "music_choices": {},
    }
    assert mgr.music_files(settings=disabled_settings) == {}


# ─────────────────────────────────────────────────────────────
# 6. Canonical English Title Search vs Localized Names
# ─────────────────────────────────────────────────────────────

def test_canonical_english_title_resolution(tmp_path, monkeypatch):
    """Localized Steam name is resolved to English canonical title for YouTube search."""
    harness = MockMediaHarness(tmp_path)
    mgr = harness.make_manager()

    def mock_store_data(appid, language="english"):
        if appid == 2172010 and language == "english":
            return {"name": "Until Dawn", "success": True}
        return {}
    monkeypatch.setattr(mgr, "store_data", mock_store_data)

    resolved = mgr.resolve_canonical_name(2172010, "Дожить до рассвета")
    assert resolved == "Until Dawn"

    searched_queries = []
    def mock_youtube_candidates(name, official=(), audio=False):
        searched_queries.append(name)
        return [{"url": "https://youtube.com/watch?v=theme123", "title": "Until Dawn OST"}]
    monkeypatch.setattr(mgr, "youtube_candidates", mock_youtube_candidates)

    def mock_download_youtube(url, destination_stem, settings, audio=False):
        p = harness.media_dir / f"{destination_stem}.m4a"
        p.write_bytes(b"dummy_m4a")
        return p
    monkeypatch.setattr(mgr, "_download_youtube", mock_download_youtube)

    settings = {"theme_music_consent": True, "hub_music": True}
    res = mgr.build_theme(2172010, "Дожить до рассвета", settings)
    assert res["ok"] is True
    # Searched using English canonical name "Until Dawn"
    assert "Until Dawn" in searched_queries


# ─────────────────────────────────────────────────────────────
# 7. Strict PC Storage Budgets (2/4/8/16 GB)
# ─────────────────────────────────────────────────────────────

def test_strict_pc_storage_budgets(tmp_path):
    """PC MediaManager respects strict 2/4/8/16 GB storage limits."""
    harness = MockMediaHarness(tmp_path)
    mgr = harness.make_manager()

    mgr._configure({"disk_limit_gb": 4})
    assert mgr._limit_bytes == 4 * 1024 ** 3

    mgr._configure({"disk_limit_gb": 8})
    assert mgr._limit_bytes == 8 * 1024 ** 3

    mgr._configure({"disk_limit_gb": 16})
    assert mgr._limit_bytes == 16 * 1024 ** 3

    # Invalid / Deck default 1GB budget clamps to PC default 2GB
    mgr._configure({"disk_limit_gb": 1})
    assert mgr._limit_bytes == PC_DEFAULT_DISK_BUDGET_GB * 1024 ** 3

    mgr._configure({"disk_limit_gb": 999})
    assert mgr._limit_bytes == PC_DEFAULT_DISK_BUDGET_GB * 1024 ** 3


# ─────────────────────────────────────────────────────────────
# 8. Structured UI State / Capabilities Helper Tests
# ─────────────────────────────────────────────────────────────

def test_structured_game_media_status_reporting(tmp_path):
    """Status helper returns structured states and non-empty reasons."""
    harness = MockMediaHarness(tmp_path)
    mgr = harness.make_manager()

    settings = {
        "theme_music_consent": False,
        "youtube_consent": False,
        "hub_music": False,
        "disk_limit_gb": 2,
    }

    status = get_game_media_status(mgr, 2172010, "Until Dawn", settings)
    assert status["appid"] == 2172010
    assert status["video"]["status"] in ("ready", "no_video", "error")
    assert len(status["video"]["reason"]) > 0

    assert status["music"]["status"] == "setup_required"
    assert "consent required" in status["music"]["reason"]

    assert status["budget"]["status"] == "ok"
    assert status["budget"]["limit_gb"] == 2
    assert len(status["budget"]["reason"]) > 0

    # Test with setup completed and music enabled
    setup_settings = enable_music_setup(settings)
    status2 = get_game_media_status(mgr, 2172010, "Until Dawn", setup_settings)
    assert status2["setup"]["required"] is False
    assert status2["music"]["status"] in ("waiting", "ready")


# ─────────────────────────────────────────────────────────────
# 9. Concurrency & Shared Lock Tests
# ─────────────────────────────────────────────────────────────

def test_shared_music_lock_serializes_downloads(tmp_path, monkeypatch):
    """Shared lock prevents race conditions on theme downloads."""
    shared_lock = threading.RLock()
    harness = MockMediaHarness(tmp_path)
    mgr = harness.make_manager(shared_lock=shared_lock)

    active_threads = []
    concurrency_detected = []

    def slow_build_theme(appid, name, settings):
        active_threads.append(threading.current_thread().name)
        if len(active_threads) > 1:
            concurrency_detected.append(True)
        time.sleep(0.05)
        active_threads.remove(threading.current_thread().name)
        return {"ok": True, "source": "theme", "file": f"media/{appid}_theme.m4a"}

    monkeypatch.setattr(mgr, "build_theme", slow_build_theme)

    settings = {"theme_music_consent": True, "hub_music": True}

    t1 = threading.Thread(target=lambda: mgr._maybe_theme(2172010, "Game1", settings), name="t1")
    t2 = threading.Thread(target=lambda: mgr._maybe_theme(2322010, "Game2", settings), name="t2")

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # The shared lock must serialize execution (no concurrent execution of build_theme)
    assert len(concurrency_detected) == 0
