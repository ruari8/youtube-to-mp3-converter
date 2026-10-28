#!/usr/bin/env python3
"""Build a self-contained offline HTML trimmer, with the saved full audio embedded."""
import base64
import json
import sys
from pathlib import Path
from urllib.parse import unquote
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audio_library import load_library


def build():
    downloads = ROOT / 'downloads'
    tracks = load_library(downloads)
    if not tracks:
        raise SystemExit('No saved sound pack found under downloads/stream-deck-sounds.')
    for track in tracks:
        track.pop('videoUrl', None)  # The small offline bundle remains audio-only.
        path = downloads / unquote(track.pop('url').removeprefix('/downloads/'))
        track['data'] = base64.b64encode(path.read_bytes()).decode('ascii')
    html = (ROOT / 'frontend/trimmer.html').read_text()
    assets = ROOT / 'frontend/assets/trimmer'
    html = html.replace('<link rel="stylesheet" href="/assets/trimmer/style.css">',
                        '<style>' + (assets / 'style.css').read_text() + '</style>')
    for name in ['vendor/lame.min.js', 'app.js']:
        html = html.replace(f'<script src="/assets/trimmer/{name}"></script>',
                            '<script>' + (assets / name).read_text().replace('</script', '<\\/script') + '</script>')
    library = json.dumps(tracks, separators=(',', ':')).replace('<', '\\u003c')
    html = html.replace('<script id="bundled-library" type="application/json">null</script>',
                        f'<script id="bundled-library" type="application/json">{library}</script>')
    output = downloads / 'sound-cut-share'
    output.mkdir(exist_ok=True)
    target = output / 'Sound Cut.html'
    target.write_text(html)
    readme = output / 'START HERE.txt'
    readme.write_text('SOUND CUT\n\n'
                      '1. Extract this ZIP.\n'
                      '2. Open Sound Cut.html in Chrome, Edge, Firefox or Safari on a computer.\n'
                      '3. Pick a track. All nine full-length audios are included.\n'
                      '4. Drag IN and OUT, or type start and end times in seconds.\n'
                      '5. Play the cut, then click Download cut to save an MP3 or WAV.\n\n'
                      'No installation, internet connection or server is needed.\n'
                      'Add audio files also works with your own MP3, WAV and M4A files.\n'
                      'Use Fit cut to zoom around the selection; use the overview to move around.\n'
                      'Original cut presets are provided, including both Farage versions.\n'
                      'Selections are remembered when browser storage is available.\n'
                      'Download each finished cut before closing the page.\n\n'
                      'MP3 encoder: unmodified lamejs 1.2.1, https://github.com/zhuker/lamejs\n'
                      'LAME: https://lame.sourceforge.net/ (LGPL). See included encoder source and license.\n')
    archive = downloads / 'Sound-Cut-share.zip'
    with ZipFile(archive, 'w', compression=ZIP_DEFLATED, compresslevel=6) as zipped:
        zipped.write(target, target.name)
        zipped.write(readme, readme.name)
        zipped.write(assets / 'vendor/LICENSE', 'encoder/LICENSE')
        zipped.write(assets / 'vendor/lame.min.js', 'encoder/lame.min.js')
    with ZipFile(archive) as zipped:
        assert zipped.testzip() is None
    print(f'{len(tracks)} full tracks embedded')
    print(f'Open: {target}')
    print(f'Share: {archive} ({archive.stat().st_size / 1048576:.1f} MB)')


if __name__ == '__main__':
    build()
