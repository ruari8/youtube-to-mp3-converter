#!/usr/bin/env python3
"""Minimal local web server for yt2mp3 frontend.

- Serves frontend at http://127.0.0.1:<port>/
- POST /api/convert runs yt2mp3 conversions and returns downloadable links.

This is intentionally stdlib-only (no Flask/FastAPI).
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import mimetypes
import os
import shutil
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

try:
    import yt2mp3  # type: ignore
    _YT2MP3_IMPORT_ERROR = None
except Exception as e:  # pragma: no cover
    yt2mp3 = None
    _YT2MP3_IMPORT_ERROR = str(e)


ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"
ASSETS_DIR = FRONTEND_DIR / "assets"
DOWNLOADS_DIR = ROOT / "downloads"


def _ffmpeg_ok() -> bool:
    return bool(shutil.which("ffmpeg")) and bool(shutil.which("ffprobe"))


def _json(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _safe_join(base: Path, rel: str) -> Path | None:
    rel = rel.lstrip("/")
    try:
        out = (base / rel).resolve()
        base_r = base.resolve()
        if base_r == out or base_r in out.parents:
            return out
        return None
    except Exception:
        return None


def _detect_platform(url: str) -> str:
    u = url.lower()
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    if "soundcloud.com" in u:
        return "soundcloud"
    if "twitter.com" in u or "x.com" in u:
        return "x"
    if "instagram.com" in u:
        return "instagram"
    return "unknown"


class Handler(BaseHTTPRequestHandler):
    server_version = "yt2mp3-web/0.1"

    def log_message(self, fmt: str, *args) -> None:
        # Keep stdout clean; surface logs via API responses.
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path in ("/", "/index.html"):
            self._serve_file(FRONTEND_DIR / "index.html")
            return

        if path.startswith("/assets/"):
            rel = path.removeprefix("/assets/")
            target = _safe_join(ASSETS_DIR, rel)
            if not target or not target.exists() or not target.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self._serve_file(target)
            return

        if path.startswith("/downloads/"):
            rel = path.removeprefix("/downloads/")
            target = _safe_join(DOWNLOADS_DIR, rel)
            if not target or not target.exists() or not target.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self._serve_file(target)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def _serve_file(self, file_path: Path) -> None:
        try:
            data = file_path.read_bytes()
        except Exception:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        ctype, _ = mimetypes.guess_type(str(file_path))
        if not ctype:
            ctype = "application/octet-stream"

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        # Allow local frontend iteration.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/convert":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            _json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "message": "Bad Content-Length"})
            return

        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            _json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "message": "Invalid JSON"})
            return

        url = str(body.get("url", "")).strip()
        fmt = str(body.get("format", "")).strip().lower()
        quality_kbps = str(body.get("quality_kbps", "192")).strip()
        ig = body.get("instagram") or {}
        ig_mode = str(ig.get("mode", "first")).strip().lower()
        ig_sel = str(ig.get("selection", "")).strip()

        if not url:
            _json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "message": "Missing url"})
            return

        platform = _detect_platform(url)
        if platform == "unknown":
            _json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "message": "Unsupported URL"})
            return

        if yt2mp3 is None:
            _json(
                self,
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    'ok': False,
                    'message': 'Server dependencies missing (yt-dlp).',
                    'logs': _YT2MP3_IMPORT_ERROR or '',
                    'hint': 'Run: ./venv/bin/python -m pip install -r requirements.txt',
                },
            )
            return

        # Normalize format per platform.
        if platform in ("x", "instagram"):
            fmt = "mp4"
        if platform == "soundcloud":
            fmt = "mp3"

        if fmt not in ("mp3", "flac", "mp4"):
            _json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "message": "Invalid format"})
            return

        # yt-dlp needs ffmpeg for audio extraction (MP3/FLAC).
        if fmt in ("mp3", "flac") and not _ffmpeg_ok():
            _json(
                self,
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "ok": False,
                    "message": "ffmpeg/ffprobe not found on PATH.",
                    "hint": "On macOS: brew install ffmpeg",
                    "logs": "",
                },
            )
            return

        out_dir = DOWNLOADS_DIR / platform / fmt
        out_dir.mkdir(parents=True, exist_ok=True)

        # Capture prints from yt2mp3 helpers so the UI can display them.
        started = None
        try:
            started = os.times().elapsed
        except Exception:
            started = None

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            ok = False
            try:
                if platform == "youtube":
                    if fmt == "mp4":
                        ok = yt2mp3.download_youtube_to_mp4(url, str(out_dir))
                    elif fmt == "flac":
                        ok = yt2mp3.download_youtube_to_flac(url, str(out_dir))
                    else:
                        ok = yt2mp3.download_youtube_to_mp3(url, str(out_dir), quality_kbps)
                elif platform == "soundcloud":
                    ok = yt2mp3.download_soundcloud_to_mp3(url, str(out_dir), quality_kbps)
                elif platform == "x":
                    ok = yt2mp3.download_twitter_video(url, str(out_dir))
                elif platform == "instagram":
                    if ig_mode == "all":
                        ok = yt2mp3.download_instagram_media(url, str(out_dir), download_all=True)
                    elif ig_mode == "select":
                        ok = yt2mp3.download_instagram_media(url, str(out_dir), download_all=False, playlist_items=ig_sel or None)
                    else:
                        ok = yt2mp3.download_instagram_media(url, str(out_dir), download_all=False, playlist_items=None)
            except Exception as e:
                ok = False
                print(f"Server error: {e}")

        logs = buf.getvalue().strip()
        if not ok:
            _json(
                self,
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "ok": False,
                    "message": "Conversion failed",
                    "hint": "See logs. Common causes: private/age-restricted media, geo restrictions, or VPN/proxy IPs triggering YouTube bot checks.",
                    "logs": logs,
                    "debug": {"platform": platform, "format": fmt, "output_dir": str(out_dir)},
                },
            )
            return

        # Find files touched recently.
        files = []
        try:
            # Heuristic: return the newest files in this output dir.
            candidates = [p for p in out_dir.iterdir() if p.is_file()]
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            # For carousel/multi-downloads, return a few newest.
            for p in candidates[:10]:
                rel = p.resolve().relative_to(DOWNLOADS_DIR.resolve())
                files.append({
                    "name": p.name,
                    "url": f"/downloads/{rel.as_posix()}",
                })
        except Exception:
            files = []

        _json(self, HTTPStatus.OK, {"ok": True, "message": "Complete", "logs": logs, "files": files})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8008)
    args = parser.parse_args()

    mimetypes.add_type("image/svg+xml", ".svg")

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"yt2mp3 web: http://{args.host}:{args.port}/")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
