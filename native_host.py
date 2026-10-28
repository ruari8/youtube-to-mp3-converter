#!/usr/bin/env python3
"""Chrome's on-demand bridge to the existing yt2mp3 downloader (no HTTP server)."""

import contextlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
DOWNLOAD_ROOT = Path.home() / "Downloads"
FORMATS = {"mp3", "flac", "mp4"}


def validate_request(body):
    if not isinstance(body, dict):
        raise ValueError("Expected a download request.")
    parsed = urlparse(str(body.get("url", "")))
    if parsed.scheme != "https" or parsed.hostname not in {"www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be"}:
        raise ValueError("Open a YouTube video first.")
    if parsed.hostname == "youtu.be":
        video_id = parsed.path.strip("/")
    elif parsed.path.startswith(("/shorts/", "/live/")):
        video_id = parsed.path.split("/")[2]
    elif parsed.path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [""])[0]
    else:
        video_id = ""
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("This page does not contain a YouTube video.")
    fmt = body.get("format")
    if fmt not in FORMATS:
        raise ValueError("Choose MP3, FLAC or MP4.")
    quality = str(body.get("quality", "192"))
    if quality not in {"128", "192", "256", "320"}:
        raise ValueError("Choose a supported MP3 bitrate.")
    subtitles = body.get("subtitles", False)
    if type(subtitles) is not bool or (subtitles and fmt != "mp4"):
        raise ValueError("Subtitles are available for MP4 video downloads only.")
    clip = body.get("clip")
    if clip is not None:
        if not isinstance(clip, dict):
            raise ValueError("Invalid clip times.")
        start, end = clip.get("start"), clip.get("end")
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in (start, end)):
            raise ValueError("Enter valid start and end times.")
        if not 0 <= start < end:
            raise ValueError("The end must be after the start.")
        clip = {"start": start, "end": end}
    return {"url": f"https://www.youtube.com/watch?v={video_id}", "format": fmt, "quality": quality, "clip": clip, "subtitles": subtitles}


def media_duration(source):
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(source),
    ], capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def trim_media(source, destination, clip, fmt, quality, subtitles=None):
    duration = media_duration(source)
    if clip and (clip["start"] >= duration or clip["end"] > duration + 0.25):
        raise ValueError(f"The clip must fit within the video ({duration:.1f} seconds).")
    # Decode before cutting: stream-copy cuts can drift to a nearby keyframe.
    command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(source)]
    if clip:
        command += ["-ss", str(clip["start"]), "-t", str(clip["end"] - clip["start"])]
    if fmt == "mp4":
        command += ["-map", "0:v:0", "-map", "0:a:0?", "-c:v", "libx264", "-preset", "fast",
                    "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
        if subtitles:
            # Fixed relative filename avoids FFmpeg filter escaping for arbitrary video titles/paths.
            # Burn against original timestamps before the output seek, keeping clips in sync.
            command += ["-vf", "subtitles=captions.srt"]
    else:
        command += ["-vn", "-c:a", "libmp3lame" if fmt == "mp3" else "flac"]
        if fmt == "mp3":
            command += ["-b:a", f"{quality}k"]
    result = subprocess.run(command + [str(destination)], capture_output=True, text=True,
                            cwd=subtitles.parent if subtitles else None)
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:] or "FFmpeg could not trim the file.")


class RecentLog(io.TextIOBase):
    """Keep useful downloader errors without growing a log for a long video."""
    def __init__(self):
        self.tail = ""

    def write(self, value):
        self.tail = (self.tail + value)[-6000:]
        return len(value)


