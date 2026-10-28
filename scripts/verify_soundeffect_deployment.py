#!/usr/bin/env python3
"""Check the real HTTPS login, protected files and byte-range video delivery."""
import email
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://soundeffect.ruari.dev'


def request(cookie_file, path, data=None, headers=None):
    # Use curl, the same HTTP client used for deployment diagnostics. Cloudflare
    # rejects Python urllib's default client signature on this existing zone.
    with tempfile.TemporaryDirectory() as directory:
        head, body = Path(directory) / 'headers', Path(directory) / 'body'
        command = ['curl', '-sS', '--max-time', '30', '--cookie', str(cookie_file),
                   '--cookie-jar', str(cookie_file), '--dump-header', str(head),
                   '--output', str(body), '--write-out', '%{http_code}']
        for key, value in (headers or {}).items():
            command += ['--header', f'{key}: {value}']
        if data is not None:
            command += ['--data-binary', '@-']
        command.append(ORIGIN + path)
        result = subprocess.run(command, input=data, capture_output=True, check=True)
        blocks = [block for block in head.read_bytes().split(b'\r\n\r\n') if block.startswith(b'HTTP/')]
        response_headers = email.message_from_bytes(blocks[-1].split(b'\r\n', 1)[1])
        return int(result.stdout), response_headers, body.read_bytes()


def verify(directory):
    password = os.environ['SOUNDCUT_PASSWORD']
    anonymous = Path(directory) / 'anonymous-cookies'
    status, headers, _ = request(anonymous, '/')
    assert status == 302 and headers['Location'].endswith('/login')
    assert request(anonymous, '/login', b'password=incorrect', {'Origin': ORIGIN})[0] == 401
    client = Path(directory) / 'session-cookies'
    status, headers, _ = request(client, '/login', urllib.parse.urlencode({'password': password}).encode(), {'Origin': ORIGIN})
    assert status == 303, status
    assert all(s in headers['Set-Cookie'] for s in ('Secure', 'HttpOnly', 'SameSite=Strict'))
    status, headers, html = request(client, '/')
    assert status == 200
    html = html.decode()
    assert password not in html
    library = json.loads(re.search(r'<script id="bundled-library" type="application/json">(.*?)</script>', html, re.S)[1])
    assert len(library) == 9
    results = []
    for track in library:
        for field in ('videoUrl', 'url'):
            path = track[field]
            status, headers, data = request(client, path, headers={'Range': 'bytes=0-1023'})
            assert status == 206 and len(data) == 1024, (path, status)
            local = ROOT / 'downloads/soundeffect-site/public' / path.lstrip('/')
            assert headers['Content-Range'] == f'bytes 0-1023/{local.stat().st_size}'
            assert data == local.read_bytes()[:1024]
            # Cloudflare applies the zone's browser TTL to MP4s while retaining
            # private caching. Verify no shared-cache delivery or anonymous access.
            assert 'private' in headers['Cache-Control']
            assert headers.get('CF-Cache-Status') in ('BYPASS', 'DYNAMIC')
            assert request(anonymous, path, headers={'Range': 'bytes=0-1023'})[0] == 302
        results.append({'name': track['name'], 'video_range': 'passed', 'audio_range': 'passed', 'anonymous_access': 'blocked'})
    assert request(client, '/auth.py')[0] == 404
    assert request(client, '/api/convert')[0] == 404
    for path in ('/api/library', '/api/board', '/api/imports', '/api/connection'):
        assert request(anonymous, path)[0] == 401
    status, _, body = request(client, '/api/board')
    assert status == 200
    board = json.loads(body)
    assert len(board) >= 10
    for clip in board:
        status, headers, data = request(client, clip['url'], headers={'Range':'bytes=0-1023'})
        assert status == 206 and len(data) == 1024
        assert request(anonymous, clip['url'])[0] == 302
    assert request(client, '/api/board', b'{}', {'Content-Type':'application/json'})[0] == 403
    status, _, body = request(client, '/api/library')
    assert status == 200
    shared_tracks = json.loads(body)
    for track in shared_tracks:
        if not track['url'].startswith('/shared/'):
            continue
        for field in ('url','videoUrl'):
            assert request(client, track[field], headers={'Range':'bytes=0-1023'})[0] == 206
            assert request(anonymous, track[field])[0] == 302
    report = {'url': ORIGIN, 'https_login': 'passed', 'wrong_password': 'rejected', 'secure_cookie': True,
              'library_size': len(shared_tracks), 'soundboard_clips':len(board),
              'shared_api_and_media_auth':'passed', 'mutation_origin_check':'passed', 'tracks': results}
    (ROOT / 'downloads/soundeffect-deployment-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as directory:
        verify(directory)
