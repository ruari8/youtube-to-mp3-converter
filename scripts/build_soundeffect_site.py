#!/usr/bin/env python3
"""Build the fixed MP4 library for the password-protected VPS site."""
import json
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audio_library import load_library


def build():
    output = ROOT / 'downloads/soundeffect-site'
    public = output / 'public'
    media = public / 'media'
    media.mkdir(parents=True, exist_ok=True)
    tracks = load_library(ROOT / 'downloads')
    if len(tracks) != 9 or not all(track.get('videoUrl') for track in tracks):
        raise SystemExit('All nine original MP4 videos are required.')
    for track in tracks:
        source = ROOT / unquote(track['videoUrl'].lstrip('/'))
        video = media / (track['id'] + '.mp4')
        audio = media / (track['id'] + '.m4a')
        if not video.exists() or video.stat().st_mtime < source.stat().st_mtime:
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(source), '-map', '0:v:0', '-map', '0:a:0',
                            '-c', 'copy', '-movflags', '+faststart', str(video)], check=True)
        if not audio.exists() or audio.stat().st_mtime < source.stat().st_mtime:
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(source), '-map', '0:a:0', '-vn',
                            '-c:a', 'copy', '-movflags', '+faststart', str(audio)], check=True)
        track['videoUrl'] = '/media/' + video.name
        track['url'] = '/media/' + audio.name
        print(f'Prepared {track["name"]}', flush=True)
    shutil.copytree(ROOT / 'frontend/assets/trimmer', public / 'assets/trimmer', dirs_exist_ok=True)
    html = (ROOT / 'frontend/trimmer.html').read_text()
    html = html.replace('<html lang="en">', '<html lang="en" data-library="fixed" data-shared="true">')
    html = html.replace('Runs on your computer', 'Private sound library')
    html = html.replace('Full tracks. Any cut you like.', 'Full videos. Any cut you like.')
    html = html.replace('No uploads. No account. Just your sounds.', 'Full videos in. Your own MP3 cuts out.')
    html = html.replace('<option value="wav">WAV · lossless PCM</option>', '')
    html = html.replace('↓ Download cut', '↓ Download MP3')
    html = html.replace('Choose a full track,', 'Choose a video,')
    html = html.replace(' Added files must be selected again after reopening.', '')
    html = html.replace(' WAV exports preserve the decoded audio without further lossy compression.', '')
    html = html.replace('<script id="bundled-library" type="application/json">null</script>',
                        '<script id="bundled-library" type="application/json">' +
                        json.dumps(tracks).replace('<', '\\u003c') + '</script>')
    (public / 'index.html').write_text(html)
    (output / 'library.json').write_text(json.dumps(tracks, indent=2) + '\n')
    print(f'Site ready: {public}')


if __name__ == '__main__':
    build()
