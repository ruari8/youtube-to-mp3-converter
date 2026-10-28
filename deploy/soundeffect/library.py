"""Shared library, persistent soundboard, and a single YouTube import worker."""
import json
from contextlib import contextmanager
import math
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from urllib.parse import parse_qs, urlparse


class InputError(ValueError):
    pass


def youtube_id(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise InputError('Paste a YouTube video URL.')
    try:
        url = urlparse(value.strip())
        if url.scheme not in ('https', 'http') or url.username or url.password or url.port:
            raise ValueError()
        if url.hostname in ('youtu.be', 'www.youtu.be'):
            video_id = url.path.strip('/')
        elif url.hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'):
            if url.path == '/watch':
                video_id = parse_qs(url.query).get('v', [''])[0]
            elif re.fullmatch(r'/(shorts|embed|live)/[\w-]{11}/?', url.path):
                video_id = url.path.split('/')[2]
            else:
                raise ValueError()
        else:
            raise ValueError()
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
            raise ValueError()
        return video_id
    except ValueError:
        raise InputError('Use a YouTube video link, such as youtube.com/watch?v=… or youtu.be/…') from None


def run(command, timeout=90):
    # Kill the entire process group on timeout, including FFmpeg children.
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        out, err = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        import os
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise RuntimeError('This took too long. Try a shorter video.') from None
    if process.returncode:
        raise RuntimeError(err.decode(errors='replace')[-3000:])
    return out


class Library:
    def __init__(self, data, public, seed, worker=True):
        self.data, self.public = Path(data), Path(public)
        for folder in ('imports', 'clips', 'work'):
            (self.data / folder).mkdir(parents=True, exist_ok=True)
        self.db_path = self.data / 'library.sqlite3'
        self.clip_lock = threading.Lock()
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS tracks(id TEXT PRIMARY KEY, youtube_id TEXT UNIQUE, metadata TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS clips(id TEXT PRIMARY KEY, metadata TEXT NOT NULL, removed INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, youtube_id TEXT NOT NULL, status TEXT NOT NULL,
                    message TEXT NOT NULL, track_id TEXT, created REAL NOT NULL);
            ''')
            for track in seed:
                db.execute('INSERT OR IGNORE INTO tracks VALUES(?,?,?)',
                           (track['id'], track.get('youtubeId'), json.dumps(track)))
            if worker:
                db.execute("UPDATE jobs SET status='failed', message='The server restarted. Paste the link again to retry.' WHERE status='downloading'")
        self.wake = threading.Event()
        if worker:
            threading.Thread(target=self.work, daemon=True).start()

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db_path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def tracks(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT metadata FROM tracks ORDER BY rowid')]

    def board(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT metadata FROM clips WHERE removed=0 ORDER BY rowid')]

    def jobs(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute('SELECT * FROM jobs ORDER BY created DESC LIMIT 8')]

    def connection(self):
        proxy = os.environ.get('SOUNDCUT_PROXY')
        if not proxy:
            return {'requiresMac': False, 'available': True}
        address = urlparse(proxy)
        try:
            with socket.create_connection((address.hostname, address.port), timeout=2) as connection:
                # The SOCKS reply comes from the Mac. A listening port alone can
                # remain on the VPS briefly after the Mac sleeps or loses Wi-Fi.
                connection.sendall(b'\x05\x01\x00')
                response = b''
                while len(response) < 2:
                    chunk = connection.recv(2 - len(response))
                    if not chunk:
                        break
                    response += chunk
                return {'requiresMac': True, 'available': response == b'\x05\x00'}
        except OSError:
            return {'requiresMac': True, 'available': False}

    def import_video(self, url):
        video_id = youtube_id(url)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT metadata FROM tracks WHERE youtube_id=?', (video_id,)).fetchone()
            if existing:
                return {'track': json.loads(existing[0]), 'existing': True}
            pending = db.execute("SELECT * FROM jobs WHERE youtube_id=? AND status IN ('queued','downloading')", (video_id,)).fetchone()
            if pending:
                return {'job': dict(pending)}
            if db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','downloading')").fetchone()[0] >= 3:
                raise InputError('Three videos are already waiting. Let one finish first.')
            if db.execute('SELECT count(*) FROM tracks').fetchone()[0] >= 100:
                raise InputError('The library has reached its 100-video limit.')
            if shutil.disk_usage(self.data).free < 2 * 1024**3:
                raise InputError('The server needs more free space before another import.')
            job_id = uuid.uuid4().hex
            db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?)', (job_id, video_id, 'queued', 'Waiting to download…', None, time.time()))
        self.wake.set()
        return {'job': next(job for job in self.jobs() if job['id'] == job_id)}

    def job_update(self, job_id, status, message, track_id=None):
        with self.connect() as db:
            db.execute('UPDATE jobs SET status=?,message=?,track_id=? WHERE id=?', (status, message, track_id, job_id))

    def work(self):
        while True:
            with self.connect() as db:
                job = db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
            if not job:
                self.wake.wait(2)
                self.wake.clear()
                continue
            if not self.connection()['available']:
                self.job_update(job['id'], 'queued', 'Waiting for Ruari’s Mac to wake up and connect…')
                self.wake.wait(5)
                self.wake.clear()
                continue
            try:
                self.download(dict(job))
            except Exception as error:
                message = str(error)
                if 'Sign in' in message or 'bot' in message.lower():
                    message = 'YouTube blocked this download from the server. Try another video or try again later.'
                elif 'Private video' in message or 'unavailable' in message.lower():
                    message = 'This video is private, unavailable, or restricted.'
                elif not isinstance(error, InputError):
                    message = 'YouTube could not supply this video. Try again later or use another link.'
                self.job_update(job['id'], 'failed', message[:300])

    def download(self, job):
        self.job_update(job['id'], 'downloading', 'Checking the video…')
        url = 'https://www.youtube.com/watch?v=' + job['youtube_id']
        base = [sys.executable, '-m', 'yt_dlp', '--ignore-config', '--no-playlist', '--js-runtimes', 'node',
                '--socket-timeout', '20', '--retries', '2', '--fragment-retries', '2', '--no-warnings']
        if os.environ.get('SOUNDCUT_PROXY'):
            base += ['--proxy', os.environ['SOUNDCUT_PROXY']]
        metadata = json.loads(run(base + ['--skip-download', '--dump-single-json', url], timeout=90))
        duration = metadata.get('duration')
        if metadata.get('is_live') or not duration or not 0 < duration <= 600:
            raise InputError('Choose a finished video up to 10 minutes long.')
        self.job_update(job['id'], 'downloading', 'Downloading the full video…')
        track_id = 'yt-' + job['youtube_id']
        with tempfile.TemporaryDirectory(dir=self.data / 'work') as work:
            output = Path(work)
            run(base + ['-f', 'bv[ext=mp4][vcodec^=avc1][height<=720]+ba[ext=m4a]/b[ext=mp4][height<=720]',
                        '--max-filesize', '300M', '--merge-output-format', 'mp4', '--no-progress',
                        '-o', str(output / 'source.%(ext)s'), url], timeout=480)
            source = output / 'source.mp4'
            if not source.exists() or source.stat().st_size > 400 * 1024**2:
                raise InputError('This video is too large. Choose a shorter video.')
            self.job_update(job['id'], 'downloading', 'Preparing the video and waveform audio…')
            run(['ffmpeg', '-v', 'error', '-y', '-i', str(source), '-map', '0:v:0', '-map', '0:a:0',
                 '-c', 'copy', '-movflags', '+faststart', str(output / 'video.mp4')])
            run(['ffmpeg', '-v', 'error', '-y', '-i', str(source), '-vn', '-c:a', 'aac', '-b:a', '192k',
                 '-ac', '2', '-ar', '44100', '-movflags', '+faststart', str(output / 'audio.m4a')])
            actual = float(run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', str(output / 'audio.m4a')]))
            if not 0 < actual <= 601:
                raise InputError('Choose a video up to 10 minutes long.')
            track = {'id': track_id, 'youtubeId': job['youtube_id'], 'name': str(metadata.get('title') or 'YouTube video')[:200],
                     'category': str(metadata.get('uploader') or 'YouTube')[:100], 'duration': actual,
                     'url': f'/shared/imports/{track_id}.m4a', 'videoUrl': f'/shared/imports/{track_id}.mp4',
                     'presets': [{'label': 'First five seconds', 'start': 0, 'end': min(5, actual)}]}
            for source_name, extension in [('video.mp4', 'mp4'), ('audio.m4a', 'm4a')]:
                (output / source_name).replace(self.data / 'imports' / f'{track_id}.{extension}')
            with self.connect() as db:
                db.execute('INSERT OR IGNORE INTO tracks VALUES(?,?,?)', (track_id, job['youtube_id'], json.dumps(track)))
            self.job_update(job['id'], 'complete', 'Added to the shared library.', track_id)

    def source(self, track):
        url = track['url']
        if url.startswith('/media/'):
            return self.public / url.lstrip('/')
        if url.startswith('/shared/imports/'):
            return self.data / 'imports' / Path(url).name
        raise InputError('The source audio is unavailable.')

    def save_clip(self, payload, clip_id=None):
        if not isinstance(payload, dict):
            raise InputError('Provide a clip name and start and end times.')
        track = next((t for t in self.tracks() if t['id'] == payload.get('trackId')), None)
        if not track:
            raise InputError('Choose a video from the library.')
        name, start, end = payload.get('name'), payload.get('start'), payload.get('end')
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
            raise InputError('Give the sound a name of up to 120 characters.')
        if any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) for n in (start, end)):
            raise InputError('Enter valid start and end times.')
        if not 0 <= start < end <= track['duration'] + .05 or not .02 <= end - start <= 300:
            raise InputError('The cut must be within the video and between 0.02 seconds and 5 minutes long.')
        if not self.clip_lock.acquire(blocking=False):
            raise InputError('Another sound is being saved. Try again in a moment.')
        clip_id = clip_id or uuid.uuid4().hex
        target = self.data / 'clips' / f'{clip_id}.mp3'
        try:
            with self.connect() as db:
                if db.execute('SELECT count(*) FROM clips WHERE removed=0').fetchone()[0] >= 250:
                    raise InputError('The soundboard has reached its 250-sound limit.')
            with tempfile.TemporaryDirectory(dir=self.data / 'work') as work:
                temp = Path(work) / 'clip.mp3'
                run(['ffmpeg', '-v', 'error', '-y', '-i', str(self.source(track)), '-ss', str(start), '-t', str(end-start),
                     '-vn', '-c:a', 'libmp3lame', '-b:a', '320k', '-ar', '44100', str(temp)], timeout=60)
                temp.replace(target)
            clip = {'id': clip_id, 'trackId': track['id'], 'name': name.strip(), 'start': start, 'end': end,
                    'duration': end-start, 'sourceName': track['name'], 'url': f'/shared/clips/{clip_id}.mp3'}
            with self.connect() as db:
                db.execute('INSERT INTO clips(id,metadata) VALUES(?,?)', (clip_id, json.dumps(clip)))
            return clip
        finally:
            self.clip_lock.release()

    def remove_clip(self, clip_id, restore=False):
        with self.connect() as db:
            result = db.execute('UPDATE clips SET removed=? WHERE id=?', (0 if restore else 1, clip_id))
            if not result.rowcount:
                raise InputError('This sound is no longer available.')
        return {'ok': True}

    def seed_board(self):
        for track in self.tracks():
            if track['id'].startswith('yt-'):
                continue
            for index, preset in enumerate(track.get('presets', [])):
                clip_id = f"original-{track['id']}-{index}"
                with self.connect() as db:
                    if db.execute('SELECT 1 FROM clips WHERE id=?', (clip_id,)).fetchone():
                        continue
                name = track['name'] if len(track['presets']) == 1 else preset['label']
                self.save_clip({'trackId': track['id'], 'name': name, 'start': preset['start'], 'end': preset['end']}, clip_id)