def download(body, send):
    request = validate_request(body)
    import yt2mp3

    if not all(shutil.which(tool) for tool in ("ffmpeg", "ffprobe")):
        raise RuntimeError("FFmpeg is missing. Install it with brew install ffmpeg.")
    fmt, clip = request["format"], request["clip"]
    output_dir = DOWNLOAD_ROOT / f"YouTube_{fmt.upper()}"
    output_dir.mkdir(parents=True, exist_ok=True)
    last_update = 0

    def progress(event):
        nonlocal last_update
        now = time.monotonic()
        if event["status"] == "finished":
            send({"status": "working", "message": "Converting media…"})
        elif event["status"] == "downloading" and now - last_update > 0.5:
            last_update = now
            total = event.get("total_bytes") or event.get("total_bytes_estimate")
            percent = min(100, round(event.get("downloaded_bytes", 0) / total * 100)) if total else None
            send({"status": "working", "message": "Downloading source…", "percent": percent})

    send({"status": "working", "message": "Getting video…"})
    # Each request owns a directory; old files and concurrent CLI runs cannot be mistaken for this result.
    with tempfile.TemporaryDirectory(prefix=".yt2mp3-", dir=output_dir) as work:
        log = RecentLog()
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            downloader = getattr(yt2mp3, f"download_youtube_to_{fmt}")
            kwargs = {"progress_hook": progress}
            if fmt == "mp3":
                kwargs["quality"] = request["quality"]
            if fmt == "mp4":
                kwargs["subtitles"] = request["subtitles"]
            ok = downloader(request["url"], work, **kwargs)
        if not ok:
            raise RuntimeError(log.tail.strip() or "The download failed. Try again.")
        candidates = [p for p in Path(work).iterdir() if p.suffix.lower() == f".{fmt}"]
        if len(candidates) != 1:
            raise RuntimeError(f"The downloader did not produce a single {fmt.upper()} file.")
        source = candidates[0]
        name = source.stem
        subtitles = None
        if request["subtitles"]:
            captions = list(Path(work).glob("*.srt"))
            if len(captions) != 1:
                raise RuntimeError("English subtitles could not be downloaded. Try again or turn off Include subtitles.")
            subtitles = Path(work) / "captions.srt"
            captions[0].replace(subtitles)
        if clip or subtitles:
            send({"status": "working", "message": "Adding subtitles and exporting…" if subtitles else "Trimming your clip…"})
            trimmed = Path(work) / "trimmed" / f"clip.{fmt}"
            trimmed.parent.mkdir()
            trim_media(source, trimmed, clip, fmt, request["quality"], subtitles)
            if clip:
                name += f" [{clip['start']:g}-{clip['end']:g}s]"
            if subtitles:
                name += " [subtitles]"
            source = trimmed
        # Reserve a unique name, never overwrite a previous download.
        index = 1
        while True:
            suffix = "" if index == 1 else f" ({index})"
            destination = output_dir / f"{name[:160]}{suffix}.{fmt}"
            try:
                fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                os.close(fd)
                break
            except FileExistsError:
                index += 1
        try:
            os.replace(source, destination)
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
    send({"status": "done", "message": "Saved to Downloads", "path": str(destination), "filename": destination.name})


def handle(body, send):
    if not isinstance(body, dict):
        raise ValueError("Expected a message object.")
    if body.get("action") == "ping":
        import yt_dlp.version
        missing = [tool for tool in ("ffmpeg", "ffprobe", "deno") if not shutil.which(tool)]
        send({"status": "ready" if not missing else "error", "message": "Ready on this Mac" if not missing else f"Missing: {', '.join(missing)}", "version": yt_dlp.version.__version__})
    elif body.get("action") == "download":
        download(body, send)
    elif body.get("action") == "reveal":
        target = Path(str(body.get("path", ""))).resolve()
        allowed = [(DOWNLOAD_ROOT / f"YouTube_{fmt.upper()}").resolve() for fmt in FORMATS]
        if target.parent not in allowed or not target.is_file() or target.suffix[1:] not in FORMATS:
            raise ValueError("This download no longer exists.")
        subprocess.run(["/usr/bin/open", "-R", str(target)], check=True)
        send({"status": "revealed"})
    else:
        raise ValueError("Unknown action.")


def read_message(stream):
    header = stream.read(4)
    if not header:
        return None
    if len(header) != 4:
        raise ValueError("Incomplete message header.")
    length = struct.unpack("=I", header)[0]
    if length > 65536:
        raise ValueError("Message is too large.")
    data = stream.read(length)
    if len(data) != length:
        raise ValueError("Incomplete message.")
    return json.loads(data)


def main():
    wire = sys.stdout.buffer
    sys.stdout = sys.stderr  # Only framed JSON may reach Chrome's stdout pipe.

    def send(message):
        data = json.dumps(message, ensure_ascii=False).encode("utf-8")
        wire.write(struct.pack("=I", len(data)) + data)
        wire.flush()

    while True:
        try:
            body = read_message(sys.stdin.buffer)
            if body is None:
                return
            handle(body, send)
        except BrokenPipeError:
            return
        except Exception as error:
            send({"status": "error", "message": str(error)[-6000:]})


if __name__ == "__main__":
    main()
