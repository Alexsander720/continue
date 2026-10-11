"""Autonomous media cache for the public Continue? Deck release.

The module deliberately has no third-party Python dependencies.  It is only
constructed by ``main.py`` when ``RELEASE.json`` is present.  Network and
subprocess entry points are small so the clean-Deck harness can replace them.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import ssl
import subprocess
import struct
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path


SKIP_NAME = re.compile(
    r"teaser|tease|announcement|reveal|soundtrack|ost\b|interview|behind|dev ?diary|livestream",
    re.I,
)
TRUSTED = (
    "playstation", "xbox", "bandai", "naughty dog", "santa monica",
    "insomniac", "ign", "gamespot", "gametrailers", "devolver",
    "sony interactive", "konami", "thq nordic", "dire wolf",
)
RETRY_SECONDS = 7 * 86400
YTDLP_UPDATE_SECONDS = 7 * 86400
LOOP_SECONDS = 20
MAX_DOWNLOAD_BYTES = 512 * 1024 * 1024
CHUNK_BYTES = 64 * 1024
MAX_METADATA_BYTES = 8 * 1024 * 1024
ACTIVE_SECONDS = 120
GENERIC_STUDIO_WORDS = frozenset({
    "games", "game", "interactive", "studio", "studios", "entertainment",
    "digital", "publishing", "productions", "media", "inc", "ltd", "llc",
    "corporation", "company", "the", "and", "sa", "srl", "gmbh", "co",
})
SOURCES = ("steam", "youtube", "recording")
PRESETS = {
    "light": {"height": 720, "crf": 25, "min_free_gb": 0.25, "max_games": 40},
    "balanced": {"height": 720, "crf": 23, "min_free_gb": 0.5, "max_games": 40},
    "maximum": {"height": 1080, "crf": 21, "min_free_gb": 1, "max_games": 40},
}


def _ssl_context():
    try:
        import certifi  # type: ignore
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        cafile = "/etc/ssl/certs/ca-certificates.crt"
        return ssl.create_default_context(cafile=cafile if os.path.isfile(cafile) else None)


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _read_at(stream, offset, length):
    if length < 0 or length > MAX_METADATA_BYTES:
        raise ValueError("oversized media metadata")
    stream.seek(offset)
    raw = stream.read(length)
    if len(raw) != length:
        raise ValueError("truncated media metadata")
    return raw


def _boxes(stream, start, end):
    """Iterate bounded ISO BMFF boxes by seeking over media payloads."""
    count = 0
    while start < end:
        count += 1
        if count > 20000 or end - start < 8:
            raise ValueError("invalid media box table")
        size, kind = struct.unpack(">I4s", _read_at(stream, start, 8))
        header = 8
        if size == 1:
            size = struct.unpack(">Q", _read_at(stream, start + 8, 8))[0]
            header = 16
        elif size == 0:
            size = end - start
        if size < header or start + size > end:
            raise ValueError("truncated media box")
        yield kind, start, start + header, start + size
        start += size


def _children(stream, item):
    return list(_boxes(stream, item[2], item[3]))


def _one(items, kind):
    return next((item for item in items if item[0] == kind), None)


def _payload(stream, item):
    if not item:
        raise ValueError("required media metadata is missing")
    return _read_at(stream, item[2], item[3] - item[2])


def _uints(raw, offset=0):
    if (len(raw) - offset) % 4:
        raise ValueError("invalid sample metadata")
    return struct.unpack(">" + "I" * ((len(raw) - offset) // 4), raw[offset:])


def _bmff(path, *, audio=False, init_only=False):
    """Validate container structure, codec metadata and sample byte ranges.

    This is deliberately stricter than magic-byte sniffing, and deliberately
    does not claim to be a full H.264 decoder.  Encoded output is additionally
    decoded with ffmpeg before promotion when that executable is present.
    Only browser-compatible AVC MP4 / AAC M4A are accepted.
    """
    with Path(path).open("rb") as stream:
        size = os.fstat(stream.fileno()).st_size
        top = list(_boxes(stream, 0, size))
        ftyp = _payload(stream, _one(top, b"ftyp"))
        if len(ftyp) < 8 or len(ftyp) % 4:
            raise ValueError("invalid ftyp")
        moov = _one(top, b"moov")
        children = _children(stream, moov) if moov else []
        tracks = [item for item in children if item[0] == b"trak"]
        mdats = [(item[2], item[3]) for item in top if item[0] == b"mdat"]
        fragmented = bool(_one(children, b"mvex"))
        duration, codec, matching, width, height = 0.0, None, [], 0, 0
        scales, fragment_ticks = {}, {}
        for track in tracks:
            tkhd = _one(_children(stream, track), b"tkhd")
            mdia = _one(_children(stream, track), b"mdia")
            md = _children(stream, mdia) if mdia else []
            hdlr = _payload(stream, _one(md, b"hdlr"))
            if len(hdlr) < 12 or hdlr[8:12] != (b"soun" if audio else b"vide"):
                continue
            mdhd = _payload(stream, _one(md, b"mdhd"))
            if mdhd[0] == 0 and len(mdhd) >= 24:
                scale, ticks = struct.unpack(">II", mdhd[12:20])
            elif mdhd[0] == 1 and len(mdhd) >= 36:
                scale, ticks = struct.unpack(">IQ", mdhd[20:32])
            else:
                raise ValueError("invalid track duration")
            if scale <= 0:
                raise ValueError("invalid track timescale")
            if tkhd:
                raw = _payload(stream, tkhd)
                trackid = struct.unpack(">I", raw[20:24] if raw[0] == 1 else raw[12:16])[0]
                scales[trackid] = scale
            duration = max(duration, ticks / scale)
            minf = _one(md, b"minf")
            stbl = _one(_children(stream, minf), b"stbl") if minf else None
            tables = _children(stream, stbl) if stbl else []
            stsd = _payload(stream, _one(tables, b"stsd"))
            if len(stsd) < 16 or struct.unpack(">I", stsd[4:8])[0] != 1:
                raise ValueError("unsupported sample descriptions")
            sample_size, codec = struct.unpack(">I4s", stsd[8:16])
            if sample_size != len(stsd) - 8:
                raise ValueError("invalid codec sample description")
            offset = 8 + (36 if audio else 86)
            if codec not in ((b"mp4a",) if audio else (b"avc1", b"avc3")) or len(stsd) < offset:
                raise ValueError("unsupported browser media codec")
            if not audio:
                width, height = struct.unpack(">HH", stsd[40:44])
                if width <= 0 or height <= 0 or width > 8192 or height > 8192:
                    raise ValueError("invalid video sample dimensions")
            entry_start = _one(tables, b"stsd")[2] + offset
            entry_end = _one(tables, b"stsd")[3]
            codec_boxes = list(_boxes(stream, entry_start, entry_end))
            config = _payload(stream, _one(codec_boxes, b"esds" if audio else b"avcC"))
            if len(config) < (8 if audio else 7) or (not audio and config[0] != 1):
                raise ValueError("invalid codec configuration")
            if init_only:
                matching.append(True)
                continue
            stsz = _payload(stream, _one(tables, b"stsz"))
            if len(stsz) < 12:
                raise ValueError("invalid sample sizes")
            constant, samples = struct.unpack(">II", stsz[4:12])
            if samples > 2000000 or len(stsz) != 12 + (0 if constant else 4 * samples):
                raise ValueError("invalid sample count")
            if samples == 0:
                if not fragmented:
                    raise ValueError("empty media track")
                matching.append(True)
                continue
            sizes = _uints(stsz, 12) if not constant else ()
            if not constant and any(value <= 0 for value in sizes):
                raise ValueError("empty media samples")
            stts = _payload(stream, _one(tables, b"stts"))
            times = _uints(stts, 8)
            if len(stts) < 8 or len(times) != struct.unpack(">I", stts[4:8])[0] * 2:
                raise ValueError("invalid sample timing")
            if sum(times[::2]) != samples or any(t <= 0 for t in times[1::2]):
                raise ValueError("invalid sample duration")
            offsets_box = _one(tables, b"stco") or _one(tables, b"co64")
            offsets_raw = _payload(stream, offsets_box)
            width = 8 if offsets_box[0] == b"co64" else 4
            chunks = struct.unpack(">I", offsets_raw[4:8])[0]
            if chunks < 1 or chunks > 1000000 or len(offsets_raw) != 8 + chunks * width:
                raise ValueError("invalid chunk offsets")
            offsets = struct.unpack(">" + ("Q" if width == 8 else "I") * chunks, offsets_raw[8:])
            stsc = _payload(stream, _one(tables, b"stsc"))
            mapping = _uints(stsc, 8)
            if len(stsc) < 20 or len(mapping) != struct.unpack(">I", stsc[4:8])[0] * 3 or mapping[0] != 1:
                raise ValueError("invalid sample chunk table")
            rows = list(zip(mapping[::3], mapping[1::3], mapping[2::3]))
            if any(a < 1 or b < 1 or c != 1 for a, b, c in rows) or any(rows[i][0] >= rows[i + 1][0] for i in range(len(rows) - 1)):
                raise ValueError("invalid sample chunk mapping")
            sample_index, row_index = 0, 0
            for chunk_index, byte_offset in enumerate(offsets, 1):
                if row_index + 1 < len(rows) and chunk_index >= rows[row_index + 1][0]:
                    row_index += 1
                n = rows[row_index][1]
                length = constant * n if constant else sum(sizes[sample_index:sample_index + n])
                if length <= 0 or sample_index + n > samples or not any(a <= byte_offset and byte_offset + length <= b for a, b in mdats):
                    raise ValueError("sample bytes extend outside mdat")
                sample_index += n
            if sample_index != samples:
                raise ValueError("missing media sample bytes")
            matching.append(True)
        if not matching:
            raise ValueError("no supported media track")
        if init_only:
            return {"codec": codec.decode(), "duration": duration, "fragmented": fragmented, "width": width, "height": height}
        if not mdats:
            raise ValueError("missing media payload")
        if fragmented:
            defaults = {}
            mvex = _one(children, b"mvex")
            for trex in _children(stream, mvex):
                if trex[0] == b"trex":
                    raw = _payload(stream, trex)
                    if len(raw) != 24:
                        raise ValueError("invalid fragment defaults")
                    trackid, _, tick, sample_size, _ = struct.unpack(">IIIII", raw[4:])
                    defaults[trackid] = (tick, sample_size)
            fragments, sample_total = 0, 0
            for moof in [item for item in top if item[0] == b"moof"]:
                fragments += 1
                next_mdat = next(((a, b) for a, b in mdats if a > moof[1]), None)
                if not next_mdat:
                    raise ValueError("fragment has no mdat")
                for traf in [item for item in _children(stream, moof) if item[0] == b"traf"]:
                    tf = _children(stream, traf)
                    header = _payload(stream, _one(tf, b"tfhd"))
                    flags = int.from_bytes(header[1:4], "big")
                    trackid = struct.unpack(">I", header[4:8])[0]
                    tick, default_size = defaults.get(trackid, (0, 0))
                    pos, base = 8, moof[1]
                    if flags & 1:
                        base = struct.unpack(">Q", header[pos:pos + 8])[0]
                        pos += 8
                    if flags & 2:
                        pos += 4
                    if flags & 8:
                        tick = struct.unpack(">I", header[pos:pos + 4])[0]
                        pos += 4
                    if flags & 16:
                        default_size = struct.unpack(">I", header[pos:pos + 4])[0]
                        pos += 4
                    cursor = next_mdat[0]
                    for trun in [item for item in tf if item[0] == b"trun"]:
                        raw = _payload(stream, trun)
                        flags = int.from_bytes(raw[1:4], "big")
                        count = struct.unpack(">I", raw[4:8])[0]
                        if not 0 < count <= 2000000:
                            raise ValueError("invalid fragment sample count")
                        pos, length = 8, 0
                        if flags & 1:
                            cursor = base + struct.unpack(">i", raw[pos:pos + 4])[0]
                            pos += 4
                        if flags & 4:
                            pos += 4
                        for _ in range(count):
                            d, n = tick, default_size
                            if flags & 0x100:
                                d = struct.unpack(">I", raw[pos:pos + 4])[0]
                                pos += 4
                            if flags & 0x200:
                                n = struct.unpack(">I", raw[pos:pos + 4])[0]
                                pos += 4
                            if flags & 0x400:
                                pos += 4
                            if flags & 0x800:
                                pos += 4
                            if n <= 0 or d <= 0:
                                raise ValueError("empty or untimed fragment sample")
                            length += n
                            fragment_ticks[trackid] = fragment_ticks.get(trackid, 0) + d
                        if pos != len(raw) or not any(a <= cursor and cursor + length <= b for a, b in mdats):
                            raise ValueError("fragment sample bytes extend outside mdat")
                        cursor += length
                        sample_total += count
            if not fragments or not sample_total:
                raise ValueError("empty fragmented media")
            if scales:
                duration = max((ticks / scales[tid] for tid, ticks in fragment_ticks.items() if tid in scales), default=0)
        return {"codec": codec.decode(), "duration": duration, "fragmented": fragmented, "width": width, "height": height}


class MediaManager:
    """Owns files created by the autonomous public release.

    ``urlopen`` and ``run`` are injectable for deterministic offline tests.
    Every completed asset is first written beside its destination and then
    installed with ``os.replace``.  A failed attempt never replaces a valid
    cached file.
    """

    def __init__(self, data_dir, plugin_dir=None, *, urlopen=None, run=None, now=None, allowed=None):
        self.data = Path(data_dir)
        self.plugin_dir = Path(plugin_dir or Path(__file__).resolve().parents[1])
        self.media = self.data / "media"
        self.bin = self.data / "bin"
        self.state_path = self.data / "standalone_media.json"
        self.urlopen = urlopen or urllib.request.urlopen
        self._injected_run = run
        self.run = self._run
        self.now = now or time.time
        self.allowed = allowed or (lambda: True)
        self._cancelled = False
        self._limit_bytes = 2 * 1024 ** 3
        self._min_free_bytes = int(0.5 * 1024 ** 3)
        self._max_games = 40

    def cancel(self):
        """Cooperatively stop this manager's work; never kill Steam processes."""
        self._cancelled = True

    def _checkpoint(self):
        if self._cancelled or not self.allowed():
            raise RuntimeError("media work deferred: cancelled or no longer allowed")

    def _run(self, command, *, capture_output=True, text=False, timeout=180, **kwargs):
        self._checkpoint()
        if self._injected_run:
            result = self._injected_run(command, capture_output=capture_output, text=text, timeout=timeout, **kwargs)
            self._checkpoint()
            return result
        # Files avoid pipe deadlocks and bounded search/frame output reads avoid
        # keeping a large subprocess payload in memory.  Only our child stops.
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            proc = subprocess.Popen(command, stdout=stdout, stderr=stderr, **kwargs)
            started = time.monotonic()
            try:
                while proc.poll() is None:
                    self._checkpoint()
                    self._check_space(0)
                    if time.monotonic() - started > timeout:
                        raise subprocess.TimeoutExpired(command, timeout)
                    time.sleep(0.2)
                self._checkpoint()
                for output in (stdout, stderr):
                    if output.tell() > 16 * 1024 * 1024:
                        raise RuntimeError("subprocess output exceeds bounded metadata limit")
                    output.seek(0)
                out, err = stdout.read(), stderr.read()
                if text:
                    out, err = out.decode("utf-8", "replace"), err.decode("utf-8", "replace")
                return subprocess.CompletedProcess(command, proc.returncode, out, err)
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=3)

    def _configure(self, settings):
        profile = PRESETS.get(str(settings.get("preset") or "light"), PRESETS["light"])
        try:
            limit = float(settings.get("disk_limit_gb", 2))
            free = float(settings.get("min_free_gb", max(0.5, profile["min_free_gb"])))
            if not math.isfinite(limit) or not math.isfinite(free):
                raise ValueError("non-finite cache setting")
            self._limit_bytes = max(256 * 1024 ** 2, int(limit * 1024 ** 3))
            self._min_free_bytes = max(0, int(free * 1024 ** 3))
        except (TypeError, ValueError, OverflowError):
            self._limit_bytes, self._min_free_bytes = 2 * 1024 ** 3, int(0.5 * 1024 ** 3)
        self._max_games = max(1, min(40, _safe_int(settings.get("max_cached_games"), profile["max_games"])))

    def _cache_bytes(self):
        if not self.media.exists():
            return 0
        total = 0
        for p in self.media.rglob("*"):
            try:
                if p.is_file():
                    total += p.stat().st_size
            except OSError:
                continue
        return total

    def _check_space(self, additional):
        self.data.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(self.data).free < self._min_free_bytes + additional:
            raise RuntimeError("insufficient free disk space for media")
        if self._cache_bytes() + additional > self._limit_bytes:
            raise RuntimeError("media cache budget exceeded including temporary files")

    def _reserve_job(self, appid):
        """Reserve scratch space by evicting oldest OTHER games before I/O.

        Keep the game's old loop through failures. Final assets and scratch
        count toward the same budget. One job is active at a time in main.py.
        """
        reserve = min(MAX_DOWNLOAD_BYTES, self._limit_bytes // 3)
        groups = {}
        if self.media.exists():
            for path in self.media.iterdir():
                if path.name.split("_", 1)[0] == str(appid) or ".part" in path.name:
                    continue
                try:
                    if path.is_file():
                        groups.setdefault(path.name.split("_", 1)[0], []).append((path, path.stat()))
                except OSError:
                    continue
        for files in sorted(groups.values(), key=lambda rows: max(st.st_mtime for _, st in rows)):
            if self._cache_bytes() + reserve <= self._limit_bytes:
                break
            for path, _ in files:
                path.unlink(missing_ok=True)
        self._check_space(0)

    def _promote(self, part, destination):
        self._checkpoint()
        self._check_space(0)
        os.replace(part, destination)

    # ---- small, testable I/O helpers -------------------------------------------------

    def _open(self, request, timeout=20):
        self._checkpoint()
        try:
            response = self.urlopen(request, timeout=timeout, context=_ssl_context())
        except TypeError:  # simple harness stubs often do not accept context
            response = self.urlopen(request, timeout=timeout)
        final_url = getattr(response, "geturl", lambda: None)()
        if final_url and urllib.parse.urlparse(str(final_url)).scheme != "https":
            close = getattr(response, "close", None)
            if close:
                close()
            raise RuntimeError("network redirect downgraded from HTTPS")
        return response

    def _bytes(self, url, timeout=30, limit=MAX_METADATA_BYTES):
        # Only bounded JSON/manifests/checksum text; assets stream to disk.
        url = self._https(url)
        limit = min(MAX_METADATA_BYTES, limit)
        req = urllib.request.Request(url, headers={"User-Agent": "Continue-Deck/1"})
        response = self._open(req, timeout)
        chunks, size = [], 0
        try:
            while True:
                self._checkpoint()
                chunk = response.read(min(CHUNK_BYTES, limit - size + 1))
                if not chunk:
                    break
                size += len(chunk)
                if size > limit:
                    raise ValueError("download exceeds cache safety limit")
                chunks.append(chunk)
        finally:
            close = getattr(response, "close", None)
            if close:
                close()
        return b"".join(chunks)

    def _json_url(self, url, timeout=20):
        return json.loads(self._bytes(url, timeout=timeout, limit=8 * 1024 * 1024).decode("utf-8", "replace"))

    @staticmethod
    def _atomic_bytes(path, data):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".part", dir=str(path.parent))
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, path)
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    @staticmethod
    def _atomic_json(path, value):
        raw = (json.dumps(value, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
        MediaManager._atomic_bytes(path, raw)

    def _state(self):
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def _save_state(self, state):
        try:
            self._atomic_json(self.state_path, state)
        except OSError:
            pass

    @staticmethod
    def _valid_video(path):
        try:
            _bmff(path)
            return True
        except (OSError, ValueError, TypeError, IndexError, struct.error, OverflowError):
            return False

    @staticmethod
    def _valid_audio(path):
        try:
            _bmff(path, audio=True)
            return True
        except (OSError, ValueError, TypeError, IndexError, struct.error, OverflowError):
            return False

    @staticmethod
    def _valid_image(path):
        try:
            with Path(path).open("rb") as source:
                head = source.read(32)
        except OSError:
            return False
        return (head.startswith(b"\x89PNG\r\n\x1a\n") and head[12:16] == b"IHDR") or head.startswith(b"\xff\xd8\xff") or (head[:4] == b"RIFF" and head[8:12] == b"WEBP")

    def _stream(self, url, destination, *, limit=MAX_DOWNLOAD_BYTES, append=False, timeout=60):
        self._checkpoint()
        self._check_space(0)
        url = self._https(url)
        req = urllib.request.Request(url, headers={"User-Agent": "Continue-Deck/1"})
        response = self._open(req, timeout)
        size = 0
        try:
            destination = Path(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            headers = getattr(response, "headers", {})
            expected = _safe_int(headers.get("Content-Length"), -1)
            if expected > limit:
                raise ValueError("download exceeds cache safety limit")
            with destination.open("ab" if append else "wb") as target:
                while True:
                    self._checkpoint()
                    chunk = response.read(min(CHUNK_BYTES, limit - size + 1))
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > limit:
                        raise ValueError("download exceeds cache safety limit")
                    self._check_space(len(chunk))
                    target.write(chunk)
                target.flush()
                os.fsync(target.fileno())
            if expected >= 0 and expected != size:
                raise ValueError("truncated HTTP body")
        finally:
            response.close()
        return size

    def _download_atomic(self, url, destination, *, kind="video", limit=MAX_DOWNLOAD_BYTES):
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        part = destination.with_name(destination.name + ".download.part")
        try:
            self._stream(url, part, limit=limit)
            valid = self._valid_video(part) if kind == "video" else self._valid_image(part)
            if not valid:
                raise ValueError(f"downloaded {kind} failed structural validation")
            self._promote(part, destination)
        finally:
            try:
                part.unlink()
            except OSError:
                pass
        return destination

    # ---- cache contract ---------------------------------------------------------------

    def _asset(self, appid, source):
        stem = f"{int(appid)}_{source}"
        for ext in (".mp4", ".webm", ".mkv", ".mov"):
            path = self.media / (stem + ext)
            if self._valid_video(path):
                return path
        return None

    def _image(self, appid, kind):
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            path = self.media / f"{int(appid)}_{kind}{ext}"
            if self._valid_image(path):
                return path
        return None

    def _relative(self, path):
        return Path(path).relative_to(self.data).as_posix() if path else None

    def media_for(self, appid, settings):
        appid = int(appid)
        source = str((settings.get("game_source") or {}).get(str(appid)) or settings.get("bg_source") or "steam")
        if source not in SOURCES:
            source = "steam"
        steam = self._asset(appid, "steam")
        youtube = self._asset(appid, "youtube")
        recording = self._asset(appid, "recording")
        trailer = youtube if source == "youtube" and youtube else steam or youtube
        chosen = recording if source == "recording" else trailer
        if chosen is None:
            chosen = steam or youtube or recording
        out = {
            "loop": self._relative(chosen),
            "trl": self._relative(trailer),
            "rec": self._relative(recording),
            "wall": self._relative(self._image(appid, "wall")),
            "logo": self._relative(self._image(appid, "logo")),
            "source": source,
            "available_sources": [s for s, p in (("steam", steam), ("youtube", youtube), ("recording", recording)) if p],
        }
        attempts = self._state().get("attempts") or {}
        out["video_windows"] = {self._relative(path): {"start": (attempts.get(f"{appid}:{kind}") or {}).get("local_start", 0),
                                                      "seconds": LOOP_SECONDS}
                                for kind, path in (("steam", steam), ("youtube", youtube), ("recording", recording)) if path}
        return {k: v for k, v in out.items() if v not in (None, [], "")}

    def music_files(self):
        out = {}
        try:
            paths = list(self.media.glob("*_theme.*")) if self.media.exists() else []
        except OSError:
            return out
        for path in paths:
            try:
                appid = path.name.split("_", 1)[0]
                if appid.isdigit() and self._valid_audio(path):
                    out[appid] = self._relative(path)
            except OSError:
                continue
        return out

    def status(self):
        files = []
        error = None
        try:
            if self.media.exists():
                files = [p for p in self.media.iterdir() if p.is_file() and ".part" not in p.name]
            used = self._cache_bytes()
            tool = bool(self.locate_ytdlp())
        except OSError as exc:
            used, tool = 0, False
            error = f"{type(exc).__name__}: {exc}"[:240]
        games = {p.name.split("_", 1)[0] for p in files
                 if "_" in p.name and p.name.split("_", 1)[0].isdigit()}
        state = self._state()
        return {
            "cached_backgrounds": sum(1 for appid in games if any(self._asset(appid, s) for s in SOURCES)),
            "cached_games": len(games),
            "bytes": used,
            "ffmpeg": bool(shutil.which("ffmpeg")),
            "ffprobe": bool(shutil.which("ffprobe")),
            "node": bool(shutil.which("node")),
            "yt_dlp": tool,
            "yt_dlp_checked_at": (state.get("yt_dlp") or {}).get("checked_at"),
            "youtube_experimental": not bool(shutil.which("node")),
            "error": error,
        }

    def clear(self):
        removed, freed = 0, 0
        try:
            paths = list(self.media.iterdir()) if self.media.exists() else []
        except OSError as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:240]}
        if self.media.exists():
            for path in paths:
                if not path.is_file():
                    continue
                try:
                    size = path.stat().st_size
                    path.unlink()
                    removed += 1
                    freed += size
                except OSError:
                    pass
        state = self._state()
        state["attempts"] = {}
        self._save_state(state)
        return {"ok": True, "removed": removed, "bytes": freed}

    def enforce_limit(self, limit_gb):
        try:
            limit = max(256 * 1024 * 1024, int(float(limit_gb) * 1024 ** 3))
        except (TypeError, ValueError, OverflowError):
            limit = 2 * 1024 ** 3
        if not self.media.exists():
            return {"removed_games": 0, "bytes": 0}
        groups = {}
        try:
            paths = list(self.media.iterdir())
        except OSError as exc:
            return {"removed_games": 0, "bytes": 0, "error": f"{type(exc).__name__}: {exc}"[:240]}
        mtimes = {}
        for path in paths:
            if not path.is_file() or path.name.endswith(".part"):
                continue
            appid = path.name.split("_", 1)[0]
            try:
                if appid.isdigit():
                    mtimes[path] = path.stat().st_mtime
                    groups.setdefault(appid, []).append(path)
            except OSError:
                continue
        try:
            total = self._cache_bytes()
        except OSError:
            total = self._limit_bytes + 1
        removed = 0
        ordered = sorted(groups.values(), key=lambda ps: max(mtimes[p] for p in ps))
        for paths in ordered:
            if total <= limit and len(groups) - removed <= self._max_games:
                break
            for path in paths:
                try:
                    total -= path.stat().st_size
                    path.unlink()
                except OSError:
                    pass
            removed += 1
        return {"removed_games": removed, "bytes": max(0, total)}

    # ---- Steam Store -----------------------------------------------------------------

    def store_data(self, appid, language="english"):
        lang = urllib.parse.quote(str(language or "english"))
        url = f"https://store.steampowered.com/api/appdetails?appids={int(appid)}&l={lang}&filters=basic,movies"
        node = (self._json_url(url).get(str(int(appid))) or {})
        return (node.get("data") or {}) if node.get("success") else {}

    @staticmethod
    def pick_movie(data):
        movies = [m for m in (data.get("movies") or []) if m.get("hls_h264") or (m.get("mp4") or {}).get("max")]
        good = [m for m in movies if not SKIP_NAME.search(str(m.get("name") or ""))]
        ranked = sorted(good or movies, key=lambda m: (not m.get("highlight"), "trailer" not in str(m.get("name") or "").lower()))
        return ranked[0] if ranked else None

    def best_variant(self, master_url, max_height):
        text = self._bytes(master_url, timeout=20, limit=2 * 1024 * 1024).decode("utf-8", "replace")
        variants = []
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if not line.startswith("#EXT-X-STREAM-INF"):
                continue
            match = re.search(r"RESOLUTION=\d+x(\d+)", line)
            height = int(match.group(1)) if match else 0
            uri = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if not uri or uri.startswith("#"):
                continue
            codec = re.search(r'CODECS="([^"]+)"', line)
            if codec and not any(c.strip().startswith(("avc1", "avc3")) for c in codec.group(1).split(",")):
                continue
            variants.append((height, urllib.parse.urljoin(master_url, uri)))
        if variants:
            within = [row for row in variants if 0 < row[0] <= max_height]
            if not within:
                raise RuntimeError("HLS has no resolution within the selected preset")
            return max(within)[1]
        if "#EXT-X-STREAM-INF" in text:
            raise RuntimeError("HLS has no browser-compatible H.264 variant")
        return master_url

    @staticmethod
    def _https(url):
        parsed = urllib.parse.urlparse(str(url))
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise RuntimeError("media download requires an HTTPS URL")
        return str(url)

    def _download_hls(self, master_url, destination, max_height):
        """Download a bounded middle window; ffmpeg never opens remote URLs.

        VOD fMP4 playlists only.  Encryption, byte ranges, changing init data,
        discontinuities and live playlists fail safely to the cached picture.
        """
        source = self.best_variant(self._https(master_url), max_height)
        playlist = self._bytes(source, limit=2 * 1024 * 1024).decode("utf-8", "replace")
        if not playlist.lstrip().startswith("#EXTM3U"):
            raise RuntimeError("invalid HLS playlist")
        if any(line.startswith("#EXT-X-KEY:") and "METHOD=NONE" not in line for line in playlist.splitlines()):
            raise RuntimeError("encrypted HLS is unsupported")
        if "#EXT-X-ENDLIST" not in playlist:
            raise RuntimeError("live HLS is not a completed trailer")
        if any(tag in playlist for tag in ("#EXT-X-BYTERANGE", "#EXT-X-DISCONTINUITY")):
            raise RuntimeError("HLS ranges/discontinuities are unsupported")
        init_urls, segments, length = set(), [], None
        for line in playlist.splitlines():
            line = line.strip()
            if line.startswith("#EXT-X-MAP:"):
                match = re.search(r'URI="([^"]+)"', line)
                if not match or "BYTERANGE=" in line:
                    raise RuntimeError("HLS init range is unsupported")
                init_urls.add(self._https(urllib.parse.urljoin(source, match.group(1))))
            elif line.startswith("#EXTINF:"):
                length = float(line.partition(":")[2].split(",", 1)[0])
                if not math.isfinite(length) or not 0 < length <= LOOP_SECONDS:
                    raise RuntimeError("invalid HLS segment duration")
            elif line and not line.startswith("#"):
                if length is None:
                    raise RuntimeError("HLS segment duration is missing")
                segments.append((self._https(urllib.parse.urljoin(source, line)), length))
                length = None
        if len(init_urls) != 1 or not segments or len(segments) > 2000:
            raise RuntimeError("HLS requires one fMP4 initialization map")
        total = sum(row[1] for row in segments)
        if total < LOOP_SECONDS:
            raise RuntimeError("Steam trailer is shorter than 20 seconds")
        target = max(0, (total - LOOP_SECONDS) / 2)
        window, cursor, before = [], 0.0, 0.0
        for url, length in segments:
            if cursor + length > target and cursor < target + LOOP_SECONDS:
                if not window:
                    before = cursor
                window.append((url, length))
            cursor += length
        destination = Path(destination)
        try:
            used = self._stream(next(iter(init_urls)), destination, limit=MAX_METADATA_BYTES)
            init_info = _bmff(destination, init_only=True)
            if int(init_info.get("height") or 0) > int(max_height):
                raise RuntimeError("HLS media playlist exceeds the selected preset resolution")
            for url, _ in window:
                used += self._stream(url, destination, append=True, limit=MAX_DOWNLOAD_BYTES - used)
            self._normalize_fragments(destination)
            if not self._valid_video(destination):
                raise RuntimeError("downloaded HLS fragments failed structural validation")
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        return {"duration": total, "local_duration": sum(row[1] for row in window),
                "start": target, "local_start": target - before, "segments": len(window)}

    @staticmethod
    def _normalize_fragments(path):
        """Rebase copied fMP4 decode timestamps to zero without reencoding.

        Fragment offsets are moof-relative and unchanged; validation rejects
        absolute offsets that no longer address the copied fragment payload.
        """
        starts = {}
        with Path(path).open("r+b") as stream:
            end = os.fstat(stream.fileno()).st_size
            top = list(_boxes(stream, 0, end))
            for moof in (item for item in top if item[0] == b"moof"):
                for traf in (item for item in _children(stream, moof) if item[0] == b"traf"):
                    rows = _children(stream, traf)
                    header = _payload(stream, _one(rows, b"tfhd"))
                    tid = struct.unpack(">I", header[4:8])[0]
                    tfdt = _one(rows, b"tfdt")
                    if not tfdt:
                        raise ValueError("fragment decode timestamp missing")
                    raw = _payload(stream, tfdt)
                    fmt = ">Q" if raw[0] == 1 else ">I"
                    width = 8 if raw[0] == 1 else 4
                    timestamp = struct.unpack(fmt, raw[4:4 + width])[0]
                    first = starts.setdefault(tid, timestamp)
                    if timestamp < first:
                        raise ValueError("fragment decode timestamps not ordered")
                    stream.seek(tfdt[2] + 4)
                    stream.write(struct.pack(fmt, timestamp - first))
        return _bmff(path)

    def _probe_duration(self, source):
        if urllib.parse.urlparse(str(source)).scheme in ("http", "https"):
            raise RuntimeError("ffprobe remote media is disabled")
        try:
            duration = float(_bmff(source)["duration"])
            if duration > 0:
                return duration
        except (OSError, ValueError, KeyError, struct.error):
            pass
        probe = shutil.which("ffprobe")
        if not probe:
            return 0.0
        try:
            result = self.run(
                [probe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(source)],
                capture_output=True, text=True, timeout=90,
            )
            return float((result.stdout or "").strip()) if result.returncode == 0 else 0.0
        except (OSError, ValueError, subprocess.SubprocessError):
            return 0.0

    def _ffmpeg_loop(self, source, destination, preset, *, start=None, length=LOOP_SECONDS, audio=False):
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return None
        profile = PRESETS.get(preset, PRESETS["light"])
        duration = self._probe_duration(source)
        if urllib.parse.urlparse(str(source)).scheme in ("http", "https"):
            raise RuntimeError("ffmpeg remote media is disabled")
        start = max(0.0, (duration - length) / 2) if start is None and duration else float(start or 0)
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        part = destination.with_name(destination.stem + ".encode.part" + destination.suffix)
        vf = f"scale=-2:'min({profile['height']},ih)'"
        commands = [
            [ffmpeg, "-v", "error", "-y", "-protocol_whitelist", "file,pipe", "-ss", f"{start:.3f}", "-i", str(source), "-t", str(length),
             "-an", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", str(profile["crf"]),
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(part)],
        ]
        if audio:
            commands = [[ffmpeg, "-v", "error", "-y", "-protocol_whitelist", "file,pipe", "-ss", f"{start:.3f}",
                         "-i", str(source), "-t", str(length), "-vn", "-c:a", "aac", "-b:a", "128k", str(part)]]
        try:
            for command in commands:
                try:
                    result = self.run(command, capture_output=True, timeout=180)
                except (OSError, subprocess.SubprocessError):
                    continue
                valid = self._valid_audio(part) if audio else self._valid_video(part)
                if result.returncode == 0 and valid:
                    decoded = self.run([ffmpeg, "-v", "error", "-xerror", "-protocol_whitelist", "file,pipe", "-i", str(part),
                                        "-f", "null", "-"], capture_output=True, timeout=120)
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

    def _cache_store_images(self, appid, data):
        results = {}
        for kind, keys in (("wall", ("background_raw", "background", "header_image")), ("logo", ("library_logo",))):
            url = next((data.get(k) for k in keys if data.get(k)), None)
            if kind == "logo" and not url:
                # Same public library art filename as steam_data.py. A capsule
                # is not a transparent logo; 404 safely leaves the text title.
                url = f"https://cdn.akamai.steamstatic.com/steam/apps/{int(appid)}/library_logo.png"
            if not url:
                continue
            ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
            if ext not in (".jpg", ".jpeg", ".png", ".webp"):
                ext = ".jpg"
            dst = self.media / f"{int(appid)}_{kind}{ext}"
            if self._valid_image(dst):
                results[kind] = self._relative(dst)
                continue
            try:
                self._download_atomic(url, dst, kind="image", limit=24 * 1024 * 1024)
                results[kind] = self._relative(dst)
            except Exception:
                pass
        return results

    def build_steam(self, appid, name, settings):
        self._configure(settings)
        self._check_space(0)
        data = self.store_data(appid, "english")
        self._cache_store_images(appid, data)
        movie = self.pick_movie(data)
        if not movie:
            raise RuntimeError("Steam Store has no suitable movie")
        destination = self.media / f"{int(appid)}_steam.mp4"
        preset = str(settings.get("preset") or "light")
        hls = movie.get("hls_h264")
        if hls:
            local = destination.with_name(destination.name + ".hls.part")
            try:
                window = self._download_hls(hls, local, PRESETS.get(preset, PRESETS["light"])["height"])
                if shutil.which("ffmpeg"):
                    made = self._ffmpeg_loop(local, destination, preset, start=window["local_start"])
                    if not made:
                        raise RuntimeError("ffmpeg could not produce a valid Steam loop")
                    return {"ok": True, "source": "steam", "movie": movie.get("name"), **window, **made}
                self._promote(local, destination)
                return {"ok": True, "source": "steam", "movie": movie.get("name"), **window,
                        "encoded": False, "uncut": True, "playback_seconds": LOOP_SECONDS,
                        "fallback": "bounded H.264 fMP4 segment window; browser limits playback to 20s"}
            except RuntimeError:
                if not (movie.get("mp4") or {}):
                    raise
            finally:
                local.unlink(missing_ok=True)
        mp4 = movie.get("mp4") or {}
        direct = mp4.get("max") or mp4.get("480")
        if not direct:
            raise RuntimeError("Steam movie has HLS only and ffmpeg is unavailable")
        if shutil.which("ffmpeg"):
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
            info = _bmff(local)
            duration = info["duration"]
            if info["height"] > PRESETS.get(preset, PRESETS["light"])["height"]:
                raise RuntimeError("progressive trailer exceeds preset resolution and requires ffmpeg")
            if not 0 < duration <= LOOP_SECONDS + 0.5:
                raise RuntimeError("progressive trailer requires ffmpeg to trim; use bounded HLS or static background")
            self._promote(local, destination)
        finally:
            local.unlink(missing_ok=True)
        return {"ok": True, "source": "steam", "movie": movie.get("name"), "encoded": False,
                "uncut": True, "playback_seconds": LOOP_SECONDS, "fallback": "validated short progressive MP4"}

    # ---- verified yt-dlp zipapp ------------------------------------------------------

    def _own_ytdlp(self):
        path = self.bin / "yt-dlp"
        if not path.is_file() or path.stat().st_size < 512 * 1024:
            return None
        digest = (self._state().get("yt_dlp") or {}).get("sha256")
        return path if digest and self._hash_file(path) == digest else None

    @staticmethod
    def _hash_file(path):
        digest = hashlib.sha256()
        with Path(path).open("rb") as stream:
            for chunk in iter(lambda: stream.read(CHUNK_BYTES), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def locate_ytdlp(self):
        own = self._own_ytdlp()
        if own:
            return own
        # Optional reuse only.  No autonomous operation depends on this plugin.
        candidates = (
            "/home/deck/homebrew/plugins/SDH-GameThemeMusic/yt-dlp",
            "/home/deck/homebrew/data/SDH-GameThemeMusic/yt-dlp",
            "/home/deck/homebrew/data/SDH-GameThemeMusic/bin/yt-dlp",
        )
        return next((Path(p) for p in candidates if Path(p).is_file()), None)

    def install_ytdlp(self, consent=False, force=False):
        if not consent:
            return {"ok": False, "consent_required": True}
        state = self._state()
        previous = state.get("yt_dlp") or {}
        own = self._own_ytdlp()
        checked = previous.get("checked_at")
        if checked is not None and self.now() - float(checked) < YTDLP_UPDATE_SECONDS and not (force and previous.get("error")):
            return {"ok": bool(own), "path": str(own) if own else None, "updated": False,
                    "retry_at": float(checked) + YTDLP_UPDATE_SECONDS, "error": previous.get("error"),
                    "node": bool(shutil.which("node")), "experimental": not bool(shutil.which("node"))}
        # Record attempts before I/O. Explicit force retries a failed attempt;
        # successful installation/update checks keep the weekly bandwidth window.
        state["yt_dlp"] = {**previous, "checked_at": self.now()}
        self._save_state(state)
        part = self.bin / "yt-dlp.download.part"
        try:
            self._checkpoint()
            self._check_space(0)
            release = self._json_url("https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest")
            version = str(release.get("tag_name") or "")
            if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", version):
                raise RuntimeError("invalid official yt-dlp release tag")
            assets = {a.get("name"): a.get("browser_download_url") for a in release.get("assets") or []}
            for name in ("yt-dlp", "SHA2-256SUMS"):
                expected = f"https://github.com/yt-dlp/yt-dlp/releases/download/{version}/{name}"
                if assets.get(name) != expected:
                    raise RuntimeError("yt-dlp asset is not from the official GitHub release")
            sums = self._bytes(assets["SHA2-256SUMS"], limit=4 * 1024 * 1024).decode("utf-8", "replace")
            match = re.search(r"(?mi)^([0-9a-f]{64})\s+\*?yt-dlp\s*$", sums)
            if not match:
                raise RuntimeError("yt-dlp checksum is missing from SHA2-256SUMS")
            self._stream(assets["yt-dlp"], part, timeout=120, limit=32 * 1024 * 1024)
            digest = self._hash_file(part)
            if digest != match.group(1).lower():
                raise RuntimeError("yt-dlp sha256 mismatch")
            if part.stat().st_size < 512 * 1024:
                raise RuntimeError("official yt-dlp zipapp is too small")
            destination = self.bin / "yt-dlp"
            part.chmod(part.stat().st_mode | 0o700)
            self._promote(part, destination)
            state["yt_dlp"] = {"checked_at": self.now(), "version": version, "sha256": digest}
            self._save_state(state)
            return {"ok": True, "path": str(destination), "updated": True, "version": version,
                    "sha256": digest, "node": bool(shutil.which("node")), "experimental": not bool(shutil.which("node"))}
        except Exception as exc:
            state["yt_dlp"]["error"] = f"{type(exc).__name__}: {exc}"[:240]
            self._save_state(state)
            return {"ok": bool(own), "updated": False, "error": state["yt_dlp"]["error"],
                    "retry_at": float(state["yt_dlp"]["checked_at"]) + YTDLP_UPDATE_SECONDS,
                    "experimental": not bool(shutil.which("node"))}
        finally:
            part.unlink(missing_ok=True)

    def _ytdlp_command(self):
        own = self.bin / "yt-dlp"
        if own.exists() and not self._own_ytdlp():
            raise RuntimeError("installed yt-dlp sha256 integrity check failed")
        tool = self.locate_ytdlp()
        if not tool:
            raise RuntimeError("yt-dlp is not installed; user consent is required")
        # The official Unix asset is a Python zipapp.  Invoking it with the
        # Decky interpreter also works when its executable bit is unavailable.
        with tool.open("rb") as stream:
            native = stream.read(4) == b"\x7fELF"
        return [str(tool)] if native else [sys.executable, str(tool)]

    @staticmethod
    def _meaningful_words(name):
        return [w for w in re.findall(r"\w+", re.sub(r"[™®©]", "", str(name)).casefold())
                if w not in {"the", "of", "and", "remastered", "digital"}]

    def youtube_candidates(self, name, official=(), *, audio=False):
        query = f"ytsearch12:{name} {'Theme Music' if audio else 'official trailer'}"
        command = self._ytdlp_command() + [query, "--dump-json", "--skip-download", "--ignore-errors", "--no-warnings", "--no-playlist",
                    "--socket-timeout", "20", "--retries", "1", "--extractor-retries", "1", "--no-cache-dir", "--ignore-config"]
        if audio:
            command += ["--match-filter", "duration < 900"]
        if shutil.which("node"):
            command += ["--js-runtimes", "node"]
        result = self.run(command, capture_output=True, text=True, timeout=180)
        if result.returncode not in (0, 1):
            raise RuntimeError((result.stderr or "yt-dlp search failed")[-300:])
        wanted = self._meaningful_words(name)
        rows = []
        for line in (result.stdout or "").splitlines():
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if not entry or not entry.get("webpage_url"):
                continue
            title = str(entry.get("title") or "")
            hay = set(re.findall(r"\w+", title.casefold()))
            if wanted and not all(word in hay for word in wanted):
                continue
            channel = str(entry.get("channel") or entry.get("uploader") or "").casefold()
            channel_words = re.findall(r"\w+", channel)
            normalized = " " + " ".join(channel_words) + " "
            studio_names = []
            for studio in official:
                words = [word for word in re.findall(r"\w+", str(studio).casefold())
                         if len(word) > 2 and word not in GENERIC_STUDIO_WORDS]
                if words and len(" ".join(words[:2])) > 3:
                    studio_names.append(" ".join(words[:2]))
            trusted = any(" " + word + " " in normalized for word in (*TRUSTED, *studio_names))
            formats = [f for f in (entry.get("formats") or []) if f.get("vcodec") not in (None, "none", "images")]
            height = max((_safe_int(f.get("height")) for f in formats), default=0)
            if audio:
                if not entry.get("duration") or not 0 < float(entry["duration"]) < 900:
                    continue
            elif not formats or not trusted or SKIP_NAME.search(title):
                continue
            rows.append({"url": entry["webpage_url"], "title": title, "channel": channel,
                         "height": height, "trusted": trusted, "duration": entry.get("duration")})
        rows.sort(key=lambda row: (row["trusted"], row["height"], "trailer" in row["title"].casefold()), reverse=True)
        return rows

    def _download_youtube(self, url, destination_stem, settings, *, audio=False):
        self._configure(settings)
        preset = str(settings.get("preset") or "light")
        height = PRESETS.get(preset, PRESETS["light"])["height"]
        self.media.mkdir(parents=True, exist_ok=True)
        marker = self.media / (destination_stem + ".part")
        for old in self.media.glob(marker.name + ".*"):
            try:
                old.unlink()
            except OSError:
                pass
        output = str(marker) + ".%(ext)s"
        command = self._ytdlp_command() + [url, "--no-playlist", "--no-warnings", "--retries", "1", "-o", output,
                    "--downloader", "native", "--socket-timeout", "20", "--extractor-retries", "1", "--no-cache-dir", "--ignore-config",
                    "--max-filesize", str(min(MAX_DOWNLOAD_BYTES, self._limit_bytes // 3))]
        if audio:
            command += ["-f", "bestaudio[ext=m4a][acodec^=mp4a]", "--match-filter", "duration < 900"]
        else:
            command += ["-f", f"bv[ext=mp4][vcodec^=avc1][height<={height}]/b[ext=mp4][vcodec^=avc1][height<={height}]"]
        if shutil.which("node"):
            command += ["--js-runtimes", "node"]
        try:
            result = self.run(command, capture_output=True, timeout=300)
            made = [p for p in self.media.glob(marker.name + ".*") if p.is_file()]
            valid = next((p for p in made if p.suffix in (".m4a", ".mp4") and
                          (self._valid_audio(p) if audio else self._valid_video(p))), None)
            if result.returncode != 0 or not valid:
                return None
            destination = self.media / (destination_stem + (".m4a" if audio else ".mp4"))
            if shutil.which("ffmpeg"):
                if not self._ffmpeg_loop(valid, destination, preset, audio=audio, length=40 if audio else LOOP_SECONDS):
                    return None
            else:
                duration = _bmff(valid, audio=audio)["duration"]
                if not 0 < duration <= (40 if audio else LOOP_SECONDS) + 0.5:
                    raise RuntimeError("YouTube requires ffmpeg for bounded clips on this system")
                self._promote(valid, destination)
            return destination
        finally:
            for path in self.media.glob(marker.name + ".*"):
                path.unlink(missing_ok=True)

    def build_youtube(self, appid, name, settings):
        if not settings.get("youtube_consent"):
            return {"ok": False, "consent_required": True, "source": "youtube"}
        if self._own_ytdlp() or not self.locate_ytdlp():
            self.install_ytdlp(True)
        store = self.store_data(appid, "english")
        english_name = store.get("name") or name or str(appid)
        official = tuple(str(x).casefold() for x in [*(store.get("developers") or []), *(store.get("publishers") or [])])
        candidates = self.youtube_candidates(english_name, official)
        for candidate in candidates[:6]:  # an age-gated upload fails; try the next copy
            try:
                made = self._download_youtube(candidate["url"], f"{int(appid)}_youtube", settings)
            except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
                continue
            if made:
                return {"ok": True, "source": "youtube", "video": candidate["url"], "title": candidate["title"],
                        "channel": candidate["channel"], "height": candidate["height"],
                        "node": bool(shutil.which("node")), "experimental": not bool(shutil.which("node"))}
        raise RuntimeError("no accessible YouTube trailer could be downloaded")

    def build_theme(self, appid, name, settings):
        if not settings.get("theme_music_consent"):
            return {"ok": False, "consent_required": True, "source": "theme"}
        if self._own_ytdlp() or not self.locate_ytdlp():
            self.install_ytdlp(True)
        store = self.store_data(appid, "english")
        candidates = self.youtube_candidates(store.get("name") or name or str(appid), audio=True)
        if not candidates:
            raise RuntimeError("no theme-music candidate found")
        made = self._download_youtube(candidates[0]["url"], f"{int(appid)}_theme", settings, audio=True)
        if not made:
            raise RuntimeError("theme-music download failed")
        return {"ok": True, "source": "theme", "file": self._relative(made)}

    # ---- Steam Background Recording --------------------------------------------------

    @staticmethod
    def _steam_roots():
        roots = [Path.home() / ".local/share/Steam", Path.home() / ".steam/steam"]
        return [root for root in roots if root.exists()]

    def recording_candidates(self, appid):
        appid = str(int(appid))
        files = []
        exact = re.compile(r"^(?:(?:bg|clip)_" + appid + r"_\d{8}_\d{6}|app_" + appid + r"_(?:clip|recording))$")
        for root in self._steam_roots():
            for rec in root.glob("userdata/*/gamerecordings"):
                try:
                    for path in rec.rglob("*"):
                        if not path.is_file() or not any(exact.fullmatch(p.name) for p in path.parents if p != rec):
                            continue
                        if path.suffix.lower() not in (".mp4", ".webm") and path.name != "init-stream0.m4s":
                            continue
                        siblings = list(path.parent.glob("chunk-stream0-*.m4s")) if path.suffix == ".m4s" else [path]
                        if siblings and all(self.now() - p.stat().st_mtime >= ACTIVE_SECONDS for p in siblings):
                            files.append(path)
                except OSError:
                    continue
        return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)

    @staticmethod
    def _frames_gameplay(frames):
        """Conservative 120x68 gray-frame heuristic, without numpy/Pillow.

        Mirrors the local reference's 55% dark/flat and 4.5 delta thresholds.
        It cannot prove semantics, but rejects obvious loading/menu scenes.
        """
        if len(frames) != 5 or any(len(f) != 120 * 68 for f in frames):
            return False
        flagged = 0
        for frame in frames:
            dark = sum(v < 24 for v in frame) / len(frame)
            flat = sum(abs(frame[i] - frame[i - 1]) < 3 for i in range(1, len(frame)) if i % 120) / (119 * 68)
            flagged += dark >= 0.55 or flat >= 0.55
        still = sum(sum(abs(a - b) for a, b in zip(frames[i], frames[i + 1])) / len(frames[i]) < 4.5 for i in range(4))
        return flagged < 3 and still < 2

    def _vet_recording(self, source, start):
        frames = []
        for fraction in (0.12, 0.3, 0.5, 0.7, 0.88):
            result = self.run([shutil.which("ffmpeg"), "-v", "error", "-protocol_whitelist", "file,pipe",
                               "-ss", str(start + LOOP_SECONDS * fraction), "-i", str(source),
                               "-frames:v", "1", "-vf", "scale=120:68", "-pix_fmt", "gray", "-f", "rawvideo", "-"],
                              capture_output=True, timeout=30)
            if result.returncode:
                return False
            frames.append(result.stdout)
        return self._frames_gameplay(frames)

    def _copy_bounded(self, sources, destination):
        used = 0
        with Path(destination).open("wb") as target:
            for source in sources:
                with Path(source).open("rb") as stream:
                    for chunk in iter(lambda: stream.read(CHUNK_BYTES), b""):
                        self._checkpoint()
                        used += len(chunk)
                        if used > MAX_DOWNLOAD_BYTES:
                            raise RuntimeError("recording exceeds bounded staging budget")
                        self._check_space(len(chunk))
                        target.write(chunk)
        return used

    def build_recording(self, appid, name, settings):
        if not settings.get("recording_enabled"):
            return {"ok": False, "disabled": True, "source": "recording"}
        candidates = self.recording_candidates(appid)
        if not candidates:
            raise RuntimeError("Steam Background Recording has no clips for this app")
        if not shutil.which("ffmpeg"):
            raise RuntimeError("recording requires ffmpeg frame analysis; static background retained")
        destination = self.media / f"{int(appid)}_recording.mp4"
        self.media.mkdir(parents=True, exist_ok=True)
        for original in candidates[:3]:
            joined = destination.with_name(destination.name + ".recording.part")
            try:
                source = original
                if original.name == "init-stream0.m4s":
                    chunks = sorted(original.parent.glob("chunk-stream0-*.m4s"), key=lambda p: int(re.search(r"(\d+)\.m4s$", p.name)[1]))
                    # Steam chunks are contiguous, usually 2 seconds. Bound I/O
                    # and verify measured duration rather than assume 2s.
                    middle = max(0, len(chunks) // 2 - 8)
                    selected = chunks[middle:middle + 32]
                    indexes = [int(re.search(r"(\d+)\.m4s$", p.name)[1]) for p in selected]
                    if not indexes or indexes != list(range(indexes[0], indexes[0] + len(indexes))):
                        continue
                    self._copy_bounded([original, *selected], joined)
                    self._normalize_fragments(joined)
                    source = joined
                duration = self._probe_duration(source)
                if duration < LOOP_SECONDS:
                    continue
                center = max(0, (duration - LOOP_SECONDS) / 2)
                for start in dict.fromkeys((center, max(0, center - LOOP_SECONDS), min(duration - LOOP_SECONDS, center + LOOP_SECONDS))):
                    if not self._vet_recording(source, start):
                        continue
                    made = self._ffmpeg_loop(source, destination, str(settings.get("preset") or "light"), start=start)
                    if made:
                        return {"ok": True, "source": "recording", "recording": original.parent.name,
                                "heuristic": "five gray frames: dark/flat/still rejection; semantic quality needs Deck review", **made}
            finally:
                joined.unlink(missing_ok=True)
        raise RuntimeError("no recording window passed conservative gameplay frame analysis")

    # ---- one synchronous worker operation --------------------------------------------

    def _maybe_theme(self, appid, name, settings):
        if not settings.get("theme_music_consent") or self.music_files().get(str(appid)):
            return None
        state = self._state()
        if not isinstance(state.get("theme_attempts"), dict):
            state["theme_attempts"] = {}
        attempts = state["theme_attempts"]
        prior = attempts.get(str(appid)) or {}
        if prior.get("ok") is False and self.now() - float(prior.get("at") or 0) < RETRY_SECONDS:
            return {"ok": False, "retry_at": float(prior["at"]) + RETRY_SECONDS, "error": prior.get("error")}
        try:
            result = self.build_theme(appid, name, settings)
        except Exception as exc:
            result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:240]}
        # The installer may have changed checksum/update metadata during work.
        state = self._state()
        state.setdefault("theme_attempts", {})[str(appid)] = {"ok": bool(result.get("ok")), "at": self.now(), "error": result.get("error")}
        self._save_state(state)
        return result

    def build(self, appid, name, settings, source=None, *, force=False):
        self._configure(settings)
        appid = int(appid)
        source = str(source or (settings.get("game_source") or {}).get(str(appid)) or settings.get("bg_source") or "steam")
        if source not in SOURCES:
            return {"ok": False, "error": "unknown source", "source": source}
        state = self._state()
        if not isinstance(state.get("attempts"), dict):
            state["attempts"] = {}
        attempts = state["attempts"]
        key = f"{appid}:{source}"
        prior = attempts.get(key) or {}
        preset = str(settings.get("preset") or "light")
        existing = self._asset(appid, source)
        if existing and not force and prior.get("preset", preset) == preset:
            try:
                os.utime(existing, None)
            except OSError:
                pass
            result = {"ok": True, "cached": True, "source": source, "file": self._relative(existing)}
            theme = self._maybe_theme(appid, name, settings)
            if theme is not None:
                result["theme"] = theme
            return result
        if not force and prior.get("ok") is False and self.now() - float(prior.get("at") or 0) < RETRY_SECONDS:
            return {"ok": False, "retry_at": float(prior.get("at") or 0) + RETRY_SECONDS,
                    "source": source, "error": prior.get("error")}
        try:
            self._checkpoint()
            self.enforce_limit(settings.get("disk_limit_gb", 2))
            self._reserve_job(appid)
            if source == "steam":
                result = self.build_steam(appid, name, settings)
            elif source == "youtube":
                result = self.build_youtube(appid, name, settings)
            else:
                result = self.build_recording(appid, name, settings)
            if result.get("ok"):
                theme = self._maybe_theme(appid, name, settings)
                if theme is not None:
                    result["theme"] = theme
                latest = self._state()
                for state_key in ("yt_dlp", "theme_attempts"):
                    if state_key in latest:
                        state[state_key] = latest[state_key]
            attempts[key] = {"ok": bool(result.get("ok")), "at": self.now(),
                             "error": result.get("error"), "source": source, "preset": preset,
                             "local_start": result.get("local_start", 0) if result.get("uncut") else 0,
                             "playback_seconds": result.get("playback_seconds", LOOP_SECONDS)}
        except Exception as exc:
            result = {"ok": False, "source": source, "error": f"{type(exc).__name__}: {exc}"[:240]}
            attempts[key] = {"ok": False, "at": self.now(), "error": result["error"], "source": source}
        latest = self._state()
        for state_key in ("yt_dlp", "theme_attempts"):
            if state_key in latest:
                state[state_key] = latest[state_key]
        self._save_state(state)
        try:
            result["cache"] = self.enforce_limit(settings.get("disk_limit_gb", 2))
        except OSError as exc:
            result["cache_error"] = f"{type(exc).__name__}: {exc}"[:240]
        return result
