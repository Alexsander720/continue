"""Public PC Media Policy and Runtime Adapter for Continue? PC.

Provides:
- PCMediaManager: Subclass of standalone_media.MediaManager tailored for PC Big Picture.
- Quality presets (720, 1080, 2160/4K) without mutating global standalone_media.PRESETS.
- Honest 4K capability inspection (Steam store native video is provider-bounded to 1080p; upscaling forbidden).
- Bounded fallback from Steam to YouTube ONLY when global youtube_consent is True.
- Strict music gating requiring both theme_music_consent AND hub_music/home_music toggles.
- Automatic theme downloads per visited game, suppressed by explicit "none" choice.
- Canonical English title resolution for localized Steam titles.
- Strict PC storage budgets (2, 4, 8, 16 GB).
- Shared lock synchronization for manual and automatic music downloads.
- Structured, actionable UI state helpers for frontend consumption.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import urllib.parse
import urllib.request

import standalone_media as _sm

MediaManager = _sm.MediaManager
LOOP_SECONDS = _sm.LOOP_SECONDS
SOURCES = _sm.SOURCES
RETRY_SECONDS = _sm.RETRY_SECONDS
MAX_DOWNLOAD_BYTES = _sm.MAX_DOWNLOAD_BYTES

# PC Quality Presets (subclass override; never mutate _sm.PRESETS)
PC_PRESETS = {
    "720": {"height": 720, "crf": 23, "min_free_gb": 0.5, "max_games": 40},
    "1080": {"height": 1080, "crf": 20, "min_free_gb": 1.0, "max_games": 40},
    "2160": {"height": 2160, "crf": 18, "min_free_gb": 2.0, "max_games": 40},
    "light": {"height": 720, "crf": 25, "min_free_gb": 0.25, "max_games": 40},
    "balanced": {"height": 720, "crf": 23, "min_free_gb": 0.5, "max_games": 40},
    "maximum": {"height": 1080, "crf": 20, "min_free_gb": 1.0, "max_games": 40},
}
PC_DEFAULT_QUALITY = "1080"
PC_DISK_BUDGETS_GB = (2, 4, 8, 16)
PC_DEFAULT_DISK_BUDGET_GB = 2


# ─────────────────────────────────────────────────────────────
# Policy and Capability Helper Functions
# ─────────────────────────────────────────────────────────────

def is_music_enabled(settings: dict, context: str = "hub") -> bool:
    """Check if music is permitted to play and download.

    Requires BOTH:
    1. Global theme_music_consent is strictly True.
    2. Active context toggle (hub_music for Gameview/Hub, home_music for Home) is True.
    """
    if not isinstance(settings, dict):
        return False
    if settings.get("theme_music_consent") is not True:
        return False
    toggle_key = "home_music" if context == "home" else "hub_music"
    return bool(settings.get(toggle_key, False))


def enable_music_setup(settings: dict) -> dict:
    """One-time simple setup: enable consent and active music toggles."""
    updated = dict(settings or {})
    updated["theme_music_consent"] = True
    updated["hub_music"] = True
    updated["home_music"] = True
    return updated


def get_media_capabilities(settings: dict | None = None, *, tool_lookup=None) -> dict:
    """Report quality ceilings and tools, leaving source resolution unconfirmed.

    The manager's lookup includes its verified private runtime as well as PATH.
    Actual cached video dimensions belong to get_game_media_status, not here.
    """
    lookup = tool_lookup or shutil.which
    ffmpeg_available = bool(lookup("ffmpeg"))
    ffprobe_available = bool(lookup("ffprobe"))
    node_available = bool(lookup("node"))

    selected_quality = "1080"
    if settings and isinstance(settings, dict):
        q = str(settings.get("media_quality") or settings.get("preset") or "1080")
        if q in PC_PRESETS:
            selected_quality = q

    reason = (
        "Quality is a download ceiling, not a source guarantee. Steam often provides up to 1080p; "
        "native 4K depends on the specific source and available tools. No upscaling is performed."
    )

    return {
        "supported_qualities": [720, 1080, 2160],
        "default_quality": 1080,
        "selected_quality": int(selected_quality) if selected_quality.isdigit() else 1080,
        "max_effective_quality": None,
        "real_4k_available": None,
        "provider_bounded": True,
        "reason": reason,
        "ffmpeg": ffmpeg_available,
        "ffprobe": ffprobe_available,
        "node": node_available,
        "storage_budgets_gb": list(PC_DISK_BUDGETS_GB),
        "default_budget_gb": PC_DEFAULT_DISK_BUDGET_GB,
    }


def get_game_media_status(
    media_manager: "PCMediaManager",
    appid: int,
    name: str,
    settings: dict,
) -> dict:
    """Produce actionable structured UI state for a game's media and music.

    Returns non-empty explicit reasons for every state instead of missing booleans.
    """
    appid_int = int(appid)
    appid_str = str(appid_int)

    # 1. Video state
    steam_asset = media_manager._asset(appid_int, "steam")
    yt_asset = media_manager._asset(appid_int, "youtube")
    rec_asset = media_manager._asset(appid_int, "recording")
    active_video = steam_asset or yt_asset or rec_asset
    actual_height = None
    if active_video:
        try:
            height = _sm._bmff(active_video).get('height')
            if type(height) is int and 0 < height <= 16384:
                actual_height = height
        except (OSError,ValueError,RuntimeError,TypeError):
            pass

    video_source = None
    if steam_asset:
        video_source = "steam"
    elif yt_asset:
        video_source = "youtube"
    elif rec_asset:
        video_source = "recording"

    attempts = (media_manager._state().get("attempts") or {}).get(f"{appid_int}:{video_source or 'steam'}") or {}

    video_status = "ready" if active_video else "no_video"
    video_reason = "Video trailer cached and ready" if active_video else "No trailer available"
    if not active_video and attempts.get("ok") is False:
        video_status = "error"
        video_reason = str(attempts.get("error") or "Failed to build trailer")
    elif not active_video and not (settings.get("youtube_consent") or steam_asset):
        video_reason = "Steam trailer not found; YouTube fallback requires consent"

    # 2. Music state
    music_choices = settings.get("music_choices") or {}
    choice = music_choices.get(appid_str, "auto")
    music_files_map = media_manager.music_files(settings=None)  # raw disk check
    has_theme_file = appid_str in music_files_map

    music_allowed = is_music_enabled(settings, context="hub")
    if choice == "none":
        music_status = "no_music"
        music_reason = "Music explicitly disabled for this game"
    elif not settings.get("theme_music_consent"):
        music_status = "setup_required"
        music_reason = "Theme music consent required"
    elif not (settings.get("hub_music", False) or settings.get('home_music',False)):
        music_status = "music_disabled"
        music_reason = "Music is disabled in hub settings (hub_music is off)"
    elif has_theme_file:
        music_status = "ready"
        music_reason = "Theme music ready for playback"
    else:
        theme_attempts = (media_manager._state().get("theme_attempts") or {}).get(appid_str) or {}
        if theme_attempts.get("ok") is False:
            music_status = "error"
            music_reason = str(theme_attempts.get("error") or "Failed to download theme track")
            reason = theme_attempts.get('reason')
            if reason in _sm.THEME_REASONS or reason in ('youtube_blocked', 'python3_required'):
                music_status = reason
                music_reason = reason
        else:
            music_status = "waiting"
            music_reason = "Theme music will be automatically fetched on visit"

    # 3. Budget state
    cache_bytes = media_manager._cache_bytes()
    limit_gb = settings.get("disk_limit_gb", PC_DEFAULT_DISK_BUDGET_GB)
    if limit_gb not in PC_DISK_BUDGETS_GB:
        limit_gb = PC_DEFAULT_DISK_BUDGET_GB
    limit_bytes = int(limit_gb * 1024 ** 3)

    if cache_bytes > limit_bytes:
        budget_status = "budget_exceeded"
        budget_reason = f"Cache size ({cache_bytes // (1024*1024)}MB) exceeds {limit_gb}GB budget"
    elif cache_bytes > int(limit_bytes * 0.85):
        budget_status = "storage_pressure"
        budget_reason = f"Cache is near capacity ({cache_bytes // (1024*1024)}MB of {limit_gb}GB)"
    else:
        budget_status = "ok"
        budget_reason = "Cache is within budget"

    return {
        "appid": appid_int,
        "name": name,
        "video": {
            "status": video_status,
            "source": video_source,
            "file": media_manager._relative(active_video) if active_video else None,
            "effective_quality": actual_height,
            "max_effective_quality": actual_height,
            "reason": video_reason,
        },
        "music": {
            "status": music_status,
            "file": music_files_map.get(appid_str),
            "choice": choice,
            "reason": music_reason,
        },
        "budget": {
            "status": budget_status,
            "limit_gb": limit_gb,
            "used_bytes": cache_bytes,
            "limit_bytes": limit_bytes,
            "reason": budget_reason,
        },
        "setup": {
            "theme_music_consent": bool(settings.get("theme_music_consent")),
            "youtube_consent": bool(settings.get("youtube_consent")),
            "hub_music": bool(settings.get("hub_music")),
            "home_music": bool(settings.get("home_music")),
            "required": not bool(settings.get("theme_music_consent")),
        },
    }


# ─────────────────────────────────────────────────────────────
# PCMediaManager Class
# ─────────────────────────────────────────────────────────────

class PCMediaManager(MediaManager):
    """Subclass of standalone_media.MediaManager for PC Big Picture runtime.

    Implements:
    - Subclass preset extension without mutating global PRESETS.
    - Fallback from Steam to YouTube ONLY when youtube_consent is True.
    - Gated automatic music on visit, suppressed by "none" per-game choices.
    - Canonical English title resolution for localized Steam titles.
    - Strict PC storage budgets (2/4/8/16 GB).
    - Shared music lock preventing file races between auto build and manual picker.
    """

    def __init__(
        self,
        data_dir,
        plugin_dir=None,
        *,
        urlopen=None,
        run=None,
        now=None,
        allowed=None,
        shared_lock: Optional[threading.RLock] = None,
    ):
        super().__init__(data_dir, plugin_dir=plugin_dir, urlopen=urlopen, run=run, now=now, allowed=allowed)
        self.music_lock = shared_lock if shared_lock is not None else threading.RLock()
        self._canonical_title_cache: Dict[int, str] = {}
        self.runtime = None
        self.active = None
        self._choice_gate = threading.Lock()
        self._theme_epochs = {}
        self._active_theme = None
        self._operation_deadline = None

    def invalidate_theme(self, appid):
        with self._choice_gate:
            self._theme_epochs[int(appid)] = self._theme_epochs.get(int(appid),0) + 1

    def _checkpoint(self):
        super()._checkpoint()
        if self._operation_deadline is not None and time.monotonic() >= self._operation_deadline:
            raise RuntimeError('media job deadline exceeded; retry when ready')
        with self._choice_gate:
            if self._active_theme and self._theme_epochs.get(self._active_theme[0],0) != self._active_theme[1]:
                raise RuntimeError('Theme choice changed')

    def tool(self, name):
        return (self.runtime.tool(name) if self.runtime else None) or shutil.which(name)

    def clear(self):
        if not self.music_lock.acquire(blocking=False):
            return {'ok':False,'deferred':'busy'}
        try:
            result = super().clear()
            if result.get('ok'):
                state = self._state()
                state['theme_attempts'] = {}
                self._save_state(state)
            return result
        finally:
            self.music_lock.release()

    def _ytdlp_command(self):
        command = super()._ytdlp_command()
        node = self.tool('node')
        if node:
            command += ['--js-runtimes', 'node:' + str(node)]
        return command

    def _probe_duration(self, path):
        probe = self.tool('ffprobe')
        if not probe:
            return super()._probe_duration(path)
        result = self.run([str(probe), '-v', 'error', '-show_entries', 'format=duration',
                           '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
                          capture_output=True, text=True, timeout=20)
        try:
            duration = float(result.stdout)
            return duration if math.isfinite(duration) and 0 < duration < 86400 else None
        except (TypeError, ValueError):
            return None

    def get_preset(self, preset_or_quality: Any) -> dict:
        """Resolve preset configuration from PC_PRESETS without mutating global PRESETS."""
        key = str(preset_or_quality or PC_DEFAULT_QUALITY).lower()
        if key in PC_PRESETS:
            return copy.deepcopy(PC_PRESETS[key])
        return copy.deepcopy(PC_PRESETS[PC_DEFAULT_QUALITY])

    def _configure(self, settings):
        """Configure cache limits and quality using PC budgets and presets."""
        quality = str(settings.get("media_quality") or settings.get("preset") or PC_DEFAULT_QUALITY)
        profile = self.get_preset(quality)

        try:
            limit = float(settings.get("disk_limit_gb", PC_DEFAULT_DISK_BUDGET_GB))
            if limit not in PC_DISK_BUDGETS_GB:
                limit = float(PC_DEFAULT_DISK_BUDGET_GB)
            free = float(settings.get("min_free_gb", max(0.5, profile["min_free_gb"])))
            if not math.isfinite(limit) or not math.isfinite(free):
                raise ValueError("non-finite cache setting")
            self._limit_bytes = max(256 * 1024 ** 2, int(limit * 1024 ** 3))
            self._min_free_bytes = max(0, int(free * 1024 ** 3))
        except (TypeError, ValueError, OverflowError):
            self._limit_bytes = PC_DEFAULT_DISK_BUDGET_GB * 1024 ** 3
            self._min_free_bytes = int(0.5 * 1024 ** 3)

        self._max_games = max(1, min(40, _sm._safe_int(settings.get("max_cached_games"), profile["max_games"])))

    def enforce_limit(self, limit_gb):
        """Enforce strict PC storage limit (2/4/8/16 GB)."""
        try:
            limit_val = float(limit_gb)
            if limit_val not in PC_DISK_BUDGETS_GB:
                limit_val = float(PC_DEFAULT_DISK_BUDGET_GB)
            limit = int(limit_val * 1024 ** 3)
        except (TypeError, ValueError, OverflowError):
            limit = PC_DEFAULT_DISK_BUDGET_GB * 1024 ** 3

        return super().enforce_limit(limit / (1024 ** 3))

    def _cache_bytes(self):
        total=super()._cache_bytes()
        runtime=getattr(getattr(self,'runtime',None),'runtime_dir',self.data/'bin/pc-runtime')
        if runtime.is_dir() and not runtime.is_symlink():
            for directory,dirs,files in os.walk(runtime,followlinks=False):
                dirs[:]=[name for name in dirs if not (Path(directory)/name).is_symlink()]
                for name in files:
                    path=Path(directory)/name
                    if not path.is_symlink():
                        try:total+=path.stat().st_size
                        except OSError:pass
        return total

    def _ffmpeg_loop(self, source, destination, preset, *, start=None, length=LOOP_SECONDS, audio=False):
        """Subclass override: use self.get_preset without touching global PRESETS."""
        ffmpeg = self.tool("ffmpeg")
        if not ffmpeg:
            return None
        profile = self.get_preset(preset)
        duration = self._probe_duration(source)
        if urllib.parse.urlparse(str(source)).scheme in ("http", "https"):
            raise RuntimeError("ffmpeg remote media is disabled")
        start = max(0.0, (duration - length) / 2) if start is None and duration else float(start or 0)
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        part = destination.with_name(destination.stem + ".encode.part" + destination.suffix)
        # Bounded scaling: scale down if larger, but never upscale lower-res sources.
        vf = f"scale=-2:'min({profile['height']},ih)'"
        commands = [
            [
                ffmpeg, "-v", "error", "-y", "-protocol_whitelist", "file,pipe",
                "-ss", f"{start:.3f}", "-i", str(source), "-t", str(length),
                "-an", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", str(profile["crf"]),
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(part),
            ],
        ]
        if audio:
            commands = [[
                ffmpeg, "-v", "error", "-y", "-protocol_whitelist", "file,pipe",
                "-ss", f"{start:.3f}", "-i", str(source), "-t", str(length),
                "-vn", "-c:a", "aac", "-b:a", "128k", str(part),
            ]]
        try:
            for command in commands:
                try:
                    result = self.run(command, capture_output=True, timeout=180)
                except subprocess.TimeoutExpired:
                    if audio:
                        raise _sm.ThemeMusicError('theme_timeout')
                    continue
                except (OSError, subprocess.SubprocessError):
                    continue
                valid = self._valid_audio(part) if audio else self._valid_video(part)
                if result.returncode == 0 and valid:
                    decoded = self.run(
                        [ffmpeg, "-v", "error", "-xerror", "-protocol_whitelist", "file,pipe", "-i", str(part), "-f", "null", "-"],
                        capture_output=True, timeout=120,
                    )
                    if decoded.returncode != 0:
                        part.unlink(missing_ok=True)
                        continue
                    self._promote(part, destination)
                    return {"duration": duration, "start": start, "encoded": command is commands[0]}
                try:
                    part.unlink()
                except OSError:
                    pass
        finally:
            try:
                part.unlink()
            except OSError:
                pass
        return None

    def build_steam(self, appid, name, settings):
        """Build Steam media using PC presets and cache English canonical name."""
        self._configure(settings)
        self._check_space(0)
        data = self.store_data(appid, "english")
        canonical_name = data.get("name")
        if canonical_name and isinstance(canonical_name, str):
            self._canonical_title_cache[int(appid)] = canonical_name.strip()

        self._cache_store_images(appid, data)
        movie = self.pick_movie(data)
        if not movie:
            raise RuntimeError("Steam Store has no suitable movie")
        destination = self.media / f"{int(appid)}_steam.mp4"
        preset = str(settings.get("media_quality") or settings.get("preset") or PC_DEFAULT_QUALITY)
        target_height = self.get_preset(preset)["height"]
        hls = movie.get("hls_h264")
        if hls:
            local = destination.with_name(destination.name + ".hls.part")
            try:
                window = self._download_hls(hls, local, target_height)
                if self.tool("ffmpeg"):
                    made = self._ffmpeg_loop(local, destination, preset, start=window["local_start"])
                    if not made:
                        raise RuntimeError("ffmpeg could not produce a valid Steam loop")
                    return {"ok": True, "source": "steam", "movie": movie.get("name"), **window, **made}
                self._promote(local, destination)
                return {
                    "ok": True, "source": "steam", "movie": movie.get("name"), **window,
                    "encoded": False, "uncut": True, "playback_seconds": LOOP_SECONDS,
                    "fallback": "bounded H.264 fMP4 segment window; browser limits playback to 20s",
                }
            except RuntimeError:
                if not (movie.get("mp4") or {}):
                    raise
            finally:
                local.unlink(missing_ok=True)
        mp4 = movie.get("mp4") or {}
        direct = mp4.get("max") or mp4.get("480")
        if not direct:
            raise RuntimeError("Steam movie has HLS only and ffmpeg is unavailable")
        if self.tool("ffmpeg"):
            local = destination.with_name(destination.name + ".source.part")
            try:
                self._stream(self._https(direct), local)
                if not self._valid_video(local):
                    raise RuntimeError("progressive Steam movie failed structural validation")
                made = self._ffmpeg_loop(local, destination, preset)
                if not made:
                    raise RuntimeError("ffmpeg could not produce a valid Steam loop")
                return {"ok": True, "source": "steam", "movie": movie.get("name"), **made}
            finally:
                local.unlink(missing_ok=True)
        local = destination.with_name(destination.name + ".source.part")
        try:
            self._stream(self._https(direct), local)
            info = _sm._bmff(local)
            duration = info["duration"]
            if info["height"] > target_height:
                raise RuntimeError("progressive trailer exceeds preset resolution and requires ffmpeg")
            if not 0 < duration <= LOOP_SECONDS + 0.5:
                raise RuntimeError("progressive trailer requires ffmpeg to trim; use bounded HLS or static background")
            self._promote(local, destination)
        finally:
            local.unlink(missing_ok=True)
        return {
            "ok": True, "source": "steam", "movie": movie.get("name"), "encoded": False,
            "uncut": True, "playback_seconds": LOOP_SECONDS, "fallback": "validated short progressive MP4",
        }

    def _download_youtube(self, url, destination_stem, settings, *, audio=False):
        with self.music_lock:
            previous_deadline = self._operation_deadline
            if previous_deadline is None:
                self._operation_deadline = time.monotonic() + 240
            if audio:
                appid = int(destination_stem.split('_',1)[0])
                with self._choice_gate:
                    self._active_theme = (appid,self._theme_epochs.get(appid,0))
            try:
                return self._download_youtube_locked(url, destination_stem, settings, audio=audio)
            finally:
                self._active_theme = None
                self._operation_deadline = previous_deadline

    def _download_youtube_locked(self, url, destination_stem, settings, *, audio=False):
        """Download YouTube media bounded by PC presets."""
        self._configure(settings)
        preset = str(settings.get("media_quality") or settings.get("preset") or PC_DEFAULT_QUALITY)
        height = self.get_preset(preset)["height"]
        self.media.mkdir(parents=True, exist_ok=True)
        marker = self.media / (destination_stem + ".part")
        for old in self.media.glob(marker.name + ".*"):
            try:
                old.unlink()
            except OSError:
                pass
        output = str(marker) + ".%(ext)s"
        command = self._ytdlp_command() + [
            url, "--no-playlist", "--no-warnings", "--retries", "1", "-o", output,
            "--downloader", "native", "--socket-timeout", "20", "--extractor-retries", "1",
            "--no-cache-dir", "--ignore-config",
            "--max-filesize", str(min(MAX_DOWNLOAD_BYTES, self._limit_bytes // 3)),
        ]
        if audio:
            command += ["-f", "bestaudio[ext=m4a][acodec^=mp4a]", "--match-filter", "duration < 900"]
        else:
            command += ["-f", f"bv[ext=mp4][vcodec^=avc1][height<={height}]/b[ext=mp4][vcodec^=avc1][height<={height}]"]
        try:
            result = self.run(command, capture_output=True, timeout=300)
            _sm.check_youtube_refusal(result.stderr)
            made = [p for p in self.media.glob(marker.name + ".*") if p.is_file()]
            valid = next(
                (p for p in made if p.suffix in (".m4a", ".mp4") and
                 (self._valid_audio(p) if audio else self._valid_video(p))),
                None,
            )
            if result.returncode != 0 or not valid:
                if audio:
                    raise _sm.ThemeMusicError(_sm.theme_failure_reason(result.stderr) if result.returncode else 'theme_format_unavailable')
                return None
            destination = self.media / (destination_stem + (".m4a" if audio else ".mp4"))
            if self.tool("ffmpeg"):
                if not self._ffmpeg_loop(valid, destination, preset, audio=audio, length=40 if audio else LOOP_SECONDS):
                    if audio:
                        raise _sm.ThemeMusicError('theme_encode_failed')
                    return None
            else:
                duration = _sm._bmff(valid, audio=audio)["duration"]
                if not 0 < duration <= (40 if audio else LOOP_SECONDS) + 0.5:
                    raise RuntimeError("YouTube requires ffmpeg for bounded clips on this system")
                self._promote(valid, destination)
            return destination
        finally:
            for path in self.media.glob(marker.name + ".*"):
                path.unlink(missing_ok=True)

    def resolve_canonical_name(self, appid: int, name: str = "") -> str:
        """Resolve English canonical title for searching YouTube."""
        appid_int = int(appid)
        if appid_int in self._canonical_title_cache:
            return self._canonical_title_cache[appid_int]
        try:
            data = self.store_data(appid_int, "english")
            canonical = data.get("name")
            if canonical and isinstance(canonical, str):
                cleaned = canonical.strip()
                self._canonical_title_cache[appid_int] = cleaned
                return cleaned
        except Exception:
            pass
        return name or str(appid_int)

    def build_theme(self, appid, name, settings):
        """Build theme audio track using English canonical title resolution."""
        if not settings.get("theme_music_consent"):
            return {"ok": False, "consent_required": True, "source": "theme"}
        if self._own_ytdlp() or not self.locate_ytdlp():
            self.install_ytdlp(True)

        canonical_name = self.resolve_canonical_name(appid, name)
        candidates = self.theme_candidates(canonical_name)

        made = self._download_youtube(candidates[0]["url"], f"{int(appid)}_theme", settings, audio=True)
        if not made:
            raise _sm.ThemeMusicError('theme_download_failed')
        return {"ok": True, "source": "theme", "file": self._relative(made)}

    def _maybe_theme(self, appid, name, settings, *, force=False):
        """Automatic background theme download with lock and per-game choice gate."""
        with self.music_lock:
            if not (is_music_enabled(settings, context="hub") or is_music_enabled(settings, context="home")):
                return None

            choices = settings.get("music_choices") or {}
            choice = choices.get(str(int(appid)), "auto")
            # Explicit none suppresses automatic theme downloads completely
            if choice == "none":
                return None

            self._configure(settings)
            self.enforce_limit(settings.get('disk_limit_gb',PC_DEFAULT_DISK_BUDGET_GB))

            if self.music_files(settings=None).get(str(int(appid))):
                return None

            state = self._state()
            if not isinstance(state.get("theme_attempts"), dict):
                state["theme_attempts"] = {}
            attempts = state["theme_attempts"]
            prior = attempts.get(str(int(appid))) or {}
            cooldown = _sm.YTDLP_ERROR_RETRY_SECONDS
            loader_version = (state.get('yt_dlp') or {}).get('version')
            if (not force and prior.get("ok") is False and prior.get('loader_version') == loader_version
                    and self.now() - float(prior.get("at") or 0) < cooldown):
                return {"ok": False, "retry_at": float(prior["at"]) + cooldown, "error": prior.get("error"), "reason": prior.get("reason")}

            try:
                self.active = {'appid': int(appid), 'kind': 'music'}
                self._reserve_job(int(appid))
                if isinstance(choice, str) and re.fullmatch(r'[A-Za-z0-9_-]{11}', choice):
                    made = self._download_youtube('https://www.youtube.com/watch?v=' + choice, f'{int(appid)}_theme', settings, audio=True)
                    result = {'ok': bool(made), 'source': 'theme', 'file': self._relative(made) if made else None}
                else:
                    result = self.build_theme(appid, name, settings)
            except _sm.YouTubeBlockedError as exc:
                result = {'ok': False, 'reason': 'youtube_blocked', 'error': str(exc)}
            except _sm.Python3RequiredError as exc:
                result = {'ok': False, 'reason': 'python3_required', 'error': str(exc)}
            except Exception as exc:
                reason = _sm.theme_failure_reason(exc)
                result = {"ok": False, "reason": reason, "error": reason}

            state = self._state()
            state.setdefault("theme_attempts", {})[str(int(appid))] = {
                "ok": bool(result.get("ok")),
                "at": self.now(),
                "error": result.get("error"),
                "reason": result.get("reason"),
                "loader_version": (state.get('yt_dlp') or {}).get('version'),
            }
            self._save_state(state)
            self.active = None
            return result

    def music_files(self, settings=None):
        """Return valid cached theme files, respecting per-game 'none' and consent toggles."""
        raw_files = super().music_files()
        if settings is None:
            return raw_files

        # If music is disabled by global settings, return empty map
        if not (is_music_enabled(settings, context="hub") or is_music_enabled(settings,context='home')):
            return {}

        choices = settings.get("music_choices") or {}
        # Filter out apps explicitly set to "none"
        return {
            appid: path
            for appid, path in raw_files.items()
            if choices.get(str(appid)) != "none"
        }

    def build(self, appid, name, settings, source=None, *, force=False):
        with self.music_lock:
            previous_deadline = self._operation_deadline
            self._operation_deadline = time.monotonic() + 600
            try:
                self.active = {'appid': int(appid), 'kind': 'background'}
                return self._build_locked(appid, name, settings, source, force=force)
            finally:
                self.active = None
                self._operation_deadline = previous_deadline

    def _build_locked(self, appid, name, settings, source=None, *, force=False):
        """Build game media with bounded fallback from Steam to YouTube when permitted.

        Fallback rules:
        - If primary is Steam or Auto:
          Attempt Steam first.
          If Steam has no suitable movie/fails AND youtube_consent is strictly True:
            Fall back to YouTube.
          If Steam fails and youtube_consent is False:
            Never fall back to YouTube; return failure with explanation.
        - Background build preserves existing per-game choices and unrelated cache.
        """
        self._configure(settings)
        appid_int = int(appid)
        if settings.get('live_bg') == 'off' or (settings.get('game_bg') or {}).get(str(appid_int)) in ('image','steam'):
            theme = self._maybe_theme(appid_int,name,settings,force=force)
            return {'ok':bool(theme.get('ok')) if theme is not None else True,'disabled':True,'source':'steam',**({'theme':theme} if theme is not None else {})}
        configured_source = str(
            source or (settings.get("game_source") or {}).get(str(appid_int))
            or settings.get("bg_source") or "steam"
        )
        if configured_source not in (*SOURCES, "auto"):
            return {"ok": False, "error": "unknown source", "source": configured_source}

        effective_source = "steam" if configured_source == "auto" else configured_source
        youtube_consent = settings.get("youtube_consent") is True and settings.get('media_fallback') is True

        state = self._state()
        if not isinstance(state.get("attempts"), dict):
            state["attempts"] = {}
        attempts = state["attempts"]
        key = f"{appid_int}:{effective_source}"
        prior = attempts.get(key) or {}
        preset = str(settings.get("media_quality") or settings.get("preset") or PC_DEFAULT_QUALITY)

        existing = self._asset(appid_int, effective_source)
        if existing and not force and prior.get("preset", preset) == preset:
            try:
                os.utime(existing, None)
            except OSError:
                pass
            result = {"ok": True, "cached": True, "source": effective_source, "file": self._relative(existing)}
            theme = self._maybe_theme(appid_int, name, settings,force=force)
            if theme is not None:
                result["theme"] = theme
            return result

        if not force and prior.get("ok") is False and self.now() - float(prior.get("at") or 0) < RETRY_SECONDS:
            result = {
                "ok": False,
                "retry_at": float(prior.get("at") or 0) + RETRY_SECONDS,
                "source": effective_source,
                "error": prior.get("error"),
            }
            theme = self._maybe_theme(appid_int, name, settings,force=force)
            if theme is not None:
                result['theme'] = theme
                result['ok'] = bool(theme.get('ok'))
            return result

        try:
            self._checkpoint()
            self.enforce_limit(settings.get("disk_limit_gb", PC_DEFAULT_DISK_BUDGET_GB))
            self._reserve_job(appid_int)

            result = None
            if effective_source == "steam":
                try:
                    result = self.build_steam(appid_int, name, settings)
                except Exception as steam_exc:
                    # Check fallback to YouTube
                    if youtube_consent:
                        try:
                            result = self.build_youtube(appid_int, name, settings)
                            result["fallback_from"] = "steam"
                        except Exception as yt_exc:
                            result = {
                                "ok": False,
                                "source": "steam",
                                "error": f"Steam failed ({steam_exc}); YouTube fallback failed ({yt_exc})"[:240],
                            }
                    else:
                        result = {
                            "ok": False,
                            "source": "steam",
                            "error": f"{type(steam_exc).__name__}: {steam_exc}"[:240],
                            "fallback_blocked": "youtube_consent required",
                        }
            elif effective_source == "youtube":
                result = self.build_youtube(appid_int, name, settings)
            else:
                result = self.build_recording(appid_int, name, settings)

            video_ok = bool(result and result.get('ok'))
            if result:
                theme = self._maybe_theme(appid_int, name, settings,force=force)
                if theme is not None:
                    result["theme"] = theme
                    if theme.get('ok'):
                        result['ok'] = True
                latest = self._state()
                for state_key in ("yt_dlp", "theme_attempts"):
                    if state_key in latest:
                        state[state_key] = latest[state_key]

            attempts[key] = {
                "ok": video_ok,
                "at": self.now(),
                "error": result.get("error") if result else "No result",
                "source": result.get("source", effective_source) if result else effective_source,
                "preset": preset,
                "local_start": (result or {}).get("local_start", 0) if (result or {}).get("uncut") else 0,
                "playback_seconds": (result or {}).get("playback_seconds", LOOP_SECONDS),
            }
        except Exception as exc:
            result = {"ok": False, "source": effective_source, "error": f"{type(exc).__name__}: {exc}"[:240]}
            attempts[key] = {"ok": False, "at": self.now(), "error": result["error"], "source": effective_source}

        latest = self._state()
        for state_key in ("yt_dlp", "theme_attempts"):
            if state_key in latest:
                state[state_key] = latest[state_key]
        self._save_state(state)

        try:
            result["cache"] = self.enforce_limit(settings.get("disk_limit_gb", PC_DEFAULT_DISK_BUDGET_GB))
        except OSError as exc:
            result["cache_error"] = f"{type(exc).__name__}: {exc}"[:240]

        return result
