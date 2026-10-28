"""Run with ./venv/bin/python -m unittest discover -s tests -v."""

import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import native_host
import yt2mp3

ROOT = Path(__file__).resolve().parents[1]
REQUEST = {"action": "download", "url": "https://www.youtube.com/watch?v=BaW_jenozKc", "format": "mp3", "quality": "192"}


class RequestTests(unittest.TestCase):
    def test_canonical_url_excludes_playlist_and_other_parameters(self):
        result = native_host.validate_request({**REQUEST, "url": "https://youtu.be/BaW_jenozKc?list=PL123&t=20"})
        self.assertEqual(result["url"], REQUEST["url"])

    def test_rejects_invalid_inputs(self):
        invalid = [
            {"url": "https://youtube.com.attacker.test/watch?v=BaW_jenozKc"},
            {"url": "file:///etc/passwd"}, {"url": "https://www.youtube.com/playlist?list=abc"},
            {"format": "exe"}, {"quality": "192; open /tmp"},
            {"subtitles": "yes"}, {"subtitles": True},
            {"clip": {"start": 2, "end": 1}}, {"clip": {"start": -1, "end": 1}},
            {"clip": {"start": 0, "end": float("inf")}}, {"clip": {"start": True, "end": 4}},
        ]
        for update in invalid:
            with self.subTest(update=update), self.assertRaises(ValueError):
                native_host.validate_request({**REQUEST, **update})

    def test_rejects_revealing_unrelated_file(self):
        with self.assertRaises(ValueError):
            native_host.handle({"action": "reveal", "path": __file__}, lambda _: None)

    def test_native_protocol_from_subprocess(self):
        messages = [{"action": "ping"}, {**REQUEST, "url": "https://invalid.test"}]
        wire = b""
        for message in messages:
            encoded = json.dumps(message).encode()
            wire += struct.pack("=I", len(encoded)) + encoded
        process = subprocess.run([sys.executable, str(ROOT / "native_host.py")], input=wire, capture_output=True, check=True)
        stream = io.BytesIO(process.stdout)
        self.assertEqual(native_host.read_message(stream)["status"], "ready")
        self.assertEqual(native_host.read_message(stream)["status"], "error")
        self.assertIsNone(native_host.read_message(stream))


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
class MediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.source = cls.root / "fixture.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=30",
                        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100", "-t", "4",
                        "-c:v", "libx264", "-c:a", "aac", str(cls.source)], check=True)
        for fmt in ("mp3", "flac"):
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(cls.source), "-vn", str(cls.root / f"fixture.{fmt}")], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_all_formats_full_and_trimmed_and_repeat_download(self):
        for fmt in ("mp3", "flac", "mp4"):
            with self.subTest(format=fmt), tempfile.TemporaryDirectory() as output:
                fixture = self.root / f"fixture.{fmt}"

                def downloader(url, directory, **kwargs):
                    print("Downloader output must not corrupt Chrome's protocol")
                    kwargs["progress_hook"]({"status": "downloading", "downloaded_bytes": 5, "total_bytes": 10})
                    shutil.copyfile(fixture, Path(directory) / f"My video.{fmt}")
                    return True

                with patch.object(native_host, "DOWNLOAD_ROOT", Path(output)), patch.object(yt2mp3, f"download_youtube_to_{fmt}", downloader):
                    results = []
                    native_host.download({**REQUEST, "format": fmt}, results.append)
                    full = Path(results[-1]["path"])
                    self.assertEqual(full.read_bytes(), fixture.read_bytes())
                    native_host.download({**REQUEST, "format": fmt, "clip": {"start": 1.456, "end": 2.789}}, results.append)
                    clip = Path(results[-1]["path"])
                    self.assertAlmostEqual(native_host.media_duration(clip), 1.333, delta=0.0001 if fmt == "flac" else 0.1)
                    native_host.download({**REQUEST, "format": fmt}, results.append)
                    duplicate = Path(results[-1]["path"])
                    self.assertNotEqual(full, duplicate)
                    self.assertEqual(full.read_bytes(), duplicate.read_bytes())
                    self.assertFalse(list(Path(output).glob("**/.yt2mp3-*")))

    def test_clip_beyond_source_fails(self):
        with self.assertRaises(ValueError):
            native_host.trim_media(self.source, self.root / "invalid.mp4", {"start": 1, "end": 20}, "mp4", "192")

    def test_burned_subtitles_stay_in_sync_in_full_video_and_clip(self):
        with tempfile.TemporaryDirectory() as output:
            root = Path(output)
            black = root / "black.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:size=480x270:rate=30",
                            "-t", "4", "-c:v", "libx264", str(black)], check=True)
            captions = "1\n00:00:00,200 --> 00:00:01,500\nAcross the cut\n\n2\n00:00:02,200 --> 00:00:02,600\nInside the clip\n\n3\n00:00:03,200 --> 00:00:03,700\nAfter the clip\n"

            def downloader(url, directory, **kwargs):
                self.assertTrue(kwargs["subtitles"])
                shutil.copyfile(black, Path(directory) / "Video.mp4")
                (Path(directory) / "Video.en.srt").write_text(captions)
                return True

            def has_text(path, seconds):
                frame = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(seconds), "-i", str(path),
                                        "-frames:v", "1", "-pix_fmt", "gray", "-f", "rawvideo", "-"],
                                       capture_output=True, check=True).stdout
                self.assertEqual(len(frame), 480 * 270)
                return sum(pixel > 180 for pixel in frame) > 20

            with patch.object(native_host, "DOWNLOAD_ROOT", root), patch.object(yt2mp3, "download_youtube_to_mp4", downloader):
                for clip, expected in [
                    (None, [(0.4, True), (1.8, False), (2.4, True), (3.4, True)]),
                    ({"start": 1, "end": 3}, [(0.1, True), (0.8, False), (1.4, True), (1.8, False)]),
                ]:
                    with self.subTest(clip=clip):
                        events = []
                        native_host.download({**REQUEST, "format": "mp4", "subtitles": True, "clip": clip}, events.append)
                        saved = Path(events[-1]["path"])
                        self.assertIn("[subtitles]", saved.name)
                        for seconds, visible in expected:
                            self.assertEqual(has_text(saved, seconds), visible, f"Caption visibility at {seconds}s")
                        self.assertAlmostEqual(native_host.media_duration(saved), 2 if clip else 4, delta=0.1)

    def test_missing_subtitle_file_does_not_silently_save_an_uncaptioned_video(self):
        def downloader(url, directory, **kwargs):
            shutil.copyfile(self.source, Path(directory) / "Video.mp4")
            return True
        with tempfile.TemporaryDirectory() as output, patch.object(native_host, "DOWNLOAD_ROOT", Path(output)), patch.object(yt2mp3, "download_youtube_to_mp4", downloader):
            with self.assertRaisesRegex(RuntimeError, "subtitles could not be downloaded"):
                native_host.download({**REQUEST, "format": "mp4", "subtitles": True}, lambda _: None)
            self.assertEqual(list((Path(output) / "YouTube_MP4").iterdir()), [])

    def test_failed_download_returns_useful_error_and_cleans_up(self):
        def fail(*args, **kwargs):
            print("Source unavailable")
            return False
        with tempfile.TemporaryDirectory() as output, patch.object(native_host, "DOWNLOAD_ROOT", Path(output)), patch.object(yt2mp3, "download_youtube_to_mp3", fail):
            with self.assertRaisesRegex(RuntimeError, "Source unavailable"):
                native_host.download(REQUEST, lambda _: None)
            self.assertEqual(list((Path(output) / "YouTube_MP3").iterdir()), [])


class SubtitleSelectionTests(unittest.TestCase):
    def test_creator_captions_take_priority_over_automatic_english(self):
        info = {"subtitles": {"en-GB": [{}]}, "automatic_captions": {"en": [{}]}}
        self.assertEqual(yt2mp3._english_subtitle_language(info), "en-GB")

    def test_automatic_english_and_unavailable_captions(self):
        self.assertEqual(yt2mp3._english_subtitle_language({"automatic_captions": {"en": [{}], "en-orig": [{}]}}), "en-orig")
        with self.assertRaisesRegex(ValueError, "No English subtitles"):
            yt2mp3._english_subtitle_language({"subtitles": {"es": [{}]}})


if __name__ == "__main__":
    unittest.main()
