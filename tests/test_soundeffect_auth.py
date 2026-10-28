import http.client
import importlib.util
import json
from pathlib import Path
import threading
import unittest
from urllib.parse import urlencode

spec = importlib.util.spec_from_file_location('soundeffect_auth', Path(__file__).resolve().parents[1] / 'deploy/soundeffect/auth.py')
auth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth)


class AuthTests(unittest.TestCase):
    def test_signed_session_expiry_and_tampering(self):
        key = b'x' * 32
        token = auth.session_token(key, now=100)
        cookie = f'{auth.COOKIE}={token}'
        self.assertTrue(auth.valid_session(cookie, key, now=101))
        self.assertFalse(auth.valid_session(cookie, key, now=100 + auth.SESSION_SECONDS))
        self.assertFalse(auth.valid_session(cookie + '0', key, now=101))
        self.assertFalse(auth.valid_session(cookie, b'y' * 32, now=101))
        self.assertFalse(auth.valid_session('', key))
        self.assertFalse(auth.valid_session(f'{auth.COOKIE}=bad.value', key))

    def test_login_and_auth_request(self):
        salt = 'ab' * 16
        auth.Handler.config = {'salt': salt, 'password_hash': auth.password_hash('test-password', salt), 'session_key': 'cd' * 32}
        server = auth.ThreadingHTTPServer(('127.0.0.1', 0), auth.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            def request(method, path, body=None, headers=None):
                client = http.client.HTTPConnection(*server.server_address, timeout=5)
                client.request(method, path, body=body, headers=headers or {})
                response = client.getresponse()
                result = (response.status, dict(response.getheaders()), response.read())
                client.close()
                return result
            self.assertEqual(request('GET', '/auth/check')[0], 401)
            self.assertEqual(request('POST', '/login', urlencode({'password': 'test-password'}))[0], 403)
            self.assertEqual(request('POST', '/login', urlencode({'password': 'wrong'}), {'Origin': auth.ORIGIN})[0], 401)
            status, headers, _ = request('POST', '/login', urlencode({'password': 'test-password'}), {'Origin': auth.ORIGIN})
            self.assertEqual(status, 303)
            self.assertEqual(headers['Location'], '/')
            for attribute in ('Secure', 'HttpOnly', 'SameSite=Strict', 'Path=/'):
                self.assertIn(attribute, headers['Set-Cookie'])
            cookie = headers['Set-Cookie'].split(';')[0]
            self.assertEqual(request('GET', '/auth/check', headers={'Cookie': cookie})[0], 204)
            self.assertEqual(request('GET', '/auth/check', headers={'Cookie': cookie + 'bad'})[0], 401)
            self.assertEqual(request('GET', '/unknown')[0], 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
