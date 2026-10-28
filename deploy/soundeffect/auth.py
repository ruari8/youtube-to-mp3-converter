#!/usr/bin/env python3
"""Password-only login and signed sessions behind Nginx auth_request."""
import hashlib
import hmac
import json
import os
import secrets
import time
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

COOKIE = '__Host-soundcut'
SESSION_SECONDS = 7 * 24 * 60 * 60
ORIGIN = 'https://soundeffect.ruari.dev'


def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()


def session_token(secret, now=None):
    expiry = int(time.time() if now is None else now) + SESSION_SECONDS
    payload = f'{expiry}.{secrets.token_hex(16)}'
    return payload + '.' + hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()


def valid_session(cookie_header, secret, now=None):
    try:
        cookies = SimpleCookie()
        cookies.load(cookie_header or '')
        value = cookies[COOKIE].value
        expiry, nonce, signature = value.split('.')
        expected = hmac.new(secret, f'{expiry}.{nonce}'.encode(), hashlib.sha256).hexdigest()
        return int(expiry) > (time.time() if now is None else now) and hmac.compare_digest(signature, expected)
    except (CookieError, KeyError, ValueError, TypeError):
        return False


def login_page(message=''):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sound cut · Sign in</title>
<style>*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#f7f6f2;color:#23332e;font:15px/1.6 system-ui,sans-serif;padding:24px}}main{{width:100%;max-width:430px;background:#fff;border:1px solid #e0e3da;border-radius:16px;padding:40px}}.brand{{font-size:27px;font-weight:750;letter-spacing:-1px}}.brand span{{color:#dc541e}}h1{{font:40px/1.1 Georgia,serif;letter-spacing:-1px;margin:32px 0 16px}}p{{color:#747a72;font-size:14px}}label{{display:block;font-size:12px;margin:24px 0 8px}}input{{width:100%;padding:14px;font:16px system-ui;border:1px solid #d8ded3;border-radius:7px}}button{{margin-top:18px;width:100%;padding:14px;background:#dc541e;color:white;border:0;border-radius:7px;font:600 14px system-ui;cursor:pointer}}input:focus-visible,button:focus-visible{{outline:3px solid #edb185;outline-offset:3px}}.error{{color:#aa331f;min-height:23px;font-size:12px}}small{{display:block;margin-top:24px;color:#8b9385;font-size:11px}}</style></head>
<body><main><div class="brand">sound cut<span>.</span></div><h1>Your sounds.<br>Your cut.</h1><p>Your video library and shared soundboard.<br>Enter the shared password to get started.</p><form method="post" action="/login"><label for="password">PASSWORD</label><input id="password" name="password" type="password" autocomplete="current-password" autofocus required maxlength="200"><button type="submit">Open the sound library →</button><p class="error" role="alert">{message}</p></form><small>Watch the video. Find the moment. Download your MP3.</small></main></body></html>'''.encode()


class Handler(BaseHTTPRequestHandler):
    config = None
    library = None

    def api(self):
        if not valid_session(self.headers.get('Cookie'), bytes.fromhex(self.config['session_key'])):
            self.json_response(401, {'error': 'Please sign in again.'})
            return
        if self.command not in ('GET', 'HEAD') and self.headers.get('Origin') not in (ORIGIN, ORIGIN + ':443'):
            self.json_response(403, {'error': 'Reload the page and try again.'})
            return
        from library import InputError
        try:
            path = self.path.split('?')[0]
            if self.command in ('GET', 'HEAD'):
                if path == '/api/library':
                    result = self.library.tracks()
                elif path == '/api/board':
                    result = self.library.board()
                elif path == '/api/imports':
                    result = self.library.jobs()
                elif path == '/api/connection':
                    result = self.library.connection()
                else:
                    self.json_response(404, {'error': 'Not found.'})
                    return
            elif self.command == 'POST' and path in ('/api/imports', '/api/board'):
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 4096:
                    raise InputError('The request is too large or empty.')
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise InputError('Invalid request.')
                result = self.library.import_video(payload.get('url')) if path == '/api/imports' else self.library.save_clip(payload)
            elif self.command == 'DELETE' and path.startswith('/api/board/'):
                result = self.library.remove_clip(path.removeprefix('/api/board/'))
            elif self.command == 'POST' and path.startswith('/api/board/') and path.endswith('/restore'):
                result = self.library.remove_clip(path.removeprefix('/api/board/').removesuffix('/restore'), restore=True)
            else:
                self.json_response(404, {'error': 'Not found.'})
                return
            self.json_response(200, result)
        except (InputError, ValueError, UnicodeError):
            import sys
            self.json_response(400, {'error': str(sys.exception())})
        except Exception:
            self.json_response(500, {'error': 'Could not complete this request. Please try again.'})

    def json_response(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'private, no-store')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(data)

    def log_message(self, fmt, *args):
        return  # Never log passwords or cookies.

    def respond(self, code, body=b'', headers=None):
        self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'private, no-store')
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith('/api/'):
            self.api()
        elif self.path == '/auth/check':
            valid = valid_session(self.headers.get('Cookie'), bytes.fromhex(self.config['session_key']))
            self.respond(204 if valid else 401)
        elif self.path == '/login':
            self.respond(200, login_page())
        else:
            self.respond(404)

    do_HEAD = do_GET

    def do_POST(self):
        if self.path.startswith('/api/'):
            self.api()
            return
        if self.path != '/login':
            self.respond(404)
            return
        if self.headers.get('Origin') not in (ORIGIN, ORIGIN + ':443'):
            self.respond(403)
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 4096:
                self.respond(413)
                return
            form = parse_qs(self.rfile.read(size).decode('utf-8'), max_num_fields=4)
            password = form.get('password', [''])[0]
        except (ValueError, UnicodeError):
            self.respond(400)
            return
        actual = password_hash(password, self.config['salt'])
        if not hmac.compare_digest(actual, self.config['password_hash']):
            self.respond(401, login_page('That password did not match. Try again.'))
            return
        token = session_token(bytes.fromhex(self.config['session_key']))
        self.respond(303, headers={
            'Location': '/',
            'Set-Cookie': f'{COOKIE}={token}; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age={SESSION_SECONDS}',
        })

    def do_DELETE(self):
        if self.path.startswith('/api/'):
            self.api()
        else:
            self.respond(404)


def main():
    from library import Library
    Handler.config = json.loads(Path(os.environ.get('SOUNDCUT_AUTH_CONFIG', '/etc/soundeffect/auth.json')).read_text())
    root = Path(__file__).resolve().parent
    Handler.library = Library(os.environ.get('SOUNDCUT_DATA', '/home/deploy/apps/soundeffect/data'),
                              root / 'public', json.loads((root / 'library.json').read_text()))
    ThreadingHTTPServer(('127.0.0.1', 8018), Handler).serve_forever()


if __name__ == '__main__':
    main()
