#!/usr/bin/env python3
"""Verify the portable pack and optional real exports made through the UI.

Example after exporting the documented test cuts:
python3 scripts/verify_trimmer.py --mp3 /path/proud-to-be-an-american_44.00-51.50.mp3 \
    --wav /path/boring-boring-boring_0.00-6.50.wav
"""
import argparse
import array
import base64
import hashlib
import json
import math
import subprocess
import sys
import wave
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audio_library import load_library


class EmbeddedPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.library = ''
        self.in_library = False
        self.external_resources = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script':
            self.in_library = attrs.get('id') == 'bundled-library'
        if tag in ('script', 'img', 'iframe', 'link') and (attrs.get('src') or attrs.get('href')):
            self.external_resources.append(attrs)

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_library = False

    def handle_data(self, data):
        if self.in_library:
            self.library += data


def probe(path):
    result = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)]))
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(path), '-f', 'null', '-'], check=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mp3', type=Path, help='UI export of Proud to be an American, 44–51.5 seconds')
    parser.add_argument('--wav', type=Path, help='UI WAV export of Farage, 0–6.5 seconds')
    args = parser.parse_args()
    downloads = ROOT / 'downloads'
    page = EmbeddedPage()
    page.feed((downloads / 'sound-cut-share/Sound Cut.html').read_text())
    assert not page.external_resources, page.external_resources
    embedded = json.loads(page.library)
    sources = load_library(downloads)
    assert len(embedded) == len(sources) == 9
    assert sum(len(track['presets']) for track in embedded) == 10
    for track, source in zip(embedded, sources):
        data = base64.b64decode(track['data'], validate=True)
        path = downloads / unquote(source['url'].removeprefix('/downloads/'))
        assert hashlib.sha256(data).digest() == hashlib.sha256(path.read_bytes()).digest(), track['name']
    with ZipFile(downloads / 'Sound-Cut-share.zip') as archive:
        assert archive.testzip() is None
        assert archive.read('Sound Cut.html') == (downloads / 'sound-cut-share/Sound Cut.html').read_bytes()
    report = {'embedded_full_tracks': len(embedded), 'original_presets': 10, 'all_audio_bytes_match': True,
              'external_page_resources': 0, 'zip_integrity': 'passed',
              'browser_file_url_test': 'Unavailable: preview browser blocks file URLs.'}
    if args.mp3:
        info = probe(args.mp3)
        duration = float(info['format']['duration'])
        assert info['streams'][0]['codec_name'] == 'mp3'
        assert abs(duration - 7.5) < .1, duration
        report['ui_mp3_export_seconds'] = duration
    if args.wav:
        info = probe(args.wav)
        with wave.open(str(args.wav)) as source:
            assert source.getframerate() == 44100 and source.getnchannels() == 2
            assert source.getnframes() == 286650
            actual = array.array('h', source.readframes(source.getnframes()))
        expected = array.array('h', subprocess.check_output([
            'ffmpeg', '-v', 'error', '-i', str(downloads / 'stream-deck-sounds/full-audio/05-nigel-farage-boring.mp3'),
            '-t', '6.5', '-f', 's16le', '-ar', '44100', '-ac', '2', '-']))
        assert len(actual) == len(expected)
        rms = math.sqrt(sum((a-b)**2 for a, b in zip(actual, expected)) / len(actual))
        assert rms < 2, f'Export differs from the source cut: {rms}'
        report['ui_wav_export_seconds'] = float(info['format']['duration'])
        report['wav_rms_difference_in_16bit_units'] = rms
    (downloads / 'trimmer-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
