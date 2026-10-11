"""Serve the Continue? showcase on loopback, including tour video byte ranges."""
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "site"
TOURS = {"/media/tour-{}.mp4".format(lang): REPO / "docs" / "img" / "tour-{}.mp4".format(lang)
         for lang in ("en", "uk", "ru")}


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE), **kwargs)

    def translate_path(self, path):
        tour = TOURS.get(urlsplit(path).path)
        return str(tour) if tour else super().translate_path(path)

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def send_head(self):
        self.byte_range = None
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        target = Path(self.translate_path(self.path))
        if self.command != "GET" or not match or not any(match.groups()) or not target.is_file():
            return super().send_head()
        handle = target.open("rb")
        stat = target.stat()
        size = stat.st_size
        validator = self.headers.get("If-Range")
        if validator and validator != self.date_time_string(stat.st_mtime):
            handle.close()
            return super().send_head()
        first, last = match.groups()
        start = int(first) if first else max(0, size - int(last))
        end = min(size - 1, int(last)) if first and last else size - 1
        if size == 0 or start >= size or start > end:
            handle.close()
            self.send_response(416)
            self.send_header("Content-Range", "bytes */{}".format(size))
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        self.byte_range = (start, end)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(target)))
        self.send_header("Content-Range", "bytes {}-{}/{}".format(start, end, size))
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Last-Modified", self.date_time_string(stat.st_mtime))
        self.end_headers()
        handle.seek(start)
        return handle

    def copyfile(self, source, output):
        try:
            if self.byte_range is None:
                return super().copyfile(source, output)
            left = self.byte_range[1] - self.byte_range[0] + 1
            while left > 0:
                chunk = source.read(min(left, 64 * 1024))
                if not chunk:
                    break
                output.write(chunk)
                left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # Browsers cancel video requests when changing games or closing the tour.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8811, help="local port (default: 8811)")
    args = parser.parse_args()
    if not SITE.is_dir():
        parser.error("site/ is missing; use a complete checkout")
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    try:
        with ThreadingHTTPServer(("127.0.0.1", args.port), PreviewHandler) as server:
            print("Continue? preview: http://127.0.0.1:{}/".format(server.server_port), flush=True)
            print("Ctrl+C to stop. No Steam or game files are accessed.", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    except OSError as exc:
        parser.exit(1, "Cannot start preview: {}. Try --port 8813.\n".format(exc))


if __name__ == "__main__":
    main()
